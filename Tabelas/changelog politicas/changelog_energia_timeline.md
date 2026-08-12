# Linha do Tempo — Políticas CP Energia

> **Cobertura:** jan/2023 – mar/2026  
> **113 mudanças** · CDC Energia excluído

---

## Legenda

| Ícone | Tipo de Mudança |
|:-----:|-----------------|
| 🚫 | Bloqueio / Negativa |
| ✅ | Aprovação automática |
| 💰 | Limite de crédito / Pricing |
| 🔍 | Validação |
| 📊 | Variável |
| 🔌 | API / Integração |
| 🆕 | Nova regra |
| 🔄 | Fluxo |
| 📝 | Outros |

---

## Calendário de Mudanças

| Ano | Jan | Fev | Mar | Abr | Mai | Jun | Jul | Ago | Set | Out | Nov | Dez |
|-----|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **2023** | · | · | **6** | 2 | 1 | · | 3 | 1 | · | · | · | 1 |
| **2024** | **11** | · | **6** | · | **8** | 2 | 2 | · | 4 | · | 1 | 2 |
| **2025** | **9** | · | **10** | 2 | 2 | **6** | **11** | 1 | **10** | 1 | 5 | · |
| **2026** | 3 | 2 | 1 | · | · | · | · | · | · | · | · | · |

---

## Mudanças por Versão

### 2023

#### Março · 6 mudanças

##### V23.0303 &nbsp; <sub>03/03/2023</sub>

> **CIA:** `ENEL`

- 📝 **---- Pré-Análise ----**
  <small>_Alteradas_</small>

  O produto Energia está suspenso para as cidades atendidas pela Enel GO.

##### V23.0307 &nbsp; <sub>07/03/2023</sub>

> **CIA:** `Todas as CIAs`

- 📝 **Único - Avaliação de ponto de corte score biometria facial**
  <small>_Alteradas_</small>

  Para os clientes Recompra, a faixa de -100 a -41 não nega mais a proposta, apenas alerta o resultado e deriva para a mesa.

##### V23.0314 &nbsp; <sub>14/03/2023</sub>

> **CIA:** `Todas as CIAs`

- 🔍 **Datacob - Contrato em Andamento**
  <small>_Removidas_</small>

  Para validar se o cliente possui um contrato de energia em andamento, não será mais utilizado o Datacob. Por isso, essa regra será desativada apenas para os clientes novos.

- 🔍 **Datacob - Contrato em Andamento**
  <small>_Removidas_</small>

  Para validar se o cliente possui um contrato de energia em andamento, não será mais utilizado o Datacob. Por isso, essa regra será desativada.

- 🔍 **RBM - Contrato em Andamento**
  <small>_Adicionadas_</small>

  Para validar se o cliente possui um contrato de energia em andamento, não será mais utilizado o Datacob, mas sim a RBM. Assim, essa regra será criada a fim de realizar essa validação.

##### V23.0320 &nbsp; <sub>20/03/2023</sub>

> **CIA:** `Todas as CIAs`

- 🔄 **Renda Presumida Promobank**
  <small>_Alteradas_</small>

  A partir dessa versão, a renda presumida da promobank antes utilizada em 10% dos casos passará a ser usada em 50% das propostas.

---

#### Abril · 2 mudanças

##### V23.0413 &nbsp; <sub>13/04/2023</sub>

> **CIA:** `Todas as CIAs`

- 🆕 **Int - Histórico Contrato de Energia**
  <small>_Adicionadas_</small>

  A partir dessa data, foi adicionada essa nova regra para negar todos os clientes que tiveram ou tem contrato de Energia para clientes Boleto Recompra.

##### V23.0419 &nbsp; <sub>19/04/2023</sub>

> **CIA:** `ENEL`

- 💰 **Int - Matriz de Liberação**
  <small>_Alteradas_</small>

    - A partir desta versão, tivemos uma flexibilização da quantidade máxima de restritivos e seus valores paraclientes recompras(que já tenham quitado um contrato de energia) atendidos pela ENEL.
  - Para estes clientes, caso a idade seja igual ou superior à 41 anos, o valor liberado será R$ 1.500,00.
  - Caso contrário, o valor liberado será R$ 1.400,00.A nova quantidade de restritivos é descrita abaixo.Quantidade total de restritivos = 4
  - Quantidade total de restritivos =∞Valor total dos restritivos = R$ 15.000,00
  - Valor total dos restritivos =∞
  - Os clientes que se enquadram nesta regra se encontram em uma planilha alimentada pela setor deMonitoramento de Energiae que será utilizada na liberação de valores no Crivo.
  - Modalidade do Cliente: Recompra de EnergiaIdade do cliente: 45 anosQuantidade máxima de restritivos:∞Valor máximo dos restritivos:∞Bureau SPC: 18 restritivos, totalizando R$ 371.000,00.Bureau Quod: 7 restritivos, totalizando R$ 1.400,00.No Crivo,este cliente terá o valor liberado de R$ 1.500,00 já que o cliente é Liquidado e possui idade >= 41.
  - Modalidade do Cliente: Recompra de EnergiaIdade do cliente: 40 anosQuantidade máxima de restritivos:∞Valor máximo dos restritivos:∞Bureau SPC: 13 restritivos, totalizando R$ 1.400,00.Bureau Quod: 7 restritivos, totalizando R$ 189.000,00.No Crivo,este cliente terá o valor liberado de R$ 1.400,00 já que o cliente é Liquidado e possui idade < 41.

