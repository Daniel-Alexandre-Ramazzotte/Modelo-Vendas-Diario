# -*- coding: utf-8 -*-
"""
Projecao diaria de VALOR e QUANTIDADE na AWS -- modelos SARIMA com intervencoes.

Substitui a antiga rotina AWS que carregava um .pkl fixo do TPOT (etl_pipeline /
model_construct / ml_pipeline) pelos DOIS modelos finais do notebook
`notebooks/experimentos/experimento_sarimax.ipynb`:

    - VALOR : SARIMA(order, seas) + regressores de intervencao selecionados
    - QTD   : SARIMA(order, seas) + regressores de intervencao selecionados

Diferente do TPOT (modelo fixo que preve a partir de lags), o SARIMA e RE-AJUSTADO
a cada execucao na janela recente da serie diaria e faz a previsao 1-passo-a-frente
para o proximo dia util. As "intervencoes selecionadas" (dias de Log_Erro e vesperas
de Natal/Ano Novo/Carnaval) sao materializadas como regressores exogenos e limpam o
efeito desses choques do ajuste -- exatamente como no notebook.

------------------------------------------------------------------------------------
CONFIG CONGELADA (order/seas + funcao vencedora por evento)
------------------------------------------------------------------------------------
A selecao pesada (funcoes de transferencia Box-Tiao via grid de AIC) roda UMA vez no
notebook; aqui apenas relemos a decisao de um JSON e re-ajustamos o SARIMA. Gere o
JSON no notebook (com VPN/ClickHouse) apos rodar as Secoes 3/4:

    from scripts.producao.aws_projecao_sarima import montar_config_json
    montar_config_json(
        {'valor': (order_v, seas_v, specs_sarima_v, eventos_v),
         'qntd':  (order_q, seas_q, specs_sarima_q, eventos_q)},
        'config/modelo_sarima_producao.json')

------------------------------------------------------------------------------------
COMO INCLUIR NOVAS INTERVENCOES (3 caminhos, sem tocar no codigo)
------------------------------------------------------------------------------------
1) NOVO Log_Erro / NOVA vespera: basta a nova linha existir em `logs/Log_Erro.xlsx`
   (ou o calendario avancar). O evento e detectado automaticamente e modelado com a
   funcao padrao do seu TIPO (`func_por_tipo`). Nada a editar.

2) FIXAR uma funcao especifica para um evento conhecido: adicione o rotulo do evento
   em `overrides` (ex.: {"OPA (2026-03-10)": {"func": "e", "delta": 0.6}}).

3) INTERVENCAO AVULSA (nao vem do Log_Erro nem do calendario -- ex.: campanha, feirao):
   adicione uma entrada em `eventos_extra` com as datas e a funcao desejada.

Ordem de precedencia por evento: overrides > func_por_tipo > 'abrupto' (fallback).

------------------------------------------------------------------------------------
Dependencias: pandas, numpy, statsmodels, workadays, openpyxl (+ pyspark no job AWS).
"""

import os
import json
import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta

from statsmodels.tsa.statespace.sarimax import SARIMAX
from workadays import workdays as wd


# ==================================================================================
# CONFIG PADRAO (usada quando o JSON nao traz o campo). Os defaults por TIPO abaixo
# refletem a leitura comum do notebook: dia de erro tende a deslocar o nivel (degrau,
# funcao 'c') e a vespera e um pulso pontual ('abrupto'). Ajuste no JSON a vontade.
# ==================================================================================
CONFIG_PADRAO = {
    'hist_dias': 540,
    'log_erro_path': os.path.join('logs', 'Log_Erro.xlsx'),
    'valor': {
        'order': None, 'seasonal_order': None,      # OBRIGATORIO vir do JSON (congelado)
        'func_por_tipo': {'log_erro': {'func': 'c', 'delta': None},
                          'vespera':  {'func': 'abrupto', 'delta': None}},
        'overrides': {},
        'eventos_extra': [],
    },
    'qntd': {
        'order': None, 'seasonal_order': None,
        'func_por_tipo': {'log_erro': {'func': 'c', 'delta': None},
                          'vespera':  {'func': 'abrupto', 'delta': None}},
        'overrides': {},
        'eventos_extra': [],
    },
}

CONFIG_PATH_PADRAO = os.path.join('config', 'modelo_sarima_producao.json')


