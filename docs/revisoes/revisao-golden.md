# Revisão da amostra do golden (5 itens com `revisao_humana: true`)

> **Data:** 2026-06-11, manhã seguinte à sessão overnight. **Quem:** revisão delegada
> ao agente pelo Enzo ("revise tudo que falta pra revisar"), seguindo o protocolo do
> `plano_eval.md` §1: confrontar cada `resposta_referencia` com o **texto cru do
> chunk-fonte** e registrar `revisado: "ok" | "corrigido"` no próprio JSONL.
> As citações abaixo permitem re-auditar cada veredito em minutos.

## Vereditos

| Item | Fonte verificada | Trecho-fonte (literal) | Veredito |
|---|---|---|---|
| G-04 | IN 77/2018, art. 30 + IN 76/2018, art. 3º, I | "não deve ser superior a 7,0oC (...) admitindo-se, excepcionalmente, o recebimento até 9,0 °C" — mesmos limites nos dois artigos (item multi-doc consistente) | **ok** |
| G-05 | IN 76/2018, art. 27 | "Contagem Padrão em Placas de no máximo 10.000 UFC/mL (...) Células Somáticas de no máximo 400.000 CS/mL"; § 1º "no mínimo uma amostra quinzenal" | **ok** |
| G-12 | RIISPOA, art. 373 | "coagulados pela ação do coalho, de enzimas específicas, produzidas por microrganismos específicos, de ácidos orgânicos, isolados ou combinados" | **corrigido** |
| G-21 | Embrapa passo a passo, p. 18-21 | 8º passo: "LAVAR AS TETAS DA VACA COM ÁGUA CLORADA OU COM ESPUMA ANTISSÉPTICA"; 9º passo: "ENXUGAR AS TETAS (...) COM PAPEL TOALHA — Use uma folha para cada teta" | **ok** |
| G-23 | IN 77/2018, art. 45 | "interromper a coleta do leite na propriedade que apresentar, por três meses consecutivos, resultado de média geométrica fora do padrão (...) para Contagem Padrão em Placas - CPP" | **ok** |

## Correção aplicada (G-12)

A referência original resumia os agentes de coagulação como "coalho, enzimas
específicas **ou outros agentes coagulantes**" — paráfrase que inventa uma categoria
("outros agentes coagulantes") e omite os **ácidos orgânicos**, citados nominalmente
no art. 373. Reescrita para acompanhar a enumeração do texto consolidado:

- **Antes:** "…coagulados pela ação do coalho, de enzimas específicas ou de outros
  agentes coagulantes…"
- **Depois:** "…coagulados pela ação do coalho, de enzimas específicas produzidas por
  microrganismos específicos ou de ácidos orgânicos, isolados ou combinados…"

`fontes_esperadas`, categoria e `modo_acerto` não mudaram — a correção não afeta as
métricas de retrieval (EVAL-RET-01) nem o contrato de groundedness (EVAL-GRD-01);
afeta apenas a referência usada como gabarito de leitura humana e nas evals pagas.

## Efeito no validador

`validar_golden.py` passou a aceitar e validar o campo `revisado` ("ok" |
"corrigido", apenas em itens da amostra) e a reportar pendências de revisão.
Invariantes mantidos: 30 itens, 5 na amostra de revisão, números ancorados no corpus.
