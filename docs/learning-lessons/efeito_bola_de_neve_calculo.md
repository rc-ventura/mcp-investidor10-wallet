# Efeito bola de neve: usar rendimento recorrente atual, nunca DY médio

**Context:** Sessão de 17/10/2026 — usuário pediu quantas cotas de MXRF11 e dos FIIs da carteira ativam o "efeito bola de neve". Primeira tentativa usou DY 12m (`cotas = 1200/dy`) e depois média dos últimos 12 rendimentos; o usuário corrigiu que CDII11 hoje paga R$ 1,00/cota e a média inflada por pagamentos extras estava errada (dava 78 cotas vs. 95 reais).
**Date:** 2026-10-17
**Future intent:** Adotar esta metodologia em toda simulação de renda/bola de neve e, se uma tool de "renda projetada" for criada, embutir a detecção de piso recorrente vs. extras.

---

## Mental Model: definição e escopo do efeito

```
Bola de neve = proventos mensais recebidos ≥ preço de 1 cota
             → a posição compra 1 cota nova por mês sozinha

     cotas_necessárias = ceil(preço_atual / rendimento_mensal_por_cota)
```

| Classe | Aplica? | Por quê |
|---|---|---|
| FIIs | Sim — efeito literal | Pagam todo mês; o reforço é mensal de verdade |
| Ações B3 | Só como média conceitual | Pagam em lotes (semestral/trimestral); não existe "compra mensal" real |
| ETFs internacionais | Impraticável | Mesmo efeito lote + withholding 30%; cotas caras → centenas de cotas necessárias |
| Tesouro / Cripto | Não | Não distribuem renda; "bola de neve" é juro composto embutido no preço |

## Lição central: qual rendimento usar

**Não usar** (ambos falharam na prática):

- `DY 12m` (`1200/dy`) — mistura pagamentos extraordinários com piso; para CDII11 deu 78 cotas.
- Média simples dos últimos 12 pagamentos — mesmo problema: CDII11 tinha R$ 1,23–1,61 extras no início do ano, inflando a média para R$ 1,22 quando o piso atual é R$ 1,00. Deu 78 cotas; a resposta certa era 95.

**Usar**: o **rendimento recorrente atual** = o valor que se repete nos últimos ~5–6 pagamentos (o "piso"), ignorando extras pontuais. Verificar a série com datas antes de assumir.

Exemplo real (CDII11, mais recente primeiro): `1,00 × 5 meses seguidos` depois `1,23 / 1,38 / 1,14 / 1,32 / 1,52 / 1,39 / 1,61` → piso = **R$ 1,00**, não a média.

Sinais de que o último pagamento NÃO é o piso: JURO11 alterna `0,75 / 1,00 / 0,75 / 0,50 / 1,00...` — aí a média dos recentes é mais honesta que o último isolado; declarar a escolha.

## Fonte de dados (API upstream, fora do MCP)

```
GET https://investidor10.com.br/api/rest/assets/fiis/{ticker}
    last_quotation.price          → cota atual
    payments[] (mais novo → mais antigo)
        .payment_date, .amount_paid, .type == "DIV"
```

```python
pays = [
    p["amount_paid"] for p in d["payments"] if p["type"] == "DIV" and p["amount_paid"]
]
recorrente = piso_dos_ultimos_6(pays)  # não média cega
cotas = math.ceil(price / recorrente)
```

## Resultado validado na sessão (17/10/2026)

| FII | Cota | Rendimento usado | Cotas p/ neve |
|---|---|---|---|
| MXRF11 | 9,34 | 0,10 (estável 2+ anos) | 94 |
| CDII11 | 94,50 | 1,00 (piso, 5 meses) | 95 |
| IRIM11 | 65,90 | 0,75 (piso) | 88 |
| JURO11 | 98,90 | 0,75 (oscila 0,75–1,00) | 132 (conservador) |

## Próximos passos

- Em toda resposta de renda projetada: mostrar o rendimento usado e o racional (piso vs. média), nunca o número nu.
- Se criar tool de projeção: implementar detecção de regime — mediana dos últimos 6 pagamentos como piso e flag de "extras detectados" quando desvio > ~20%.
- Cruzar com a lesson `earnings_list_detalhe_proventos_por_ativo`: `payments[]` do endpoint de FIIs dá o rendimento por cota; `/earnings/list/{wallet}` dá o que a carteira efetivamente recebeu — fontes complementares (declarado vs. recebido).
