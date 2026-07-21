import json

TARGETS = [
    {
        'nb_path': 'notebooks/experimentos/experimento_valor.ipynb',
        'anchor_id': 'c9788381',          # SEÇÃO 7 · DADOS POR CANAL
        'selecao_id': 'ac3baad0',         # SELEÇÃO DE CANAIS (contém montar_ag_canal7)
        'voting_id': '739b0545',
        'tpot_id': '4c093aea',
        'S': '7',
        'has_fila_geral': True,           # valor ja tem df_fila (Geral) -- merge continua
    },
    {
        'nb_path': 'notebooks/experimentos/experimento_qtd.ipynb',
        'anchor_id': 'canal6-dados',
        'selecao_id': 'canal6-selecao',
        'voting_id': 'canal6-voting',
        'tpot_id': 'canal6-tpot',
        'S': '6',
        'has_fila_geral': False,
    },
]

EXOG_TEMPLATE = r'''# ==================== EXOGENAS POR CANAL (fila etapa 15 + leads digitais) ====================
# Fila por canal: mesma logica do query_fila usado no Geral (ultima etapa do dia por
# proposta, argMax) -- aqui quebrada por canal via o MESMO JOIN ft_contrato/cadastro ja
# usado na query de canal acima. Serve de EXOGENA (lag 1 dia) para Voting/TPOT por canal
# (SARIMA/ETS sao univariados e nao usam; ExtraTrees(EXT,j90) por canal, quando existe,
# mantem o FEATS_EXT original do Geral -- nao foi estendido).
query_fila_canal{S} = f"""
WITH cte_total AS (
    SELECT
        prop.propostaid,
        argMax(prop.propostaetapaid, prop.data) AS etapa,
        MAX(toDate(prop.data)) AS Data
    FROM crefazon15m.dbo_propostastatushistorico AS prop
    WHERE prop.data >= today() - INTERVAL {{DIAS_QUERY}} DAY AND prop.data < today()
    GROUP BY prop.propostaid, toDate(prop.data)
)
SELECT
    tot.Data AS data,
    cad.canal AS canal,
    COUNT(tot.propostaid) AS QUANTIDADE
FROM cte_total AS tot
LEFT JOIN crefaz.ft_contrato fc ON fc.propostaid = tot.propostaid
LEFT JOIN mis_s3.cadastro cad ON cad.loginVendedor = fc.loginvendedorrbm
WHERE tot.etapa = 15
GROUP BY data, canal
"""

# Leads digitais (bitrix.leads): NAO tem canal proprio nem propostaid -- fonte/utm sao
# funil de lead-gen, nao o canal de venda (cadastro.canal). So' as fontes digitais
# (Landing Page/Site Crefaz/Facebook) mapeiam razoavelmente pro canal 'CANAL DIGITAL';
# os demais canais (CORBAN/LOJAS CREFAZ/CDC LOJISTA/CANAL INTERNO/REALLIZI) nao tem
# sinal de lead digital -- ficam com a feature zerada (ver montar_ag_canal{S} abaixo).
# Feature = soma de leads em (t-3..t-1), nunca inclui o dia t (sem vazamento temporal).
FONTES_LEADS_DIGITAL{S} = ['Landing Page', 'Site Crefaz', 'Facebook']
CANAL_DIGITAL_LABEL{S}  = 'CANAL DIGITAL'
query_leads_digital{S} = f"""
SELECT
    toDate(criado_em) AS data,
    COUNT(*) AS leads
FROM bitrix.leads
WHERE fonte IN {{tuple(FONTES_LEADS_DIGITAL{S})}}
    AND criado_em >= today() - INTERVAL {{DIAS_QUERY}} DAY AND criado_em < today()
GROUP BY data
"""

def _consultar_exog_canal{S}():
    client = clickhouse_connect.get_client(host=HOST, port=PORT, username=USER, password=PASS)
    return client.query_df(query_fila_canal{S}), client.query_df(query_leads_digital{S})

df_fila_canal{S}, df_leads_digital{S} = carregar_com_cache(
    'query_exog_canal{S}',
    [pd.Timestamp.today().date(), DIAS_QUERY, query_fila_canal{S}, query_leads_digital{S}],
    _consultar_exog_canal{S},
)
df_fila_canal{S}['data']        = pd.to_datetime(df_fila_canal{S}['data'])
df_fila_canal{S}['QUANTIDADE']  = pd.to_numeric(df_fila_canal{S}['QUANTIDADE'], errors='coerce').astype(float)
df_leads_digital{S}['data']     = pd.to_datetime(df_leads_digital{S}['data'])
df_leads_digital{S}['leads']    = pd.to_numeric(df_leads_digital{S}['leads'], errors='coerce').astype(float)
print(f'Fila por canal: {{len(df_fila_canal{S})}} linhas (canal x dia) | '
      f'Leads digitais ({{"+".join(FONTES_LEADS_DIGITAL{S})}}): {{len(df_leads_digital{S})}} dias, '
      f'total={{df_leads_digital{S}["leads"].sum():.0f}}')
'''

for t in TARGETS:
    with open(t['nb_path'], encoding='utf-8') as f:
        nb = json.load(f)
    ids = [c['id'] for c in nb['cells']]
    anchor_idx = ids.index(t['anchor_id'])
    new_id = f"canal{t['S']}-exog"
    assert new_id not in ids

    src = EXOG_TEMPLATE.format(S=t['S'])
    cell = {
        'cell_type': 'code',
        'execution_count': None,
        'id': new_id,
        'metadata': {},
        'outputs': [],
        'source': src.splitlines(keepends=True),
    }
    nb['cells'][anchor_idx + 1:anchor_idx + 1] = [cell]

    with open(t['nb_path'], 'w', encoding='utf-8') as f:
        json.dump(nb, f, indent=1, ensure_ascii=False)
        f.write('\n')

    print(f"{t['nb_path']}: inserida celula {new_id} apos {t['anchor_id']} (idx {anchor_idx + 1})")
