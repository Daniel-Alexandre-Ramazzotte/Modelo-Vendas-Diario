# -*- coding: utf-8 -*-
# bootstrap: roda a partir da raiz do projeto (acha CLAUDE.md), seja qual for o CWD
import os as _os
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.exists(_os.path.join(_r, 'CLAUDE.md')) and _os.path.dirname(_r) != _r:
    _r = _os.path.dirname(_r)
_os.chdir(_r)
"""Prototipagem de novo modelo de valor — valida candidatos nos mesmos folds do top15."""
import sys, os, pickle, glob, warnings
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
from datetime import datetime, timedelta
from workadays import workdays as wd
from sklearn.base import clone
from sklearn.metrics import mean_absolute_percentage_error as mape_fn
from sklearn.compose import TransformedTargetRegressor
from sklearn.ensemble import (GradientBoostingRegressor, RandomForestRegressor,
                              ExtraTreesRegressor, VotingRegressor, HistGradientBoostingRegressor)
from sklearn.linear_model import HuberRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRegressor

JANELA_DIAS = 45
INCLUIR_SABADO_TREINO = True

# ---- dados (cache) ----
df, df_fila = pickle.load(open(glob.glob('cache/query_valor_*.pkl')[0], 'rb'))

_bkp = pd.read_excel(r'resultados\backup_valor.xlsx')
_col_data = 'Dia Referência'
_dp = pd.to_datetime(_bkp[_col_data], errors='coerce').dt.normalize().dropna()
_dp = _dp[_dp.dt.dayofweek < 5]
DATA_REFERENCIA = pd.Timestamp(_dp.max().date())
DATA_REFERENCIA_MIN = pd.Timestamp(_dp.min().date())

# ---- feature engineering (igual cell 4) ----
data_min = DATA_REFERENCIA_MIN - timedelta(days=70)
df_ag = df[(df['data'] <= DATA_REFERENCIA) & (df['data'] >= data_min)].copy()
df_ag = df_ag.groupby('data').agg({'qntd':'sum','valor':'sum'}).reset_index()
df_ag['qntd'] = df_ag['qntd'].astype(int)
df_ag = pd.merge(df_ag, df_fila, on='data', how='left')
df_ag['dia_semana'] = df_ag['data'].dt.day_of_week
df_ag['lag_0'] = df_ag['qntd'].shift(1)
for k in range(1,7):
    df_ag[f'lag_{k}'] = df_ag['valor'].shift(k)
df_ag['lag_7'] = df_ag['QUANTIDADE'].shift(1)
df_ag.dropna(inplace=True); df_ag.reset_index(drop=True, inplace=True)

mask_invalido = df_ag['data'].apply(lambda d: d.dayofweek==6 or bool(wd.is_holiday(d.date(), country='BR')))
mask_pred = ~mask_invalido & (df_ag['data'].dt.dayofweek < 5)
df_pred = df_ag[mask_pred].reset_index(drop=True)
dates = df_pred['data'].reset_index(drop=True)
X = df_pred.drop(columns=['data','qntd','QUANTIDADE','valor']).astype(float)
y = df_pred['valor'].astype(float)

mask_train = ~mask_invalido if INCLUIR_SABADO_TREINO else mask_pred
df_train_all = df_ag[mask_train].reset_index(drop=True)
dates_train = df_train_all['data'].reset_index(drop=True)
X_train = df_train_all.drop(columns=['data','qntd','QUANTIDADE','valor']).astype(float)
y_train = df_train_all['valor'].astype(float)

# ---- folds (igual cell 6) ----
_bkp_clean = _bkp.copy()
_bkp_clean[_col_data] = pd.to_datetime(_bkp_clean[_col_data], errors='coerce').dt.normalize()
_bkp_clean = _bkp_clean.dropna(subset=[_col_data])
_bkp_clean = _bkp_clean[_bkp_clean[_col_data].dt.dayofweek < 5]
backup_dates = sorted(set(pd.Timestamp(d.date()) for d in _bkp_clean[_col_data]))
_dates_index = {d:i for i,d in enumerate(dates)}

def get_fold_data(test_date_ts):
    if test_date_ts not in _dates_index: return None
    ti = _dates_index[test_date_ts]
    X_te = X.iloc[[ti]]; y_te = y.iloc[[ti]]
    prior = dates_train < test_date_ts
    Xtr_p = X_train[prior]; ytr_p = y_train[prior]
    if len(Xtr_p) < 3: return None
    n = min(JANELA_DIAS, len(Xtr_p))
    return Xtr_p.iloc[-n:].reset_index(drop=True), ytr_p.iloc[-n:].reset_index(drop=True), X_te, y_te