---

#### Maio · 1 mudança

##### V23.0525 &nbsp; <sub>25/05/2023</sub>

> **CIA:** `CPFL` · `RGE`

- 🔍 **Crefaz - Consulta CPFL - Validação Luz em Dia - PF**
  <small>_Alteradas_</small>

  A partir dessa data, a validação do luz em dia para CPFL/RGE foi alterada. Agora serão aceitos apenas clientes com no máximo 2 faturas (<=2) em atraso, onde uma delas está em atraso a mais de 25 dias (> 25) e a outra tem de 1 a 25 dias de atraso (>= 1 e <= 25).

---

#### Julho · 3 mudanças

##### V23.0710 &nbsp; <sub>10/07/2023</sub>

> **CIA:** `ENEL SP` · `CPFL` · `RGE`

- 📝 **SPC e ACP - Valida Restrições**
  <small>_Alteradas_</small>

  As faixas de idade e restrições para cada CIA foram alteradas (exceto para a ENEL SP). Segue abaixo cenário anterior e atual:

- 📝 **Int - Matriz de Liberação**
  <small>_Alteradas_</small>

  A quantidade de restrições aceitas para cada CIA e faixa etária foram alteradas (exceto para a ENEL SP). Segue abaixo cenário anterior e atual:

- 🔍 **Crefaz - Consulta CPFL - Validação Luz em Dia - PF**
  <small>_Alteradas_</small>

  A partir desta versão, o valor de Luz em Dia liberado para a Cia CPFL/RGE será de R$ 1.000,00.

---

#### Agosto · 1 mudança

##### V23.0821 &nbsp; <sub>21/08/2023</sub>

> **CIA:** `Todas as CIAs`

- 📝 **Oferta Débito**
  <small>_Adicionadas_</small>

    - A partir desta versão, o produto Débito estará disponível em produção.
  - O manual de regras e o resumo da política se encontram no site das Políticas.
  - As regras "REGRA: (Oferta Débito) - Int - Cliente com CP/CDC com atraso superior a 30 dias", "REGRA: (Oferta Débito) - Int – Cliente com produto energia com atraso superior a 130 dias" e "REGRA: (Oferta Débito) - Int – Cliente com produto débito em conta em atraso" estão desativadas temporariamente devido a retirada da consulta ao Datacob em produção, até que possa ser reativada.

---

#### Dezembro · 1 mudança

##### V23.1221 &nbsp; <sub>21/12/2023</sub>

> **CIA:** `Todas as CIAs`

- 📝 **Code - UC faz parte da Blocklist**
  <small>_Alteradas_</small>

  A partir desta versão, a regra deixou de ser executada e retirada da documentação.

---


### 2024

#### Janeiro · 11 mudanças

##### V24.0104 &nbsp; <sub>04/01/2024</sub>

> **CIA:** `CPFL` · `ENEL SP`

- 📝 **Crefaz - Consulta CPFL - Fornecimento Suspenso**
  <small>_Alteradas_</small>

  A partir desta versão, o Crivo passa a tomar 100% das decisões (Negar ou Aprovar) de acordo com o que é retornado pelo Bureau.

- 📝 **Crefaz - Consulta CPFL - Titularidade - PF**
  <small>_Alteradas_</small>

  A partir desta versão, o Crivo passa a tomar 100% das decisões (Negar ou Aprovar) de acordo com o que é retornado pelo Bureau.

- 🔌 **Crefaz - API ENEL - SP - Fornecimento Suspenso**
  <small>_Alteradas_</small>

  A partir desta versão, o Crivo passa a tomar 100% das decisões (Negar ou Aprovar) de acordo com o que é retornado pelo Bureau.

- 🔌 **Crefaz - API ENEL - SP - Titularidade - PF**
  <small>_Alteradas_</small>

  A partir desta versão, o Crivo passa a tomar 100% das decisões (Negar ou Aprovar) de acordo com o que é retornado pelo Bureau.

