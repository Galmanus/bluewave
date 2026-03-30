# Anti-Timeout Protocol (OBRIGATÓRIO)

Regra absoluta para TODA sessão Claude neste servidor. Violação = timeout = falha.

## 1. Nunca processar mais de 4 arquivos por chamada
- Precisa ler 12 arquivos? → 3 chamadas Read paralelas de 4 cada
- NUNCA sequencial

## 2. Bash sempre com timeout máximo para operações pesadas
- Todo comando Bash que leva >5s DEVE ter `timeout: 600000`
- SSH para servidores remotos: SEMPRE `timeout: 600000`

## 3. Análise complexa = Agents paralelos
- Análise de projeto inteiro → mínimo 3 Agents em paralelo (backend, frontend, infra)
- Cada Agent analisa no máximo 1 diretório/componente
- NUNCA um único Agent para projeto inteiro

## 4. SSH remoto = background
- Comandos SSH para IALUM_DEV (2a02:4780:14:e3ce::1) ou qualquer servidor remoto: `run_in_background: true`
- Exceto comandos simples (<5s esperado)

## 5. Resposta parcial > timeout
- Se uma sub-tarefa falhar, entregar o que já tem
- NUNCA esperar todas as sub-tarefas para responder
- Resultado parcial + "[continuando...]" > silêncio + timeout

## 6. Limites por tipo de operação
| Operação | Max arquivos | Max por Agent | Timeout |
|---|---|---|---|
| Read | 4 paralelos | N/A | default |
| Análise de projeto | N/A | 1 componente | 600000 |
| SSH remoto | N/A | 1 comando | 600000 + background |
| Docker build/restart | N/A | 1 container | 600000 |
| Git operations | N/A | N/A | 600000 |
