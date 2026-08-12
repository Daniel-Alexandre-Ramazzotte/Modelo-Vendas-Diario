# Efeito de canal como causa da retração mar-jun/2025 e da recuperação em jul/2025

**Pergunta:** a retração de valor/qtd de mar a jun/2025 (e a recuperação abrupta em jul/2025,
achada via `experimento_mensal.ipynb` Seção 8 — ver mudanças de política "Bloqueio/Negativa"
em mar/abr/jun e "Aprovação Automática" em 23/07, no changelog de Energia) tem componente de
**canal de venda** (Reallizi, Corban, Lojas Crefaz, Canal Interno, Canal Digital, CDC Lojista)?
Ou é um efeito só de CIA/produto, transversal a qualquer canal?

**Veredito: não há efeito de canal. O choque é transversal.** Nenhuma evidência de causa ou
correlação por canal — nem no changelog de políticas, nem nos dados reais de venda.
**Recomendação: não investigar canal como variável explicativa desse episódio; a causa já
identificada (política de crédito por CIA) já explica o padrão observado.**

## Como foi testado

1. **Changelog de políticas** (`changelog politicas/changelog_politicas_tipo_mudanca.xlsx`, aba
   "Changelog Completo") — busca da palavra "canal" (case-insensitive) em **todas** as colunas
   (`Nome da Regra`, `Política`, `Texto da Mudança`, `Abrangência`, etc.), sem filtro de data.
   **Resultado: 0 ocorrências.** O motor de políticas registrado nesse changelog opera só em
   granularidade CIA × Produto — não tem conceito de canal de venda.

2. **Dados reais de venda por canal** — `df_painel` (query unificada canal × produto × cia,
   2018+, usada na Seção 2 do `experimento_mensal.ipynb`), lido do cache já populado
   (`cache/query_mensal_painel_2018_query_b5ffc7c28898.pkl`, sem precisar de VPN). Valor mensal
   agregado por canal, jan-set/2025:

   | Mês | Corban | Lojas Crefaz | Reallizi | Canal Interno | CDC Lojista | Canal Digital |
   |---|---:|---:|---:|---:|---:|---:|
   | Jan | 36,0 mi | 21,7 mi | 19,7 mi | 11,9 mi | 3,2 mi | 2,4 mi |
   | Mar | 29,5 mi | 17,8 mi | 17,4 mi | 9,7 mi | 3,2 mi | 1,9 mi |
   | Jun | 24,8 mi | 15,6 mi | 17,1 mi | 7,9 mi | 3,1 mi | 1,5 mi |
   | **Jul** | **41,8 mi** | **21,2 mi** | **21,7 mi** | **12,0 mi** | 4,2 mi | 1,9 mi |

   Share % de cada canal no total do mês fica **estável o tempo todo** (Corban ~36-40%,
   Lojas Crefaz ~20-23%, Reallizi ~20-24%, Canal Interno ~10-13%, CDC Lojista ~3,5-5,5%,
   Canal Digital ~1,5-2,5%). Todos os 6 canais caem juntos de jan a jun e recuperam juntos em
   julho — nenhum canal específico despenca, some ou entra fora desse padrão comum.

## Interpretação

O padrão "todos os canais se movem junto, share relativo estável" é exatamente o esperado se a
causa é uma política de crédito aplicada por CIA (CPFL, NeoEnergia — ver changelog de
"Bloqueio/Negativa" mar-jun/2025 e "Aprovação Automática" 23/07/2025): qualquer canal que origina
propostas para aquela CIA é afetado igualmente, então o corte/liberação aparece proporcional em
todos os canais, sem redistribuição de share. Um efeito de canal (ex.: um canal sendo
desligado/reativado, ou um canal específico sofrendo trava operacional) apareceria como queda de
share daquele canal e ganho relativo dos demais — o que não acontece aqui.

## Ressalvas

- Teste feito na série TOTAL por canal, sem cruzar canal × CIA (ex.: será que dentro do canal
  Reallizi, especificamente as propostas CPFL caíram mais que as demais CIAs do mesmo canal?).
  Não foi necessário aprofundar porque a causa por CIA já está bem estabelecida e o padrão
  agregado por canal já é suficiente para descartar canal como driver.
- Busca no changelog foi só pela palavra "canal" — não cobre sinônimos que por acaso não usem
  esse termo. Mas como o motor de políticas desse changelog é estruturalmente CIA×Produto (todas
  as colunas confirmam isso), é improvável que exista uma dimensão de canal não capturada pelo
  termo.