##### V24.0109 &nbsp; <sub>09/01/2024</sub>

> **CIA:** `ENEL SP`

- 📝 **Parâmetro Pula Contato**
  <small>_Alteradas_</small>

  A partir desta versão, a CIA Elekto e a CIA Enel SP passam a estar liberadas para o parâmetro "Pula Contato".

##### V24.0118 &nbsp; <sub>18/01/2024</sub>

> **CIA:** `Todas as CIAs`

- 📝 **Int - Valida Instituição Bancária**
  <small>_Adicionada_</small>

  A partir desta versão, se a CIA de Energia do cliente for "Elektro", a hierarquia de quem digitou a proposta for "CFZ" e o banco informado para pagamento estiver na lista abaixo (Bancos suspeitos), a proposta será alertada para mesa de análise.

##### V24.0124 &nbsp; <sub>24/01/2024</sub>

> **CIA:** `CPFL` · `ENEL CE` · `ENEL RJ`

- 🔌 **CPFL WS GMP - Valida Baixa Renda**
  <small>_Adicionada_</small>

  A partir desta versão, a mesa de análise passa a ser alertada caso o cliente se enquadre no Baixa Renda.

- 🚫 **API ENEL - CE - Fornecimento Suspenso**
  <small>_Alterada_</small>

  A partir desta versão, caso o cliente não possua fornecimento de energia, a proposta deixará de ser negada e será apenas alertado a mesa de análise.

- 🚫 **API ENEL - RJ - Fornecimento Suspenso**
  <small>_Alterada_</small>

  A partir desta versão, caso o cliente não possua fornecimento de energia, a proposta deixará de ser negada e será apenas alertado a mesa de análise.

- 🚫 **API ENEL - CE - Titularidade - PF**
  <small>_Alterada_</small>

  A partir desta versão, caso o nome do cliente digitado na proposta possua similaridade menor que 60%, a proposta deixará de ser negada e será apenas alertado a mesa de análise.

- 🚫 **API ENEL - RJ - Titularidade - PF**
  <small>_Alterada_</small>

  A partir desta versão, caso o nome do cliente digitado na proposta possua similaridade menor que 60%, a proposta deixará de ser negada e será apenas alertado a mesa de análise.

---

#### Março · 6 mudanças

##### V24.0318 &nbsp; <sub>18/03/2024</sub>

> **CIA:** `CPFL` · `ENEL SP` · `NEO` · `Todas as CIAs` · `ENEL CE` · `ENEL RJ`

- 🔌 **CPFL WS GMP - Valida Baixa Renda**
  <small>_Alteradas_</small>

  A partir desta versão, a regra passa a negar o cliente se o retorno obtido pela API for "sim" e o valor da fatura mais recente for menor ou igual a R$ 80,00 (≤ R$ 80,00).

- 🔌 **API ENEL - SP – Loja Sem Permissao de Venda**
  <small>_Alteradas_</small>

  A partir desta versão, esta regra deixa de existir em produção.

- 🚫 **API NeoEnergia - Verifica Titularidade – PF**
  <small>_Alteradas_</small>

  A partir desta versão, esta regra deixará de ser negada pelo Crivo.

- 🚫 **Crefaz - Consulta Elektro - Titularidade - PF**
  <small>_Alteradas_</small>

  A partir desta versão, esta regra deixará de ser negada pelo Crivo.

- 🚫 **API ENEL - CE - Fornecimento Suspenso**
  <small>_Alteradas_</small>

  A partir desta versão, o cliente passa a ser negado se o retorno obtido para Titularidade for "ok" e o retorno de Fornecimento for "1".

- 🚫 **API ENEL - RJ - Fornecimento Suspenso**
  <small>_Alteradas_</small>

  A partir desta versão, o cliente passa a ser negado se o retorno obtido para Titularidade for "ok" e o retorno de Fornecimento for "1".

---

#### Maio · 8 mudanças

##### V24.0520 &nbsp; <sub>20/05/2024</sub>

> **CIA:** `CPFL` · `RGE`

- 💰 **Especificações de Pricing (CPFL/RGE)**
  <small>_Alterada_</small>

  A partir desta versão, haverá uma nova tabela de Pricing para cliente Novo e Recompra, dos produtos CP Energia e CDC Energia.

##### V24.0528 &nbsp; <sub>28/05/2024</sub>

> **CIA:** `Todas as CIAs` · `ENEL SP` · `ENEL CE` · `ENEL RJ`

