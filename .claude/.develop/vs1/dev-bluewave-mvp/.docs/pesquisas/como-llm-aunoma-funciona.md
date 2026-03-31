# Como Agentes Autônomos (LLM) Funcionam

## O loop básico

Um agente autônomo é essencialmente um **loop de decisão**:

```
while True:
    observação = perceber_ambiente()
    decisão = modelo.decidir(observação, contexto, objetivo)
    if decisão == AGIR:
        resultado = executar_ação(decisão.ação)
        contexto.append(resultado)
    elif decisão == RESPONDER:
        enviar_resposta(decisão.conteúdo)
    elif decisão == ESPERAR:
        continue
```

Não há mágica — é um LLM sendo chamado repetidamente, recebendo contexto e decidindo o próximo passo.

## Quando interagir de volta?

Existem duas arquiteturas principais:

### 1. Event-driven (baseado em eventos)

- O agente **não fica rodando**. Ele é **acionado** por um evento externo: uma mensagem nova, um webhook, um timer.
- Exemplo: um bot de chat só é invocado quando chega uma mensagem. Não há polling.

### 2. Polling com decisão

- O agente **verifica periodicamente** se há algo novo (nova mensagem, mudança de estado).
- A cada verificação, o LLM decide: "isso requer minha ação?"
- Isso é mais raro em produção porque é caro (cada check = chamada ao modelo).

## Como ele decide SE deve responder?

### Classifier/Score

Um modelo menor (ou heurística) avalia a entrada e decide se o agente principal deve ser ativado. Tipo um "filtro de relevância".

### System prompt com regras

O próprio LLM recebe instruções como: "Só responda se a mensagem for direcionada a você ou se contiver uma pergunta técnica." A decisão é do modelo.

### Tool use / Function calling

O modelo recebe ferramentas disponíveis e decide por si se precisa usar alguma. Se não precisa, fica quieto.

## O caso do NotebookLM (Google)

1. Você faz **upload de documentos** (PDFs, textos, etc.)
2. O sistema **indexa** esse conteúdo (chunking + embeddings)
3. Quando você pergunta algo, ele faz **retrieval** (busca semântica nos chunks relevantes)
4. Monta um prompt com os chunks encontrados + sua pergunta
5. O LLM gera a resposta **baseada nos documentos**

Ele **não fica lendo incessantemente**. É puramente reativo — você pergunta, ele busca e responde. O podcast gerado é um processo batch separado.

## Agentes com ferramentas (tipo Claude Code)

1. Recebe o pedido do usuário
2. Decide qual **ferramenta** usar (ler arquivo, rodar comando, editar código)
3. Recebe o resultado da ferramenta
4. Decide: "preciso de mais informação?" → volta ao passo 2
5. Ou: "tenho o suficiente" → responde ao usuário

É um **loop de raciocínio com ferramentas**, não polling contínuo. O modelo decide a cada passo se precisa agir mais ou se pode parar.

## Comparação de mecanismos

| Mecanismo | Como funciona | Custo |
|-----------|--------------|-------|
| Event-driven | Ativado por evento externo | Baixo |
| Polling + LLM | Verifica periodicamente, LLM decide | Alto |
| Polling + heurística | Verifica periodicamente, regra simples decide | Médio |
| RAG (NotebookLM) | Reativo — busca + gera sob demanda | Médio |
| Tool loop (Claude Code) | LLM decide próximo passo até concluir | Variável |

## Conclusão

A grande maioria dos agentes em produção é **event-driven**, não fica "lendo incessantemente". O custo de ficar chamando um LLM para decidir "devo agir?" seria proibitivo.