def carregar_config(path=CONFIG_PATH_PADRAO):
    """Le o JSON congelado e mescla sobre CONFIG_PADRAO (campos ausentes usam o padrao)."""
    cfg = json.loads(json.dumps(CONFIG_PADRAO))   # deep copy
    if path and os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            user = json.load(f)
        for k, v in user.items():
            if isinstance(v, dict) and isinstance(cfg.get(k), dict):
                cfg[k].update(v)
            else:
                cfg[k] = v
        print(f'[config] carregada de {path}')
    else:
        print(f'[config] AVISO: {path} inexistente -- usando CONFIG_PADRAO '
              f'(order/seas precisam vir do JSON; sem eles cai no fallback auto_arima)')
    return cfg


# ==================================================================================
# 1) DIAS ESPECIAIS (portado de experimento_sarimax, cell de CONFIGURACAO)
# ==================================================================================
def _eh_util(d):
    d = pd.Timestamp(d).normalize()
    return d.weekday() < 5 and not wd.is_holiday(d.date(), country='BR')


def _bdays_from(start, n):
    """Primeiros n dias UTEIS (seg-sex, exclui feriado BR) a partir de `start` (inclusive)."""
    out, d = [], pd.Timestamp(start).normalize()
    while len(out) < n:
        if _eh_util(d):
            out.append(d)
        d += pd.Timedelta(days=1)
    return out


def _bday_anterior(d):
    """Dia UTIL imediatamente ANTERIOR a d."""
    d = pd.Timestamp(d).normalize() - pd.Timedelta(days=1)
    while not _eh_util(d):
        d -= pd.Timedelta(days=1)
    return d.normalize()


def proximo_dia_util(d):
    """Proximo dia UTIL apos d (o alvo da previsao 1-passo)."""
    d = pd.Timestamp(d).normalize() + pd.Timedelta(days=1)
    while not _eh_util(d):
        d += pd.Timedelta(days=1)
    return d.normalize()


def _pascoa(ano):
    a = ano % 19; b = ano // 100; c = ano % 100; d = b // 4; e = b % 4
    f = (b + 8) // 25; g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30; i = c // 4; k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7; m = (a + 11 * h + 22 * l) // 451
    mes = (h + l - 7 * m + 114) // 31; dia = ((h + l - 7 * m + 114) % 31) + 1
    return pd.Timestamp(ano, mes, dia)


def _vespera_carnaval(ano):
    """Ultimo dia UTIL antes da segunda de Carnaval (Pascoa - 48 dias)."""
    d = _pascoa(ano) - pd.Timedelta(days=48) - pd.Timedelta(days=1)
    while not _eh_util(d):
        d -= pd.Timedelta(days=1)
    return d.normalize()


DIAS_VESPERA_CARNAVAL = {_vespera_carnaval(y) for y in range(2020, 2036)}


def _tipo_vespera(d):
    """'natal'/'ano_novo'/'carnaval' se d for vespera relevante; None senao (mesmo escopo dos _vies)."""
    dn = pd.Timestamp(d).normalize()
    if dn.month == 12 and dn.day == 24:
        return 'natal'
    if dn.month == 12 and dn.day == 31:
        return 'ano_novo'
    if dn in DIAS_VESPERA_CARNAVAL:
        return 'carnaval'
    return None


