import time
import zmq
import msgpack
import threading

clock_state = {'value': 0}
clock_lock = threading.Lock()
servers = {}
next_rank = 1
current_coordinator = None
HEARTBEAT_TIMEOUT = 15

def increment_clock():
    with clock_lock:
        clock_state['value'] += 1
        return clock_state['value']

def update_clock(received_clock):
    with clock_lock:
        if received_clock is None:
            return clock_state['value']
        clock_state['value'] = max(clock_state['value'], received_clock)
        return clock_state['value']

def cleanup_servers():
    global servers, current_coordinator
    now = time.time()
    removed = []
    for name, info in list(servers.items()):
        if now - info['last_seen'] > HEARTBEAT_TIMEOUT:
            removed.append(name)
            servers.pop(name, None)
    if current_coordinator and current_coordinator in removed:
        current_coordinator = None

def pick_coordinator():
    global current_coordinator
    if not servers:
        current_coordinator = None
        return
    current_coordinator = min(servers.items(), key=lambda item: item[1]['rank'])[0]

def handle_rank(data):
    global next_rank
    name = data.get('user')
    if not name:
        return {"error": "Nome do servidor não fornecido"}
    cleanup_servers()
    if name not in servers:
        servers[name] = {"rank": next_rank, "last_seen": time.time()}
        next_rank += 1
        pick_coordinator()
    else:
        servers[name]['last_seen'] = time.time()
    return {"rank": servers[name]['rank']}

def handle_list():
    cleanup_servers()
    pick_coordinator()
    sorted_servers = sorted(
        [{"name": name, "rank": info['rank']} for name, info in servers.items()],
        key=lambda item: item['rank']
    )
    return {"list": sorted_servers, "coordinator": current_coordinator}

def handle_heartbeat(data):
    name = data.get('user')
    if name and name in servers:
        servers[name]['last_seen'] = time.time()
    else:
        handle_rank(data)
    cleanup_servers()
    pick_coordinator()
    return {"status": "OK", "coordinator": current_coordinator}

def handle_clock():
    cleanup_servers()
    pick_coordinator()
    return {"time": time.time(), "coordinator": current_coordinator}

def handle_election(data):
    requested = data.get('user')
    cleanup_servers()
    pick_coordinator()
    if requested and requested in servers:
        current = requested
    else:
        current = current_coordinator
    if not current:
        pick_coordinator()
        current = current_coordinator
    return {"election": "OK", "coordinator": current}

def build_response(service, payload):
    response_clock = increment_clock()
    return {
        "service": service,
        "data": {
            **payload,
            "timestamp": int(time.time()),
            "clock": response_clock
        }
    }

def main():
    context = zmq.Context()
    rep_socket = context.socket(zmq.REP)
    rep_socket.bind("tcp://*:5560")
    print("Serviço de referência iniciado na porta 5560.")

    handlers = {
        "rank": handle_rank,
        "list": lambda data=None: handle_list(),
        "heartbeat": handle_heartbeat,
        "clock": lambda data=None: handle_clock(),
        "election": handle_election
    }

    while True:
        try:
            message_bytes = rep_socket.recv()
            message = msgpack.unpackb(message_bytes, raw=False)
            service = message.get('service')
            data = message.get('data', {})
            update_clock(data.get('clock'))

            handler = handlers.get(service)
            if not handler:
                response = build_response(service, {"status": "erro", "description": "Serviço inválido"})
            else:
                result = handler(data)
                response = build_response(service, result)

            rep_socket.send(msgpack.packb(response, use_bin_type=True))

        except Exception as e:
            error_response = build_response("internal_error", {"status": "erro", "description": str(e)})
            rep_socket.send(msgpack.packb(error_response, use_bin_type=True))

if __name__ == "__main__":
    main()