# ---- candidatos ----
def mk_log(reg):
    return TransformedTargetRegressor(regressor=reg, func=np.log1p, inverse_func=np.expm1)

def cand_gbr_log():
    return mk_log(GradientBoostingRegressor(n_estimators=300, max_depth=3, learning_rate=0.05,
                                            subsample=0.9, random_state=42))
def cand_xgb_log():
    return mk_log(XGBRegressor(n_estimators=300, max_depth=3, learning_rate=0.05,
                               subsample=0.9, colsample_bytree=0.9, random_state=42, verbosity=0))
def cand_voting_log():
    v = VotingRegressor([
        ('gbr', GradientBoostingRegressor(n_estimators=300, max_depth=3, learning_rate=0.05, subsample=0.9, random_state=42)),
        ('xgb', XGBRegressor(n_estimators=300, max_depth=3, learning_rate=0.05, subsample=0.9, colsample_bytree=0.9, random_state=42, verbosity=0)),
        ('etr', ExtraTreesRegressor(n_estimators=300, random_state=42)),
    ])
    return mk_log(v)
def cand_gbr_lad():
    # GBR otimizando MAE (mediana-oriented), em log
    return mk_log(GradientBoostingRegressor(loss='absolute_error', n_estimators=300, max_depth=3,
                                            learning_rate=0.05, subsample=0.9, random_state=42))
def cand_hist_log():
    return mk_log(HistGradientBoostingRegressor(max_iter=400, learning_rate=0.05, max_depth=3, random_state=42))

# Ensemble robusto: mediana das predições de vários modelos em log
class MedianEnsemble:
    def __init__(self, builders): self.builders=builders
    def fit(self, Xtr, ytr):
        self.models=[]
        for b in self.builders:
            m=b(); m.fit(Xtr,ytr); self.models.append(m)
        return self
    def predict(self, Xte):
        P=np.column_stack([m.predict(Xte) for m in self.models])
        return np.median(P, axis=1)
def cand_median_ens():
    return MedianEnsemble([cand_gbr_log, cand_xgb_log, cand_gbr_lad,
                           lambda: mk_log(ExtraTreesRegressor(n_estimators=300, random_state=42))])

# Sample-weight 1/y (foco em erro relativo) sobre GBR em log
class WGBRLog:
    def fit(self, Xtr, ytr):
        self.m = GradientBoostingRegressor(n_estimators=300, max_depth=3, learning_rate=0.05, subsample=0.9, random_state=42)
        w = 1.0/np.clip(ytr.values, 1e3, None)
        self.m.fit(Xtr, np.log1p(ytr), sample_weight=w*np.mean(1.0/w))
        return self
    def predict(self, Xte):
        return np.expm1(self.m.predict(Xte))
def cand_wgbr(): return WGBRLog()

CANDS = {
    'GBR-log':            cand_gbr_log,
    'XGB-log':            cand_xgb_log,
    'GBR-LAD-log':        cand_gbr_lad,
    'Hist-log':           cand_hist_log,
    'Voting-log(GBR+XGB+ETR)': cand_voting_log,
    'MedianEns-log':      cand_median_ens,
    'wGBR-log(1/y)':      cand_wgbr,
}

print(f'Folds avaliáveis: {sum(1 for d in backup_dates if get_fold_data(d) is not None)}')
print(f'{"modelo":<26}{"media":>8}{"mediana":>9}{"desvio":>8}{"Q1":>7}{"Q3":>7}{"<5%":>8}{"<10%":>8}{"n":>5}')
print('-'*92)
ALL={}
for nome, builder in CANDS.items():
    mapes=[]
    for d in backup_dates:
        fold=get_fold_data(d)
        if fold is None: continue
        Xtr,ytr,Xte,yte=fold
        if len(Xtr)<8: continue
        try:
            m=builder(); m.fit(Xtr,ytr); p=float(np.ravel(m.predict(Xte))[0])
        except Exception as e:
            continue
        mapes.append(mape_fn(yte,[p])*100)
    if not mapes:
        print(f'{nome:<26} sem resultados'); continue
    a=np.array(mapes); ALL[nome]=a
    print(f'{nome:<26}{a.mean():8.2f}{np.median(a):9.2f}{a.std():8.2f}'
          f'{np.percentile(a,25):7.2f}{np.percentile(a,75):7.2f}'
          f'{(a<5).sum():>4}/{len(a):<3}{(a<10).sum():>4}/{len(a):<3}{len(a):5d}')

print('\nALVOS: mediana < 5.65 (TPOT) ; media < ~10 (sklearn) ; desvio <= ~12')
