# Cronologia — Modelo Vendas Diário

Cronologia do projeto montada a partir do histórico git, das notas de projeto e do
trabalho em sessão. Foco em **ações simples tomadas**, em ordem.

## 📦 2026-05-18 — Início
- Subiu o projeto completo de previsão diária de vendas (modelos de **quantidade** e **valor**, TPOT + ClickHouse).
- Reorganizou as pastas e trocou caminhos absolutos por relativos.

## 🐛 2026-05-25 — Bug dos folds
- Percebeu que o `experimento_qtd.ipynb` avaliava **234 dias em vez dos 295** do backup.
- Causa: `DIAS_QUERY` calculado da data **máxima** em vez da **mínima**, e `TimeSeriesSplit` desalinhado do backup.

## 📊 2026-05-26 → 06-01 — Apresentação e experimentos
- Escreveu a apresentação do modelo de quantidade (`apresentacao_modelo_qtd.md`).
- Começou a testar arquiteturas novas (`_exp_novo_modelo.py`).

## ⚖️ 2026-06-08 / 06-09 — Viés do backup (achado central)
- Ao tentar bater a Pipeline Antiga em **mediana de MAPE**, percebeu que a comparação era **injusta**.
- Diagnóstico: a coluna `Map` do backup foi calculada contra o **realizado incompleto do próprio dia** (ex.: dias com `Map` de milhares de % que viram <2% recalculados).
- Decisão: **sempre recalcular** o MAPE da antiga na mesma base (`Valor Previsto` ÷ realizado atual), nunca usar a coluna `Map`.
- Confirmou a semântica das colunas: parear por `Data previsao` (valor) / `Dia Referência` (qtd).
- Aplicou as correções nos notebooks de qtd e valor.

## 🔧 2026-06-11 / 06-12 — Notebooks realinhados e decisão de modelo
- Atualizou `experimento_qtd.ipynb` e `experimento_valor.ipynb`.
- Criou os `top15_*_realinhado.ipynb` com **folds alinhados ao backup** e foco em mediana.
- Investigou as siglas `FEAT+ABR(n)` — concluiu que são **arquiteturas diferentes**, não retreinos.
- Decidiu a **janela 90** (oscilou j90→j45→j90) e adicionou a coluna **Tipo** no ranking.

## 🧩 2026-06-17 — Incremento por canal/produto
- Criou a análise de incremento por canal/produto (`incremento_canal_produto.ipynb`, `comparativo_canal_produto.xlsx`).

## 🎯 2026-06-18 — Notebooks de viés + cache
- Criou os notebooks de **viés** (`experimento_qtd_vies.ipynb`, `experimento_valor_vies.ipynb`) com seções de re-ranking por |viés| e correção walk-forward (debias).
- Adicionou **cache da query ClickHouse** nos dois notebooks (P1/P2/P4 já estavam cacheados).
- Confirmou onde o MAPE da antiga é recalculado: **sim nas seções 6/7** (base consistente), **não no ranking integrado** (usa `Map` do backup).

---

**Fio condutor:** sair de comparações enviesadas (MAPE salvo no backup) para uma avaliação
**justa e consistente** — folds alinhados, realizado recalculado, mesmo N entre modelos — e
agora também olhando **viés**, não só erro médio.
