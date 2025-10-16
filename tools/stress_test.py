# tools/stress_test.py
import threading, time, random, socket, json
from datetime import datetime

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 6000   # puerto de tu ServidorCentral 

ACCOUNTS_SAMPLE = [i for i in range(1000, 1000+10000)]  # en caso START_ID 1000

def worker_thread(id_thread, ops=100):
    for i in range(ops):
        op = random.choice(["CONSULTAR_CUENTA","TRANSFERIR_CUENTA"])
        if op == "CONSULTAR_CUENTA":
            acc = random.choice(ACCOUNTS_SAMPLE)
            req = {"type":"CONSULTAR_CUENTA","account":acc}
        else:
            a = random.choice(ACCOUNTS_SAMPLE)
            b = random.choice(ACCOUNTS_SAMPLE)
            while b==a:
                b = random.choice(ACCOUNTS_SAMPLE)
            amount = round(random.uniform(1.0, 200.0), 2)
            req = {"type":"TRANSFERIR_CUENTA","from":a,"to":b,"amount":amount}
        try:
            with socket.create_connection((SERVER_HOST, SERVER_PORT), timeout=4) as s:
                s.sendall((json.dumps(req)+"\n").encode())
                resp = s.recv(4096).decode().strip()
                # opcional: parse y log
        except Exception as e:
            # errores de conexión posibles durante saturación
            pass
        # random delay to simulate real clients
        time.sleep(random.uniform(0.01, 0.5))

def run_stress(num_clients=200, ops_per_client=200):
    threads = []
    start = datetime.now()
    for i in range(num_clients):
        t = threading.Thread(target=worker_thread, args=(i, ops_per_client), daemon=True)
        threads.append(t)
        t.start()
    for t in threads:
        t.join()
    print("Stress test finished in", datetime.now()-start)

if __name__ == "__main__":
    # Ajusta conforme recursos de tu máquina
    run_stress(num_clients=100, ops_per_client=200)
