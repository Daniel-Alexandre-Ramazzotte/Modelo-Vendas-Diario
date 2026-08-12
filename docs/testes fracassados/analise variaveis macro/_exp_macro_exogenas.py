"""Teste isolado: variaveis macro (desemprego, salario minimo, comprometimento de renda
das familias, indice Big Mac) agregam ao SARIMAX mensal (baseline atual: total + n_uteis
exogeno, ver `wf_sarimax` em experimento_mensal.ipynb Secao 5) ou so adicionam ruido?

Roda FORA do notebook de proposito -- protocolo de decisao binaria (entra ou nao entra):
    1) baixa cada serie macro (cache em disco via cache_utils, resiliente a falta de VPN/rede)
    2) alinha cada serie ao mes-alvo respeitando a DEFASAGEM DE PUBLICACAO real (senao o
       teste vaza informacao do futuro e super-estima o ganho)
    3) roda o MESMO motor de walk-forward do nowcast mensal (expansivo, 1 passo, min 6
       meses de treino) com e sem cada exogena extra, no MESMO periodo avaliado
    4) reporta MAPE/RMSPE/Vies de cada candidato + teste de Diebold-Mariano contra o
       SARIMAX baseline (H0: mesma acuracia -- p < 0.05 = a diferenca e estatisticamente
       distinguivel de ruido) + Granger causality como triagem diagnostica (nao decide
       nada sozinho, so contextualiza)

Uso: python scripts/experimentos/_exp_macro_exogenas.py
Saida: prints no console + saidas/macro_exogenas_teste.xlsx (1 aba por target: valor/qntd,
       + aba 'resumo' com o veredito).
"""
import io
import json
import os
import pathlib
import sys
import urllib.request
import warnings

import numpy as np
import pandas as pd

# ==================== bootstrap: raiz do projeto ====================
_r = pathlib.Path(__file__).resolve()
while not (_r / 'CLAUDE.md').exists() and _r != _r.parent:
    _r = _r.parent
os.chdir(_r)
sys.path.insert(0, 'scripts')

from cache_utils import carregar_com_cache  # noqa: E402
from workadays import workdays as wd  # noqa: E402

import clickhouse_connect  # noqa: E402
import pmdarima as pm  # noqa: E402
from scipy import stats  # noqa: E402
from statsmodels.tsa.stattools import grangercausalitytests  # noqa: E402

warnings.filterwarnings('ignore')
pd.set_option('display.float_format', '{:.2f}'.format)

# ==================== CONFIG ====================
HOST, PORT = '10.101.150.150', 8123
USER, PASS = 'daniel_ramazzotte', 'O9pLTAv*yVz0lGP^#M'

TARGETS = ['valor', 'qntd']
MIN_TREINO_M = 6
COBERTURA_MIN = 0.80
DATA_INICIO_MENSAL = pd.Timestamp('2021-01-01')  # mesma decisao de 2021 do experimento_mensal

_PATH_SNAPSHOT_DIARIO = 'resultados/snapshot_query_mensal.xlsx'
_PATH_SAIDA = 'saidas/macro_exogenas_teste.xlsx'

# Series do BCB (SGS, https://api.bcb.gov.br) -- codigo + defasagem de publicacao (em MESES)
# a aplicar antes de usar como exogena: exog_no_mes[M] = valor_bruto[M - lag_publicacao].
# Isso evita vazamento -- o dado do mes de referencia M so fica disponivel na pratica
# `lag_publicacao` meses depois.
#   - desemprego (24369, Taxa de desocupacao - PNAD Continua/IBGE): trimestre movel,
#     divulgado com ~2 meses de atraso em relacao ao fechamento do periodo de referencia.
#   - salario_minimo (1619): definido por decreto/lei, CONHECIDO DE ANTEMAO (mesmo racional
#     de n_uteis) -- lag 0.
#   - comprometimento_renda (29034, Comprometimento de renda das familias com o servico da
#     divida): usado como PROXY de "taxa de endividamento" -- as series diretas de
#     endividamento das familias (SGS 19881/19882) foram DESCONTINUADAS em 2021-08 (checado
#     em 2026-07-28: ultimo ponto retornado e 2021-08), inuteis pro periodo avaliado aqui.
#     Publicada com ~3 meses de atraso (checado: mais recente disponivel = abr/2026 em jul/2026).
SERIES_BCB = {
    'desemprego':            {'codigo': 24369, 'lag_publicacao': 2},
    'salario_minimo':        {'codigo': 1619,  'lag_publicacao': 0},
    'comprometimento_renda': {'codigo': 29034, 'lag_publicacao': 3},
}