# ==================================================================================
# 2) EVENTOS DE INTERVENCAO (portado de montar_eventos + eventos_extra do config)
# ==================================================================================
def montar_eventos(index, log_erro_path, eventos_extra=None):
    """Eventos de intervencao restritos ao periodo de `index` (DatetimeIndex de dias uteis):
       - Log_Erro (1 por linha, janela de dias uteis de impacto);
       - Vesperas Natal/Ano Novo/Carnaval (1 por tipo) + dia util anterior a cada vespera;
       - eventos_extra do config (intervencoes avulsas definidas a mao).
    Espelha montar_eventos() do experimento_sarimax."""
    idx = pd.DatetimeIndex(index).normalize()
    eventos = []
    try:
        le = pd.read_excel(log_erro_path)
        le['Data'] = pd.to_datetime(le['Data'], errors='coerce').dt.normalize()
        le['Impacto/dias'] = pd.to_numeric(le['Impacto/dias'], errors='coerce').fillna(1).astype(int)
        for _, r in le.dropna(subset=['Data']).iterrows():
            n = max(int(r['Impacto/dias']), 1)
            dias = [d for d in _bdays_from(r['Data'], n) if d in idx]
            if dias:
                eventos.append({'tipo': 'log_erro',
                                'rotulo': f"{str(r['Sistema Erro']).strip()} ({r['Data'].date()})",
                                'datas': pd.DatetimeIndex(dias), 'inicio': min(dias),
                                'impacto_dias': n})
    except Exception as e:
        print(f'[eventos] Log_Erro indisponivel ({log_erro_path}): {e}')

    nomes_vespera = {'natal': 'Natal', 'ano_novo': 'Ano Novo', 'carnaval': 'Carnaval'}
    for tipo, nome in nomes_vespera.items():
        ves = sorted(d for d in idx if _tipo_vespera(d) == tipo)
        if ves:
            eventos.append({'tipo': 'vespera', 'rotulo': f'vespera {nome} (n={len(ves)})',
                            'datas': pd.DatetimeIndex(ves), 'inicio': min(ves), 'impacto_dias': 1})
        pre = sorted({_bday_anterior(d) for d in ves} & set(idx))
        if pre:
            eventos.append({'tipo': 'vespera',
                            'rotulo': f'dia anterior a vespera de {nome} (n={len(pre)})',
                            'datas': pd.DatetimeIndex(pre), 'inicio': min(pre), 'impacto_dias': 1})

    # Intervencoes avulsas (config) -- so as datas que caem no index atual
    for ex in (eventos_extra or []):
        datas = [pd.Timestamp(d).normalize() for d in ex['datas']]
        datas = [d for d in datas if d in idx]
        if not datas:
            continue
        eventos.append({'tipo': ex.get('tipo', 'custom'),
                        'rotulo': ex['rotulo'],
                        'datas': pd.DatetimeIndex(sorted(datas)),
                        'inicio': min(datas),
                        'impacto_dias': int(ex.get('impacto_dias', len(datas))),
                        '_spec_fixo': {'func': ex.get('func', 'abrupto'), 'delta': ex.get('delta')}})
    eventos.sort(key=lambda e: e['inicio'])
    return eventos


# ==================================================================================
# 3) REGRESSORES DE INTERVENCAO (portado das cells 12/13 do experimento_sarimax)
#    Classicos: abrupto/gradual/rebote | Transferencia Box-Tiao: b/c/d/e/f/g
# ==================================================================================
def _reg_abrupto(index, ev):
    s = pd.Series(0.0, index=pd.DatetimeIndex(index))
    s.loc[s.index.isin(ev['datas'])] = 1.0
    return s


def _reg_gradual(index, ev):
    index = pd.DatetimeIndex(index)
    datas = list(pd.DatetimeIndex(ev['datas']).sort_values())
    n = len(datas)
    s = pd.Series(0.0, index=index)
    if n == 0:
        return s
    for k, d in enumerate(datas):
        if d in s.index:
            s.loc[d] = (n - k) / n
    return s


def _reg_rebote(index, ev):
    index = pd.DatetimeIndex(index)
    datas = list(pd.DatetimeIndex(ev['datas']).sort_values())
    dia1 = pd.Series(0.0, index=index)
    pos = pd.Series(0.0, index=index)
    if datas and datas[0] in dia1.index:
        dia1.loc[datas[0]] = 1.0
    for d in datas[1:]:
        if d in pos.index:
            pos.loc[d] = 1.0
    return pd.DataFrame({'rebote_dia1': dia1, 'rebote_pos': pos})


def _filtro_ar1(ind, delta):
    """v_t = delta*v_(t-1) + ind_t (pulso que decai geometricamente do proprio dia; d/e/f/g)."""
    x = ind.to_numpy(dtype=float)
    v = np.zeros(len(x)); acc = 0.0
    for i in range(len(x)):
        acc = delta * acc + x[i]; v[i] = acc
    return pd.Series(v, index=ind.index)


def _filtro_delay_ar1(ind, delta):
    """d_t = delta*d_(t-1) + ind_(t-1) (pulso atrasado 1 dia; funcao b)."""
    x = ind.to_numpy(dtype=float)
    d = np.zeros(len(x)); acc = 0.0
    for i in range(len(x)):
        acc = delta * acc + (x[i - 1] if i > 0 else 0.0); d[i] = acc
    return pd.Series(d, index=ind.index)


def _filtro_degrau(ind):
    """s_t = s_(t-1) + ind_t (degrau permanente; funcao c)."""
    return ind.cumsum()


def _filtro_dupla(ind, delta):
    """Convergencia gradual e suave a novo nivel permanente (funcao f)."""
    return _filtro_ar1(ind, delta).cumsum()


