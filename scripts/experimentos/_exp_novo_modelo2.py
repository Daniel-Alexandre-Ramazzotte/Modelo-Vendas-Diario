# -*- coding: utf-8 -*-
# bootstrap: roda a partir da raiz do projeto (acha CLAUDE.md), seja qual for o CWD
import os as _os
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.exists(_os.path.join(_r, 'CLAUDE.md')) and _os.path.dirname(_r) != _r:
    _r = _os.path.dirname(_r)
_os.chdir(_r)
"""Exp v2: features derivadas + janela + stacking robusto. Foco em MEDIANA."""
import sys, glob, pickle, warnings
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
from datetime import timedelta
from workadays import workdays as wd
from sklearn.metrics import mean_absolute_percentage_error as mape_fn
from sklearn.compose import TransformedTargetRegressor
from sklearn.preprocessing import FunctionTransformer, StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.ensemble import (GradientBoostingRegressor, ExtraTreesRegressor,
                              VotingRegressor, StackingRegressor)
from sklearn.linear_model import HuberRegressor, RidgeCV
from xgboost import XGBRegressor

INCLUIR_SABADO_TREINO = True
df, df_fila = pickle.load(open(glob.glob('cache/query_valor_*.pkl')[0], 'rb'))
_bkp = pd.read_excel(r'resultados\backup_valor.xlsx')
_col_data = 'Dia Referência'
_dp = pd.to_datetime(_bkp[_col_data], errors='coerce').dt.normalize().dropna()
_dp = _dp[_dp.dt.dayofweek < 5]
DATA_REFERENCIA = pd.Timestamp(_dp.max().date()); DATA_REFERENCIA_MIN = pd.Timestamp(_dp.min().date())

data_min = DATA_REFERENCIA_MIN - timedelta(days=70)
df_ag = df[(df['data'] <= DATA_REFERENCIA) & (df['data'] >= data_min)].copy()
df_ag = df_ag.groupby('data').agg({'qntd':'sum','valor':'sum'}).reset_index()
df_ag['qntd'] = df_ag['qntd'].astype(int)
df_ag = pd.merge(df_ag, df_fila, on='data', how='left')
df_ag['dia_semana'] = df_ag['data'].dt.day_of_week
df_ag['lag_0'] = df_ag['qntd'].shift(1)
for k in range(1,7): df_ag[f'lag_{k}'] = df_ag['valor'].shift(k)
df_ag['lag_7'] = df_ag['QUANTIDADE'].shift(1)
df_ag.dropna(inplace=True); df_ag.reset_index(drop=True, inplace=True)

mask_invalido = df_ag['data'].apply(lambda d: d.dayofweek==6 or bool(wd.is_holiday(d.date(), country='BR')))
mask_pred = ~mask_invalido & (df_ag['data'].dt.dayofweek < 5)
df_pred = df_ag[mask_pred].reset_index(drop=True)
dates = df_pred['data'].reset_index(drop=True)
COLS = [c for c in df_pred.columns if c not in ('data','qntd','QUANTIDADE','valor')]
X = df_pred[COLS].astype(float); y = df_pred['valor'].astype(float)
mask_train = ~mask_invalido if INCLUIR_SABADO_TREINO else mask_pred
df_train_all = df_ag[mask_train].reset_index(drop=True)
dates_train = df_train_all['data'].reset_index(drop=True)
X_train = df_train_all[COLS].astype(float); y_train = df_train_all['valor'].astype(float)

_bkp_clean = _bkp.copy()
_bkp_clean[_col_data] = pd.to_datetime(_bkp_clean[_col_data], errors='coerce').dt.normalize()
_bkp_clean = _bkp_clean.dropna(subset=[_col_data])
_bkp_clean = _bkp_clean[_bkp_clean[_col_data].dt.dayofweek < 5]
backup_dates = sorted(set(pd.Timestamp(d.date()) for d in _bkp_clean[_col_data]))
_didx = {d:i for i,d in enumerate(dates)}

def get_fold(d, janela):
    if d not in _didx: return None
    ti=_didx[d]; X_te=X.iloc[[ti]]; y_te=y.iloc[[ti]]
    prior=dates_train<d; Xp=X_train[prior]; yp=y_train[prior]
    if len(Xp)<3: return None
    n=min(janela,len(Xp))
    return Xp.iloc[-n:].reset_index(drop=True), yp.iloc[-n:].reset_index(drop=True), X_te, y_te