# Indice Big Mac (The Economist, dataset publico) -- semestral (jan/jul, as vezes irregular),
# preenchido pra mensal via ffill. Usa USD_raw (Brasil): % de sobre/subvalorizacao do BRL
# vs USD pela paridade do preco do Big Mac -- proxy (não-ortodoxo, testado por curiosidade/
# pedido explicito) de cambio/poder de compra. lag_publicacao=1 mes (divulgacao e proxima da
# data de referencia, mas fica 1 mes de folga conservador).
BIGMAC_URL = 'https://raw.githubusercontent.com/TheEconomist/big-mac-data/master/output-data/big-mac-full-index.csv'
BIGMAC_LAG_PUBLICACAO = 1


# ==================== dados diarios -> tab_mensal (mesma logica do experimento_mensal.ipynb,
# Secoes 1-4: query propostas etapa 16, agrega por mes, filtra cobertura) ====================
def n_dias_uteis_mes(ano, mes):
    _ini = pd.Timestamp(ano, mes, 1)
    _fim = _ini + pd.offsets.MonthEnd(0)
    _rng = pd.date_range(_ini, _fim, freq='D')
    return int(sum((x.weekday() < 5) and not wd.is_holiday(x.date(), country='BR') for x in _rng))


def carregar_tab_mensal():
    _mins = [DATA_INICIO_MENSAL]
    for _bp, _c in [('resultados/backup_valor.xlsx', 'Data previsao'),
                     ('resultados/backup_qtd.xlsx', 'Data previsao')]:
        try:
            _b = pd.read_excel(_bp)
            _d = pd.to_datetime(_b[_c], errors='coerce').dropna()
            if len(_d):
                _mins.append(_d.min())
        except Exception as _e:
            print('aviso ao ler backup', _bp, '->', _e)
    data_inicio_efetiva = min(_mins)

    query = f"""
    SELECT
        toStartOfFifteenMinutes(ultimaalteracao) AS Intervalo,
        SUM(valor) AS valor,
        COUNT(propostaid) AS qntd
    FROM crefaz.ft_proposta fp
    WHERE
        propostaetapaid = 16
        AND propostadecisaoid IS NULL
        AND toDate(ultimaalteracao) >= toDate('{data_inicio_efetiva.date()}')
        AND toDate(ultimaalteracao) < toDate(today())
    GROUP BY Intervalo
    """

    def _consultar():
        _cli = clickhouse_connect.get_client(host=HOST, port=PORT, username=USER, password=PASS)
        return _cli.query_df(query)

    try:
        df = carregar_com_cache('query_mensal', [pd.Timestamp.today().date(), data_inicio_efetiva, query], _consultar)
    except RuntimeError as _e:
        if os.path.exists(_PATH_SNAPSHOT_DIARIO):
            print(f'[fallback xlsx] {_e}')
            df = pd.read_excel(_PATH_SNAPSHOT_DIARIO)
        else:
            raise

    df['Intervalo'] = df['Intervalo'].astype(str)
    df['data'] = pd.to_datetime(pd.to_datetime(df['Intervalo'].str.split('+').str[0]).dt.date)

    df_diario = df.groupby('data', as_index=False).agg(valor=('valor', 'sum'), qntd=('qntd', 'sum'))

    _g = df_diario.copy()
    _g['ano'] = _g['data'].dt.year
    _g['mes'] = _g['data'].dt.month
    _agg = _g.groupby(['ano', 'mes']).agg(
        tot_valor=('valor', 'sum'), tot_qntd=('qntd', 'sum'),
        dias_com_dados=('data', 'nunique')).reset_index()
    _agg['n_uteis'] = _agg.apply(lambda r: n_dias_uteis_mes(int(r['ano']), int(r['mes'])), axis=1)
    _agg['cobertura'] = _agg['dias_com_dados'] / _agg['n_uteis']
    _agg['periodo'] = pd.to_datetime(dict(year=_agg['ano'], month=_agg['mes'], day=1))

    _mes_corrente = pd.Timestamp.today().normalize().replace(day=1)
    _completo = (_agg['cobertura'] >= COBERTURA_MIN) & (_agg['periodo'] < _mes_corrente)
    tab_mensal = _agg[_completo].sort_values('periodo').reset_index(drop=True)
    tab_mensal['media_valor'] = tab_mensal['tot_valor'] / tab_mensal['n_uteis']
    tab_mensal['media_qntd'] = tab_mensal['tot_qntd'] / tab_mensal['n_uteis']
    print(f'tab_mensal: {len(tab_mensal)} meses completos | '
          f'{tab_mensal["periodo"].min().date()} -> {tab_mensal["periodo"].max().date()}')
    return tab_mensal


