import pandas as pd
from tpot import TPOTRegressor
import datetime as dt
from datetime import datetime, timedelta
from workadays import workdays as wd
from sklearn.metrics import mean_absolute_percentage_error
import joblib
import os
import glob
import clickhouse_connect
import pyodbc

# Configurar a conexão com o ClickHouse

if wd.is_workday(datetime.today(),country='BR'):

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
 
 query2 = """
 WITH cte_total AS (
	SELECT
		prop.propostaid,
		argMax(prop.propostaetapaid,prop.data) AS etapa,
		MAX(toDate(prop.data)) AS Data
	FROM
		crefazon15m.dbo_propostastatushistorico as prop
	WHERE
		prop.data >= today() - INTERVAL 65 DAY AND
		prop.data < today()
	GROUP BY
		prop.propostaid,toDate(prop.data)
)
SELECT
	tot.Data,
	COUNT(tot.propostaid) AS QUANTIDADE
FROM
	cte_total AS tot
WHERE
	tot.etapa = 15
GROUP BY
	tot.Data
 """
fila = client.query_df(query2)


 
fila['Data']= pd.to_datetime(fila['Data'], yearfirst= True)
 
fila = fila.rename(
     columns={
        "Data":"data"
     }
 )
 
df=client.query_df(query)
df['Intervalo'] = df['Intervalo'].astype(str)  # Garante que a coluna seja string
df['data_hora'] = df['Intervalo'].str.split('+').str[0]
df['data_hora'] = pd.to_datetime(df['data_hora'])
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
df_agrupado = df[(df['data'] <= data_referencia) & (df['data'] >= data_min)]
df_agrupado = df_agrupado.groupby('data').agg({'qntd': 'sum', 'valor': 'sum'}).reset_index()
        
df_agrupado['qntd'] = df_agrupado['qntd'].astype(int)
df_agrupado= pd.merge(df_agrupado, fila, on='data', how='left')
df_agrupado['dia_semana'] = df_agrupado['data'].dt.day_of_week
df_agrupado['lag_0'] = df_agrupado['qntd'].shift(1)
df_agrupado['lag_1'] = df_agrupado['valor'].shift(1)
df_agrupado['lag_2'] = df_agrupado['valor'].shift(2)
df_agrupado['lag_3'] = df_agrupado['valor'].shift(3)
df_agrupado['lag_4'] = df_agrupado['valor'].shift(4)
df_agrupado['lag_5'] = df_agrupado['valor'].shift(5)
df_agrupado['lag_6'] = df_agrupado['valor'].shift(6)
df_agrupado['lag_7'] = df_agrupado['QUANTIDADE'].shift(1)

df_agrupado.dropna(inplace=True)
df_agrupado.drop(columns=['data', 'qntd','QUANTIDADE'], inplace=True)
df_agrupado.reset_index(drop=True, inplace=True)
# Separando o conjunto de treino (todas as linhas, exceto a última)
train = df_agrupado[:-1]

# Selecionando a última linha, para o teste
teste = df_agrupado[-1:]
X_train = train.drop(columns='valor')
y_train = train['valor']

X_teste = teste.drop(columns='valor')
y_teste = teste['valor']
contador = 1
while True:
    model = TPOTRegressor(generations=60,
                        population_size=60,
                        verbosity=2,
                        n_jobs=6,
                        early_stop=10)

    model.fit(X_train, y_train)

    y_pred = model.predict(X_teste)

    mape = mean_absolute_percentage_error(y_teste,y_pred)*100

    print('------------------------')
    print('METRICAS')
    print(f'MAPE: {mape}')                                                     
    print('------------------------')
    print(f'Contador: {contador}')
    if (contador <= 3) and (mape > 5):
        contador += 1
        continue
    elif contador <= 3 and 1 <= mape <= 5:
        joblib.dump(model.fitted_pipeline_, f'M:\\03-Relatorios\\Projecoes\\Modelos_valor\\modelo_treinado-{data_referencia.date()}.pkl')
        break
    elif contador > 3:
        break
arquivos = glob.glob(r'M:\03-Relatorios\Projecoes\Modelos_valor\*.pkl')
arquivos_dec = sorted(arquivos, key=lambda t: -os.stat(t).st_mtime)
arquivo_max = arquivos_dec[0]
modelo_treinado = joblib.load(arquivo_max)
plot= client.query_df(query)
plot['Intervalo'] = plot['Intervalo'].astype(str)  # Garante que a coluna seja string
plot['data_hora'] = plot['Intervalo'].str.split('+').str[0]
plot['data_hora'] = pd.to_datetime(plot['data_hora'])
plot['data'] = plot['data_hora'].dt.date
plot['data'] = pd.to_datetime(plot['data'])
plot_agrupado = plot[(plot['data'] <= data_referencia) & (plot['data'] >= data_min)]
plot_agrupado = plot_agrupado.groupby('data').agg({
    'qntd': 'sum', 
    'valor':'sum' 
}).reset_index()
plot_agrupado= pd.merge(plot_agrupado, fila, on='data', how='left')

plot_agrupado['dia_semana'] = (plot_agrupado['data']+ pd.to_timedelta(dias, unit='d')).dt.day_of_week
plot_agrupado['lag_0'] = plot_agrupado['qntd']
plot_agrupado['lag_1'] = plot_agrupado['valor']
plot_agrupado['lag_2'] = plot_agrupado['valor'].shift(1) 
plot_agrupado['lag_3'] = plot_agrupado['valor'].shift(2)
plot_agrupado['lag_4'] = plot_agrupado['valor'].shift(3)
plot_agrupado['lag_5'] = plot_agrupado['valor'].shift(4)
plot_agrupado['lag_6'] = plot_agrupado['valor'].shift(5)
plot_agrupado['lag_7'] = plot_agrupado['QUANTIDADE']
plot_agrupado.drop(columns=['data', 'qntd', 'valor','QUANTIDADE'], inplace=True)
plot_agrupado.reset_index(drop=True, inplace=True)
ultima_linha = plot_agrupado.tail(1)
y_pred_next = modelo_treinado.predict(ultima_linha)
base = pd.read_excel(r'M:\03-Relatorios\Projecoes\backup_valor.xlsx')
infos = {
        'Dia Referência': data_referencia,
        'Valor Previsto': y_pred_next[0],
        'Map': mape,
        'Modelo Utilizado': arquivos_dec[0].split('\\')[-1].split('.pkl')[0],
        'Data previsao' : hj
    }
df_infos = pd.DataFrame([infos])
final = pd.concat([base,df_infos])
final.to_excel(r'M:\03-Relatorios\Projecoes\backup_valor.xlsx',index=False)