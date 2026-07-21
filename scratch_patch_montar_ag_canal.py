import json

# ---------------------------------------------------------------------------
# VALOR: ac3baad0 -- montar_ag_canal7 + chamada em SERIES7
# ---------------------------------------------------------------------------
VALOR_PATH = 'notebooks/experimentos/experimento_valor.ipynb'
with open(VALOR_PATH, encoding='utf-8') as f:
    nb = json.load(f)
ids = [c['id'] for c in nb['cells']]
cell = nb['cells'][ids.index('ac3baad0')]
src = ''.join(cell['source'])

OLD_FUNC7 = '''def montar_ag_canal7(df_sub, datas_ativas, df_fila_):
    """Mesma engenharia de features da celula FEATURE ENGINEERING (Secao 1), reindexada no
    calendario ATIVO por canal (zero-fill so' quando o CANAL nao vendeu, nunca dia morto)."""
    ag = (df_sub.groupby('data').agg(qntd=('qntd', 'sum'), valor=('valor', 'sum'))
          .reindex(datas_ativas).fillna(0.0))
    ag.index.name = 'data'; ag = ag.reset_index()
    ag['qntd'] = ag['qntd'].astype(int)
    ag = pd.merge(ag, df_fila_, on='data', how='left')
    ag['dia_semana'] = ag['data'].dt.day_of_week
    ag['lag_0'] = ag['qntd'].shift(1)
    for k in range(1, 7):
        ag[f'lag_{k}'] = ag['valor'].shift(k)
    ag['lag_7'] = ag['QUANTIDADE'].shift(1)
    ag.dropna(inplace=True); ag.reset_index(drop=True, inplace=True)
    return ag'''

NEW_FUNC7 = '''def montar_ag_canal7(df_sub, datas_ativas, df_fila_, canal=None):
    """Mesma engenharia de features da celula FEATURE ENGINEERING (Secao 1), reindexada no
    calendario ATIVO por canal (zero-fill so' quando o CANAL nao vendeu, nunca dia morto).
    canal=None (compat retro): sem exogenas por canal (lag_fila_canal/lag_leads_digital=0).
    Passe o nome do canal p/ ativar as exogenas da celula 'EXOGENAS POR CANAL' (fila etapa
    15 quebrada por canal + leads digitais lag(1-3), so' para 'CANAL DIGITAL')."""
    ag = (df_sub.groupby('data').agg(qntd=('qntd', 'sum'), valor=('valor', 'sum'))
          .reindex(datas_ativas).fillna(0.0))
    ag.index.name = 'data'; ag = ag.reset_index()
    ag['qntd'] = ag['qntd'].astype(int)
    ag = pd.merge(ag, df_fila_, on='data', how='left')
    ag['dia_semana'] = ag['data'].dt.day_of_week
    ag['lag_0'] = ag['qntd'].shift(1)
    for k in range(1, 7):
        ag[f'lag_{k}'] = ag['valor'].shift(k)
    ag['lag_7'] = ag['QUANTIDADE'].shift(1)

    # ---- EXOGENAS por canal (Voting/TPOT por canal apenas -- SARIMA/ETS sao univariados;
    # ExtraTrees(EXT,j90) por canal mantem FEATS_EXT original do Geral, sem essas colunas) ----
    _fila_serie7 = (df_fila_canal7[df_fila_canal7['canal'] == canal]
                    .set_index('data')['QUANTIDADE'].reindex(datas_ativas).fillna(0.0))
    ag['lag_fila_canal'] = _fila_serie7.shift(1).values
    if canal == CANAL_DIGITAL_LABEL7:
        _leads_serie7 = df_leads_digital7.set_index('data')['leads'].reindex(datas_ativas).fillna(0.0)
        ag['lag_leads_digital'] = _leads_serie7.shift(1).rolling(3, min_periods=1).sum().values
    else:
        ag['lag_leads_digital'] = 0.0

    ag.dropna(inplace=True); ag.reset_index(drop=True, inplace=True)
    return ag'''

assert src.count(OLD_FUNC7) == 1, f'montar_ag_canal7: found {src.count(OLD_FUNC7)}'
src = src.replace(OLD_FUNC7, NEW_FUNC7)

OLD_CALL7 = '''SERIES7 = {}
for canal in CANAIS7:
    ag_c = montar_ag_canal7(df_canal7_lbl[df_canal7_lbl['canal_label'] == canal], _datas_ativas7, df_fila)
    SERIES7[canal] = preparar_pred_treino7(ag_c)'''
NEW_CALL7 = '''SERIES7 = {}
for canal in CANAIS7:
    ag_c = montar_ag_canal7(df_canal7_lbl[df_canal7_lbl['canal_label'] == canal], _datas_ativas7, df_fila, canal=canal)
    SERIES7[canal] = preparar_pred_treino7(ag_c)'''
assert src.count(OLD_CALL7) == 1, f'SERIES7 loop: found {src.count(OLD_CALL7)}'
src = src.replace(OLD_CALL7, NEW_CALL7)

cell['source'] = src.splitlines(keepends=True)
cell['outputs'] = []
cell['execution_count'] = None

