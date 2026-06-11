# Manual de perguntas — o que perguntar para a demo (e por quê)

> **Por que algumas perguntas "não funcionam".** A [demo pública](https://rag-conformidade.streamlit.app)
> roda na nuvem gratuita, que não comporta o modelo de embedding (BGE-m3) na RAM — então
> ela usa **só BM25**, que é busca **lexical**: casa palavras, não significado. Se você
> perguntar "o leite pode estar quente quando chega?", o BM25 não encontra — a norma diz
> "temperatura do leite cru refrigerado no ato de sua recepção". **Use o vocabulário da
> norma** (CCS, CPP, alizarol, leite cru refrigerado, recepção, granja leiteira…) e o
> sistema responde citando o artigo. Rodando local (`scripts/ingerir.py`), as 4
> estratégias ficam ativas e a busca passa a entender paráfrases.

As 24 perguntas abaixo foram **testadas no mesmo modo da nuvem** (BM25 + grader
cross-encoder): todas retornam resposta citada e aprovada pelo verificador de
groundedness. Pode copiar e colar.

## Limites numéricos (a fonte mais direta)

| Pergunta | Cita |
|---|---|
| Qual o limite máximo de Contagem de Células Somáticas (CCS) para o leite cru refrigerado? | IN 76/2018, art. 7º |
| Qual a Contagem Padrão em Placas máxima admitida para o leite cru refrigerado antes do processamento no estabelecimento beneficiador? | IN 76/2018, art. 8º |
| Qual o teor mínimo de gordura exigido do leite cru refrigerado? | IN 76/2018, art. 5º |
| Quais os limites de CPP e CCS para o leite cru destinado à fabricação de leite pasteurizado tipo A? | IN 76/2018, art. 27 |
| Em qual concentração mínima deve ser feito o teste do Álcool/Alizarol na seleção do leite cru? | IN 77/2018, art. 31 |
| Qual a temperatura máxima de conservação e expedição do leite no posto de refrigeração? | IN 76/2018, art. 3º |
| Qual a faixa de acidez aceitável para o leite pasteurizado? | IN 76/2018, art. 15 |

## Multi-documento (a resposta cruza duas normas)

| Pergunta | Cita |
|---|---|
| Qual a temperatura máxima do leite cru refrigerado no momento da recepção pelo estabelecimento? | IN 77/2018, art. 30 + IN 76/2018, art. 3º |

## Definições (RIISPOA e INs)

| Pergunta | Cita |
|---|---|
| O que é leite cru refrigerado? | IN 76/2018, art. 2º; RIISPOA, art. 355 |
| O que é leite pasteurizado tipo A e onde ele deve ser produzido? | IN 76/2018, art. 22 |
| O que é leite reconstituído? | RIISPOA, art. 361 |
| Quais tipos de leites fluidos são permitidos pelo RIISPOA? | RIISPOA, art. 354 |
| Como são classificados os estabelecimentos de leite e derivados? | RIISPOA, art. 21 |
| O que é pasteurização segundo o RIISPOA? | RIISPOA, art. 255 |

## Procedimentos

| Pergunta | Cita |
|---|---|
| Como deve ser realizado o processo de coleta do leite cru refrigerado na propriedade rural? | IN 77/2018, art. 21 |
| Quais análises o estabelecimento deve realizar diariamente no leite cru refrigerado de cada compartimento do veículo transportador? | IN 77/2018, art. 31 |
| O que deve ser feito com os carros-tanque de leite antes e depois do descarregamento? | IN 77/2018, art. 28 |
| Para que serve o teste da caneca de fundo escuro na ordenha? | Embrapa, passo a passo da ordenha, p. 17 |
| Como devem ser higienizadas as tetas da vaca antes da ordenha manual? | Embrapa, passo a passo da ordenha, p. 18-21 |

## Prazos e responsabilidades

| Pergunta | Cita |
|---|---|
| Qual o tempo máximo que pode transcorrer entre as coletas de leite nas propriedades rurais? | IN 77/2018, art. 27 |
| Em quanto tempo o leite transportado em latões em temperatura ambiente deve ser entregue ao estabelecimento? | IN 77/2018, art. 29 |
| Com que frequência mínima o leite cru estocado nos tanques deve ser analisado em laboratório da RBQL? | IN 77/2018, art. 40 |
| Em que situação o estabelecimento deve interromper a coleta de leite de uma propriedade rural? | IN 77/2018, art. 45 |
| Quais são as atribuições do médico veterinário responsável pela propriedade rural fornecedora de leite? | IN 77/2018, art. 4º |

## Para ver a recusa honesta (o sistema NÃO inventa)

Essas perguntas **não têm base** no corpus indexado — o sistema deve responder que não
encontrou, em vez de chutar. É uma feature, não um bug:

- Qual o limite máximo de aflatoxina M1 permitido no leite?
- Qual o limite de Contagem de Células Somáticas para o leite de cabra?
- Qual o prazo de validade do leite pasteurizado?

## Casos de borda conhecidos (recusa indevida na demo)

Estas três têm resposta no corpus, mas o grader cross-encoder da demo as recusa — é o
tradeoff documentado ("nunca inventar > sempre responder"); o modo real com LLM **não**
resolve (mede pior, ver [`eval/results/RESULTS_PAGAS.md`](../eval/results/RESULTS_PAGAS.md)):

- Como o RIISPOA define queijo? *(RIISPOA, art. 373)*
- Por que se recomenda manter a vaca em pé após a ordenha? *(Embrapa, p. 24-25)*
- Quanto tempo após a publicação a IN 76/2018 entrou em vigor? *(IN 76/2018, art. 37)*
