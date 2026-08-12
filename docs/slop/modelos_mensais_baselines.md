# Modelos de Total Mensal — Baselines

Comparação dos modelos que preveem o **total do mês** (valor e quantidade). Todos são avaliados por *walk-forward* de 1 passo: a cada mês, o modelo treina apenas com o passado e prevê o mês seguinte — **sem vazamento**.

## O mecanismo comum: MediaUtil

Em vez de prever o total diretamente, prevê-se a **média por dia útil** do mês e reconstrói-se o total:

$$\text{total} = \overline{\text{média-útil}} \times n_{\text{úteis}}$$

onde $n_{\text{úteis}}$ é o número de dias úteis do mês — **conhecido de antemão pelo calendário**. Isso separa *"quanto rende um dia típico"* de *"quantos dias o mês tem"*, removendo a variação espúria entre meses de 19 e de 23 dias úteis (a maior fonte de sazonalidade no total).

## Os modelos

**1. Naive (mês-1) — persistência.**

$$\widehat{\text{total}}_{m} = \text{média-útil}_{m-1} \times n_{\text{úteis},\,m}$$

O dia típico do próximo mês rende o mesmo que o do mês passado. Usa apenas o mês imediatamente anterior (`lag1`). É o baseline mais simples.

**2. MediaUtil MM3 (média móvel simples — MMS) — suavização.**

$$\widehat{\text{total}}_{m} = \left(\frac{1}{3}\sum_{k=1}^{3}\text{média-útil}_{m-k}\right) \times n_{\text{úteis},\,m}$$

Igual ao Naive, mas usa a média-útil dos **3 meses anteriores** (só passado, sem vazamento). Filtra o ruído mês-a-mês — mais estável quando há um mês atípico, porém **reage mais devagar** a mudanças reais de nível.

**3. ARIMAX — paramétrico com exógena de calendário.**

ARIMA$(p,d,q)$ **não-sazonal** sobre a série mensal do total, com $n_{\text{úteis}}$ como **única regressora exógena**. A sazonalidade é descartada de propósito: a variação de tamanho do mês entra pela exógena (conhecida pelo calendário), não por um componente sazonal estimado. O `auto_arima` reseleciona $(p,d,q)$ a cada mês ($\text{max}\,p = \text{max}\,q = 2$, $\text{max}\,d = 1$).

## Resultados (walk-forward mensal)

### Valor

| Modelo | MAPE médio (%) | RMSPE (%) | Mediana (%) | Máx (%) | R² |
|---|---:|---:|---:|---:|---:|
| **Naive (mês-1)** | **3,53** | **4,66** | 2,33 | 9,50 | 0,641 |
| Nowcast (últ. dia mês-1) | 4,43 | 5,27 | 4,17 | 11,04 | 0,547 |
| MediaUtil MM3 (MMS) | 6,17 | 6,92 | 5,29 | 11,80 | 0,280 |
| ARIMAX | 7,70 | 8,53 | 7,77 | 14,18 | −0,078 |

### Quantidade

| Modelo | MAPE médio (%) | RMSPE (%) | Mediana (%) | Máx (%) | R² |
|---|---:|---:|---:|---:|---:|
| **Naive (mês-1)** | **2,94** | **3,64** | 2,80 | 6,89 | 0,597 |
| MediaUtil MM3 (MMS) | 3,27 | 4,06 | 2,77 | 7,19 | 0,519 |
| Nowcast (últ. dia mês-1) | 4,19 | 4,57 | 3,82 | 7,80 | 0,368 |
| ARIMAX | 5,49 | 6,55 | 3,65 | 11,17 | −0,277 |

## Leitura

> Para o **total mensal**, os baselines de **persistência (Naive)** batem o modelo paramétrico (**ARIMAX**), que chega a ter R² negativo. Isso **não** enfraquece o SARIMA diário — são objetos diferentes: o SARIMA modela a **trajetória diária**, e o **Nowcast** usa esse SARIMA para prever o total somando os dias úteis restantes do mês, convergindo conforme o mês avança. O ARIMAX aqui serve de referência paramétrica do total mensal, mostrando que, nesse recorte agregado e com pouco histórico, o modelo simples ganha.