- 🚫 **SPC - Valida Restrições**
  <small>_Alteradas_</small>

  A partir desta versão, caso o cliente novo possua restrições, não será mais negado, apenas alertado a mesa de análise. O cliente recompra, independente de ter ou não restrições, deixará de ser alertado a mesa de análise, ele será aprovado.

- 🚫 **ACP - Valida Restrições**
  <small>_Alteradas_</small>

  A partir desta versão, caso o cliente novo possua restrições, não será mais negado, apenas alertado a mesa de análise. O cliente recompra, independente de ter ou não restrições, deixará de ser alertado a mesa de análise, ele será aprovado.

- 💰 **Int - Matriz de Liberação**
  <small>_Alteradas_</small>

  A partir desta versão, a matriz de liberação da Enel SP, Enel CE e Enel RJ terá seus limites alterados. Os novos limites estão descritos no material do produto, no site de políticas.

- 📝 **Valida Score SPC**
  <small>_Adicionadas_</small>

  A partir desta versão, teremos a informação de Score do SPC de cada cliente.

- 📝 **Valida Score ACP**
  <small>_Adicionadas_</small>

  A partir desta versão, teremos a informação de Score da ACP de cada cliente.

- 📝 **Valida Score Modelo SCR**
  <small>_Adicionadas_</small>

  A partir desta versão, teremos a informação de Score do SCR de cada cliente.

- 📝 **Int - Rating**
  <small>_Adicionadas_</small>

  A partir desta versão, tanto o cliente Novo, quanto o cliente Recompra, passarão a ser classificados de acordo com o seu Rating.

---

#### Junho · 2 mudanças

##### V24.0617 &nbsp; <sub>17/06/2024</sub>

> **CIA:** `CPFL` · `RGE`

- 💰 **Especificações de Pricing (CPFL/RGE)**
  <small>_Alteradas_</small>

  A partir desta versão, haverão novas tabelas de juros para cliente Novo e Recompra, do produto CDC Energia.

##### V24.0624 &nbsp; <sub>24/06/2024</sub>

> **CIA:** `ENEL RJ`

- 🚫 **Int – Rating**
  <small>_Alteradas_</small>

  A partir desta versão, haverá a inversão da decisão do Crivo para os Rating's "I" e "J" (ENEL RJ). O que aprovava passará a ser negado, e o que negava passará a ser aprovado.

---

#### Julho · 2 mudanças

##### V24.0723 &nbsp; <sub>23/07/2024</sub>

> **CIA:** `NEO` · `COSERN`

- 📝 **Int - Rating**
  <small>_Alterada_</small>

  A partir desta versão, haverá um rating para a CIA Neoenergia também, que abrange COELBA, COSERN, CELPE e Elektro.

##### V24.0730 &nbsp; <sub>30/07/2024</sub>

> **CIA:** `Todas as CIAs`

- 📝 **Int - Alerta - Departamento Monitoramento Energia**
  <small>_Alterada_</small>

  A partir desta versão, os clientes que eram alertados nesta regra, passarão a ser negados (com possibilidade de reanálise).

---

#### Setembro · 4 mudanças

##### V24.0910 &nbsp; <sub>10/09/2024</sub>

> **CIA:** `ENEL RJ`

- 📝 **Int - Rating**
  <small>_Alterada_</small>

  A partir desta versão, haverá a inversão da Letra I e J no rating da ENEL RJ, para que o I aprove e todos os J reprovem.

##### V24.0930 &nbsp; <sub>30/09/2024</sub>

> **CIA:** `NEO` · `CPFL`

- 📝 **Int – Rating**
  <small>_Alteradas_</small>

  A partir desta versão, alguns rating’s que eram negados para a CIA NEO, passarão a ser aprovados.

- 💰 **Especificações de Pricing (Energia)**
  <small>_Alteradas_</small>

  A partir desta versão, o valor máximo liberado para clientes CPFL, tanto novo, quanto recompra, será de R$ 3.300,00 (a depender da idade e da quantidade de restrições).

- 📝 **Crefaz – Consulta CPFL – Quantidade de faturas abaixo do permitido**
  <small>_Alterada_</small>

  A partir desta versão, esta regra voltará a ser executada, verificando se o cliente possui pelo menos 3 faturas geradas em seu nome ou tempo de contrato ≥ 120 dias.

---

#### Novembro · 1 mudança

##### V24.1107 &nbsp; <sub>07/11/2024</sub>

> **CIA:** `CPFL`

- 📝 **Crefaz - Consulta CPFL – Quantidade de faturas abaixo do permitido**
  <small>_Alterada_</small>

  A partir desta versão, se o cliente (novo) não possuir pelo menos 3 faturas geradas em seu nome, precisará ter contrato com a CIA de pelo menos 90 dias, e não mais de 120 dias.

---

