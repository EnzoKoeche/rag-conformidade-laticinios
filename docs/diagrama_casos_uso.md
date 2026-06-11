# Diagrama de casos de uso

```mermaid
graph LR
    AN([" Analista "])
    MA([" Mantenedor "])
    AV([" Avaliador "])

    subgraph Sistema["rag-conformidade-laticinios"]
        UC1("UC-01<br/>Perguntar sobre<br/>conformidade")
        UC2("UC-02<br/>Pergunta fora<br/>do domínio")
        UC3("UC-03<br/>'Não sei' honesto<br/>(sem base)")
        UC4("UC-04<br/>Injeção via<br/>pergunta")
        UC5("UC-05<br/>Injeção via<br/>documento")
        UC6("UC-06<br/>Ingestão<br/>incremental")
        UC7("UC-07<br/>Comparar estratégias<br/>de retrieval")
        UC7x("Pipeline de retrieval<br/>(4 estratégias)")
    end

    AN --> UC1
    AN --> UC2
    AN --> UC4
    MA --> UC6
    MA -. "doc comprometido<br/>sem saber" .-> UC5
    AV --> UC7

    UC1 -. "«extend»<br/>sem chunk aprovado /<br/>2 ciclos esgotados" .-> UC3
    UC1 -. "«include»<br/>retrieve→grade→generate→verify" .-> UC7x
    UC7 -. "«include»" .-> UC7x
    UC4 -. "«extend»" .-> UC3
```

Leitura: UC-01 é o fluxo feliz; UC-03 é a saída honesta compartilhada por baixa
similaridade, documento não indexado e ciclos de correção esgotados; UC-04/05 são os
cenários adversariais exigidos pelos requisitos (RF-09); o pipeline de retrieval é o
componente comum entre o uso interativo e a avaliação comparativa (UC-07).
