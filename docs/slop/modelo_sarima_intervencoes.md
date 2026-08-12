# Modelos SARIMA e Funções de Intervenção

Sistema de previsão diária de vendas — **Quantidade** (propostas analisadas) e **Valor** (valor monetário). Ambos os modelos usam SARIMAX (regressão com erros SARIMA) sobre os 540 dias mais recentes, com sazonalidade semanal de dias úteis ($s = 5$).

---

## 1. Funções de intervenção

Todo evento (feriado, mudança operacional, incidente) parte de um **indicador de pulso**. Seja $\mathcal{D}_E$ o conjunto de datas do evento $E$:

$$P_t = \begin{cases} 1, & t \in \mathcal{D}_E \\ 0, & \text{caso contrário} \end{cases}$$

As funções abaixo transformam esse pulso no regressor exógeno que entra no SARIMAX. O fator $\delta \in (0,1)$ controla a velocidade do decaimento.

### 1.1 Clássicas

**Abrupto (a)** — choque pontual só no dia do evento:

$$x_t = P_t$$

**Gradual** — para evento de $n$ dias ordenados $d_0 < \dots < d_{n-1}$, rampa linear decrescente (peso $1$ no primeiro dia até $1/n$ no último):

$$x_t = \frac{n-k}{n}, \quad t = d_k, \; k = 0,\dots,n-1$$

**Rebote** — dois regressores, separando o primeiro dia do "rebote" dos dias seguintes (coeficientes independentes, podendo ter sinais opostos):

$$x^{(1)}_t = \mathbb{1}[\,t = d_0\,], \qquad x^{(2)}_t = \mathbb{1}[\,t \in \{d_1,\dots,d_{n-1}\}\,]$$

### 1.2 Transferência (Box–Tiao)

Todas se apoiam no filtro AR(1) $\;v_t = \delta\,v_{t-1} + \text{entrada}_t$.

**g** — decaimento geométrico puro (choque temporário que volta ao nível original):

$$x_t = \delta\,x_{t-1} + P_t$$

**b** — igual ao **g**, mas com atraso de um dia (efeito começa no dia seguinte):

$$x_t = \delta\,x_{t-1} + P_{t-1}$$

**c** — degrau permanente (mudança de patamar que não volta):

$$x_t = x_{t-1} + P_t = \sum_{\tau \le t} P_\tau$$

**e** — pulso imediato + cauda que decai (dois regressores):

$$x^{(1)}_t = P_t, \qquad x^{(2)}_t = \delta\,x^{(2)}_{t-1} + P_t$$

**d** — transitório que decai + degrau permanente (dois regressores):

$$x^{(1)}_t = \delta\,x^{(1)}_{t-1} + P_t, \qquad x^{(2)}_t = \sum_{\tau \le t} P_\tau$$

**f** — convergência suave a um novo patamar permanente (soma acumulada do filtro AR(1)):

$$x_t = \sum_{\tau \le t} v_\tau, \qquad v_\tau = \delta\,v_{\tau-1} + P_\tau$$

> A classe **"nao signif."** significa que o evento foi testado e **descartado** — nenhum regressor entra no modelo. A função vencedora de cada evento é escolhida por AIC.

---

## 2. Modelos SARIMA finais

Ambos são estimados como **regressão com erros SARIMA** (SARIMAX):

$$y_t = \boldsymbol{\beta}'\mathbf{X}_t + \eta_t$$

onde $\mathbf{X}_t$ é a matriz de intervenções da Seção 1 e $\eta_t$ segue um processo SARIMA. A sazonalidade é $s = 5$ (semana útil).

### 2.1 Valor — SARIMA(0,1,1)(0,0,1)₅

$$(1 - B)\,\eta_t = (1 + \theta_1 B)\,(1 + \Theta_1 B^5)\,\varepsilon_t$$

- Não-sazonal: sem AR, 1 diferença, MA(1)
- Sazonal ($s = 5$): MA(1), sem diferença sazonal

### 2.2 Quantidade — SARIMA(0,1,1)(0,0,2)₅

$$(1 - B)\,\eta_t = (1 + \theta_1 B)\,(1 + \Theta_1 B^5 + \Theta_2 B^{10})\,\varepsilon_t$$

- Não-sazonal: sem AR, 1 diferença, MA(1)
- Sazonal ($s = 5$): MA(2), sem diferença sazonal

---

> **Nota sobre os coeficientes.** O modelo congelado guarda a *estrutura* (ordens $+$ função de intervenção por evento), não os valores de $\phi, \theta, \Theta, \boldsymbol{\beta}$ — esses são reestimados a cada rodada sobre os 540 dias mais recentes.

---

## 3. Interpretação e Conclusão

### 3.1 Coeficientes estruturais (ajuste in-sample, $N = 414$ dias úteis)

