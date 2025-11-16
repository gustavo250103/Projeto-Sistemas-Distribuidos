# Sistema Distribuído de Mensagens

Este repositório implementa um sistema completo de troca de mensagens inspirado em BBS/IRC. Utilizamos ZeroMQ como transporte, MessagePack para serialização binária e Docker para orquestrar todos os serviços. O trabalho foi dividido em cinco partes (mais um listener em Go), cobrindo Request/Reply, Publish/Subscribe, MessagePack, relógios e replicação.

---

## Visão Geral

- REQ/REP entre clientes/bots e servidores via broker.
- PUB/SUB entre servidores e consumidores via proxy.
- Serialização binária com MessagePack.
- Relógios lógicos (Lamport) e sincronização Berkeley por meio do servidor de referência.
- Replicação eventual: cada operação é replicada via tópico interno eplica.
- Linguagens: Python, Node.js e Go.

---

## Estrutura de Diretórios

`
ROOT
├── src/
│   ├── bot/          -> Bots automáticos (Node.js)
│   ├── broker/       -> Broker REQ/REP (Python)
│   ├── client/       -> Cliente interativo (Python)
│   ├── go-listener/  -> Listener escrito em Go
│   ├── proxy/        -> Proxy PUB/SUB (Python)
│   ├── reference/    -> Servidor de referência (Python)
│   └── server/       -> Servidores principais (Python)
├── Dockerfile        -> Imagem base dos componentes em Python
├── docker-compose.yml
└── README.md
`

---

## Componentes

| Serviço           | Linguagem | Função principal |
|-------------------|-----------|------------------|
| reference         | Python    | Rank, heartbeat e clock (algoritmo de Berkeley) |
| broker            | Python    | ROUTER/DEALER para o tráfego REQ/REP |
| proxy             | Python    | XSUB/XPUB para o tráfego PUB/SUB |
| server (3 réplicas) | Python  | Processa requisições, persiste e replica dados |
| client            | Python    | Interface interativa |
| bot (2 réplicas)  | Node.js   | Mensagens automáticas em canais |
| go-listener       | Go        | Listener adicional inscrito nos tópicos geral e servers |

---

## Funcionalidades por parte

1. **REQ/REP**: login, listagem de usuários/canais, persistência inicial.
2. **PUB/SUB**: canais públicos, mensagens privadas e bots automáticos.
3. **MessagePack**: toda a comunicação passa para formato binário.
4. **Relógios**: Lamport em cada processo, Berkeley para clock físico; eleição do coordenador.
5. **Replicação**: eventos são difundidos no tópico eplica e aplicados por todas as réplicas.
6. **Listener Go**: terceiro idioma exigido, subscrevendo tópicos do proxy.

---

## Persistência

| Arquivo              | Conteúdo |
|----------------------|----------|
| data/users.json    | Usuários cadastrados |
| data/channels.json | Lista de canais |
| data/messages.log  | Histórico de publicações e mensagens |

---

## Execução com Docker

### Pré-requisitos
- Docker
- Docker Compose

### Subir tudo
`
cd src
docker compose up -d --build
`

### Monitorar serviços
`
docker compose logs -f reference  # rank/heartbeat/clock
docker compose logs -f server     # requisições + replicação
docker compose logs -f bot        # bots automáticos
docker compose logs -f go-listener
`

### Cliente interativo
`
docker compose run --rm client
`
1. Informe um nome.  
2. Opção 6: assinar geral.  
3. Opções 4/5: publicar em canal ou enviar mensagem privada.

### Derrubar
`
docker compose down
`
Use docker compose down -v --remove-orphans para limpar volumes.

---

## Branches

| Branch                        | Parte |
|-------------------------------|-------|
| feature/parte1-request-reply  | 1 – REQ/REP |
| feature/parte2-pub-sub        | 2 – PUB/SUB |
| feature/parte3-messagepack    | 3 – MessagePack |
| feature/parte4-relogios       | 4 – Relógios |
| feature/parte5-consistencia   | 5 – Replicação |
| feature/go-listener           | Extra – Listener em Go |

Após finalizar cada parte: git checkout main, git merge feature/..., git push origin main.

---

## Fluxo das mensagens

`
Clientes/Bots   ->REQ->   Broker   ->DEALER->   Servidores (x3)
                                  ^
                                  |
                           Referência (rank/clock)

Servidores   ->PUB->   Proxy (XPUB/XSUB)   ->SUB->   Clientes/Bots/Go-listener
              |\
              | \__ tópico "replica"   -> replicação de dados
              |____ tópico "servers"   -> anúncios de coordenador
`

---

## Testes sugeridos

1. **Replicação** – envie mensagens, pare src-server-1 e observe eference. Ao religar, o histórico está preservado (outros servidores replicaram).
2. **Relógios** – verifique o campo clock retornado ao cliente; os incrementos confirmam o Lamport.
3. **Go listener** – docker compose logs -f go-listener mostra mensagens recebidas nos tópicos geral e servers.

---

## Tecnologias
- ZeroMQ (pyzmq, zeromq.js, zmq4)
- MessagePack
- Docker + Docker Compose
- Python 3.13, Node.js 20, Go 1.22

---

## Critérios atendidos
- Cliente com bibliotecas corretas, REQ/REP + PUB/SUB, relógio lógico.
- Bots automáticos em Node.js.
- Broker/proxy/reference com rank, heartbeat e sincronização de clock.
- Servidores com Lamport + Berkeley + replicação.
- Documentação e testes descritos neste README.
- Apresentação via comandos/logs.
- Três linguagens diferentes: Python, Node.js, Go.

---

## Licença
Projeto desenvolvido para a disciplina de Sistemas Distribuídos.