def _reg_b(index, ev, delta): return _filtro_delay_ar1(_reg_abrupto(index, ev), delta)
def _reg_c(index, ev):        return _filtro_degrau(_reg_abrupto(index, ev))
def _reg_d(index, ev, delta):
    ind = _reg_abrupto(index, ev)
    return pd.DataFrame({'d_decai': _filtro_ar1(ind, delta), 'd_degrau': _filtro_degrau(ind)})
def _reg_e(index, ev, delta):
    ind = _reg_abrupto(index, ev)
    return pd.DataFrame({'e_pulso': ind, 'e_decai': _filtro_ar1(ind, delta)})
def _reg_f(index, ev, delta): return _filtro_dupla(_reg_abrupto(index, ev), delta)
def _reg_g(index, ev, delta): return _filtro_ar1(_reg_abrupto(index, ev), delta)


def _normaliza_spec(v):
    if isinstance(v, dict):
        return {'func': v.get('func', 'abrupto'), 'delta': v.get('delta')}
    return {'func': v, 'delta': None}


def _reg_por_spec(index, ev, spec):
    f = spec['func']; delta = spec.get('delta')
    if f in ('abrupto', 'a'): return _reg_abrupto(index, ev)
    if f == 'gradual':        return _reg_gradual(index, ev)
    if f == 'rebote':         return _reg_rebote(index, ev)
    if f == 'b':              return _reg_b(index, ev, delta)
    if f == 'c':              return _reg_c(index, ev)
    if f == 'd':              return _reg_d(index, ev, delta)
    if f == 'e':              return _reg_e(index, ev, delta)
    if f == 'f':              return _reg_f(index, ev, delta)
    if f == 'g':              return _reg_g(index, ev, delta)
    return None


def matriz_intervencao(index, eventos, classes):
    """Matriz exogena de intervencoes. `classes`: dict rotulo -> spec {'func','delta'}.
    Espelha matriz_intervencao() do experimento_sarimax (mesmos nomes de coluna)."""
    index = pd.DatetimeIndex(index)
    cols = {}
    for ev in eventos:
        spec = _normaliza_spec(classes.get(ev['rotulo'], 'abrupto'))
        if spec['func'] in ('nao signif.', None):
            continue
        reg = _reg_por_spec(index, ev, spec)
        if reg is None:
            continue
        d = spec.get('delta')
        tag = spec['func'] if d is None else f"{spec['func']}{int(round(d * 100)):02d}"
        if isinstance(reg, pd.DataFrame):
            for c in reg.columns:
                cols[f"{ev['tipo']}_{tag}_{c}_{ev['inicio']}"] = reg[c]
        else:
            cols[f"{ev['tipo']}_{tag}_{ev['inicio']}"] = reg
    return pd.DataFrame(cols, index=index).astype(float) if cols else pd.DataFrame(index=index)


def resolver_specs(eventos, cfg_target):
    """Funcao vencedora por evento: overrides > func_por_tipo > 'abrupto'.
    Eventos avulsos (eventos_extra) trazem `_spec_fixo` e ignoram a resolucao por tipo."""
    overrides = cfg_target.get('overrides', {}) or {}
    por_tipo = cfg_target.get('func_por_tipo', {}) or {}
    classes = {}
    for ev in eventos:
        if '_spec_fixo' in ev:
            classes[ev['rotulo']] = _normaliza_spec(ev['_spec_fixo'])
        elif ev['rotulo'] in overrides:
            classes[ev['rotulo']] = _normaliza_spec(overrides[ev['rotulo']])
        elif ev['tipo'] in por_tipo:
            classes[ev['rotulo']] = _normaliza_spec(por_tipo[ev['tipo']])
        else:
            classes[ev['rotulo']] = {'func': 'abrupto', 'delta': None}
    return classes


