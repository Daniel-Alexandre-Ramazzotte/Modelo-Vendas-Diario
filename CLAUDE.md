# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Sistema de previsão diária/mensal de vendas. Dois alvos independentes, quantidade e valor,
hoje trabalhados via os notebooks de experimento (`Scripts/experimentos/`) — os scripts de
produção automatizados (TPOT, execução agendada) foram **descontinuados neste repositório**
em 12/08/2026 (ver "Reorganização de pastas" abaixo); não há mais um `python
scripts/producao/projecoes_*.py` para rodar. O modelo de **quantidade** em produção
continua sendo o pipeline identificado como **`ABR-2`** (AdaBoostRegressor, 2ª colisão de
sigla — ver `_pipeline_sigla`/`_carregar_pipeline_abr2_qtd` em `experimento_mensal.ipynb` e
`experimento_qtd.ipynb`), carregado a partir do arquivo `.pkl` mais recente compatível em
`Tabelas/modelos/quantidade/`.

Os fluxos que ainda rodam (dentro dos notebooks) só fazem sentido em dias úteis brasileiros
(verificam feriados e fins de semana via `workadays`).

## Estrutura de pastas

```
Scripts/
  experimentos/  notebooks de experimento (experimento_mensal/qtd/valor/sarimax.ipynb) +
                 modelo_qtd.py, modelo_valor.py, ranking_qtd_corr.csv
  cache_utils.py cache de queries (carregar_com_cache) -- ver secao propria abaixo
  changelog_politicas/  scripts do changelog de politicas de credito (CP Energia)
  config/        config de producao congelada (modelo_sarima_producao*.json)
  cache/         cache de queries/predicoes (ignorado pelo git)
  lightning_logs/artefatos de treino (ignorado pelo git)
Docs/            documentacao (.md), apresentacoes (.md/.html), imagens de relatorio
  img_sarima/    figuras embutidas no experimento_sarimax.ipynb
Tabelas/
  resultados/    backups oficiais lidos pelos notebooks (backup_qtd/valor.xlsx) + predicoes
                 exportadas (sarima_*_predicoes.pkl, abr2_qtd_predicoes.pkl, etc.)
  saidas/        planilhas/CSVs gerados (comparativos, recalc, etc.)
    bi/          exports padronizados p/ consumo em BI (ver "Exports para BI" abaixo)
  modelos/       modelos .pkl -- quantidade/ (restaurado; ver nota abaixo), valor/ e
                 arquivo/{fracos,diversos} (NAO restaurados, ver nota abaixo)
  changelog politicas/  saida de dados do changelog (distinto de Scripts/changelog_politicas)
Apresentacao/    apresentacoes .pptx
```

**Caminhos relativos:** notebooks resolvem a raiz do projeto procurando o `CLAUDE.md`
(subindo a árvore de diretórios) e fazem `os.chdir()` até lá — todos os caminhos literais no
código (`'Scripts/cache'`, `'Tabelas/resultados/...'`, etc.) são relativos a essa raiz, **não**
à pasta onde o próprio notebook está salvo (`Scripts/experimentos/`).

### Reorganização de pastas (12/08/2026)

A estrutura antiga (`notebooks/`, `scripts/`, `docs/`, `saidas/`, `modelos/`, `resultados/`,
`estudo/`, `logs/`, `cache/`, `config/`, `changelog politicas/`, todos em minúsculo, direto na
raiz) foi consolidada manualmente em `Scripts/`, `Docs/`, `Tabelas/`, `Apresentacao/` (acima).
Isso quebrou todo caminho relativo hardcoded que assumia a estrutura antiga — foram corrigidos
nos 4 notebooks de experimento ativos (`experimento_mensal/qtd/valor/sarimax.ipynb`) e em
`cache_utils.py` (default de `cache_dir` apontava pra `'cache'`, agora `'Scripts/cache'`).

O que foi **removido de propósito** nessa reorganização (confirmado com o usuário) e **não**
foi restaurado — ainda recuperável do histórico do git se necessário:
- `scripts/producao/` (`projecoes_qtd.py`, `projecoes_valor.py`, `aws_projecao_sarima.py`) —
  scripts de produção automatizada.
- `modelos/valor/` e `modelos/arquivo/{fracos,diversos}` — arquivo histórico de modelos.

O que foi identificado como **perdido sem querer** (não confirmado como intencional) e foi
**restaurado do git para o novo local**:
- `scripts/cache_utils.py` → `Scripts/cache_utils.py` (só sobrava o `.pyc` compilado em
  `Scripts/__pycache__/` — o `.py` tinha sumido; sem ele, `carregar_com_cache` quebra em
  todos os notebooks).
- `modelos/quantidade/` (104 arquivos `.pkl`) → `Tabelas/modelos/quantidade/` — necessário
  porque `_carregar_pipeline_abr2_qtd()` (nowcast recursivo em `experimento_mensal.ipynb`, e a
  lógica equivalente em `experimento_qtd.ipynb`) varre o histórico **inteiro** em ordem
  cronológica pra achar a 2ª colisão de sigla `'ABR'` — não dá pra restaurar só o `.pkl` mais
  recente.

