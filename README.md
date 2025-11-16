# 🚀 Sistema Distribuído de Mensageria com ZeroMQ, Docker e Multi-Linguagem

Este projeto implementa um **sistema distribuído de mensageria** completo, utilizando o padrão **ZeroMQ** para comunicação entre processos, com múltiplas linguagens integradas (**Python**, **Node.js**, **Go**) e **containers Docker**.

O objetivo é demonstrar, de forma prática, conceitos de **comunicação distribuída**, **consistência**, **replicação de dados** e **sincronização de relógios** em uma arquitetura modular, escalável e tolerante a falhas.

---

## 📦 Visão Geral

O sistema combina dois padrões clássicos de mensageria:

- **REQ/REP (Request-Reply)** → para comunicação síncrona entre **clientes** e **servidores**, mediada pelo **broker**.
- **PUB/SUB (Publish-Subscribe)** → para disseminação assíncrona de eventos e mensagens em **canais**, mediada pelo **proxy**.

Com o avanço das etapas, foram adicionadas:
- **Serialização binária (MessagePack)**
- **Relógios lógicos e físicos (Lamport e Berkeley)**
- **Replicação e consistência entre servidores**

---

## 🧩 Estrutura de Diretórios

`
.
├── src/
│   ├── bot/              # Bots automáticos (Node.js)
│   ├── broker/           # Broker REQ/REP (Python)
│   ├── client/           # Cliente interativo (Python)
│   ├── go-listener/      # Listener Go (3ª linguagem)
│   ├── proxy/            # Proxy PUB/SUB (Python)
│   ├── reference/        # Servidor de referência (Python)
│   └── server/           # Servidores (Python)
├── Dockerfile            # Imagem base dos serviços em Python
├── docker-compose.yml    # Orquestração de todos os componentes
└── README.md             # Este documento
`

---

## ⚙️ Componentes

| Serviço          | Linguagem | Função principal |
|------------------|-----------|------------------|
| **reference**    | Python    | Ranks, heartbeats e relógio Berkeley |
| **broker**       | Python    | ROUTER/DEALER (REQ/REP) entre clientes e servidores |
| **proxy**        | Python    | XSUB/XPUB (PUB/SUB) entre servidores e clients |
| **server (x3)**  | Python    | Processa requisições, persiste dados, replica eventos e sincroniza relógios |
| **client**       | Python    | Interface interativa (login, canais, mensagens privadas) |
| **bot (x2)**     | Node.js   | Cliente automático que gera mensagens em canais |
| **go-listener**  | Go        | Listener adicional inscrito em geral e servers |

---

## 🧠 Funcionalidades por Parte

### Parte 1 – Request-Reply
- Broker com ZeroMQ ROUTER-DEALER.
- Servidores respondem a login, users, channel, channels.
- Persistência inicial em arquivos JSON.

### Parte 2 – Publisher-Subscriber
- Proxy PUB/SUB para canais e mensagens diretas.
- Cliente/bot publicam; servidor envia privadas no tópico do destinatário.

### Parte 3 – MessagePack
- Toda comunicação migrou para MessagePack (REQ/REP e PUB/SUB).
- Compatibilidade total entre Python e Node.js.

### Parte 4 – Relógios
- Relógios lógicos (Lamport) em todos os processos.
- Servidor de referência fornece rank, heartbeat e clock de Berkeley.
- Eleição de coordenador: menor rank; anúncio via tópico servers.

### Parte 5 – Replicação e Consistência
- Servidores publicam eventos (login, channel, publish, message) no tópico eplica.
- Todas as réplicas assinam eplica, aplicam o evento e gravam o histórico completo.
- Deduplicação via message_id (UUID + origem).

---

## 📥 Persistência

| Arquivo             | Descrição |
|---------------------|-----------|
| data/users.json   | Usuários cadastrados |
| data/channels.json| Canais disponíveis |
| data/messages.log | Histórico de publicações e mensagens privadas |

Cada servidor monta ./data como volume. Como todos aplicam as replicações, esses arquivos convergem.

---

## 🐳 Execução com Docker

### Pré-requisitos
- Docker e Docker Compose.

### Subir todos os serviços
`
cd src
docker compose up -d --build
`

### Monitorar serviços
`
docker compose logs -f reference   # ranks/heartbeat/clock
docker compose logs -f server      # requisições + replicação
docker compose logs -f bot         # bots automáticos
docker compose logs -f go-listener # listener em Go
`

### Cliente interativo
`
docker compose run --rm client
`
1. Digite um nome para login.
2. Use 6 para assinar o canal geral.
3. Publique em 4 (canal) / 5 (privado).

### Derrubar tudo
`
docker compose down
`
Use docker compose down -v --remove-orphans para limpar volumes.

---

## 🌿 Branches e Partes

| Branch                             | Parte | Descrição |
|------------------------------------|-------|-----------|
| eature/parte1-request-reply     | 1     | Broker REQ/REP e persistência inicial |
| eature/parte2-pub-sub           | 2     | Proxy PUB/SUB, canais e privadas |
| eature/parte3-messagepack       | 3     | MessagePack em toda a comunicação |
| eature/parte4-relogios          | 4     | Relógios Lamport + sincronização Berkeley |
| eature/parte5-consistencia      | 5     | Replicação e consistência eventual |
| eature/go-listener              | Extra | Listener Go para cobrir 3ª linguagem |

### Acessar cada parte
`
git checkout feature/parte1-request-reply
# Teste REQ/REP

...

git checkout main
`
Após concluir cada parte → git merge main e git push origin main.

---

## 🔁 Fluxo das mensagens

`
Clientes/Bots  --REQ-->  Broker (ROUTER)  --DEALER-->  Servers (x3)
                                 ^
                                 |
                                Reference (rank/clock)

Servers  --PUB-->  Proxy (XPUB/XSUB)  --SUB-->  Clients/Bots/Go-Listener
            |\
            | \__ tópico "replica" -> replicação de dados
            |____ tópico "servers" -> anúncios de coordenador
`

---

## 🧪 Testes sugeridos

1. **Replicação**: mande mensagens, pare src-server-1 (docker stop ...) e veja os outros servidores mantendo o histórico; religue com docker start ....
2. **Relógios**: observe o campo clock das respostas no cliente; a cada evento o contador aumenta.
3. **Listener Go**: docker compose logs -f go-listener mostra mensagens recebidas nos tópicos geral e servers.

---

## 🧰 Tecnologias
- ZeroMQ (pyzmq, zeromq.js, zmq4)
- MessagePack
- Docker + Docker Compose
- Python 3.13, Node.js 20, Go 1.22

---

## ✅ Critérios atendidos
- Cliente: bibliotecas corretas, REQ/REP + PUB/SUB, relógio lógico.
- Bot: bibliotecas corretas, mensagens automáticas.
- Broker/Proxy/Reference: funcionando com ranks, heartbeat e relógios.
- Servidores: relógios lógicos, sincronização Berkeley, eleição e replicação.
- Documentação: README completo com passos de execução.
- Apresentação: logs e scripts permitem demonstrar todas as etapas.
- Três linguagens: Python, Node.js e Go.

---

## 📄 Licença
Projeto desenvolvido para a disciplina de Sistemas Distribuídos.
