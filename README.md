# Distributed Messaging System

This project delivers a full messaging stack inspired by BBS/IRC. ZeroMQ handles the transport layer, MessagePack keeps payloads compact, and Docker orchestrates every process. The work is split across five parts (plus an extra Go service) covering request/reply, publish/subscribe, binary encoding, clocks, and replication.

---

## Overview

- REQ/REP between clients and servers via the broker.
- PUB/SUB between servers and consumers via the proxy.
- Binary serialization with MessagePack.
- Lamport clocks on every process and Berkeley clock sync through a reference server.
- Eventual replication of user/channel/message data between servers.
- Three programming languages: Python, Node.js, and Go.

---

## Directory layout

`
.
├── src/
│   ├── bot/          # Node.js bots
│   ├── broker/       # Python broker (REQ/REP)
│   ├── client/       # Python interactive client
│   ├── go-listener/  # Go listener (third language)
│   ├── proxy/        # Python proxy (PUB/SUB)
│   ├── reference/    # Python reference server
│   └── server/       # Python application servers
├── Dockerfile
├── docker-compose.yml
└── README.md
`

---

## Components

| Service         | Language | Role |
|-----------------|----------|------|
| reference       | Python   | Rank, heartbeat and Berkeley clock server |
| broker          | Python   | ROUTER/DEALER hub for REQ/REP |
| proxy           | Python   | XSUB/XPUB hub for PUB/SUB |
| server (x3)     | Python   | Handles API calls, persists and replicates data, syncs clocks |
| client          | Python   | CLI for humans |
| bot (x2)        | Node.js  | Automatic publishers |
| go-listener     | Go       | Extra listener subscribed to geral and servers |

---

## Features per part

1. **Part 1** – request/reply, persistence in JSON files.
2. **Part 2** – publish/subscribe layer, channels and private messages.
3. **Part 3** – switch to MessagePack for every socket.
4. **Part 4** – Lamport clocks, Berkeley sync, coordinator election.
5. **Part 5** – replication topic (eplica) so every server holds the same state.
6. **Go listener** – bonus service for the third language requirement.

---

## Persistence

| File               | Content |
|--------------------|---------|
| data/users.json  | Registered users |
| data/channels.json | Channel list |
| data/messages.log  | Channel and private messages |

Each server mounts its own data directory; replication keeps them aligned.

---

## Running with Docker

### Prerequisites
- Docker + Docker Compose

### Start everything
`
cd src
docker compose up -d --build
`

### Watch logs
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

### Interactive client
`
docker compose run --rm client
`
1. Enter a username.  
2. Option 6 subscribes to geral.  
3. Options 4/5 publish to a channel or send direct messages.

### Tear down
`
docker compose down
`
Use docker compose down -v --remove-orphans to drop volumes.

---

## Branches

| Branch                      | Description |
|-----------------------------|-------------|
| feature/parte1-request-reply| Part 1 implementation |
| feature/parte2-pub-sub      | Part 2 implementation |
| feature/parte3-messagepack  | Part 3 implementation |
| feature/parte4-relogios     | Part 4 implementation |
| feature/parte5-consistencia | Part 5 implementation |
| feature/go-listener         | Go listener service |

Switch example:
`
git checkout feature/parte3-messagepack
`
Merge into main and push after each part.

---

## Message flow (ASCII)

`
Clients/Bots  --REQ-->  Broker (ROUTER)  --DEALER-->  Servers (x3)
                                 ^
                                 |
                           Reference server

Servers  --PUB-->  Proxy (XPUB/XSUB)  --SUB-->  Clients/Bots/Go listener
            |\
            | \__ topic "replica" -> data replication
            |____ topic "servers" -> coordinator events
`

---

## Suggested tests

1. **Replication** – send traffic, stop src-server-1, observe eference, restart the server and confirm the history remains.
2. **Clocks** – watch the clock field returned to the client to verify Lamport updates.
3. **Go listener** – docker compose logs -f go-listener should show messages from geral and coordinator announcements.

---

## Technologies
- ZeroMQ (pyzmq, zeromq.js, zmq4)
- MessagePack
- Docker + Docker Compose
- Python 3.13, Node.js 20, Go 1.22

---

## Criteria satisfied
- Client uses the right libraries, REQ/REP + PUB/SUB, Lamport clock.
- Bots publish automatically via the specified protocol.
- Broker, proxy and reference server implement rank, heartbeat and clock sync.
- Application servers maintain Lamport clocks, Berkeley sync, coordinator election and data replication.
- Documentation is consolidated in this README.
- Presentation can be done through the provided logs/commands.
- Three different languages are in use.

---

## License
Project developed for the Distributed Systems course.
