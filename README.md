# Sistema Distribuído de Mensageria

Este projeto implementa um sistema completo de troca de mensagens inspirado em BBS/IRC. Utilizamos ZeroMQ para a comunicação entre processos, MessagePack para serialização binária e Docker para orquestrar todos os componentes.

O desenvolvimento foi dividido em cinco partes (mais um serviço extra em Go), cobrindo Request-Reply, Publisher-Subscriber, MessagePack, relógios (Lamport + Berkeley) e replicação de dados.

---

## Visão Geral

- REQ/REP (Request-Reply) entre clientes e servidores via broker.
- PUB/SUB (Publish-Subscribe) entre servidores e consumidores via proxy.
- Serialização binária com MessagePack.
- Relógios lógicos em todos os processos, sincronização com Berkeley através de um servidor de referência.
- Replicação eventual de dados entre servidores usando um tópico interno.
- Múltiplas linguagens: Python, Node.js e Go.

---

## Estrutura de Diretórios

`
.
├── src/
│   ├── bot/              # Bots automáticos (Node.js)
│   ├── broker/           # Broker REQ/REP (Python)
│   ├── client/           # Cliente interativo (Python)
│   ├── go-listener/      # Listener Go (3ª linguagem)
│   ├── proxy/            # Proxy PUB/SUB (Python)
│   ├── reference/        # Servidor de referência (Python)
│   └── server/           # Servidores principais (Python)
├── Dockerfile            # Imagem base dos serviços em Python
├── docker-compose.yml    # Orquestração completa dos containers
└── README.md             # Este documento
`

---

## Componentes

| Serviço          | Linguagem | Função principal |
|------------------|-----------|------------------|
| reference        | Python    | Distribui rank, heartbeat e clock (algoritmo de Berkeley)
| broker           | Python    | ROUTER/DEALER para REQ/REP entre clientes e servidores
| proxy            | Python    | XSUB/XPUB para PUB/SUB
| server (x3)      | Python    | Processa requisições, persiste e replica dados, sincroniza relógios
| client           | Python    | Cliente interativo para usuários humanos
| bot (x2)         | Node.js   | Bots automáticos que publicam mensagens periodicamente
| go-listener      | Go        | Listener adicional inscrito nos tópicos "geral" e "servers"

---

## Funcionalidades por Parte

### Parte 1 – Request-Reply
- Broker ROUTER/DEALER.
- Serviços login, users, channel, channels.
- Persistência inicial em arquivos JSON.

### Parte 2 – Publisher-Subscriber
- Proxy PUB/SUB separado.
- Clientes e bots publicam em canais e recebem mensagens.
- Servidor envia mensagens privadas no tópico do destinatário.

### Parte 3 – MessagePack
- Toda comunicação REQ/REP e PUB/SUB passa a usar MessagePack.
- Compatibilidade entre Python e Node.js.

### Parte 4 – Relógios
- Relógios de Lamport em cada processo.
- Servidor de referência fornece clock físico (Berkeley) e define o coordenador (menor rank).
- Coordenador é anunciado no tópico servers.

### Parte 5 – Replicação e Consistência
- Servidores publicam eventos (login, criação de canal, mensagens) no tópico interno eplica.
- Todos os servidores assinam esse tópico e aplicam o evento localmente.
- Deduplicação via message_id (UUID + origem), garantindo consistência eventual.

### Extra – Listener em Go
- Serviço em Go inscrito nos tópicos geral e servers para atender ao requisito de três linguagens diferentes.

---

## Persistência

| Arquivo             | Descrição |
|---------------------|-----------|
| data/users.json   | Usuários cadastrados |
| data/channels.json| Lista de canais |
| data/messages.log | Mensagens e publicações |

Cada servidor monta o diretório data local. Como todos replicam os eventos, o conteúdo convergente é o mesmo.

---

## Execução com Docker

### Pré-requisitos
- Docker
- Docker Compose

### Subir os serviços
`ash
cd src
docker compose up -d --build
`

### Acompanhar os logs
`ash
docker compose logs -f reference   # rank, heartbeat, clock
docker compose logs -f server      # requisições, replicação
docker compose logs -f bot         # bots automáticos
docker compose logs -f go-listener # listener Go
`

### Cliente interativo
`ash
docker compose run --rm client
`
1. Digite um nome para login.
2. Opção 6 para assinar o canal geral.
3. Opções 4/5 para publicar em canal ou enviar mensagem privada.

### Derrubar tudo
`ash
docker compose down
`
usar docker compose down -v --remove-orphans para liberar volumes.

---

## Branches e Partes

| Branch                         | Parte | Descrição |
|--------------------------------|-------|-----------|
| feature/parte1-request-reply   | 1     | Broker REQ/REP e persistência inicial |
| feature/parte2-pub-sub         | 2     | Camada PUB/SUB, canais e privadas |
| feature/parte3-messagepack     | 3     | Migração para MessagePack |
| feature/parte4-relogios        | 4     | Relógios Lamport + sincronização Berkeley |
| feature/parte5-consistencia    | 5     | Replicação e consistência eventual |
| feature/go-listener            | Extra | Listener Go (terceira linguagem) |

### Acessar cada branch
`ash
git checkout feature/parte1-request-reply
# testes da parte 1

git checkout feature/parte2-pub-sub
# e assim por diante
`
Após cada parte: git checkout main, git merge feature/..., git push origin main.

---

## Fluxo das mensagens (ASCII)

`
Clientes/Bots  --REQ-->  Broker (ROUTER)  --DEALER-->  Servidores (x3)
                                 ^
                                 |
                                Reference (rank/clock)

Servidores  --PUB-->  Proxy (XPUB/XSUB)  --SUB-->  Clients/Bots/Go-Listener
            |\
            | \__ tópico "replica" -> replicação de dados
            |____ tópico "servers" -> anúncios de coordenador
`

---

## Testes Sugeridos

1. **Replicação**: com o stack rodando, envie mensagens e derrube src-server-1. Verifique eference atualizando o rank e, ao reiniciar o servidor, note que o histórico permanece coerente.
2. **Relógios**: observe o campo clock nas respostas do cliente; a contagem continua mesmo após replicações.
3. **Listener Go**: docker compose logs -f go-listener mostra todas as mensagens recebidas em geral e servers.

---

## Tecnologias
- ZeroMQ (pyzmq, zeromq.js, zmq4)
- MessagePack
- Docker Compose
- Python 3.13
- Node.js 20
- Go 1.22

---

## Critérios Atendidos
- Cliente com bibliotecas corretas, REQ/REP + PUB/SUB, relógio lógico.
- Bots automáticos (Node.js) seguindo o protocolo.
- Broker/proxy/reference funcionando com ranks, heartbeat e relógios.
- Servidores com relógios, sincronização Berkeley, eleição e replicação de dados.
- Documentação completa neste README.
- Apresentação possível pela combinação de logs e scripts.
- Três linguagens: Python, Node.js e Go.

---

## Licença
Projeto desenvolvido para a disciplina de Sistemas Distribuídos.
