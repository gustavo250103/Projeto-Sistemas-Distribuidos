# Sistema Distribuído de Mensagens

Este repositório implementa um sistema completo de troca de mensagens inspirado em BBS/IRC. Utilizamos ZeroMQ como camada de transporte, MessagePack para serialização binária e Docker para orquestrar todos os serviços. O desenvolvimento foi dividido em etapas (REQ/REP, PUB/SUB, MessagePack, relógios e replicação), além de um listener adicional em Go para cumprir o requisito das três linguagens.

---

## Visão Geral

- Comunicação **REQ/REP** entre clientes/bots e servidores via broker.
- Comunicação **PUB/SUB** entre servidores e consumidores via proxy.
- Serialização binária em todas as mensagens (MessagePack).
- Relógios lógicos (Lamport) e sincronização física (Berkeley) via servidor de referência.
- Replicação eventual: todos os servidores recebem e aplicam cada alteração por meio de um tópico interno.
- Linguagens: **Python** (broker/proxy/servers/reference/clientes), **Node.js** (bots) e **Go** (listener extra).

---

## Estrutura de Diretórios

`
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
└── README.md
`

---

## Componentes

| Serviço           | Linguagem | Função principal |
|-------------------|-----------|------------------|
| eference       | Python    | Rank, heartbeat e clock Berkeley |
| roker          | Python    | ROUTER/DEALER para REQ/REP |
| proxy           | Python    | XSUB/XPUB para PUB/SUB |
| server (3 réplicas) | Python | Processa requisições, persiste e replica dados |
| client          | Python    | Interface interativa |
| ot (2 réplicas)| Node.js   | Publicação automática de mensagens |
| go-listener     | Go        | Listener que consome tópicos geral e servers |

---

## Funcionalidades por etapa

1. **Parte 1 – REQ/REP**: login, listagem de usuários/canais e persistência básica.
2. **Parte 2 – PUB/SUB**: canais públicos, mensagens privadas e bots automáticos.
3. **Parte 3 – MessagePack**: toda a comunicação migra para formato binário.
4. **Parte 4 – Relógios**: relógios de Lamport em todos os processos + sincronização Berkeley/eleição do coordenador.
5. **Parte 5 – Replicação**: servidores publicam eventos no tópico eplica; todos aplicam e gravam localmente.
6. **Extra – Listener Go**: serviço em Go inscrito nos tópicos para comprovar a terceira linguagem.

---

## Persistência

| Arquivo              | Conteúdo |
|----------------------|----------|
| data/users.json    | Usuários cadastrados |
| data/channels.json | Canais criados |
| data/messages.log  | Histórico de mensagens/publicações |

Cada servidor monta o diretório data como volume; a replicação garante que os arquivos converjam.

---

## Execução com Docker

### Pré-requisitos
- Docker
- Docker Compose

### Subir todos os serviços
`
cd src
docker compose up -d --build
`

### Acompanhar os logs
`
docker compose logs -f reference
` 
`
docker compose logs -f server
` 
`
docker compose logs -f bot
` 
`
docker compose logs -f go-listener
`

### Cliente interativo
`
docker compose run --rm client
`
1. Informe um nome para login.  
2. Opção 6: assinar o canal geral.  
3. Opções 4/5: publicar em canal ou enviar mensagem privada.

### Encerrar
`
docker compose down
`
Use docker compose down -v --remove-orphans para limpar volumes.

---

## Branches

| Branch                        | Descrição |
|-------------------------------|-----------|
| eature/parte1-request-reply| Parte 1 – REQ/REP |
| eature/parte2-pub-sub      | Parte 2 – PUB/SUB |
| eature/parte3-messagepack  | Parte 3 – MessagePack |
| eature/parte4-relogios     | Parte 4 – Relógios |
| eature/parte5-consistencia | Parte 5 – Replicação |
| eature/go-listener         | Listener adicional em Go |

Troque de branch com git checkout <nome>; após cada parte, faça merge em main e git push origin main.

---

## Fluxo das mensagens

`
Clientes/Bots --REQ--> Broker --DEALER--> Servidores (x3)
                              ^
                              |
                        Servidor de referência

Servidores --PUB--> Proxy (XPUB/XSUB) --SUB--> Clientes/Bots/Go-listener
            |\
            | \__ tópico "replica": replicação de dados
            |____ tópico "servers": anúncios de coordenador
`

---

## Testes sugeridos

1. **Replicação** – envie mensagens, pare src-server-1 e observe o eference. Ao reiniciar o servidor, o histórico permanece coerente.
2. **Relógios** – veja o campo clock retornado aos clientes para confirmar os incrementos de Lamport.
3. **Listener Go** – docker compose logs -f go-listener mostra mensagens dos tópicos geral e servers.

---

## Tecnologias
- ZeroMQ (pyzmq, zeromq.js, zmq4)
- MessagePack
- Docker / Docker Compose
- Python 3.13
- Node.js 20
- Go 1.22

---

## Critérios atendidos
- Cliente com bibliotecas corretas, REQ/REP + PUB/SUB e relógio lógico.
- Bots automáticos conforme especificação.
- Broker, proxy e reference com rank, heartbeat e sincronização de clock.
- Servidores com Lamport + Berkeley + replicação.
- Documentação completa neste README.
- Apresentação suportada pelos comandos/logs fornecidos.
- Três linguagens (Python, Node.js, Go).

---

## Licença
Projeto desenvolvido para a disciplina de Sistemas Distribuídos.