# ==================================================================================
# 4) ETL (Spark, igual ao ambiente AWS) -> frame diario (data, qntd, valor, fila)
# ==================================================================================
def etl_pipeline(spark, hist_dias=540):
    """Le ClickHouse via Spark e devolve um pandas DataFrame diario com colunas
    data/qntd/valor/fila (nao filtra dia util aqui -- isso e feito em montar_serie).

    - qntd/valor : etapa 16, propostadecisaoid nulo, ultimaalteracao nos ultimos hist_dias
    - fila       : etapa 15 (ultima etapa da proposta no dia) contada por dia
    """
    from pyspark.sql import functions as F

    # ---- Propostas (etapa 16) -> qtd e valor por dia ----
    ft = spark.table('clickhouse.crefaz.ft_proposta')
    ft = ft.filter(
        (F.col('propostaetapaid') == 16) &
        (F.col('propostadecisaoid').isNull()) &
        (F.col('ultimaalteracao').cast('date').between(
            F.date_sub(F.current_date(), int(hist_dias)),
            F.date_sub(F.current_date(), 1)))
    ).withColumn('data', F.to_date('ultimaalteracao'))
    ft = ft.groupBy('data').agg(
        F.count('propostaid').alias('qntd'),
        F.sum('valor').alias('valor'))

    # ---- Fila (etapa 15) -> quantidade na fila por dia ----
    hist = spark.table('clickhouse.crefazon15m.dbo_propostastatushistorico')
    hist = hist.filter(
        (F.col('data') >= F.date_sub(F.current_date(), int(hist_dias) + 10)) &
        (F.col('data') < F.current_date()))
    hist = hist.groupBy('propostaid', F.to_date('data').alias('data')).agg(
        F.max(F.struct('data', 'propostaetapaid')).alias('mx')
    ).select('data', 'propostaid', F.col('mx.propostaetapaid').alias('etapa'))
    fila = hist.filter(F.col('etapa') == 15).groupBy('data').agg(
        F.count('propostaid').alias('fila'))

    df = ft.join(fila, on='data', how='left').orderBy('data').toPandas()
    df['data'] = pd.to_datetime(df['data'])
    for c in ('qntd', 'valor', 'fila'):
        df[c] = pd.to_numeric(df[c], errors='coerce').astype(float)
    df = df.sort_values('data').reset_index(drop=True)
    print(f'[etl] {len(df)} dias | {df["data"].min().date()} -> {df["data"].max().date()}')
    return df


def montar_serie(df_diario, target):
    """Serie diaria util (seg-sex, sem feriado BR) do alvo, indexada por data.
    Espelha o recorte de dias uteis de montar_serie() do experimento_sarimax."""
    d = df_diario.copy()
    util = d['data'].apply(_eh_util)
    d = d[util].sort_values('data').reset_index(drop=True)
    s = d.set_index('data')[target].astype(float)
    return s.dropna()


# ==================================================================================
# 5) AJUSTE SARIMA + INTERVENCOES E PREVISAO 1-PASSO (proximo dia util)
# ==================================================================================
def prever_target(df_diario, target, cfg, order=None, seas=None):
    """Ajusta SARIMA(order, seas) + regressores de intervencao na serie recente e preve
    o proximo dia util. order/seas: se None, le do cfg[target]; se ainda None, cai no
    fallback auto_arima (requer pmdarima).

    Retorna dict com previsao, dia alvo, ordem usada e nomes dos regressores ativos.
    """
    cfg_t = cfg[target]
    order = order or (tuple(cfg_t['order']) if cfg_t.get('order') else None)
    seas = seas or (tuple(cfg_t['seasonal_order']) if cfg_t.get('seasonal_order') else None)

    serie = montar_serie(df_diario, target)
    if len(serie) < 30:
        raise RuntimeError(f'[{target}] serie curta demais ({len(serie)} dias uteis) para SARIMA')

    if order is None or seas is None:
        try:
            import pmdarima as pm
            print(f'[{target}] order/seas ausentes no config -- fallback auto_arima (congele depois no JSON)')
            m = pm.auto_arima(serie, seasonal=True, m=5, d=None, stepwise=True,
                              suppress_warnings=True, error_action='ignore',
                              max_p=3, max_q=3, max_P=2, max_Q=2, information_criterion='aic')
            order, seas = m.order, m.seasonal_order
        except Exception as e:
            raise RuntimeError(f'[{target}] sem order/seas no config e auto_arima indisponivel: {e}')

    # Index estendido: serie observada + o dia alvo (para materializar o regressor do alvo,
    # caso o proprio dia da previsao seja um dia especial -- Log_Erro/vespera).
    fc_day = proximo_dia_util(serie.index.max())
    idx_ext = serie.index.append(pd.DatetimeIndex([fc_day]))

    eventos = montar_eventos(idx_ext, cfg.get('log_erro_path', CONFIG_PADRAO['log_erro_path']),
                             cfg_t.get('eventos_extra'))
    classes = resolver_specs(eventos, cfg_t)
    X_full = matriz_intervencao(idx_ext, eventos, classes)

    exog_fit = exog_fc = None
    regressores = []
    if X_full.shape[1]:
        X_fit = X_full.loc[serie.index]
        # descarta colunas constantes no treino (evita matriz singular) -- igual walk_forward
        keep = X_fit.columns[(X_fit.std(ddof=0) > 0).values]
        if len(keep):
            exog_fit = X_fit[keep].astype(float)
            exog_fc = X_full.loc[[fc_day], keep].astype(float)
            regressores = list(keep)

    res = SARIMAX(serie, exog=exog_fit, order=order, seasonal_order=seas,
                  enforce_stationarity=False, enforce_invertibility=False).fit(disp=False)
    yhat = float(np.asarray(res.forecast(1, exog=exog_fc))[0])

    return {'target': target, 'dia_previsao': fc_day, 'previsao': yhat,
            'order': tuple(order), 'seasonal_order': tuple(seas),
            'n_serie': int(len(serie)), 'ultimo_dia': serie.index.max(),
            'regressores_ativos': regressores}


