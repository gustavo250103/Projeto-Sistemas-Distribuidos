# Sistema Distribuído de Mensagens

Este repositório implementa um sistema completo de troca de mensagens inspirado em BBS/IRC. Utilizamos ZeroMQ como camada de transporte, MessagePack para serialização binária e Docker para orquestrar todos os serviços. O trabalho foi dividido em cinco etapas (mais um serviço extra em Go) cobrindo Request/Reply, Publish/Subscribe, serialização binária, relógios e replicação de dados.

---

## Visão Geral

- Comunicação **REQ/REP** entre clientes/bots e servidores via broker.
- Comunicação **PUB/SUB** entre servidores e consumidores via proxy.
- Serialização binária com MessagePack.
- Relógios lógicos (Lamport) em todos os processos e sincronização Berkeley via servidor de referência.
- Replicação eventual: todos os servidores recebem cada operação via tópico interno 
eplica.
- Linguagens: **Python**, **Node.js** e **Go**.

---

## Estrutura de Diretórios

`	text
.
├── src/
│   ├── bot/              # Bots automáticos (Node.js)
│   ├── broker/           # Broker REQ/REP (Python)
│   ├── client/           # Cliente interativo (Python)
│   ├── go-listener/      # Listener escrito em Go
│   ├── proxy/            # Proxy PUB/SUB (Python)
│   ├── reference/        # Servidor de referência (Python)
│   └── server/           # Servidores principais (Python)
├── Dockerfile            # Imagem base dos componentes em Python
├── docker-compose.yml    # Orquestração completa
└── README.md             # Este documento
`

---

## Componentes

| Serviço           | Linguagem | Função principal                                                |
|-------------------|-----------|-----------------------------------------------------------------|
| reference         | Python    | Controla rank, heartbeat e clock (algoritmo de Berkeley)        |
| broker            | Python    | ROUTER/DEALER para o tráfego REQ/REP                            |
| proxy             | Python    | XSUB/XPUB para o tráfego PUB/SUB                                |
| server (3 réplicas) | Python  | Processa requisições, persiste e replica os dados               |
| client            | Python    | Interface interativa (login, canais, mensagens privadas)        |
| bot (2 réplicas)  | Node.js   | Publica mensagens aleatórias em canais                          |
| go-listener       | Go        | Listener adicional inscrito nos tópicos geral e servers     |

---

## Funcionalidades por Parte

1. **Parte 1 – Request/Reply**: login, listagem de usuários/canais, persistência básica.
2. **Parte 2 – Publish/Subscribe**: canais públicos, mensagens privadas e bots automáticos.
3. **Parte 3 – MessagePack**: todas as mensagens passam para formato binário.
4. **Parte 4 – Relógios**: Lamport em todos, sincronização Berkeley, eleição do coordenador.
5. **Parte 5 – Replicação**: eventos de usuário/canal/mensagem são propagados via tópico 
eplica.
6. **Listener Go**: terceira linguagem exigida, assinando tópicos do proxy.

---

## Persistência

| Arquivo              | Descrição                           |
|----------------------|-------------------------------------|
| data/users.json    | Usuários cadastrados                |
| data/channels.json | Canais criados                      |
| data/messages.log  | Histórico de mensagens/publicações  |

Cada servidor monta data como volume; como todos aplicam as replicações, os arquivos convergem.

---

## Execução com Docker

### Pré-requisitos
- Docker
- Docker Compose

### Subir todos os serviços
`ash
cd src
docker compose up -d --build
`

### Acompanhar os logs
`ash
docker compose logs -f reference
docker compose logs -f server
docker compose logs -f bot
docker compose logs -f go-listener
`

### Cliente interativo
`ash
docker compose run --rm client
`
1. Digite um nome para login.
2. Use a opção 6 para assinar o canal geral.
3. Opções 4/5 publicam em canais ou enviam mensagens privadas.

### Encerrar
`ash
docker compose down
`
Use docker compose down -v --remove-orphans para liberar volumes.

---

## Branches

| Branch                        | Descrição                               |
|-------------------------------|-----------------------------------------|
| feature/parte1-request-reply  | Implementação da Parte 1 (REQ/REP)      |
| feature/parte2-pub-sub        | Implementação da Parte 2 (PUB/SUB)      |
| feature/parte3-messagepack    | Implementação da Parte 3 (MessagePack)  |
| feature/parte4-relogios       | Implementação da Parte 4 (relógios)     |
| feature/parte5-consistencia   | Implementação da Parte 5 (replicação)   |
| feature/go-listener           | Listener extra em Go (3ª linguagem)     |

Faça checkout de cada branch com git checkout <nome>; após finalizar a parte, faça merge em main e git push origin main.

---

## Fluxo das mensagens

`	text
Clientes/Bots --REQ--> Broker --DEALER--> Servidores (x3)
                              ^
                              |
                        Servidor de referência

Servidores --PUB--> Proxy (XPUB/XSUB) --SUB--> Clientes/Bots/Go-listener
            |\
            | \__ tópico "replica"  -> replicação de dados
            |____ tópico "servers"  -> anúncios de coordenador
`

---

## Testes sugeridos

1. **Replicação** – envie mensagens, pare src-server-1 e observe 
eference. Ao religar, o histórico permanece íntegro graças ao tópico 
eplica.
2. **Relógios** – acompanhe o campo clock retornado às chamadas; os incrementos de Lamport aparecem para cada evento.
3. **Listener Go** – docker compose logs -f go-listener exibe todas as mensagens recebidas em geral e servers.

---

## Tecnologias
- ZeroMQ (pyzmq, zeromq.js, zmq4)
- MessagePack
- Docker e Docker Compose
- Python 3.13, Node.js 20, Go 1.22

---

## Critérios atendidos
- Cliente com bibliotecas corretas, REQ/REP + PUB/SUB, relógio lógico.
- Bots automáticos seguindo o protocolo.
- Broker, proxy e reference com rank, heartbeat e clock.
- Servidores com Lamport, Berkeley, coordenação e replicação.
- Documentação neste README.
- Apresentação suportada pelos comandos e logs.
- Três linguagens diferentes.

---

## Licença
Projeto desenvolvido para a disciplina de Sistemas Distribuídos.
