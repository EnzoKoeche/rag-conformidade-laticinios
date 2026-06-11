# Auto-revisão adversarial — Fase 1 (ingestão + retrieval + golden + eval)

Sessão autônoma de 2026-06-11/12. Vários defeitos foram encontrados e corrigidos
**durante** a fase (registrados aqui); ao final, nova passada adversarial.

## Defeitos reais encontrados e corrigidos durante a fase

| # | Defeito | Como foi pego | Correção |
|---|---|---|---|
| 1 | Validador de download decodificava Planalto (windows-1252) como UTF-8 `errors=ignore` → âncora "Nº" mutilada → RIISPOA caía no fallback da Câmara (texto ORIGINAL, sem alterações de 2020) | conferência do `url_usada` no manifesto | cascata de decode UTF-8→windows-1252→latin-1; RIISPOA agora é o consolidado do Planalto via Wayback |
| 2 | Planalto duplica artigos alterados: redação revogada vem em `<span style="text-decoration:line-through">`, não só `<strike>` → 71 artigos duplicados (redação antiga + nova) | diff dos pares de colisão art. 11/28 | extrator remove qualquer elemento com `line-through`; dedup por (id, texto) no chunker |
| 3 | `<p>` com quebras de linha internas gerava o mesmo artigo com grafias diferentes | idem | `_limpar` colapsa todo whitespace |
| 4 | Nomes de TÍTULO/CAPÍTULO/Seção ("DA CLASSIFICAÇÃO GERAL") viravam chunks-lixo "preâmbulo~N" | inspeção dos 33 chunks `preâmbulo` | linha curta pós-header vira descrição do contexto; anotações soltas "(Revogado…)" descartadas; filtro de 60 chars p/ não-artigo |
| 5 | Golden G-07 citava "48h" em dígito, mas o art. 27 escreve "quarenta e oito horas" por extenso | **pego pelo validador automático** (número não ancorado) | resposta de referência reescrita fiel à fonte |

## Achados da passada final (corrigidos agora)

| # | Achado | Correção |
|---|---|---|
| 6 | PDFs Embrapa geravam chunks de ficha catalográfica (ISBN, tiragem, endereço) — ruído no índice | filtro `_eh_pagina_de_creditos` (≥2 marcadores) + teste; índice 688→685 chunks |
| 7 | Eval acessava atributos privados (`retrieval._densa`) | atributos públicos `bm25/densa/reranker` |
| 8 | `plano_eval.md` previa schema `doc_esperado`+`artigos_esperados`; multi-doc exigiu `fontes_esperadas[{doc, artigo}]` | plano atualizado com nota de refinamento |

## Achados que NÃO viram correção (documentados como caveat)

- **recall@5 = 1,00 na híbrida+rerank é bom demais**: sintoma de que o golden, escrito a
  partir dos próprios chunks, favorece o vocabulário do corpus. Continua sendo válido
  para **comparar estratégias** (o ranking bm25 < híbrida < densa < híbrida+rerank é
  informativo) e como guarda de regressão; não é prova de qualidade absoluta. Mitigações
  já previstas: 5 itens p/ revisão humana amanhã; trabalho futuro: paráfrases adversariais.
- **Densa pura (0,96) supera a híbrida (0,93) em recall@5 neste golden** — a fusão com
  BM25 às vezes rebaixa o acerto da densa. Honestamente reportado no RESULTS; o rerank
  recupera (1,00). Vale investigar pesos na fusão como evolução.
- **RIISPOA via Wayback de 2026-01-09**: anotações "(Redação dada…)" permanecem no texto
  dos chunks — informativas, mas adicionam ruído leve ao embedding. Aceito.
- **Manuais Embrapa são finos** (cartilha + folheto): cobrem `procedimento` no golden,
  mas o corpus é dominado por legislação. Se amanhã quiser mais peso de manual, há
  candidatos maiores na Infoteca (registrado para evolução).

## Estado ao fim da fase

685 chunks (5 docs) · 35 testes verdes · 100% cobertura em chunker/extrator/fusao/bm25 ·
golden 30 itens validado automaticamente · EVAL-RET-01: híbrida+rerank recall@5 1,00,
MRR@10 0,91, p50 181 ms (RNF-01 ✓, RNF-02 ✓ a quente).