#### Dezembro · 2 mudanças

##### V24.1209 &nbsp; <sub>09/12/2024</sub>

> **CIA:** `CPFL`

- 🔌 **CPFL WS GMP - Valida Financeiras**
  <small>_Adicionada_</small>

  A partir desta versão, se o cliente possuir alguma cobrança advinda de financeiras, receberemos a quantidade de cobranças e o valor. OBS.: Ainda não será tomada nenhuma decisão, portanto apresentará bolinha preta.

##### V24.1216 &nbsp; <sub>16/12/2024</sub>

> **CIA:** `CPFL` · `RGE`

- 📝 **Int - Rating**
  <small>_Alterada_</small>

  A partir desta versão, os clientes passarão a ser classificados de acordo com seu rating, para a Cia CPFL/RGE.

---


### 2025

#### Janeiro · 9 mudanças

##### V25.0102 &nbsp; <sub>02/01/2025</sub>

> **CIA:** `Todas as CIAs`

- 🔍 **OCR - Valida Documento**
  <small>_Adicionada_</small>

  A partir desta versão, haverá a validação do CPF digitado do cliente com o CPF anexado na proposta, através da OCR. Caso haja divergência entre eles, a regra alertará a mesa de análise.

##### V25.0113 &nbsp; <sub>13/01/2025</sub>

> **CIA:** `Todas as CIAs`

- 🚫 **Valida Motivo de Recusa 1**
  <small>_Adicionadas_</small>

  A partir desta versão, clientes que submeteram propostas que foram negadas dentro de até 30 dias pelo motivo 24, se tentearem submeter uma nova proposta, ela será negada automaticamente pelo Crivo.

- 🚫 **Valida Motivo de Recusa 2**
  <small>_Adicionadas_</small>

  A partir desta versão, clientes que submeteram propostas que foram negadas dentro de até 30 dias pelo motivo 41, se tentearem submeter uma nova proposta, ela será negada automaticamente pelo Crivo.

- 🚫 **Valida Motivo de Recusa 3**
  <small>_Adicionadas_</small>

  A partir desta versão, clientes que submeteram propostas que foram negadas dentro de até 30 dias pelo motivo 54, se tentearem submeter uma nova proposta, ela será negada automaticamente pelo Crivo.

- 🚫 **Valida Motivo de Recusa 4**
  <small>_Adicionadas_</small>

  A partir desta versão, clientes que submeteram propostas que foram negadas dentro de até 30 dias pelo motivo 61, se tentearem submeter uma nova proposta, ela será negada automaticamente pelo Crivo.

- 🚫 **Valida Motivo de Recusa 5**
  <small>_Adicionadas_</small>

  A partir desta versão, clientes que submeteram propostas que foram negadas dentro de até 30 dias pelo motivo 62, se tentearem submeter uma nova proposta, ela será negada automaticamente pelo Crivo.

- 🚫 **Valida Motivo de Recusa 6**
  <small>_Adicionadas_</small>

  A partir desta versão, clientes que submeteram propostas que foram negadas dentro de até 30 dias pelo motivo 64, se tentearem submeter uma nova proposta, ela será negada automaticamente pelo Crivo.

- 🚫 **Valida Motivo de Recusa 7**
  <small>_Adicionadas_</small>

  A partir desta versão, clientes que submeteram propostas que foram negadas dentro de até 30 dias pelo motivo 107, se tentearem submeter uma nova proposta, ela será negada automaticamente pelo Crivo.

- 📝 **Google - Distância Loja e Endereço Cliente**
  <small>_Alteradas_</small>

  A partir desta versão, a regra deixou de ser executada e foi retirada da documentação.

---

#### Março · 10 mudanças

##### V25.0310 &nbsp; <sub>10/03/2025</sub>

> **CIA:** `CPFL`

- 🚫 **CPFL WS GMP - Valida Financeiras**
  <small>_Alterada_</small>

  A partir desta versão, a regra passará a ser negada caso o retorno da API de Financeiras informe que o cliente possui qualquer débito com alguma financeira.

##### V25.0313 &nbsp; <sub>13/03/2025</sub>

> **CIA:** `Todas as CIAs` · `CPFL`

- 🔌 **Int – Rating**
  <small>_Alteradas_</small>

    - A partir desta versão, a consideração de hierarquia para classificação de rating foi retirada, alterando em alguns casos, o rating que o cliente é classificado e a decisão a ser tomada.
  - Em caso de erro na consulta da API do SPC e do ACP, cliente será atribuído ao pior rating de cada CIA, de acordo com suas características.

- 🚫 **Int - Alerta - Departamento Monitoramento Energia**
  <small>_Alteradas_</small>

  A partir desta versão, o cliente será negado corretamente caso conste na lista de alerta, e a consulta da lista de energia quitado foi retirada.

