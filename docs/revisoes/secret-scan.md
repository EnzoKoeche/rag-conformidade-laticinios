# Secret-scan do histórico — 2026-06-12 (pré-publicação)

Comando: `uv run python scripts/secret_scan.py`

- **Escopo:** todos os diffs de todos os commits (`git log -p --all`) + árvore de
  trabalho atual (exceto `.git/`, `.venv/`, `data/` e binários).
- **Padrões (9):** chaves Anthropic (`sk-ant-`), OpenAI, AWS, GitHub, Google, Slack,
  webhook secrets, blocos de chave privada e atribuições genéricas
  `api_key/secret/token/senha = "..."`.
- **Allowlist auditada:** `sk-ant-teste-fake` (chave obviamente falsa usada nos testes
  do guard de custo) e placeholders.

## Resultado

```
commits varridos: 8 | padrões: 9
✓ nenhum segredo encontrado no histórico nem na árvore atual
```

## Re-scan pré-push — 2026-06-11 (manhã)

Re-executado após os commits da sessão de revisão (golden revisado, fix densa,
validação Docker, docs):

```
commits varridos: 13 | padrões: 9
✓ nenhum segredo encontrado no histórico nem na árvore atual
```

`git log --stat` revisado. O commit seguinte a este re-scan adiciona apenas este
relatório (arquivo de texto sem segredos, conferível no diff); o push é feito logo
após. Ambiente sem `.env` durante toda a sessão.

## Correção do scanner — 2026-06-11 (tarde)

Ao colar a chave real no `.env` (local, para a eval paga), o scanner **flagou o
`.env`** — ele varria a árvore inteira com `rglob`, incluindo arquivos gitignorados, e
chegou a imprimir um trecho da chave. Falha do scanner, não do repo: o `.env` está
gitignorado desde o commit zero e **nunca** entrou em commit (verificado:
`git log --all -- .env` vazio; `git ls-files` sem `.env`).

Corrigido: a varredura da árvore passou a usar
`git ls-files --cached --others --exclude-standard` — só arquivos que o git versionaria
(rastreados + não-ignorados). Gitignorados (`.env`, `.venv/`, `data/`) ficam de fora,
que é exatamente o conjunto que importa para "nenhum segredo NO repo". Pós-correção:
**21 commits varridos, árvore limpa, 0 achados** — sem ler o `.env`.

**O que isto prova:** nenhum segredo com formato conhecido entrou em nenhum commit.
**O que NÃO prova:** segredo de formato exótico/custom não seria detectado pelos
padrões; a varredura é por regex, não por entropia. O `.env` é ignorado desde o commit
zero e nunca existiu na árvore versionada.

> Recomendações para amanhã, antes do push: rodar o scan de novo (este arquivo entra em
> commit novo) e conferir `git log --stat` visualmente — leva 2 minutos.
