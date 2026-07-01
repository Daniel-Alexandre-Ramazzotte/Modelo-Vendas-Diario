import pandas as pd
import joblib
import glob
import os
import datetime as dt
from datetime import datetime, timedelta
from workadays import workdays as wd
from tpot import TPOTRegressor
from sklearn.metrics import mean_absolute_percentage_error
import clickhouse_connect

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
while not os.path.exists(os.path.join(BASE_DIR, 'CLAUDE.md')) and os.path.dirname(BASE_DIR) != BASE_DIR:
    BASE_DIR = os.path.dirname(BASE_DIR)

if wd.is_workday(datetime.today(),country='BR'):

    # Configurar a conexão com o ClickHouse
    client = clickhouse_connect.get_client(
        host='10.101.150.150',
        port=8123,
        username='debora_jesus',
        password='3fDsSF1$pe1yDv'
    )

    query = """
 SELECT
            toStartOfFifteenMinutes(ultimaalteracao) AS Intervalo,
            SUM(valor) AS valor,
            COUNT(propostaid) AS qntd
        FROM
            crefaz.ft_proposta fp 
        WHERE
            propostaetapaid = 16
            AND propostadecisaoid IS NULL
            AND toDate(ultimaalteracao) BETWEEN toDate(today() - INTERVAL 55 DAY) AND toDate(today() - INTERVAL 1 DAY)
        GROUP BY
            Intervalo
    """

    df= client.query_df(query)

    df['Intervalo'] = df['Intervalo'].astype(str)  # Garante que a coluna seja string

    df['data_hora'] = pd.to_datetime(df['Intervalo'].str.split('+').str[0])
    df['data'] = df['data_hora'].dt.date
    df['data'] = pd.to_datetime(df['data'])

    # Define a data de referência como ontem
    hj = datetime.today()
    data_ontem = hj - timedelta(days=1)
    valida_data = False
    dias = 0
    while valida_data == False:
        data_referencia = data_ontem - timedelta(days=dias)
        feriado = wd.is_holiday(data_referencia,country = 'BR')
        dia = data_referencia.weekday()
        if (feriado == False) & ( dia != 6):
            valida_data = True
        dias += 1

    data_min = data_referencia - timedelta(days=45)
    print('#####################################')
    print(data_referencia)
    print(data_min)
    print('#####################################')

    # Filtrar o DataFrame para os últimos 45 dias
    df_agrupado = df[(df['data'] <= data_referencia) & (df['data'] >= data_min)]
    df_agrupado = df_agrupado.groupby('data').agg({'qntd': 'sum', 'valor': 'sum'}).reset_index()
    df_agrupado['qntd'] = df_agrupado['qntd'].astype(int)

    # ---- Dias atipicos (Log de Erro + vespera de feriado): removidos da serie ----
    # Retirados ANTES de montar os lags, p/ nao contaminarem nem o alvo (y) nem as
    # features de defasagem dos dias vizinhos.
    def _bdays_from(_start, _n):
        """Primeiros _n dias uteis (seg-sex, exclui feriado BR) a partir de _start (inclusive)."""
        _out, _d = [], pd.Timestamp(_start).normalize()
        while len(_out) < _n:
            if _d.weekday() < 5 and not wd.is_holiday(_d.date(), country='BR'):
                _out.append(_d)
            _d += pd.Timedelta(days=1)
        return _out

    def _eh_vespera_feriado(_d):
        """True se o proximo dia de calendario nao-fim-de-semana apos _d for feriado BR."""
        _n = pd.Timestamp(_d).normalize() + pd.Timedelta(days=1)
        while _n.weekday() >= 5:          # pula sabado/domingo
            _n += pd.Timedelta(days=1)
        return bool(wd.is_holiday(_n.date(), country='BR'))

    DIAS_ERRO = set()
    _log_erro_path = os.path.join(BASE_DIR, 'logs', 'Log_Erro.xlsx')
    try:
        _log_erro = pd.read_excel(_log_erro_path)
        _log_erro['Data'] = pd.to_datetime(_log_erro['Data'], errors='coerce').dt.normalize()
        _log_erro['Impacto/dias'] = pd.to_numeric(_log_erro['Impacto/dias'], errors='coerce').fillna(1).astype(int)
        for _, _r in _log_erro.dropna(subset=['Data']).iterrows():
            for _d in _bdays_from(_r['Data'], max(int(_r['Impacto/dias']), 1)):
                DIAS_ERRO.add(_d)
        print(f'Log_Erro: {len(_log_erro)} eventos | dias de impacto (uteis): {len(DIAS_ERRO)}')
    except Exception as _e:
        print(f'[Log_Erro indisponivel] {_e} -- serie sem remocao por erro operacional')

    def _mask_atipicos(_datas):
        _dn = pd.to_datetime(_datas).dt.normalize()
        return _dn.isin(DIAS_ERRO) | _dn.map(_eh_vespera_feriado)

    _m_at = _mask_atipicos(df_agrupado['data'])
    print(f'[atipicos] removidos {int(_m_at.sum())} dias da serie (Log_Erro + vespera feriado)')
    df_agrupado = df_agrupado[~_m_at].reset_index(drop=True)

    # Features de defasagem calculadas JA sem os dias atipicos
    df_agrupado['dia_semana'] = df_agrupado['data'].dt.day_of_week
    df_agrupado['lag_0'] = df_agrupado['valor'].shift(1)
    df_agrupado['lag_1'] = df_agrupado['qntd'].shift(1)
    df_agrupado['lag_2'] = df_agrupado['qntd'].shift(2)
    df_agrupado['lag_3'] = df_agrupado['qntd'].shift(3)
    df_agrupado['lag_4'] = df_agrupado['qntd'].shift(4)
    df_agrupado['lag_5'] = df_agrupado['qntd'].shift(5)
    df_agrupado['lag_6'] = df_agrupado['qntd'].shift(6)
    df_agrupado.dropna(inplace=True)
    df_agrupado.drop(columns=['data', 'valor'], inplace=True)
    df_agrupado.reset_index(drop=True, inplace=True)

    # Separar treino e teste
    train = df_agrupado[:-1]
    teste = df_agrupado[-1:]
    X_train, y_train = train.drop(columns='qntd'), train['qntd']
    X_teste, y_teste = teste.drop(columns='qntd'), teste['qntd']

    contador = 1
    while True:
        model = TPOTRegressor(generations=60, population_size=60,verbosity =2, n_jobs=-1, early_stop=8)
        model.fit(X_train, y_train)
        y_pred = model.predict(X_teste)
        mape = mean_absolute_percentage_error(y_teste, y_pred) * 100

        print('------------------------')
        print('METRICAS')
        print(f'MAPE: {mape}')
        print('------------------------')
        print(f'Contador: {contador}')
        
        if (contador <= 4 and (mape > 5 or mape < 1)):
            contador += 1
            continue
        elif contador <=4 and 1 <= mape <= 5:
            joblib.dump(model.fitted_pipeline_, os.path.join(BASE_DIR, 'modelos', 'quantidade', f'modelo_treinado-{data_referencia.date()}.pkl'))
            break
        elif contador > 4:
            break

    # Carregar modelo mais recente
    arquivos = glob.glob(os.path.join(BASE_DIR, 'modelos', 'quantidade', '*.pkl'))
    arquivos_dec = sorted(arquivos, key=lambda t: -os.stat(t).st_mtime)
    modelo_treinado = joblib.load(arquivos_dec[0])

    # Carregar e processar dados para previsão

    plot= client.query_df(query)

    plot['Intervalo'] = plot['Intervalo'].astype(str)  # Garante que a coluna seja string
    plot['data_hora'] = pd.to_datetime(plot['Intervalo'].str.split('+').str[0])
    plot['data'] = pd.to_datetime(plot['data_hora'].dt.date)

    plot_agrupado = plot[(plot['data'] <= data_referencia) & (plot['data'] >= data_min)]
    plot_agrupado = plot_agrupado.groupby('data').agg({'qntd': 'sum', 'valor': 'sum'}).reset_index()
    plot_agrupado['qntd'] = plot_agrupado['qntd'].astype(float)

    # Remove dias atipicos do historico de lags (consistente com o treino);
    # mantem a ancora (ultimo dia = data_referencia) p/ preservar a previsao do proximo dia
    _anc = plot_agrupado['data'].max()
    _m_at = _mask_atipicos(plot_agrupado['data']) & (plot_agrupado['data'] != _anc)
    plot_agrupado = plot_agrupado[~_m_at].reset_index(drop=True)

    plot_agrupado['dia_semana'] = (plot_agrupado['data'] + pd.to_timedelta(dias, unit='d')).dt.day_of_week
    plot_agrupado['lag_0'] = plot_agrupado['valor']
    plot_agrupado['lag_1'] = plot_agrupado['qntd']
    plot_agrupado['lag_2'] = plot_agrupado['qntd'].shift(1)
    plot_agrupado['lag_3'] = plot_agrupado['qntd'].shift(2)
    plot_agrupado['lag_4'] = plot_agrupado['qntd'].shift(3)
    plot_agrupado['lag_5'] = plot_agrupado['qntd'].shift(4)
    plot_agrupado['lag_6'] = plot_agrupado['qntd'].shift(5)
    plot_agrupado.drop(columns=['data', 'qntd', 'valor'], inplace=True)
    plot_agrupado.reset_index(drop=True, inplace=True)
    
    # Fazer previsão
    y_pred_next = modelo_treinado.predict(plot_agrupado.tail(1))

    # Atualizar backup de modelos
    base = pd.read_excel(os.path.join(BASE_DIR, 'resultados', 'backup_qtd.xlsx'))
    infos = {
        'Dia Referência': data_referencia,
        'Valor Previsto': y_pred_next[0],
        'Map': mape,
        'Modelo Utilizado': os.path.splitext(os.path.basename(arquivos_dec[0]))[0],
        'Data previsao' : hj
    }
    df_infos = pd.DataFrame([infos])
    final = pd.concat([base, df_infos])
    final.to_excel(os.path.join(BASE_DIR, 'resultados', 'backup_qtd.xlsx'), index=False)