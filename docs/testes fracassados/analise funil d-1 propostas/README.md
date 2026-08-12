# Entrada de propostas (cadastro) como exógena D-1 — quantidade e valor

**Pergunta:** dá pra contar quantidade/valor de propostas que *entraram* no funil (cadastro,
ainda não vendidas) e usar isso como variável exógena D-1, no mesmo espírito da `fila_d1`
(etapa 15) que já é driver validado do SARIMAX de valor?

**Veredito: contagem é viável, mas sem sinal linear como exógena D-1.** `crefaz.ft_proposta`
tem a coluna `cadastro` (data/hora de criação, distinta da `ultimaalteracao` usada hoje pelos
scripts de produção) e `valor` — dá pra agregar quantidade e soma de valor por dia de entrada,
independente da etapa atual da proposta. Mas a correlação com o alvo atual (etapa 16,
`propostadecisaoid IS NULL`) só é forte no **mesmo dia** (contemporânea), não em D-1.

## Checagem rápida feita (ad-hoc, direto no ClickHouse, sem walk-forward completo)

Query de entrada:

```sql
SELECT toDate(cadastro) AS data, count(*) AS qntd_entrada, sum(valor) AS valor_entrada
FROM crefaz.ft_proposta
WHERE toDate(cadastro) BETWEEN today() - INTERVAL 65 DAY AND today() - INTERVAL 1 DAY
GROUP BY data ORDER BY data
```

Comparado com o alvo atual (`propostaetapaid = 16 AND propostadecisaoid IS NULL`, por
`ultimaalteracao` — a mesma query dos scripts de produção), ~62 dias, restrito a dias úteis
(qtd etapa16 > 100):

| lag | corr(qtd entrada, qtd etapa16) | corr(valor entrada, valor etapa16) |
|---|---:|---:|
| 0 (mesmo dia) | 0,89 | 0,83 |
| 1 (D-1) | -0,02 | -0,03 |
| 2 | -0,18 | -0,06 |
| 3 | -0,17 | -0,04 |
| 4 | -0,17 | -0,09 |
| 5 | -0,21 | -0,28 |

Escala também é bem diferente: entrada (`cadastro`, todos os produtos/canais, qualquer etapa)
fica na casa de 30-150 mil propostas/dia; o alvo etapa 16 fica na casa de 1-4 mil/dia (~30-40x
menor) — a maior parte da entrada é filtrada/rejeitada/automatizada antes de chegar em etapa 16.

**Interpretação:** a jornada cadastro → etapa 16 parece acontecer majoritariamente dentro do
mesmo dia útil. Isso explica a correlação alta em lag 0 e o colapso em lag ≥ 1: a entrada de
ontem não carrega informação sobre o volume/valor de hoje da forma como a fila de pagamento
(etapa 15, um passo imediatamente anterior ao alvo) carrega.

## Por que não virou teste completo (walk-forward + Diebold-Mariano)

Diferente do teste de [variáveis macro](../analise%20variaveis%20macro/README.md) (que rodou o
motor completo mesmo com Granger fraco, porque a série era mensal e barata de testar), aqui a
correlação bruta em D-1 já sai ~0 — não há sequer o sinal fraco-mas-presente que justificou
rodar Granger/DM para as macros. Rodar o motor completo (SARIMAX/TPOT walk-forward) sem nenhum
indício de relação D-1 tem custo computacional que não se justifica.

## Caminhos alternativos, não explorados aqui

- **Nowcast intradiário:** usar entrada acumulada do *próprio* dia (até a hora de rodar o
  script) para prever o restante do dia — aproveitaria a correlação contemporânea forte
  (0,89/0,83), mas exige mudar a arquitetura de produção (rodar durante o dia com dados
  parciais, não só com D-1 fechado).
- **Filtrar entrada por canal/produto** que historicamente convertem em etapa 16, em vez do
  bruto (todos os produtos) — pode limpar parte do ruído de escala/composição, não testado.
- **Backlog de entrada não resolvida** (propostas que entraram há N dias e ainda não chegaram
  em etapa 16) como proxy de fila mais upstream que a etapa 15 — não testado.

## Ressalva

Reparei que `crefaz.dim_propostaetapa` (id=16) está cadastrada como **"Operação Paga"**, não
"em análise" como o CLAUDE.md descreve o alvo ("propostas a serem analisadas"). Não investiguei
a fundo — pode ser só um rótulo desatualizado na dimensão, mas vale confirmar se o filtro atual
(`propostaetapaid=16 AND propostadecisaoid IS NULL`) ainda captura o que se pretende prever.