- 🔌 **CPFL WS GMP – Valida Informação**
  <small>_Alteradas_</small>

  A partir desta versão, será realizado um cálculo para identificar o real valor de consumo do cliente em sua fatura mais recente e oferecer o valor correto de parcela.

- 🔌 **CPFL WS GMP – Valida Baixa Renda**
  <small>_Alteradas_</small>

  A partir desta versão, a verificação de valor de fatura para clientes baixa renda será a partir do resultado do cálculo da regra “P2(CDC_Energia) – CPFL WS GMP – Valida Informação”.

##### V25.0323 &nbsp; <sub>23/03/2025</sub>

> **CIA:** `Todas as CIAs`

- 🚫 **Distância App e Cliente**
  <small>_Alterada_</small>

  A partir desta versão, caso a UF do cliente digitada na proposta seja “SP” e o cálculo da distância entre APP Cliente for maior que 350 km, a proposta será negada.

##### V25.0326 &nbsp; <sub>26/03/2025</sub>

> **CIA:** `Todas as CIAs`

- 📝 **Int - Rating**
  <small>_Alteradas_</small>

  A partir desta versão, CCF’s não serão mais consideradas como restrição do cliente.

- 🚫 **Int - UC do cliente faz parte da blocklist**
  <small>_Alterada_</small>

  A partir desta versão, a proposta será negada caso a UC do cliente conste na lista de blocklist presente no Crivo.

- 🚫 **Int - Telefone celular faz parte da blocklist**
  <small>_Alteradas_</small>

  A partir desta versão, a proposta será negada caso o telefone celular do cliente conste na lista de blocklist presente no Crivo.

- 🚫 **Int - CPF faz parte da Blocklist**
  <small>_Alteradas_</small>

  A partir desta versão, a proposta será negada caso o CPF do cliente conste na lista de blocklist presente no Crivo.

---

#### Abril · 2 mudanças

##### V25.0403 &nbsp; <sub>03/04/2025</sub>

> **CIA:** `Todas as CIAs`

- 📝 **SPC - Valida Restricoes**
  <small>_Alteradas_</small>

  A partir desta versão, utilities passarão a ser consideradas como restrição do cliente.

- 📝 **ACP - Valida Restricoes**
  <small>_Alteradas_</small>

  A partir desta versão, utilities passarão a ser consideradas como restrição do cliente.

---

#### Maio · 2 mudanças

##### V25.0522 &nbsp; <sub>22/05/2025</sub>

> **CIA:** `NEO`

- 🔄 **NeoEnergia – Valida Tempo Ativacao Contrato**
  <small>_Alterada_</small>

  A partir desta versão, esta regra deixará de negar e passará a alertar a mesa de análise.

##### V25.0526 &nbsp; <sub>26/05/2025</sub>

> **CIA:** `ENEL RJ` · `COSERN`

- 📊 **Int - Rating**
  <small>_Alteradas_</small>

    - A partir desta versão, haverá a inversão da Letra I e J no rating da ENEL RJ, para que o I aprove e todos os J reprovem (alteração já havia sido realizada, mas havia deixado de funcionar).
  - Além da correção nos rating’s da COSERN, para que olhem a variável de restrições e não de consultas, e, a faixa de score do rating E.

---

#### Junho · 6 mudanças

##### V25.0605 &nbsp; <sub>05/06/2025</sub>

> **CIA:** `CPFL`

- 📝 **Int – Matriz de Liberacao**
  <small>_Alteradas_</small>

  A partir desta versão, os valores máximos liberados para alguns rating’s da CPFL foram alterados e passaram a ser de R$ 3.300,00.

##### V25.0617 &nbsp; <sub>17/06/2025</sub>

> **CIA:** `NEO`

- 🚫 **NeoEnergia – Valida Tempo Ativacao Contrato**
  <small>_Adicionada_</small>

  A partir desta versão, esta regra passará a existir e o cliente que não tiver mais de 30 dias de consumo será negado.

##### V25.0624 &nbsp; <sub>24/06/2025</sub>

> **CIA:** `COSERN`

- 💰 **Int – Matriz de Liberacao**
  <small>_Alteradas_</small>

  A partir desta versão, haverá aumento de limite para clientes da COELBA, CELPE, COSERN e ELEKTRO, podendo chegar até R$ 2.200,00.

- 📝 **Int – Arquitetura Matriz de Juros**
  <small>_Alteradas_</small>

  A partir desta versão, haverá diferenciação nas tabelas de juros dos clientes da COELBA, CELPE, COSERN e ELEKTRO.