# ---- feature engineering derivada (opera nas 9 colunas existentes) ----
IDX = {c:i for i,c in enumerate(COLS)}
def _add_feats(A):
    A=np.asarray(A,dtype=float)
    lags=np.column_stack([A[:,IDX[f'lag_{k}']] for k in range(1,7)])  # valor 1..6
    ma3=lags[:,:3].mean(1); ma6=lags.mean(1); vol=lags.std(1)
    trend=lags[:,0]-lags[:,1]
    ratio=A[:,IDX['lag_0']]/(A[:,IDX['lag_7']]+1.0)   # qtd/fila ontem
    dev=lags[:,0]-ma6                                  # desvio do nível
    extra=np.column_stack([ma3,ma6,vol,trend,ratio,dev])
    return np.column_stack([A,extra])
FE = FunctionTransformer(_add_feats)

def log_(reg): return TransformedTargetRegressor(regressor=reg, func=np.log1p, inverse_func=np.expm1)
def gbr(): return GradientBoostingRegressor(n_estimators=250, max_depth=3, learning_rate=0.05, subsample=0.9, random_state=42)
def xgb(): return XGBRegressor(n_estimators=250, max_depth=3, learning_rate=0.05, subsample=0.9, colsample_bytree=0.9, random_state=42, verbosity=0)
def etr(): return ExtraTreesRegressor(n_estimators=250, random_state=42)

def cand_fe_gbr(): return log_(Pipeline([('fe',FE),('gbr',gbr())]))
def cand_fe_xgb(): return log_(Pipeline([('fe',FE),('xgb',xgb())]))
def cand_fe_voting():
    v=VotingRegressor([('g',Pipeline([('fe',FE),('m',gbr())])),
                       ('x',Pipeline([('fe',FE),('m',xgb())])),
                       ('e',Pipeline([('fe',FE),('m',etr())]))])
    return log_(v)
def cand_fe_stack():
    s=StackingRegressor(
        estimators=[('g',Pipeline([('fe',FE),('m',gbr())])),
                    ('x',Pipeline([('fe',FE),('m',xgb())])),
                    ('e',Pipeline([('fe',FE),('m',etr())]))],
        final_estimator=HuberRegressor(), passthrough=False, cv=3)
    return log_(s)
class MedEns:
    def __init__(self,bs): self.bs=bs
    def fit(self,X,yv):
        self.ms=[b() for b in self.bs]
        for m in self.ms: m.fit(X,yv)
        return self
    def predict(self,X):
        return np.median(np.column_stack([np.ravel(m.predict(X)) for m in self.ms]),axis=1)
def cand_fe_medens(): return MedEns([cand_fe_gbr,cand_fe_xgb,lambda:log_(Pipeline([('fe',FE),('m',etr())]))])

CANDS={'FE+GBR-log':cand_fe_gbr,'FE+XGB-log':cand_fe_xgb,
       'FE+Voting-log':cand_fe_voting,'FE+Stack-Huber-log':cand_fe_stack,
       'FE+MedEns-log':cand_fe_medens}
JANELAS={'FE+GBR-log':[35,45,60,90],'FE+Voting-log':[45,60],'FE+MedEns-log':[45,60]}

def run(nome,builder,janela):
    mp=[]
    for d in backup_dates:
        f=get_fold(d,janela)
        if f is None: continue
        Xtr,ytr,Xte,yte=f
        if len(Xtr)<8: continue
        try:
            m=builder(); m.fit(Xtr,ytr); p=float(np.ravel(m.predict(Xte))[0])
        except Exception: continue
        mp.append(mape_fn(yte,[p])*100)
    a=np.array(mp)
    return a

print(f'{"modelo":<24}{"jan":>4}{"media":>8}{"mediana":>9}{"desvio":>8}{"Q1":>7}{"Q3":>7}{"<5%":>9}{"n":>5}')
print('-'*82)
for nome,builder in CANDS.items():
    for jan in JANELAS.get(nome,[45]):
        a=run(nome,builder,jan)
        if len(a)==0: print(f'{nome:<24}{jan:>4} sem res'); continue
        print(f'{nome:<24}{jan:>4}{a.mean():8.2f}{np.median(a):9.2f}{a.std():8.2f}'
              f'{np.percentile(a,25):7.2f}{np.percentile(a,75):7.2f}{(a<5).sum():>5}/{len(a):<3}{len(a):5d}')
print('\nALVO: mediana<5.65 ; media<~10 ; desvio<=~12')