# ==================================================================================
# 6) ENTRYPOINT (equivalente ao main da rotina AWS)
# ==================================================================================
def executar(spark, config_path=CONFIG_PATH_PADRAO):
    """Roda ETL uma vez e preve VALOR e QTD para o proximo dia util."""
    cfg = carregar_config(config_path)
    df_diario = etl_pipeline(spark, hist_dias=int(cfg.get('hist_dias', 540)))

    saida = {}
    for target in ('valor', 'qntd'):
        r = prever_target(df_diario, target, cfg)
        saida[target] = r
        print(f'[{target}] SARIMA{r["order"]}x{r["seasonal_order"]} | '
              f'dia {r["dia_previsao"].date()} -> previsao={r["previsao"]:,.2f} | '
              f'regressores={len(r["regressores_ativos"])}')
    return saida


# ==================================================================================
# 7) EXPORTADOR DO CONFIG (rodar no notebook, apos as Secoes 3/4, com VPN)
# ==================================================================================
def montar_config_json(por_target, path=CONFIG_PATH_PADRAO, hist_dias=540,
                       log_erro_path=None):
    """Gera o JSON congelado a partir dos resultados do notebook.

    por_target: dict target -> (order, seas, specs, eventos), onde
        order/seas  = selecionar_ordem(serie)  (order_v/seas_v, order_q/seas_q)
        specs       = resultado['classes_sarima'] (dict rotulo -> {'func','delta'})
        eventos     = eventos_v / eventos_q     (para inferir o padrao por tipo)

    Grava, por target: order/seasonal_order + overrides (a funcao vencedora de CADA
    evento conhecido) + func_por_tipo (funcao mais comum por tipo, usada como padrao
    p/ eventos NOVOS). Depois voce pode editar overrides/eventos_extra a mao.
    """
    from collections import Counter
    cfg = {'hist_dias': int(hist_dias),
           'log_erro_path': log_erro_path or CONFIG_PADRAO['log_erro_path']}
    for target, (order, seas, specs, eventos) in por_target.items():
        tipo_por_rotulo = {ev['rotulo']: ev['tipo'] for ev in eventos}
        overrides, cont_por_tipo = {}, {}
        for rotulo, spec in specs.items():
            sp = _normaliza_spec(spec)
            overrides[rotulo] = {'func': sp['func'], 'delta': sp['delta']}
            tp = tipo_por_rotulo.get(rotulo)
            if tp and sp['func'] not in ('nao signif.', None):
                cont_por_tipo.setdefault(tp, Counter())[(sp['func'], sp['delta'])] += 1
        func_por_tipo = {}
        for tp, cnt in cont_por_tipo.items():
            (func, delta), _ = cnt.most_common(1)[0]
            func_por_tipo[tp] = {'func': func, 'delta': delta}
        func_por_tipo.setdefault('log_erro', {'func': 'c', 'delta': None})
        func_por_tipo.setdefault('vespera', {'func': 'abrupto', 'delta': None})
        cfg[target] = {
            'order': list(order), 'seasonal_order': list(seas),
            'func_por_tipo': func_por_tipo, 'overrides': overrides, 'eventos_extra': [],
        }
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    print(f'[config] gravado em {path}')
    return cfg


if __name__ == '__main__':
    # Execucao local exige uma SparkSession com o catalogo clickhouse configurado.
    try:
        from pyspark.sql import SparkSession
        spark = SparkSession.builder.getOrCreate()
        resultado = executar(spark)
        print('\nRESULTADO:', {k: round(v['previsao'], 2) for k, v in resultado.items()})
    except Exception as e:
        print('Falha ao executar via Spark local:', e)
        print('Rode dentro do ambiente AWS/Databricks com o catalogo clickhouse disponivel.')
