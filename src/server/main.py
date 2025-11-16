import os
import socket
import threading
import time
import json
import uuid
import zmq
import msgpack

DATA_DIR = 'data'
USERS_FILE = os.path.join(DATA_DIR, 'users.json')
CHANNELS_FILE = os.path.join(DATA_DIR, 'channels.json')
MESSAGES_FILE = os.path.join(DATA_DIR, 'messages.log')

REFERENCE_HOST = os.environ.get('REFERENCE_HOST', 'reference')
REFERENCE_PORT = int(os.environ.get('REFERENCE_PORT', '5560'))
HEARTBEAT_INTERVAL = int(os.environ.get('HEARTBEAT_INTERVAL', '5'))
LIST_REFRESH_INTERVAL = int(os.environ.get('LIST_REFRESH_INTERVAL', '3'))

REPLICA_TOPIC = "replica"
SERVERS_TOPIC = "servers"

server_name = os.environ.get('SERVER_NAME', socket.gethostname())
logical_clock_state = {'value': 0}
clock_lock = threading.Lock()
replica_lock = threading.Lock()
seen_events = set()
message_counter = 0
coordinator_name = None
server_rank = None
server_list = []

def ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)

def load_data(filepath):
    ensure_data_dir()
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []

def save_data(filepath, data):
    ensure_data_dir()
    unique_data = sorted(list(set(data)))
    with open(filepath, 'w') as f:
        json.dump(unique_data, f, indent=4)

def log_message(message_data):
    ensure_data_dir()
    with open(MESSAGES_FILE, 'a') as f:
        f.write(json.dumps(message_data) + '\n')

def increment_clock():
    with clock_lock:
        logical_clock_state['value'] += 1
        return logical_clock_state['value']

def update_clock(received_clock):
    with clock_lock:
        if received_clock is None:
            return logical_clock_state['value']
        logical_clock_state['value'] = max(logical_clock_state['value'], received_clock)
        return logical_clock_state['value']

def track_event(event_id):
    with replica_lock:
        seen_events.add(event_id)

def already_processed(event_id):
    with replica_lock:
        return event_id in seen_events

def reference_request(socket, lock, service, payload):
    request = {
        "service": service,
        "data": {
            **payload,
            "timestamp": int(time.time()),
            "clock": increment_clock()
        }
    }
    with lock:
        socket.send(msgpack.packb(request, use_bin_type=True))
        reply = msgpack.unpackb(socket.recv(), raw=False)
    data = reply.get('data', {})
    update_clock(data.get('clock'))
    return data

def determine_coordinator_from_list():
    global coordinator_name
    if not server_list:
        coordinator_name = None
        return
    coordinator = min(server_list, key=lambda item: item['rank'])
    coordinator_name = coordinator['name']

def heartbeat_loop(reference_socket, reference_lock):
    tick = 0
    while True:
        try:
            reference_request(reference_socket, reference_lock, "heartbeat", {"user": server_name})
            tick += 1
            if tick % LIST_REFRESH_INTERVAL == 0:
                update_server_list(reference_socket, reference_lock)
        except Exception as e:
            print(f"[Heartbeat] Falha ao comunicar com referência: {e}")
        time.sleep(HEARTBEAT_INTERVAL)

def broadcast_replica(pub_socket, event_type, payload):
    event_id = f"{server_name}:{uuid.uuid4().hex}"
    track_event(event_id)
    packet = {
        "event": event_type,
        "message_id": event_id,
        "origin": server_name,
        "payload": payload,
        "timestamp": int(time.time()),
        "clock": increment_clock()
    }
    pub_socket.send_multipart([REPLICA_TOPIC.encode('utf-8'), msgpack.packb(packet, use_bin_type=True)])

