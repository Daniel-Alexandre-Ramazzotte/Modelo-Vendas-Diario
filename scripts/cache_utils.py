"""Cache em disco (1x/dia) para os dados puxados do ClickHouse pelos notebooks.

Problema que isso resolve: de casa (sem VPN/rede corporativa) o ClickHouse
(10.101.150.150:8123) fica inacessivel. O cache antigo so tinha a chave do
dia -- se ela nao existisse (ou os parametros mudassem, ex. HIST_DIAS
crescendo dia a dia) a query rodava direto e estourava excecao, travando o
notebook inteiro sem alternativa.

Aqui: tenta a chave exata do dia -> tenta consultar ao vivo -> se a consulta
falhar (rede indisponivel, timeout, etc.) cai pro cache utilizavel mais
recente (qualquer data) daquele mesmo prefixo, avisando que os dados estao
desatualizados. So estoura erro se NENHUM cache existir.
"""
import glob
import hashlib
import os
import pickle
import time


def carregar_com_cache(prefix, chave_partes, montar_dados, cache_dir='cache'):
    """Carrega dados com cache em disco, priorizando dados frescos.

    prefix: prefixo do arquivo de cache (ex.: 'query_sarimax').
    chave_partes: lista/tupla de valores que definem a chave do cache (deve
        incluir a data de hoje para renovar 1x/dia, e todo parametro que
        muda a query, ex. HIST_DIAS e o texto da query).
    montar_dados: callable sem argumentos que conecta no banco, roda a(s)
        query(s) e retorna o objeto a cachear (df, tupla de dfs, etc.).
    """
    os.makedirs(cache_dir, exist_ok=True)
    chave = hashlib.md5('|'.join(str(p) for p in chave_partes).encode('utf-8')).hexdigest()[:12]
    caminho = os.path.join(cache_dir, f'{prefix}_{chave}.pkl')

    if os.path.exists(caminho):
        try:
            with open(caminho, 'rb') as f:
                dados = pickle.load(f)
            print(f'[cache hit] {prefix} <- {os.path.basename(caminho)}')
            return dados
        except Exception as e:
            print(f'[cache invalido] {prefix}: {e}')

    try:
        dados = montar_dados()
    except Exception as e:
        candidatos = sorted(
            glob.glob(os.path.join(cache_dir, f'{prefix}_*.pkl')),
            key=os.path.getmtime,
        )
        if candidatos:
            fallback = candidatos[-1]
            idade_h = (time.time() - os.path.getmtime(fallback)) / 3600
            print(f'[cache STALE] {prefix}: falha ao consultar ClickHouse ({type(e).__name__}: {e}). '
                  f'Usando cache antigo (~{idade_h:.1f}h atras): {os.path.basename(fallback)}')
            with open(fallback, 'rb') as f:
                return pickle.load(f)
        raise RuntimeError(
            f'{prefix}: ClickHouse inacessivel ({type(e).__name__}: {e}) e nenhum cache '
            f'disponivel em "{cache_dir}/{prefix}_*.pkl". Rode com acesso a rede/VPN '
            f'ao menos uma vez para popular o cache.'
        ) from e

    try:
        with open(caminho, 'wb') as f:
            pickle.dump(dados, f)
        print(f'[cache saved] {prefix} -> {os.path.basename(caminho)}')
    except Exception as e:
        print(f'[cache erro ao salvar] {prefix}: {e}')
    return dados
