FROM golang:1.22-bookworm AS builder

WORKDIR /app

# Dependências do libzmq para compilação
RUN apt-get update \
    && apt-get install -y --no-install-recommends libzmq3-dev pkg-config \
    && rm -rf /var/lib/apt/lists/*

COPY go.mod ./
COPY third_party ./third_party
COPY main.go .

RUN go build -o go-listener

FROM debian:bookworm-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends libzmq5 ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /app/go-listener /usr/local/bin/go-listener

ENV PROXY_SUB_ENDPOINT=tcp://proxy:5558 \
    LISTENER_TOPICS=geral,servers

CMD ["go-listener"]