def process_replica_packet(packet, users, channels):
    event_id = packet.get("message_id")
    if not event_id or already_processed(event_id):
        return
    track_event(event_id)
    update_clock(packet.get("clock"))
    event = packet.get("event")
    payload = packet.get("payload", {})

    if event == "user":
        user = payload.get("user")
        if user and user not in users:
            users.append(user)
            save_data(USERS_FILE, users)

    elif event == "channel":
        channel = payload.get("channel")
        if channel and channel not in channels:
            channels.append(channel)
            save_data(CHANNELS_FILE, channels)

    elif event in ("publish", "direct_message"):
        entry = payload.get("entry")
        if not entry:
            return
        if event == "publish":
            channel = entry.get("channel")
            if channel and channel not in channels:
                channels.append(channel)
                save_data(CHANNELS_FILE, channels)
        log_message(entry)

def subscriber_loop(sub_socket, users, channels):
    global coordinator_name
    while True:
        try:
            topic, payload = sub_socket.recv_multipart()
            topic = topic.decode('utf-8')

            if topic == SERVERS_TOPIC:
                message = msgpack.unpackb(payload, raw=False)
                data = message.get('data', {})
                update_clock(data.get('clock'))
                new_coord = data.get('coordinator')
                if new_coord:
                    coordinator_name = new_coord
                    print(f"[Coordenação] Novo coordenador anunciado: {coordinator_name}")

            elif topic == REPLICA_TOPIC:
                packet = msgpack.unpackb(payload, raw=False)
                process_replica_packet(packet, users, channels)

        except Exception as e:
            print(f"[Subscriber] Erro: {e}")
            time.sleep(1)

def notify_coordinator(pub_socket):
    data = {
        "service": "election",
        "data": {
            "coordinator": server_name,
            "timestamp": int(time.time()),
            "clock": increment_clock()
        }
    }
    pub_socket.send_multipart([
        SERVERS_TOPIC.encode('utf-8'),
        msgpack.packb(data, use_bin_type=True)
    ])
    print(f"[Coordenação] Servidor '{server_name}' anunciou-se como coordenador.")

def synchronize_clock(reference_socket, reference_lock, pub_socket):
    global coordinator_name
    try:
        response = reference_request(reference_socket, reference_lock, "clock", {})
        update_clock(response.get('clock'))
        if not response.get('coordinator'):
            notify_coordinator(pub_socket)
        else:
            coordinator_name = response.get('coordinator')
        if response.get('time'):
            print(f"[Sincronização] Horário de referência recebido: {response['time']}")
    except Exception as e:
        print(f"[Sincronização] Falha ao sincronizar: {e}")

def request_rank(reference_socket, reference_lock):
    global server_rank
    response = reference_request(reference_socket, reference_lock, "rank", {"user": server_name})
    server_rank = response.get('rank')
    update_clock(response.get('clock'))
    if server_rank is None:
        raise RuntimeError("Não foi possível obter o rank do servidor.")
    print(f"[Referência] Servidor '{server_name}' registrado com rank {server_rank}.")

def update_server_list(reference_socket, reference_lock):
    global server_list, coordinator_name
    try:
        response = reference_request(reference_socket, reference_lock, "list", {})
        server_list = response.get('list', [])
        update_clock(response.get('clock'))
        determine_coordinator_from_list()
    except Exception as e:
        print(f"[Referência] Falha ao atualizar lista de servidores: {e}")

users = load_data(USERS_FILE)
channels = load_data(CHANNELS_FILE)

