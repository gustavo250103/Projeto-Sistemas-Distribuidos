import zmq
import json
import time
import os

DATA_DIR = 'data'
USERS_FILE = os.path.join(DATA_DIR, 'users.json')
CHANNELS_FILE = os.path.join(DATA_DIR, 'channels.json')
MESSAGES_FILE = os.path.join(DATA_DIR, 'messages.log')

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

users = load_data(USERS_FILE)
channels = load_data(CHANNELS_FILE)
print(f"Servidor iniciado. {len(users)} usuários, {len(channels)} canais carregados.")

context = zmq.Context()
rep_socket = context.socket(zmq.REP)
rep_socket.connect("tcp://broker:5556")

pub_socket = context.socket(zmq.PUB)
pub_socket.connect("tcp://proxy:5557")

print("Servidor pronto para receber requisições...")

while True:
    try:
        message_str = rep_socket.recv_string()
        message = json.loads(message_str)
        print(f"Recebido: {message}")

        service = message.get('service')
        data = message.get('data', {})
        response = {}

        current_time = int(time.time())

        if service == 'login':
            user = data.get('user')
            if user:
                if user not in users:
                    users.append(user)
                    save_data(USERS_FILE, users)
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
                pub_message = {
                    "type": "channel",
                    "channel": channel,
                    "user": user,
                    "message": message_content,
                    "timestamp": current_time
                }
                pub_socket.send_multipart([
                    channel.encode('utf-8'),
                    json.dumps(pub_message).encode('utf-8')
                ])
                log_message(pub_message)
                response = {"status": "OK"}
            else:
                response = {"status": "erro", "message": "Canal não existe"}

        elif service == 'message':
            src_user = data.get('src')
            dst_user = data.get('dst')
            message_content = data.get('message')

            if dst_user in users:
                pub_message = {
                    "type": "private",
                    "from": src_user,
                    "to": dst_user,
                    "message": message_content,
                    "timestamp": current_time
                }
                pub_socket.send_multipart([
                    dst_user.encode('utf-8'),
                    json.dumps(pub_message).encode('utf-8')
                ])
                log_message(pub_message)
                response = {"status": "OK"}
            else:
                response = {"status": "erro", "message": "Usuário não existe"}

        else:
            response = {"status": "erro", "description": "Serviço desconhecido"}

        final_response = {
            "service": service,
            "data": {**response, "timestamp": current_time}
        }
        rep_socket.send_json(final_response)
        print(f"Enviado: {final_response}")

    except Exception as e:
        print(f"Erro ao processar: {e}")
        try:
            rep_socket.send_json({
                "service": "internal_error",
                "data": {"status": "erro", "description": str(e), "timestamp": int(time.time())}
            })
        except zmq.ZMQError as ze:
            print(f"Erro ZMQ ao enviar erro: {ze}")
