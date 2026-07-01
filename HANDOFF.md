# Handoff — Reorganização do diretório (2026-06-18)

Para o próximo agente. Resume **o que mudou**, **por que continua funcionando** e **o que falta**.

## O que foi feito

Reorganização **completa** da raiz (que tinha ~30 arquivos soltos) para esta estrutura:

```
notebooks/producao/      projecoes_qtd.ipynb, projecoes_valor.ipynb
notebooks/experimentos/  experimento_{qtd,valor}_vies.ipynb, top15_*_realinhado.ipynb,
                         incremento_canal_produto.ipynb
scripts/producao/        projecoes_qtd.py, projecoes_valor.py
scripts/experimentos/    _build_incremento.py,
                         _exp_novo_modelo.py, _exp_novo_modelo2.py
scripts/render_marp.py   utilitário de apresentação
docs/                    CRONOLOGIA.md, anotacoes.txt, apresentacao_modelo_qtd.{md,html},
                         explicacao_*.md
saidas/                  comparativo_canal_produto.xlsx, comparativo_marco_2026.xlsx,
                         backup_recalc_{quantidade,valor}.xlsx, valor.csv, "comp models.csv"
```
Inalterados: `modelos/`, `resultados/` (backups oficiais lidos pelos modelos), `estudo/`,
`Apresentacao/`, `logs/`, `cache/`, `lightning_logs/`, `bkp/`.

## Por que os caminhos não quebraram

Antes, tudo rodava a partir da **raiz** (os arquivos estavam na raiz), então todos os
caminhos relativos (`cache/`, `modelos/`, `resultados/`, `logs/`) eram relativos à raiz.
Para preservar isso após mover os arquivos para subpastas, foi adicionado um **bootstrap
que ancora a raiz do projeto** (marcada por `CLAUDE.md`, subindo a árvore de diretórios):

- **Notebooks (9):** célula nova no topo com marcador `# bootstrap: raiz do projeto`
  que faz `os.chdir(raiz)`.
- **scripts/experimentos/\*.py e render_marp.py:** bloco no topo (`os.chdir(raiz)`).
- **scripts/producao/projecoes_{qtd,valor}.py:** `BASE_DIR` agora sobe até achar
  `CLAUDE.md` (antes era a pasta do próprio script).

➡️ **Invariante crítica:** `CLAUDE.md` deve permanecer na raiz — é o marcador usado por
todo o bootstrap. Não mova nem renomeie.

## Edições de caminho de saída (consistência com saidas/)

- `_build_incremento.py`: saída → `saidas/comparativo_canal_produto.xlsx`; passou a gravar
  o notebook em `notebooks/experimentos/incremento_canal_produto.ipynb`.
- Notebooks `incremento_canal_produto.ipynb` e `top15_qtd_realinhado.ipynb`: refs de saída
  apontadas para `saidas/` (consistente com os builders).

## Consolidação dos notebooks de experimento (2026-06-18)

- Os `experimento_{qtd,valor}_vies.ipynb` agora são a **fonte da verdade** (editados à mão),
  não mais artefatos gerados. Removidos como obsoletos: `experimento_qtd.ipynb`,
  `experimento_valor.ipynb` e o gerador `_build_experimento_vies.py`.
- ⚠️ O gerador removia o P3 do qtd e embutia a versão **antiga** das seções 6/7. Não
  recriá-lo: regenerar sobrescreveria as correções já aplicadas no `_vies` (cache de query,
  MAPE da Pipeline Antiga recomputado, metodologia debias-primeiro) e o P3 reintegrado.
- `experimento_qtd_vies.ipynb` recebeu o **P3** (Deep Learning PyTorch + AutoARIMA/Prophet/
  NeuralProphet) portado do antigo `experimento_qtd.ipynb`, já integrado ao ranking geral e
  à seção 6 de viés. P3 tem cache próprio em `cache/` e degrada graciosamente se torch/
  pmdarima/prophet/neuralprophet não estiverem instalados.
- `render_marp.py`: lê/grava em `docs/apresentacao_modelo_qtd.{md,html}`.

## Verificações feitas

- Todos os notebooks: JSON válido + bootstrap presente (`python -c json.load`).
- Todos os scripts: `python -m py_compile` OK.
- `git mv` preservou histórico dos arquivos rastreados (status = `R`).

## Pendências / cuidados

- **Não foi commitado.** Branch atual: `main`. Sugestão: criar branch antes de commitar.
- **`bkp/` (vazia) foi mantida de propósito** — algum notebook de produção grava
  `bkp/backup_{qtd,valor}.xlsx` por **caminho absoluto** (`M:\...\bkp\...`). Não remover.
- **`modelos/valor/comparativo_*.xlsx`** foram deixados onde estão (notebooks gravam ali);
  não foram movidos para `saidas/`.
- **`.gitignore` novo** ignora `cache/`, `lightning_logs/`, `*.log`, `__pycache__/`,
  `.ipynb_checkpoints/`. Confirme que nada disso precisava ser versionado.
- **Validação em runtime não foi executada** (depende de ClickHouse `10.101.150.150` e de
  TPOT instalado). Recomendado: abrir um notebook movido e rodar a 1ª célula (bootstrap) +
  uma leitura de `resultados/backup_*.xlsx` para confirmar o `chdir`.
- `projecoes_qtd.py`, `projecoes_valor.py` e `anotacoes.txt` foram **restaurados** do git
  (estavam deletados no working tree).