**Ainda quebrado, não corrigido** (fora do escopo desta correção — avaliar se vale restaurar):
- `scripts/render_marp.py` (utilitário que gera a apresentação HTML a partir de `Docs/*.md`) —
  sumiu do disco, não confirmado se intencional.
- `experimento_qtd.ipynb` (célula 75) e `experimento_valor.ipynb` (célula 76) fazem
  `sys.path.insert(0, os.path.join('scripts', 'producao'))` pra importar de
  `scripts/producao/` — como essa pasta foi removida de propósito (ver acima), esse import
  vai falhar; não tem correção de caminho que resolva, já que o conteúdo não existe mais.

## Dependências necessárias

```bash
pip install pandas joblib scikit-learn tpot clickhouse-connect workadays openpyxl pmdarima statsmodels numba
pip install statsforecast mlforecast hierarchicalforecast neuralforecast
```

`statsforecast`/`mlforecast`/`hierarchicalforecast`/`neuralforecast` (Nixtla) são usados em
`Scripts/experimentos/experimento_mensal.ipynb` (Estratos Cruzados): backend dos candidatos
SARIMAX/ETS (statsforecast, Numba, substituiu pmdarima/statsmodels.ExponentialSmoothing),
modelo global pooled (mlforecast), reconciliação hierárquica (hierarchicalforecast) e testes
exploratórios (neuralforecast). `pmdarima`/`statsmodels` continuam em uso (Kalman/DLM e SARIMAX
do Total nas Seções 6/7 ainda não migrados).

## Arquitetura e fluxo de dados

```
ClickHouse DB (45 dias históricos)
    ↓
Agregação diária + feature engineering
    ├── dia_semana (0=seg, 6=dom)
    └── lag_1 a lag_6 (qtd) / lag_1 a lag_7 (valor, inclui fila)
    ↓
TPOT AutoML (60 gerações, população 60)
    ↓
Validação MAPE (aceitável: 1–5%)
    ├── Aprovado → salva .pkl + atualiza backup Excel
    └── Reprovado → retreina (máx 4x para qtd, 3x para valor)
```

**Modelo de valor** usa dois queries: dados de propostas (etapa 16) + dados de fila (etapa 15), que são mesclados para criar o feature `lag_7`.

## Convenções de arquivo