| Termo | **Valor** — $(0,1,1)(0,0,1)_5$ | **Quantidade** — $(0,1,1)(0,0,2)_5$ |
|---|---|---|
| MA(1) — $\theta_1$ (choque de ontem) | **−0,645** · $p < 0{,}001$ | **−0,605** · $p < 0{,}001$ |
| MA sazonal — $\Theta_1$ (lag 5) | −0,074 · $p = 0{,}11$ | −0,035 · $p = 0{,}47$ |
| MA sazonal — $\Theta_2$ (lag 10) | — | +0,014 · $p = 0{,}79$ |
| AIC | 11.796,7 | 5.661,2 |
| Ljung-Box $p(10)$ | 0,37 ✅ | 0,63 ✅ |

### 3.2 O que os modelos dizem

**1. As duas séries têm nível que passeia — não uma média fixa.** O ADF/KPSS confirma que valor e quantidade são $I(1)$: não-estacionárias em nível, estacionárias na 1ª diferença. É isso que justifica $d = 1$ nas duas — em vez de reverter a uma média histórica, a melhor âncora para amanhã é o **nível de hoje**.

**2. O motor preditivo é a MA(1), não a sazonalidade.** O termo $\theta_1 \approx -0{,}6$ é grande e altíssimamente significativo ($p < 0{,}001$) nas duas séries — de longe o coeficiente mais forte do modelo. Num IMA(1,1), isto é uma **suavização do tipo média móvel exponencial**: a previsão do próximo dia é o nível atual **corrigido por ~60–64% do erro de previsão de ontem**. É a estrutura de curto prazo que carrega quase toda a capacidade preditiva.

**3. A sazonalidade semanal é real, mas fraca.** Os termos sazonais ($\Theta_1$ no lag 5, e $\Theta_2$ no lag 10 para a quantidade) são pequenos e **não significativos individualmente** ($p \geq 0{,}11$). A maior parte do padrão semanal já é absorvida pela diferenciação e pela própria grade de dias úteis; o componente sazonal é mantido na estrutura por parcimônia e robustez, mas **não é o que governa a série**.

**4. Os dias atípicos têm efeito real e mensurável — e por isso entram como intervenção, não como descarte.** As dummies de Box–Tiao capturam quedas grandes e significativas nos incidentes operacionais (ex.: **Microsoft 29/10** ≈ −R$ 2,9 mi no valor / −1.642 propostas na quantidade, $p < 0{,}001$; erros operacionais típicos entre −R$ 0,8 e −1,1 mi) e altas no acúmulo pós-feriado (ex.: **Carnaval** ≈ +R$ 1,6 mi, gradual). Isolar esses choques **descontamina o ajuste**: sem eles puxando os parâmetros, os coeficientes AR/MA descrevem a dinâmica normal.

**5. O tratamento funciona — o diagnóstico confirma.** Com a intervenção, o **Ljung-Box deixa de rejeitar** (de $p \approx 0{,}01$ para 0,37 no valor e 0,63 na quantidade): a autocorrelação residual que os *spikes* causavam desaparece e a dinâmica de curto prazo fica bem modelada. Persistem, como ressalva, **heterocedasticidade e caudas pesadas** (erros maiores nos dias atípicos), o que torna os intervalos de confiança otimistas nos extremos.

> **Sobre covariáveis.** A especificação de produção **não usa covariável de negócio** para nenhuma das duas séries (as intervenções da Seção 1 seguem entrando como regressores $\mathbf{X}_t$). A fila de pagamento de D-1 foi avaliada como covariável exógena (SARIMAX) e melhora o ajuste do **valor**, mas a versão sem ela foi adotada por parcimônia e robustez operacional — não depende de a fila estar disponível e consistente no momento da previsão.

### 3.3 Conclusão

> **Valor → SARIMA $(0,1,1)(0,0,1)_5$ + intervenção.**
> **Quantidade → SARIMA $(0,1,1)(0,0,2)_5$ + intervenção.**

- **Modelos brancos e parcimoniosos:** uma **única especificação congelada** — não retreinada diariamente como a pipeline antiga —, com apenas os parâmetros reestimados a cada rodada sobre os 540 dias mais recentes.
- **Competitivos onde importa:** igualam ou superam a pipeline antiga no RMSPE nas duas séries, com a vantagem decisiva de serem **interpretáveis e auditáveis** — cada termo tem significado (nível $I(1)$, choque MA(1), sazonalidade semanal) e cada dia atípico tem efeito com coeficiente e $p$-valor.
- **Dinâmica em uma frase:** ambas as séries são bem descritas por uma **suavização MA(1) sobre a série diferenciada**, com sazonalidade semanal leve e os dias atípicos tratados explicitamente por **intervenção de Box–Tiao** — em vez de removidos ou ignorados.
