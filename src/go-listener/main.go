package main

import (
	"encoding/json"
	"log"
	"os"
	"os/signal"
	"strings"
	"syscall"
	"time"

	zmq "github.com/pebbe/zmq4"
)

func main() {
	log.SetFlags(log.LstdFlags | log.Lmicroseconds)

	endpoint := getenv("PROXY_SUB_ENDPOINT", "tcp://proxy:5558")
	topicEnv := getenv("LISTENER_TOPICS", "geral,servers")
	topics := parseTopics(topicEnv)

	sub, err := zmq.NewSocket(zmq.SUB)
	if err != nil {
		log.Fatalf("falha ao criar socket SUB: %v", err)
	}
	defer sub.Close()

	if err := sub.Connect(endpoint); err != nil {
		log.Fatalf("falha ao conectar ao proxy (%s): %v", endpoint, err)
	}

	if len(topics) == 0 {
		sub.SetSubscribe("")
		log.Println("[Go Listener] inscrito em todos os tópicos")
	} else {
		for _, t := range topics {
			if err := sub.SetSubscribe(t); err != nil {
				log.Fatalf("falha ao inscrever no tópico '%s': %v", t, err)
			}
			log.Printf("[Go Listener] inscrito no tópico '%s'\n", t)
		}
	}

	// Tratamento para encerramento gracioso
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)

	go func() {
		<-sigChan
		log.Println("[Go Listener] encerrando...")
		sub.Close()
		os.Exit(0)
	}()

	for {
		msg, err := sub.RecvMessage(0)
		if err != nil {
			if zmq.AsErrno(err) == zmq.Errno(syscall.EINTR) {
				continue
			}
			log.Printf("erro ao receber mensagem: %v\n", err)
			time.Sleep(time.Second)
			continue
		}

		if len(msg) < 2 {
			log.Printf("[Go Listener] mensagem inválida: %+v\n", msg)
			continue
		}

		topic := msg[0]
		payload := msg[1]
		pretty := prettifyJSON(payload)

		log.Printf("[Go Listener][%s] %s\n", topic, pretty)
	}
}

func getenv(key, def string) string {
	val := strings.TrimSpace(os.Getenv(key))
	if val == "" {
		return def
	}
	return val
}

func parseTopics(raw string) []string {
	parts := strings.Split(raw, ",")
	var topics []string
	for _, part := range parts {
		t := strings.TrimSpace(part)
		if t != "" {
			topics = append(topics, t)
		}
	}
	return topics
}

func prettifyJSON(raw string) string {
	var obj interface{}
	if err := json.Unmarshal([]byte(raw), &obj); err != nil {
		return raw
	}
	formatted, err := json.MarshalIndent(obj, "", "  ")
	if err != nil {
		return raw
	}
	return string(formatted)
}
