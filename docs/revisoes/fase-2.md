# Auto-revisão adversarial — Fase 2 (grafo agêntico + evals grátis)

A eval de groundedness funcionou como detectora de defeitos de DESIGN — três rodadas de
achado→correção até o gate G3 ficar verde de forma honesta.

## Achados REAIS (corrigidos)

| # | Achado | Como foi pego | Correção |
|---|---|---|---|
| 1 | 2 de 3 perguntas `sem_base` eram RESPONDIDAS: o grader léxico aprovava chunks "relacionados mas não-resposta" (pergunta sobre *validade* recebia artigo de *temperatura*) | EVAL-GRD-01 (1/3 recusas) | grading por cross-encoder local com limiar calibrado em dados (sem_base ≤ -0,17 vs respondíveis ≥ +1,07 no top-1 → limiar 0,5) |
| 2 | O loop corretivo DERROTAVA a recusa honesta: a query reformulada ("limite"→"máximo padrão") elevava o score do reranker acima do limiar | diagnóstico com scores por ciclo | princípio: retrieval usa a query reformulada, mas **grading e geração usam sempre a pergunta ORIGINAL** |
| 3 | Mesmo com #2, o grader usava o score ARMAZENADO do retrieval (calculado com a query reformulada) — a correção não tinha efeito | re-execução da eval (ainda 1/3) | grader **re-pontua** (pergunta original, chunk) com o cross-encoder, em lote |
| 4 | "Quanto tempo após a publicação a IN 76/2018 entrou em vigor?" caía em FORA DO DOMÍNIO — o léxico não tem termo lácteo nessa frase | trace da eval (`entender_pergunta:fora`) | classificador reconhece referência a norma (`RE_REF_NORMA`: IN/Decreto/Portaria + número) |
| 5 | Dry-run das evals pagas comparava custo de EVAL (geração + 2 juízes) com o alvo RNF-03, que é custo do SISTEMA por pergunta | leitura crítica da saída (✗ falso) | relatório separa `custo_sistema_por_pergunta` (US$ 0,005 ✓ projetado) de `custo_eval_por_item` (US$ 0,0126) |

## Tradeoff ACEITO (documentado, não corrigido)

**Taxa de resposta do modo demo: 24/27 (89%).** G-12 ("como o RIISPOA define queijo?"),
G-20 ("por que manter a vaca em pé?") e G-27 (vigência) têm chunk-fonte com score CE de
**-0,05 / -0,96 / -0,35** — dentro/abaixo do range das perguntas sem resposta (máx
-0,17). **Não existe limiar que separe**: é limitação do cross-encoder mMARCO nesses
estilos de pergunta (meta-pergunta, "por quê", prazo de vigência). Decisão: manter o
limiar 0,5 e priorizar a premissa nº 1 (nunca inventar > sempre responder). O modo real
usa grader LLM — as evals pagas de amanhã medem se ele resolve esses 3 casos.

## Caveats conhecidos

- O limiar 0,5 foi calibrado no próprio golden (n=30) — vale como guarda de regressão,
  não como verdade universal; está registrado no docstring do `GraderHeuristico`.
- O verificador de groundedness é lexical (linha citada + sobreposição ≥ 0,4): prova o
  CONTRATO de citação, não qualidade semântica — papel das evals pagas (faithfulness).
- p95 de ~8 s no grafo demo = caminho sem_base (3 retrievals + 3 grades com cross-encoder);
  p50 270 ms ✓ RNF-02. Se p95 importar, reduzir a 1 ciclo ou paralelizar (evolução).

## Estado ao fim da fase

72 testes verdes · 100% cobertura em citacao, grafo/*, llm/cliente (+ os módulos da fase 1)
· EVAL-GRD-01: 0 violações de citação, 3/3 recusas honestas, 24/24 respostas citando fonte
esperada, p50 270 ms · dry-run pago: 30 chamadas, US$ 0,126 total, sistema US$ 0,005/pergunta.