def serie_mensal(target, tab_mensal):
    _col = 'tot_valor' if target == 'valor' else 'tot_qntd'
    s = tab_mensal.set_index('periodo')[_col].astype(float)
    s.index = pd.DatetimeIndex(s.index).to_period('M').to_timestamp()
    return s.asfreq('MS')


def montar_tabela(target, tab_mensal):
    """1 linha por mes, com 'periodo'/'n_uteis'/'tot'/lags -- so p/ ter as DATAS avaliadas
    (mesmas do baseline `wf_sarimax`/Naive) e o baseline Naive(1), nao usa lag como feature
    do SARIMAX (o SARIMAX so usa a serie + exogenas)."""
    _mcol = 'media_valor' if target == 'valor' else 'media_qntd'
    _tcol = 'tot_valor' if target == 'valor' else 'tot_qntd'
    t = tab_mensal.copy()
    t['media'] = t[_mcol].astype(float)
    t['tot'] = t[_tcol].astype(float)
    t['lag1_media'] = t['media'].shift(1)
    tab_sup = t.dropna(subset=['lag1_media', 'n_uteis']).reset_index(drop=True)
    return tab_sup


# ==================== macro exogenas ====================
def _fetch_bcb_json(codigo):
    url = f'https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados?formato=json'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=25) as r:
        dados = json.loads(r.read())
    return pd.DataFrame(dados)


def fetch_bcb_serie(nome, codigo, lag_publicacao):
    df = carregar_com_cache(f'macro_bcb_{nome}', [pd.Timestamp.today().date(), codigo],
                             lambda: _fetch_bcb_json(codigo))
    df = df.copy()
    df['data'] = pd.to_datetime(df['data'], format='%d/%m/%Y')
    df['valor'] = pd.to_numeric(df['valor'], errors='coerce')
    s = df.dropna(subset=['valor']).set_index('data')['valor'].sort_index()
    s.index = s.index.to_period('M').to_timestamp()
    s = s[~s.index.duplicated(keep='last')].asfreq('MS')
    # defasagem de publicacao: o valor referente ao mes M so "existe" pro forecast do mes
    # M + lag_publicacao em diante -> desloca o indice pra frente.
    s.index = s.index + pd.DateOffset(months=lag_publicacao)
    s.name = nome
    return s