- 📝 **Int – Rating**
  <small>_Alteradas_</small>

  A partir desta versão, haverá alteração na decisão do rating G da ELEKTRO, correção do rating E da COSERN e rating F da CELPE.

- 📝 **Int – Plano diferente do intervalo permitido**
  <small>_Alterada_</small>

  A partir desta versão, clientes da COELBA, CELPE, COSERN e ELEKTRO poderão selecionar planos de até 24x.

---

#### Julho · 11 mudanças

##### V25.0703 &nbsp; <sub>03/07/2025</sub>

> **CIA:** `COSERN`

- 📝 **Int - Rating**
  <small>_Alteradas_</small>

  A partir desta versão, clientes do Rating H e I da COSERN serão classificados corretamente, de acordo com a política criada.

##### V25.0707 &nbsp; <sub>07/07/2025</sub>

> **CIA:** `COSERN`

- 📝 **Int – Arquitetura Matriz de Juros**
  <small>_Alterada_</small>

  A partir desta versão, algumas tabelas de juros foram alteradas para as CIA’s CELPE, COELBA, COSERN e ELEKTRO.

##### V25.0717 &nbsp; <sub>17/07/2025</sub>

> **CIA:** `CPFL`

- 🔌 **CPFL WS GMP - Valida Informacao**
  <small>_Adicionadas_</small>

  A partir desta versão, esta regra passará a existir.

- 🔄 **Crefaz - Consulta CPFL - Fornecimento Suspenso**
  <small>_Adicionadas_</small>

  A partir desta versão, esta regra passará a existir.

- 🔄 **Crefaz - Consulta CPFL - Titularidade – PF**
  <small>_Adicionadas_</small>

  A partir desta versão, esta regra passará a existir.

- 🔄 **Crefaz - Consulta CPFL - Valida UC – PF**
  <small>_Adicionadas_</small>

  A partir desta versão, esta regra passará a existir.

##### V25.0723 &nbsp; <sub>23/07/2025</sub>

> **CIA:** `Todas as CIAs` · `NEO`

- ✅ **Int - Aprovacao Automatica**
  <small>_Adicionadas_</small>

  A partir desta versão, esta regra passará a existir.

- ✅ **Int - Aprovacao Automatica - Neo**
  <small>_Adicionadas_</small>

  A partir desta versão, esta regra passará a existir.

- 🔄 **Int - Codigo de Barras faz parte da blocklist**
  <small>_Adicionadas_</small>

  A partir desta versão, esta regra passará a existir.

##### V25.0729 &nbsp; <sub>29/07/2025</sub>

> **CIA:** `CPFL` · `COSERN`

- 📝 **Int – Matriz de Liberacao**
  <small>_Alteradas_</small>

  A partir desta versão, os valores máximos liberados para alguns rating’s da CPFL foram alterados e passaram a ser de R$ 4.000,00.

- 📝 **Int - Rating**
  <small>_Alteradas_</small>

  A partir desta versão, os rating’s H e I da COSERN serão classificados corretamente.

---

#### Agosto · 1 mudança

##### V25.0821 &nbsp; <sub>21/08/2025</sub>

> **CIA:** `Todas as CIAs`

- 📝 **Distância App e Cliente**
  <small>_Alterada_</small>

  A partir desta versão, esta regra deixará de negar o cliente.

---

#### Setembro · 10 mudanças

##### V25.0918 &nbsp; <sub>18/09/2025</sub>

> **CIA:** `ENEL`

- 🔄 **Int - Matriz de Liberação**
  <small>_Alterada_</small>

  A partir desta versão, o valor máximo liberado para a ENEL passará a ser de R$ 2.200,00 (RJ e CE) e R$ 2.500,00 (SP).

##### V25.0923 &nbsp; <sub>23/09/2025</sub>

> **CIA:** `ENEL SP` · `ENEL CE` · `ENEL RJ` · `Todas as CIAs`

- 💰 **Int - Matriz de Liberação**
  <small>_Alteradas_</small>

  A partir desta versão, o valor liberado para a ENEL passa a ser maior: ENEL CE e RJ (R$ 2.200,00), ENEL SP (R$2.500,00).

- 🔌 **SPC - Valida CCF**
  <small>_Alteradas_</small>

  A partir desta versão, consultaremos primeiro a API da POD, e somente em caso de contingência, a do SPC Full Service.

- 🔌 **SPC - Valida Data de Nascimento**
  <small>_Alteradas_</small>

  A partir desta versão, consultaremos primeiro a API da POD, e somente em caso de contingência, a do SPC Full Service.

- 🔌 **SPC - Valida Obito**
  <small>_Alteradas_</small>

  A partir desta versão, consultaremos primeiro a API da POD, e somente em caso de contingência, a do SPC Full Service.