def main():
    global message_counter
    print(f"Servidor '{server_name}' iniciado. {len(users)} usuários, {len(channels)} canais carregados.")

    context = zmq.Context()

    rep_socket = context.socket(zmq.REP)
    rep_socket.connect("tcp://broker:5556")

    pub_socket = context.socket(zmq.PUB)
    pub_socket.connect("tcp://proxy:5557")

    sub_socket = context.socket(zmq.SUB)
    sub_socket.connect("tcp://proxy:5558")
    sub_socket.setsockopt_string(zmq.SUBSCRIBE, SERVERS_TOPIC)
    sub_socket.setsockopt_string(zmq.SUBSCRIBE, REPLICA_TOPIC)

    reference_socket = context.socket(zmq.REQ)
    reference_socket.connect(f"tcp://{REFERENCE_HOST}:{REFERENCE_PORT}")
    reference_lock = threading.Lock()

    request_rank(reference_socket, reference_lock)
    update_server_list(reference_socket, reference_lock)

    threading.Thread(target=heartbeat_loop, args=(reference_socket, reference_lock), daemon=True).start()
    threading.Thread(target=subscriber_loop, args=(sub_socket, users, channels), daemon=True).start()

    print("Servidor pronto para receber requisições...")

    while True:
        try:
            message_bytes = rep_socket.recv()
            message = msgpack.unpackb(message_bytes, raw=False)
            data = message.get('data', {})
            update_clock(data.get('clock'))

            service = message.get('service')
            response = {}
            current_time = int(time.time())

            if service == 'login':
                user = data.get('user')
                if user:
                    if user not in users:
                        users.append(user)
                        save_data(USERS_FILE, users)
                        broadcast_replica(pub_socket, "user", {"user": user})
                    response = {"status": "sucesso"}
                else:
                    response = {"status": "erro", "description": "Nome de usuário não fornecido"}

            elif service == 'users':
                response = {"users": users}

            elif service == 'channel':
                channel = data.get('channel')
                if channel:
                    if channel not in channels:
                        channels.append(channel)
                        save_data(CHANNELS_FILE, channels)
                        broadcast_replica(pub_socket, "channel", {"channel": channel})
                        response = {"status": "sucesso"}
                    else:
                        response = {"status": "erro", "description": "Canal já existe"}
                else:
                    response = {"status": "erro", "description": "Nome de canal não fornecido"}

            elif service == 'channels':
                response = {"users": channels}

            elif service == 'publish':
                user = data.get('user')
                channel = data.get('channel')
                message_content = data.get('message')
                if channel in channels:
                    pub_clock = increment_clock()
                    pub_message = {
                        "type": "channel",
                        "channel": channel,
                        "user": user,
                        "message": message_content,
                        "timestamp": current_time,
                        "clock": pub_clock
                    }
                    pub_socket.send_multipart([
                        channel.encode('utf-8'),
                        msgpack.packb(pub_message, use_bin_type=True)
                    ])
                    log_message(pub_message)
                    broadcast_replica(pub_socket, "publish", {"entry": pub_message})
                    response = {"status": "OK"}
                else:
                    response = {"status": "erro", "message": "Canal não existe"}

            elif service == 'message':
                src_user = data.get('src')
                dst_user = data.get('dst')
                message_content = data.get('message')
                if dst_user in users:
                    pub_clock = increment_clock()
                    pub_message = {
                        "type": "private",
                        "from": src_user,
                        "to": dst_user,
                        "message": message_content,
                        "timestamp": current_time,
                        "clock": pub_clock
                    }
                    pub_socket.send_multipart([
                        dst_user.encode('utf-8'),
                        msgpack.packb(pub_message, use_bin_type=True)
                    ])
                    log_message(pub_message)
                    broadcast_replica(pub_socket, "direct_message", {"entry": pub_message})
                    response = {"status": "OK"}
                else:
                    response = {"status": "erro", "message": "Usuário não existe"}

            else:
                response = {"status": "erro", "description": "Serviço desconhecido"}

            resp_clock = increment_clock()
            final_response = {
                "service": service,
                "data": {**response, "timestamp": current_time, "clock": resp_clock}
            }
            rep_socket.send(msgpack.packb(final_response, use_bin_type=True))

            message_counter += 1
            if message_counter % 10 == 0:
                synchronize_clock(reference_socket, reference_lock, pub_socket)

        except Exception as e:
            print(f"Erro ao processar: {e}")
            error_response = {
                "service": "internal_error",
                "data": {
                    "status": "erro",
                    "description": str(e),
                    "timestamp": int(time.time()),
                    "clock": increment_clock()
                }
            }
            rep_socket.send(msgpack.packb(error_response, use_bin_type=True))

if __name__ == "__main__":
    main()