def _fetch_bigmac_csv():
    req = urllib.request.Request(BIGMAC_URL, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=25) as r:
        texto = r.read().decode('utf-8')
    return pd.read_csv(io.StringIO(texto))


def fetch_bigmac_brasil():
    df = carregar_com_cache('macro_bigmac', [pd.Timestamp.today().date()], _fetch_bigmac_csv)
    _br = df[df['iso_a3'] == 'BRA'].copy()
    _br['date'] = pd.to_datetime(_br['date'])
    s = _br.set_index('date')['USD_raw'].sort_index()
    s.index = s.index.to_period('M').to_timestamp()
    s = s[~s.index.duplicated(keep='last')].asfreq('MS').ffill()  # semestral -> mensal (ultimo valor conhecido)
    s.index = s.index + pd.DateOffset(months=BIGMAC_LAG_PUBLICACAO)
    s.name = 'bigmac_usd_raw'
    return s


def montar_exog_macro():
    """Baixa as 4 series macro (3 BCB + Big Mac), ja defasadas pela publicacao. Series que
    falharem (rede/API fora) sao puladas com aviso -- o teste continua com o que conseguiu."""
    partes = []
    for nome, cfg in SERIES_BCB.items():
        try:
            partes.append(fetch_bcb_serie(nome, cfg['codigo'], cfg['lag_publicacao']))
        except Exception as e:
            print(f'[macro] falhou ao buscar {nome} (BCB {cfg["codigo"]}): {e}')
    try:
        partes.append(fetch_bigmac_brasil())
    except Exception as e:
        print(f'[macro] falhou ao buscar indice Big Mac: {e}')
    if not partes:
        raise RuntimeError('nenhuma serie macro disponivel -- confira rede/API')
    exog = pd.concat(partes, axis=1)
    print(f'Series macro carregadas: {list(exog.columns)} | {exog.index.min().date()} -> {exog.index.max().date()}')
    return exog


# ==================== walk-forward (mesmo motor do experimento_mensal.ipynb, Secao 5) ====
def wf_baseline_naive(tab_sup):
    rows = []
    for i in range(MIN_TREINO_M, len(tab_sup)):
        te = tab_sup.iloc[i]
        _prev = float(te['lag1_media']) * float(te['n_uteis'])
        rows.append({'periodo': te['periodo'], 'Previsto': _prev, 'Realizado': float(te['tot'])})
    return pd.DataFrame(rows)


def wf_sarimax_exog(serie_m, tab_sup, exog_full, colunas, min_treino=MIN_TREINO_M):
    """SARIMAX 1-passo (auto_arima) na serie mensal do TOTAL, com `colunas` de `exog_full`
    como exogenas (sempre inclui 'n_uteis' -- mesmo baseline do experimento_mensal.ipynb).
    Pula o fold se a exogena tiver NaN no treino ou no ponto futuro (fold nao avaliavel sem
    vazar/inventar dado)."""
    _datas = list(tab_sup['periodo'])
    _seas_on = len(serie_m.dropna()) >= 24
    rows = []
    for _dt in _datas[min_treino:]:
        _key = pd.Timestamp(_dt).to_period('M').to_timestamp()
        if _key not in serie_m.index or _key not in exog_full.index:
            continue
        _loc = serie_m.index.get_loc(_key)
        _ytr = serie_m.iloc[:_loc].dropna()
        if len(_ytr) < min_treino:
            continue
        _idx_validos = _ytr.index.intersection(exog_full.index)
        if len(_idx_validos) < len(_ytr):
            continue
        _exog_tr = exog_full.loc[_ytr.index, colunas]
        _exog_fut = exog_full.loc[[_key], colunas]
        if _exog_tr.isna().any().any() or _exog_fut.isna().any().any():
            continue
        try:
            _mod = pm.auto_arima(_ytr, X=_exog_tr, seasonal=_seas_on, m=12 if _seas_on else 1,
                                  stepwise=True, suppress_warnings=True, error_action='ignore',
                                  max_p=2, max_q=2, max_P=1, max_Q=1, max_d=1, max_D=1)
            _yhat = float(np.asarray(_mod.predict(1, X=_exog_fut))[0])
        except Exception:
            continue
        rows.append({'periodo': _dt, 'Previsto': _yhat, 'Realizado': float(serie_m.loc[_key])})
    return pd.DataFrame(rows)


