# Imóveis POA — avaliação por ITBI × IPTU

Motor que cruza **dados abertos oficiais da Prefeitura de Porto Alegre** para avaliar imóveis a partir de transação real, não de "achismo de anúncio".

- **ITBI** = preço de **venda real** (só dos imóveis que foram vendidos).
- **IPTU** = **cadastro completo** da cidade: valor venal, área, uso, imposto — de **todos** os imóveis, inclusive os que nunca venderam.

Cruzando os dois, para cada bairro e cada rua você obtém:

| Coluna | O que é |
|---|---|
| **venda real R$/m²** | mediana do que de fato se vendeu (ITBI) |
| **venal R$/m²** | valor venal médio do cadastro (IPTU) |
| **prêmio de mercado** | venda ÷ venal — o multiplicador que transforma o venal de QUALQUER imóvel em valor de mercado estimado |
| **giro %** | nº de vendas ÷ nº de imóveis — liquidez (facilidade de revenda) |
| **IPTU/ano** | custo de carrego mediano |

## Como rodar na sua máquina

Pré-requisito: **Python 3** instalado.

```bash
# 1. baixa os dados oficiais (ITBI 2023-2026 + IPTU 2026) de dadosabertos.poa.br
python scripts/fetch_dados_poa.py

# 2. monta a baseline de venda real (ITBI) por bairro e logradouro
python scripts/poa_itbi.py

# 3. cruza com o IPTU -> prêmio de mercado, giro, custo de carrego
python scripts/poa_cross.py
```

Saídas (em `data/poa/`):
- `poa_cross_bairro.csv` — ITBI × IPTU por bairro
- `poa_cross_logradouro.csv` — o mesmo por logradouro (comparável fino)
- `poa_baseline_bairro.csv` / `poa_baseline_logradouro.csv` — só venda real (ITBI)

> Os mesmos CSVs já vêm prontos na pasta `dados/` deste pacote — você pode abrir no Excel sem rodar nada. Rode os scripts quando quiser **atualizar** com dado novo.

## Como usar na prática

1. **Avaliar um imóvel:** pegue o valor venal dele (está no carnê do IPTU ou no cadastro) e multiplique pelo **prêmio** do bairro → estimativa de mercado. Ex.: venal R$ 600.000 em Moinhos de Vento (prêmio 1,71×) → **~R$ 1,03 mi**.
2. **Conferir um anúncio:** compare o R$/m² pedido com a **venda real** da rua/bairro. Acima = caro; abaixo = oportunidade.
3. **Negociar:** o prêmio e o giro são argumento objetivo ("nesta rua o mercado paga X e gira Y% ao ano").

## O valor que isso gera

- **Avaliação (AVM) ancorada em transação real + cadastro oficial** — não em opinião.
- **Garimpo de subavaliados:** quem está abaixo da venda real da região.
- **Validação de anúncio:** área/uso/ano oficiais do IPTU pegam metragem inflada.
- **Liquidez e custo de carrego** entram na conta da decisão.

## Fontes (dado aberto, público)

- ITBI: https://dadosabertos.poa.br/dataset/itbi
- IPTU: https://dadosabertos.poa.br/dataset/iptu

*Caveat honesto: o `base_de_calculo` do ITBI e o valor venal do IPTU são bases fiscais — tendem a ser piso conservador do mercado. O prêmio é mais confiável como multiplicador dentro de áreas de padrão parecido.*
