# EVAL-PAGA — modo real (Haiku) · executada em 2026-06-11

Juiz independente Haiku (faithfulness por linha + answer relevancy) sobre o grafo em
**modo real** (classificador/grader/gerador LLM), retrieval `hibrida_rerank`, 10 itens
estratificados do golden. Comando: `uv run python eval/run_pagas.py --executar`.

## Custo

| | |
|---|---|
| Estimado (dry-run) | US$ 0,1259 |
| **Real** | **US$ 0,1253** (teto US$ 0,50, guard não disparou) |
| Chamadas de API | **271** (não 30) |
| Custo do sistema/pergunta (só geração, RNF-03) | ~US$ 0,005 ✓ |

A estimativa de **custo** cravou (US$ 0,1253 vs 0,1259), mas a de **número de chamadas**
errou feio: o dry-run assumiu 3 chamadas/item (gerar + 2 juízes); o grafo real chama o
**grader LLM uma vez por chunk recuperado** (até 10) e ainda reformula/regrada em ciclos
de correção → 271 chamadas. O custo bateu mesmo assim porque cada chamada de grading
gasta ~5 tokens de saída. *Ajuste pendente no harness: contar chamadas de grading no
plano.*

## Resultado: 5/10 respondidas, 5/10 recusadas

| Item | Modo real | Faithfulness | Relevância | Mesmo item no modo demo |
|---|---|---|---|---|
| G-04 temperatura recepção | respondeu | 2/2 linhas ✓ | relevante ✓ | responde ✓ |
| G-10 def. leite cru refrig. | respondeu | 2/2 ✓ | relevante ✓ | responde ✓ |
| G-02 CPP máxima | respondeu | 1/1 ✓ | relevante ✓ | responde ✓ |
| G-11 def. leite tipo A | respondeu | 2/2 ✓ | relevante ✓ | responde ✓ |
| G-03 gordura mínima | respondeu | 1/1 ✓ | relevante ✓ | responde ✓ |
| G-01 limite de CCS | **recusou** | — | — | **responde ✓** |
| G-07 tempo entre coletas | **recusou** | — | — | **responde ✓** |
| G-08 entrega em latões | **recusou** | — | — | **responde ✓** |
| G-16 coleta na propriedade | **recusou** | — | — | **responde ✓** |
| G-17 análises diárias | **recusou** | — | — | **responde ✓** |

**Quando responde, responde bem:** 5/5 das respondidas têm faithfulness 100% (toda linha
sustentada pelo trecho citado) e foram julgadas relevantes. Zero alucinação.

## Achado principal (o contrário da hipótese)

A pendência dizia: *"conferir se o grader LLM resolve os falsos negativos do grader demo
(G-12/G-20/G-27)"*. **O resultado foi o oposto.** O grader LLM (Haiku, `sim`/`não` por
chunk) é **mais conservador** que o cross-encoder local e recusou **5 perguntas
respondíveis** — e nenhuma delas é recusada pelo modo demo. Como o retrieval é o mesmo
(`hibrida_rerank`, recall@5 = 1,00) e o nó de grading usa a pergunta ORIGINAL nos dois
modos, a diferença é **só o grader**:

- **grader cross-encoder local (mMARCO):** responde 24/27 (recusa 3) — EVAL-GRD-01
- **grader LLM (Haiku zero-shot):** na amostra, responde 5/10 (recusa 5)

**Conclusão:** o modelo especializado local supera o LLM geral na tarefa binária de
relevância — de graça e com menos latência. Não dá pra assumir que "trocar pra LLM
melhora": tem que medir. O grader cross-encoder fica como a escolha padrão (é o que a
demo usa).

## Caveats honestos

- Amostra pequena (10 itens); os juízes também são Haiku (mesma família que gera) — risco
  de complacência intra-família.
- O grader LLM é um `sim`/`não` zero-shot enxuto (`max_tokens=5`). Um prompt de grading
  com few-shot/rubrica, ou grading em lote com justificativa, provavelmente recupera parte
  das recusas — **trabalho futuro**, não medido aqui.
- G-12/G-20/G-27 (os falsos negativos do demo) **não caíram na amostra estratificada** —
  dado o achado acima (o grader LLM recusa mais, não menos), a hipótese de que o modo real
  os resolveria fica desfavorecida, mas não foi testada diretamente nesses três itens.