def _rank_linha(det):
    det = det.dropna(subset=['Previsto', 'Realizado'])
    r = pd.to_numeric(det['Realizado'], errors='coerce').astype(float)
    p = pd.to_numeric(det['Previsto'], errors='coerce').astype(float)
    ape = (p - r).abs() / r.abs().replace(0, np.nan) * 100
    dif = r - p
    return {'MAPE Medio (%)': round(float(ape.mean()), 2),
            'RMSPE (%)': round(float(np.sqrt(np.mean(np.square(ape.dropna())))), 2),
            'Mediana (%)': round(float(ape.median()), 2),
            'Vies (real-prev)': round(float(dif.mean()), 1),
            'N': int(len(det))}


def diebold_mariano(det_a, det_b):
    """DM test (Diebold & Mariano, 1995), loss = erro^2, so no periodo EM COMUM aos dois
    candidatos (inner join por 'periodo'). H0: mesma acuracia preditiva. p<0.05 -> a
    diferenca de erro entre os dois e estatisticamente distinguivel de ruido amostral.
    Retorna (estatistica, p-valor, N usado) ou (nan, nan, N) se N pequeno demais."""
    _m = det_a.merge(det_b, on=['periodo', 'Realizado'], suffixes=('_a', '_b'))
    n = len(_m)
    if n < 8:
        return np.nan, np.nan, n
    _erro_a = _m['Realizado'] - _m['Previsto_a']
    _erro_b = _m['Realizado'] - _m['Previsto_b']
    d = _erro_a ** 2 - _erro_b ** 2
    d_bar = d.mean()
    d_var = d.var(ddof=1) / n
    if d_var <= 0:
        return np.nan, np.nan, n
    dm_stat = float(d_bar / np.sqrt(d_var))
    p_value = float(2 * (1 - stats.t.cdf(abs(dm_stat), df=n - 1)))
    return dm_stat, p_value, n


def granger_screen(serie_m, exog_full, max_lag=3):
    """Triagem diagnostica (NAO decide sozinha): Granger causality em 1a diferenca (serie
    de vendas x cada exogena), so como contexto -- N pequeno (~50-60 meses) entao o teste
    tem pouca potencia; um p-valor baixo aqui NAO confirma causalidade real, so sugere que
    vale a pena olhar o walk-forward com mais atencao (e vice-versa)."""
    print('\n[Granger causality -- triagem diagnostica, 1a diferenca, H0: exogena NAO ajuda a prever a serie]')
    _serie_diff = serie_m.diff().dropna()
    for col in exog_full.columns:
        _exog_diff = exog_full[col].diff().dropna()
        _df = pd.concat([_serie_diff, _exog_diff], axis=1, join='inner').dropna()
        _df.columns = ['y', 'x']
        if len(_df) < max_lag + 10:
            print(f'  {col}: N insuficiente ({len(_df)}) -- pulado')
            continue
        try:
            res = grangercausalitytests(_df[['y', 'x']], maxlag=max_lag, verbose=False)
            pvals = {lag: round(res[lag][0]['ssr_ftest'][1], 3) for lag in res}
            print(f'  {col}: p-valores por lag (meses) = {pvals}')
        except Exception as e:
            print(f'  {col}: falhou ({e})')