- Modelos salvos em `Tabelas/modelos/quantidade/` e `Tabelas/modelos/valor/` com nome
  `modelo_treinado-YYYY-MM-DD.pkl` — só `quantidade/` existe atualmente (ver "Reorganização
  de pastas" acima; `valor/` e o arquivo de `fracos/diversos` foram removidos de propósito).
- `Tabelas/resultados/backup_qtd.xlsx` e `Tabelas/resultados/backup_valor.xlsx` registram
  histórico de previsões e MAPE.
- A lógica que identifica o modelo de quantidade em produção (`ABR-2`) varre
  `Tabelas/modelos/quantidade/` cronologicamente (não é simplesmente "o mais recente" — ver
  Overview acima).

## Banco de dados

ClickHouse em `10.101.150.150:8123`. As tabelas principais são:
- `crefaz.ft_proposta`: dados de propostas (etapa 16)
- `crefazon15m.dbo_propostastatushistorico`: histórico de status (etapa 15, usado em valor)

## Cache de queries (`Scripts/cache_utils.py`)

Os notebooks de experimento carregam dados via `carregar_com_cache(prefix, chave_partes,
montar_dados, ...)`, que grava `.pkl` em `Scripts/cache/` (ignorado pelo git) e permite
trabalhar offline (sem VPN) reaproveitando a última consulta bem-sucedida.

- **Formato atual (query-aware, envelope versionado):** arquivo nomeado
  `Scripts/cache/{prefix}_query_{query_sig}.pkl`, onde `query_sig` é o hash do texto
  normalizado da(s) query(s) SQL. Conteúdo é um **dict-envelope**:
  `{'__query_cache_version__': 1, 'prefix', 'created_at', 'key_signature',
  'query_signature', 'queries', 'data': <objeto original (df/tupla/etc.)>}`.
  Isso faz o cache só ser reaproveitado quando o **texto da query bate** (não só a chave
  lógica), evitando servir dados de uma query diferente sob o mesmo prefixo.
- **Formato legado:** arquivo `Scripts/cache/{prefix}_{chave}.pkl` contendo o objeto **cru**
  (sem envelope) — ainda lido para compatibilidade e migrado automaticamente para o formato
  query-aware na primeira leitura.
- Query normalizada: janelas rolantes (`INTERVAL N DAY`, `today() - N`) têm o número
  substituído por `<N>` antes do hash, para não invalidar o cache todo dia por causa da
  janela deslizante.
- **Sempre acesse via `carregar_com_cache`** (nunca leia `.pkl` de `Scripts/cache/` diretamente) —
  os notebooks já fazem isso e ficam isolados de mudanças de formato. Para ler cache cru
  manualmente (ex.: script de análise ad-hoc fora do notebook), desembrulhe assim:
  ```python
  obj = pickle.load(open(caminho, 'rb'))
  dados = obj['data'] if isinstance(obj, dict) and '__query_cache_version__' in obj else obj
  ```

## Critérios de qualidade do modelo

| Métrica | Qtd | Valor |
|---------|-----|-------|
| MAPE ideal | 1–5% | 1–5% |
| MAPE máximo aceito | 5% | 5% |
| Tentativas de retreino | 4 | 3 |
| `n_jobs` TPOT | 1 | 6 |

## Convenções dos notebooks de experimento

- **Tabelas de ranking sempre com o nome do modelo como COLUNA, nunca como índice/nome
  da linha.** Vale para `experimento_qtd_vies.ipynb` e `experimento_valor_vies.ipynb`
  (ex.: `df_ranking_int`, `_comp`). Use o helper `_com_modelo(df, nome='Modelo')` ao
  exibir (`display(_com_modelo(...))`); mantenha o DataFrame interno com o índice porque
  o código a jusante usa `.loc[modelo]`/`.index`. As tabelas de `build_table` já trazem o
  modelo na coluna `Pipeline`, então já atendem a regra.

## Exports para BI

Resultados destinados a consumo externo (BI) são gravados em `Tabelas/saidas/bi/*.xlsx` — caminhos
fixos, sobrescritos a cada execução da célula que os gera (sem versionamento). Cada notebook
que exporta deve ter uma célula própria de export logo após o resultado consolidado, e essa
célula precisa ser **reexecutada manualmente após qualquer edição relevante** (mudança nos
candidatos, critérios de escolha ou recortes) — o notebook não reexecuta sozinho.

- `Scripts/experimentos/experimento_mensal.ipynb` (seção "Export BI - Agregação x
  Estratos", logo após "Comparação de Modelos - Walk Forward Mensal"): compara os métodos
  de previsão mensal (1 passo) testados na seção "Walk Forward Mensal - Estratos" —
  **agregação** (Total, direto), **estratos por CIA unidade** (`CIA (unidade)`, CIA
  individual ex. `ENEL SP`/Produto) e **estratos cruzados por CIA unidade** (`CIA
  (unidade)/Produto x Canal`). A granularidade por CIA **grupo** (`CIA/Produto`, ex.
  `ENEL`) e por **Canal sozinho** foram **removidas** como métodos de agregação bottom-up
  por decisão explícita — só a CIA individual e a modelagem cruzada sobrevivem aqui
  (ambos os recortes retirados continuam disponíveis sob demanda: a Comparação Metas
  retreina um canal ou CIA grupo nomeado na planilha de metas quando precisa, via
  `_obter_ou_retreinar_estrato`). Gera:
  - `walkforward_detalhe_estrato.xlsx`: **único arquivo** (a série agregada dos métodos
    e o detalhe por estrato vivem na MESMA tabela, sem `walkforward_totais.xlsx`
    separado) — 1 linha por (target, método, [estrato], período). Linhas de estrato
    individual trazem `cia_produto`, `canal` e/ou `cia_unidade` conforme o método: quando a
    linha é de **CIA individual** (`cia_unidade` preenchida, ex. `ENEL SP`), `cia_produto`
    vem preenchida TAMBÉM — com o GRUPO daquela cia (ex. `ENEL`, via
    `_MAPA_GRUPO_CIA_UNIDADE`), pra dar pra filtrar/agrupar no BI pelas duas granularidades
    na mesma linha; quando é produto não-Elétrico, só `cia_produto` vem preenchida e
    `cia_unidade` fica nula. Linhas de **total agregado por método** (`Agregação (Total)`,
    `Bottom-up CIA (unidade)`, `Bottom-up CIA (unidade)/Produto x Canal`)
    trazem as 3 colunas **nulas** — é assim que o BI
    distingue "total do método" de "quebra por estrato" na mesma tabela. A coluna
    **`objetivo`** (meta cruzada, nome padronizado como `previsto`/`realizado`) prioriza
    o valor por `cia_unidade` (mais específico, direto da planilha) quando a linha tiver
    `cia_unidade` preenchida; senão cai pro valor por `cia_produto` (soma a meta das CIAs
    finas do grupo, ou produto direto) — só existe nas linhas de estrato cruzado,
    acrescentada numa célula
    própria ("Export BI — objetivo (metas) no detalhe por estrato") na seção "Comparação
    Metas" (precisa de `METAS_CRUZADO`/`METAS_CRUZADO_PRODUTO`, carregadas só ali) — **é
    essa célula que efetivamente grava o arquivo**; rode o notebook até lá antes de
    consumir no BI.
  - `metas_comparacao.xlsx` (seção "Comparação Metas", célula "Export BI — métricas da
    Comparação Metas", logo no final da seção): RMSPE do modelo x RMSPE da própria meta
    (ambos vs. Realizado) por bloco (`CIA`, `Canal`, `CIA x Canal`, `Canal x Produto`) —
    só VALOR (a planilha de metas não tem quantidade).
