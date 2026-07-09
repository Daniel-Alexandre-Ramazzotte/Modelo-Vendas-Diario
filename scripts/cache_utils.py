"""Cache em disco para dados puxados do ClickHouse.

O modo principal e query-aware: salva um .pkl com a query, uma assinatura da
query e os dados retornados. Assim, fora da VPN, o notebook so reaproveita
cache quando a query atual bate com a query cacheada; se nao bater, tenta o
ClickHouse e falha com mensagem clara caso a rede esteja indisponivel.

Tambem le caches antigos (sem metadados) pela chave exata do dia e os migra
automaticamente para o formato novo.
"""
import hashlib
import os
import pickle
import re
import time

_ENVELOPE_VERSION = 1


def _hash_partes(partes):
    return hashlib.md5('|'.join(str(p) for p in partes).encode('utf-8')).hexdigest()[:12]


def _normalizar_query(texto):
    normalizada = ' '.join(str(texto).split())
    # Queries rolling do ClickHouse mudam o numero da janela com o passar dos dias,
    # mas representam a mesma extracao para os experimentos baseados no backup.
    normalizada = re.sub(r'INTERVAL \d+ DAY', 'INTERVAL <N> DAY', normalizada, flags=re.IGNORECASE)
    normalizada = re.sub(r'today\(\) - \d+', 'today() - <N>', normalizada, flags=re.IGNORECASE)
    return normalizada


def _extrair_query_partes(chave_partes):
    query_partes = []
    for parte in chave_partes:
        texto = str(parte)
        marcador = texto.strip().upper()
        if 'SELECT' in marcador or marcador.startswith('WITH '):
            query_partes.append(_normalizar_query(texto))
    return query_partes


def _envelopar(prefix, chave_partes, query_partes, dados):
    query_partes = list(query_partes or [])
    return {
        '__query_cache_version__': _ENVELOPE_VERSION,
        'prefix': prefix,
        'created_at': time.strftime('%Y-%m-%d %H:%M:%S'),
        'key_signature': _hash_partes(chave_partes),
        'query_signature': _hash_partes(query_partes) if query_partes else None,
        'queries': query_partes,
        'data': dados,
    }


def _desenvelopar(obj):
    if isinstance(obj, dict) and obj.get('__query_cache_version__') == _ENVELOPE_VERSION:
        return obj.get('data'), obj
    return obj, None


def _carregar_pkl(caminho):
    with open(caminho, 'rb') as f:
        return pickle.load(f)


def _salvar_pkl(caminho, obj):
    with open(caminho, 'wb') as f:
        pickle.dump(obj, f)


def carregar_com_cache(prefix, chave_partes, montar_dados, cache_dir='cache', query_partes=None):
    """Carrega dados com cache em disco, priorizando dados frescos.

    prefix: prefixo do arquivo de cache (ex.: 'query_sarimax').
    chave_partes: lista/tupla de valores que definem a chave do cache (deve
        incluir a data de hoje para renovar 1x/dia, e todo parametro que
        muda a query, ex. HIST_DIAS e o texto da query).
    montar_dados: callable sem argumentos que conecta no banco, roda a(s)
        query(s) e retorna o objeto a cachear (df, tupla de dfs, etc.).
    query_partes: lista/tupla com a(s) query(s) SQL. Se omitido, tenta extrair
        automaticamente de chave_partes. Quando existe, o cache offline so e
        usado se essa assinatura bater.
    """
    os.makedirs(cache_dir, exist_ok=True)
    chave = _hash_partes(chave_partes)
    caminho_legado = os.path.join(cache_dir, f'{prefix}_{chave}.pkl')
    query_partes = list(query_partes) if query_partes is not None else _extrair_query_partes(chave_partes)
    query_partes = [_normalizar_query(q) for q in query_partes]
    query_sig = _hash_partes(query_partes) if query_partes else None
    caminho_query = os.path.join(cache_dir, f'{prefix}_query_{query_sig}.pkl') if query_sig else None

    if caminho_query and os.path.exists(caminho_query):
        try:
            dados, envelope = _desenvelopar(_carregar_pkl(caminho_query))
            if envelope and envelope.get('query_signature') == query_sig:
                print(f'[cache query hit] {prefix} <- {os.path.basename(caminho_query)}')
                return dados
            print(f'[cache invalido] {prefix}: envelope de query inesperado em {os.path.basename(caminho_query)}')
        except Exception as e:
            print(f'[cache invalido] {prefix}: {e}')

    if os.path.exists(caminho_legado):
        try:
            obj = _carregar_pkl(caminho_legado)
            dados, envelope = _desenvelopar(obj)
            print(f'[cache hit] {prefix} <- {os.path.basename(caminho_legado)}')
            if caminho_query and not envelope:
                try:
                    _salvar_pkl(caminho_query, _envelopar(prefix, chave_partes, query_partes, dados))
                    print(f'[cache query saved] {prefix} -> {os.path.basename(caminho_query)}')
                except Exception as e:
                    print(f'[cache erro ao salvar query-aware] {prefix}: {e}')
            return dados
        except Exception as e:
            print(f'[cache invalido] {prefix}: {e}')

    try:
        dados = montar_dados()
    except Exception as e:
        if caminho_query and os.path.exists(caminho_query):
            idade_h = (time.time() - os.path.getmtime(caminho_query)) / 3600
            print(f'[cache query OFFLINE] {prefix}: ClickHouse falhou ({type(e).__name__}: {e}). '
                  f'Usando query cacheada (~{idade_h:.1f}h atras): {os.path.basename(caminho_query)}')
            dados, envelope = _desenvelopar(_carregar_pkl(caminho_query))
            if envelope and envelope.get('query_signature') == query_sig:
                return dados
        raise RuntimeError(
            f'{prefix}: ClickHouse inacessivel ({type(e).__name__}: {e}) e nenhum cache com '
            f'a mesma query foi encontrado em "{cache_dir}". Rode com VPN/rede corporativa '
            f'ao menos uma vez para popular o cache query-aware.'
        ) from e

    try:
        if caminho_query:
            _salvar_pkl(caminho_query, _envelopar(prefix, chave_partes, query_partes, dados))
            print(f'[cache query saved] {prefix} -> {os.path.basename(caminho_query)}')
        else:
            _salvar_pkl(caminho_legado, dados)
            print(f'[cache saved] {prefix} -> {os.path.basename(caminho_legado)}')
    except Exception as e:
        print(f'[cache erro ao salvar] {prefix}: {e}')
    return dados