- 🔌 **SPC - Valida Restricoes**
  <small>_Alteradas_</small>

  A partir desta versão, consultaremos primeiro a API da POD, e somente em caso de contingência, a do SPC Full Service.

- 🔌 **SPC - Valida Status CPF**
  <small>_Alteradas_</small>

  A partir desta versão, consultaremos primeiro a API da POD, e somente em caso de contingência, a do SPC Full Service.

- 🔌 **SPC - Valida Consultas**
  <small>_Alteradas_</small>

  A partir desta versão, consultaremos primeiro a API da POD, e somente em caso de contingência, a do SPC Full Service.

- 🔄 **Valida vinculo do CPF na Cia**
  <small>_Adicionada_</small>

  A partir desta versão, esta regra passará a existir.

##### V25.0930 &nbsp; <sub>30/09/2025</sub>

> **CIA:** `NEO`

- 🔄 **NeoEnergia - Verifica Titularidade – PF**
  <small>_Adicionadas_</small>

  A partir desta versão, esta regra passará a existir.

---

#### Outubro · 1 mudança

##### V25.1009 &nbsp; <sub>09/10/2025</sub>

> **CIA:** `Todas as CIAs`

- 🆕 **Valida Motivo de Recusa 8**
  <small>_Adicionada_</small>

  A partir desta versão, esta regra passou a existir.

---

#### Novembro · 5 mudanças

##### V25.1110 &nbsp; <sub>10/11/2025</sub>

> **CIA:** `Todas as CIAs`

- 📝 **SPC – Valida Data de Nascimento**
  <small>_Alteradas_</small>

  A partir desta versão, caso o Bureau da PoD nos retorne que o cliente é menor de idade, não consultaremos mais o bureau da SPC e nem da ACP, já que não se faz necessário. Outro bureau será consultado, somente em caso de falha no anterior (contingência).

##### V25.1120 &nbsp; <sub>20/11/2025</sub>

> **CIA:** `ENEL` · `ENEL CE` · `ENEL RJ` · `ENEL SP`

- 🔌 **API ENEL X – Valida Tempo Ativacao Contrato**
  <small>_Adicionadas_</small>

  A partir desta versão, esta regra passou a existir.

- 🔌 **API ENEL – CE – Valida UC – PF**
  <small>_Adicionadas_</small>

  A partir desta versão, esta regra passou a existir.

- 🔌 **API ENEL – RJ – Valida UC – PF**
  <small>_Adicionadas_</small>

  A partir desta versão, esta regra passou a existir.

- 🔌 **API ENEL – SP – Valida UC – PF**
  <small>_Adicionadas_</small>

  A partir desta versão, esta regra passou a existir.

---


### 2026

#### Janeiro · 3 mudanças

##### V26.0113 &nbsp; <sub>13/01/2026</sub>

> **CIA:** `CPFL` · `Todas as CIAs`

- 🔌 **CPFL WS GMP - Valida Valor Parcela**
  <small>_Adicionada_</small>

  A partir desta versão, esta regra passou a existir.

- 📝 **SPC - Valida Idade**
  <small>_Alteradas_</small>

  A partir desta versão, haverá a possibilidade de solicitar reanálise para esta regra.

- 🚫 **Int – Cliente com acordo de cobrança em curso**
  <small>_Alteradas_</small>

  A partir desta versão, caso o cliente possua acordo, será negado nesta regra.

---

#### Fevereiro · 2 mudanças

##### V26.0204 &nbsp; <sub>04/02/2026</sub>

> **CIA:** `CPFL` · `RGE` · `Todas as CIAs`

- 📝 **Valida vinculo do CPF na Cia**
  <small>_Alteradas_</small>

  A partir desta versão, clientes CPFL/RGE que não possuam UC, ou possuam, mas não esteja ativa, serão negados.

- 🆕 **Int – Valida blocklist geolocalização**
  <small>_Adicionada_</small>

  A partir desta versão, esta regra passou a existir.

---

#### Março · 1 mudança

##### V26.0302 &nbsp; <sub>02/03/2026</sub>

> **CIA:** `CPFL`

- 🚫 **Crefaz - Consulta CPFL - Validação Luz em DIA - PF**
  <small>_Alterada_</small>

    - A partir desta versão, caso o cliente possua alguma fatura com 3 ou mais dias de atraso, ela será classificada como Luz em Dia.
  - Porém, caso haja 3 ou mais faturas em atraso, a proposta será negada.
  - Também haverá novo valor liberado para o cliente Luz em Dia, deixando de ser fixo e passando a ser de acordo com o rating do cliente.

---
