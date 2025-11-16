import zmq
import time
import threading
import sys
from datetime import datetime
import msgpack

req_address = "broker"
req_port = 5555
sub_address = "proxy"
sub_port = 5558

logical_clock_state = {'value': 0}
clock_lock = threading.Lock()

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

context = zmq.Context()
req_socket = context.socket(zmq.REQ)
req_socket.connect(f"tcp://{req_address}:{req_port}")

sub_socket = context.socket(zmq.SUB)
sub_socket.connect(f"tcp://{sub_address}:{sub_port}")

req_lock = threading.Lock()

def receiver_thread(username):
    print(f"\n[Receptor] Inscrito no tópico: {username}")
    sub_socket.setsockopt_string(zmq.SUBSCRIBE, username)
    sub_socket.setsockopt_string(zmq.SUBSCRIBE, "servers")

    while True:
        try:
            [topic, data] = sub_socket.recv_multipart()
            message = msgpack.unpackb(data, raw=False)
            topic = topic.decode('utf-8')

            update_clock(message.get('clock'))
            dt = datetime.fromtimestamp(message['timestamp']).strftime('%H:%M:%S')
            print("\r" + " " * 80 + "\r", end='')

            if message.get('type') == 'channel':
                print(f"[{dt}][Canal: {topic}] {message['user']}: {message['message']}")
            elif message.get('type') == 'private':
                print(f"[{dt}][Privado de: {message['from']}]: {message['message']}")
            elif message.get('service') == 'election':
                print(f"[{dt}][Coordenação] Novo coordenador: {message['data'].get('coordinator')}")

            print("Escolha uma opção: ", end='', flush=True)

        except (zmq.ZMQError, Exception) as e:
            print(f"\n[Receptor] Erro: {e}. Encerrando thread.")
            break

def send_request(service, data):
    request_data = {
        "service": service,
        "data": {
            **data,
            "clock": increment_clock()
        }
    }

    with req_lock:
        try:
            req_socket.send(msgpack.packb(request_data, use_bin_type=True))
            response_bytes = req_socket.recv()
            response = msgpack.unpackb(response_bytes, raw=False)
        except zmq.ZMQError as e:
            print(f"Erro de comunicação com o broker: {e}")
            return {"status": "erro", "description": "Falha no broker"}

    response_data = response.get('data', {})
    update_clock(response_data.get('clock'))
    print(f"\n[Resposta do Servidor]: {response_data}")
    return response_data

def main_menu(username):
    print("\n--- Menu Principal ---")
    print("1. Listar usuários")
    print("2. Criar canal")
    print("3. Listar canais")
    print("4. Enviar Mensagem (Canal)")
    print("5. Enviar Mensagem (Usuário)")
    print("6. Inscrever-se em Canal")
    print("q. Sair")

    while True:
        choice = input("Escolha uma opção: ").strip()

        if choice == '1':
            send_request("users", {"timestamp": int(time.time())})

        elif choice == '2':
            channel_name = input("  Nome do novo canal: ").strip()
            if channel_name:
                send_request("channel", {"channel": channel_name, "timestamp": int(time.time())})

        elif choice == '3':
            send_request("channels", {"timestamp": int(time.time())})

        elif choice == '4':
            channel_name = input("  Nome do canal: ").strip()
            message = input("  Mensagem: ").strip()
            if channel_name and message:
                send_request("publish", {
                    "user": username,
                    "channel": channel_name,
                    "message": message,
                    "timestamp": int(time.time())
                })

        elif choice == '5':
            dst_user = input("  Nome do usuário de destino: ").strip()
            message = input("  Mensagem: ").strip()
            if dst_user and message:
                send_request("message", {
                    "src": username,
                    "dst": dst_user,
                    "message": message,
                    "timestamp": int(time.time())
                })

        elif choice == '6':
            channel_name = input("  Nome do canal para inscrever-se: ").strip()
            if channel_name:
                sub_socket.setsockopt_string(zmq.SUBSCRIBE, channel_name)
                print(f"[Cliente] Inscrito no canal: {channel_name}")

        elif choice.lower() == 'q':
            print("Saindo...")
            break

        else:
            print("Opção inválida.")

if __name__ == "__main__":
    print("Cliente iniciado.")
    username = ""
    while not username:
        username = input("Digite seu nome de usuário para login: ").strip()

    login_data = {
        "user": username,
        "timestamp": int(time.time())
    }
    login_response = send_request("login", login_data)

    if login_response.get("status") == "sucesso":
        print(f"Login de '{username}' realizado com sucesso.")
        r_thread = threading.Thread(target=receiver_thread, args=(username,), daemon=True)
        r_thread.start()
        main_menu(username)
    else:
        print(f"Falha no login: {login_response.get('description')}")

    print("Encerrando cliente.")
    req_socket.close()
    sub_socket.close()
    context.term()
    sys.exit(0)