with open(VALOR_PATH, 'w', encoding='utf-8') as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)
    f.write('\n')
print('valor: ac3baad0 atualizada.')

# ---------------------------------------------------------------------------
# QTD: canal6-selecao -- montar_ag_canal6 + chamada em SERIES6
# ---------------------------------------------------------------------------
QTD_PATH = 'notebooks/experimentos/experimento_qtd.ipynb'
with open(QTD_PATH, encoding='utf-8') as f:
    nb = json.load(f)
ids = [c['id'] for c in nb['cells']]
cell = nb['cells'][ids.index('canal6-selecao')]
src = ''.join(cell['source'])

OLD_FUNC6 = '''def montar_ag_canal6(df_sub, datas_ativas):
    """Mesma engenharia de features da celula FEATURE ENGINEERING (Secao 1: dia_semana +
    lag_0=valor(t-1) + lag_1..lag_6=qntd(t-1..t-6)), reindexada no calendario ATIVO por
    canal (zero-fill so' quando o CANAL nao teve proposta, nunca dia morto)."""
    ag = (df_sub.groupby('data').agg(qntd=('qntd', 'sum'), valor=('valor', 'sum'))
          .reindex(datas_ativas).fillna(0.0))
    ag.index.name = 'data'; ag = ag.reset_index()
    ag['qntd'] = ag['qntd'].astype(int)
    ag['dia_semana'] = ag['data'].dt.day_of_week
    ag['lag_0'] = ag['valor'].shift(1)
    for k in range(1, 7):
        ag[f'lag_{k}'] = ag['qntd'].shift(k)
    ag.dropna(inplace=True); ag.reset_index(drop=True, inplace=True)
    return ag'''

NEW_FUNC6 = '''def montar_ag_canal6(df_sub, datas_ativas, canal=None):
    """Mesma engenharia de features da celula FEATURE ENGINEERING (Secao 1: dia_semana +
    lag_0=valor(t-1) + lag_1..lag_6=qntd(t-1..t-6)), reindexada no calendario ATIVO por
    canal (zero-fill so' quando o CANAL nao teve proposta, nunca dia morto).
    canal=None (compat retro): sem exogenas por canal (lag_fila_canal/lag_leads_digital=0).
    Passe o nome do canal p/ ativar as exogenas da celula 'EXOGENAS POR CANAL' (fila etapa
    15 quebrada por canal + leads digitais lag(1-3), so' para 'CANAL DIGITAL')."""
    ag = (df_sub.groupby('data').agg(qntd=('qntd', 'sum'), valor=('valor', 'sum'))
          .reindex(datas_ativas).fillna(0.0))
    ag.index.name = 'data'; ag = ag.reset_index()
    ag['qntd'] = ag['qntd'].astype(int)
    ag['dia_semana'] = ag['data'].dt.day_of_week
    ag['lag_0'] = ag['valor'].shift(1)
    for k in range(1, 7):
        ag[f'lag_{k}'] = ag['qntd'].shift(k)

    # ---- EXOGENAS por canal (unico candidato ML por canal no qtd -- Voting/TPOT; SARIMA/ETS
    # sao univariados e nao usam) ----
    _fila_serie6 = (df_fila_canal6[df_fila_canal6['canal'] == canal]
                    .set_index('data')['QUANTIDADE'].reindex(datas_ativas).fillna(0.0))
    ag['lag_fila_canal'] = _fila_serie6.shift(1).values
    if canal == CANAL_DIGITAL_LABEL6:
        _leads_serie6 = df_leads_digital6.set_index('data')['leads'].reindex(datas_ativas).fillna(0.0)
        ag['lag_leads_digital'] = _leads_serie6.shift(1).rolling(3, min_periods=1).sum().values
    else:
        ag['lag_leads_digital'] = 0.0

    ag.dropna(inplace=True); ag.reset_index(drop=True, inplace=True)
    return ag'''

assert src.count(OLD_FUNC6) == 1, f'montar_ag_canal6: found {src.count(OLD_FUNC6)}'
src = src.replace(OLD_FUNC6, NEW_FUNC6)

OLD_CALL6 = '''SERIES6 = {}
for canal in CANAIS6:
    ag_c = montar_ag_canal6(df_canal6_lbl[df_canal6_lbl['canal_label'] == canal], _datas_ativas6)
    SERIES6[canal] = preparar_pred_treino6(ag_c)'''
NEW_CALL6 = '''SERIES6 = {}
for canal in CANAIS6:
    ag_c = montar_ag_canal6(df_canal6_lbl[df_canal6_lbl['canal_label'] == canal], _datas_ativas6, canal=canal)
    SERIES6[canal] = preparar_pred_treino6(ag_c)'''
assert src.count(OLD_CALL6) == 1, f'SERIES6 loop: found {src.count(OLD_CALL6)}'
src = src.replace(OLD_CALL6, NEW_CALL6)

cell['source'] = src.splitlines(keepends=True)
cell['outputs'] = []
cell['execution_count'] = None

with open(QTD_PATH, 'w', encoding='utf-8') as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)
    f.write('\n')
print('qtd: canal6-selecao atualizada.')
