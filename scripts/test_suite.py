import socket, json, time

CENTRAL_HOST = '127.0.0.1'
CENTRAL_PORT = 6000

def enviar(req):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((CENTRAL_HOST, CENTRAL_PORT))
        s.sendall((json.dumps(req) + "\n").encode())
        resp = s.recv(4096).decode().strip()
        print("[RESPUESTA]", resp)
        return json.loads(resp)

print("\n=== TEST 1: CONSULTA ===")
enviar({"type":"CONSULTAR_CUENTA","account":1000})

print("\n=== TEST 2: TRANSFERENCIA ===")
enviar({"type":"TRANSFERIR_CUENTA","from":1000,"to":1001,"amount":50})

print("\n=== TEST 3: CREAR y ELIMINAR ===")
resp = enviar({"type":"CREAR_CUENTA","account":20000,"initial":100})
time.sleep(1)
enviar({"type":"ELIMINAR_CUENTA","account":20000})