# ==================== orquestracao ====================
def rodar_teste(target, tab_mensal, exog_macro):
    print(f'\n{"=" * 70}\n{target.upper()}\n{"=" * 70}')
    tab_sup = montar_tabela(target, tab_mensal)
    serie_m = serie_mensal(target, tab_mensal)

    n_uteis = tab_mensal.set_index('periodo')[['n_uteis']].astype(float)
    n_uteis.index = pd.DatetimeIndex(n_uteis.index).to_period('M').to_timestamp()
    exog_full = n_uteis.join(exog_macro, how='left')

    granger_screen(serie_m, exog_macro.reindex(serie_m.index))

    candidatos = {
        'Naive (mes-1)': lambda: wf_baseline_naive(tab_sup),
        'SARIMAX (baseline: n_uteis)': lambda: wf_sarimax_exog(serie_m, tab_sup, exog_full, ['n_uteis']),
    }
    for col in exog_macro.columns:
        candidatos[f'SARIMAX + {col}'] = (
            lambda col=col: wf_sarimax_exog(serie_m, tab_sup, exog_full, ['n_uteis', col]))
    candidatos['SARIMAX + macro (todas)'] = (
        lambda: wf_sarimax_exog(serie_m, tab_sup, exog_full, ['n_uteis'] + list(exog_macro.columns)))

    det = {}
    for nome, fn in candidatos.items():
        print(f'  rodando: {nome} ...')
        _d = fn()
        if _d is not None and not _d.empty:
            det[nome] = _d
        else:
            print(f'    [aviso] {nome}: sem folds avaliaveis (exogena sem historico suficiente)')

    ranking = pd.DataFrame({k: _rank_linha(v) for k, v in det.items()}).T.sort_values('RMSPE (%)')
    ranking.index.name = 'Modelo'
    ranking = ranking.reset_index()
    print(f'\nRanking ({target}), cada candidato no SEU periodo avaliado (N pode variar):')
    print(ranking.to_string(index=False))

    baseline = det.get('SARIMAX (baseline: n_uteis)')
    dm_rows = []
    if baseline is not None:
        for nome, d in det.items():
            if nome == 'SARIMAX (baseline: n_uteis)':
                continue
            stat, pval, n = diebold_mariano(d, baseline)
            dm_rows.append({'Modelo': nome, 'DM stat (vs SARIMAX baseline)': round(stat, 3) if pd.notna(stat) else np.nan,
                             'p-valor': round(pval, 4) if pd.notna(pval) else np.nan,
                             'N periodo comum': n,
                             'Melhor que baseline?': bool(pval < 0.05 and stat < 0) if pd.notna(pval) else None})
    dm_df = pd.DataFrame(dm_rows)
    if not dm_df.empty:
        print(f'\nDiebold-Mariano vs SARIMAX baseline ({target}) -- p<0.05 = diferenca nao e ruido:')
        print(dm_df.to_string(index=False))

    return ranking, dm_df, det


def main():
    os.makedirs('saidas', exist_ok=True)
    tab_mensal = carregar_tab_mensal()
    exog_macro = montar_exog_macro()

    resumo_linhas = []
    with pd.ExcelWriter(_PATH_SAIDA) as writer:
        for target in TARGETS:
            ranking, dm_df, _det = rodar_teste(target, tab_mensal, exog_macro)
            ranking.to_excel(writer, sheet_name=f'{target}_ranking', index=False)
            if not dm_df.empty:
                dm_df.to_excel(writer, sheet_name=f'{target}_dm_test', index=False)
                for _, row in dm_df.iterrows():
                    resumo_linhas.append({'Target': target, **row})
        if resumo_linhas:
            pd.DataFrame(resumo_linhas).to_excel(writer, sheet_name='resumo', index=False)

    print(f'\n{"=" * 70}\nSalvo em {_PATH_SAIDA}')
    print('Veredito pratico: so vale incluir uma exogena macro se ela (a) melhorar RMSPE/MAPE '
          'no ranking E (b) tiver p-valor < 0.05 no DM test contra o SARIMAX baseline. Se so '
          '(a) sem (b), o "ganho" e provavelmente ruido de amostra (N mensal pequeno).')


if __name__ == '__main__':
    main()
