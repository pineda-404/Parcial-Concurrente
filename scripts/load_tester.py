import socket
import json
import threading
import time
import random
import statistics

HOST = "127.0.0.1"
PORT = 6000  # Puerto del ServidorCentral

# --- Configuración de la Prueba ---
ITERATIONS_PER_THREAD = 10  # Cuántas transferencias hará cada hilo
MAX_ACCOUNT_ID = 10000      # Rango de cuentas a usar (1000 a 1000+MAX_ACCOUNT_ID)
THREAD_LEVELS = [10, 20, 50, 100, 150, 200] # Niveles de concurrencia a probar

results = []

def do_transfer(from_acc, to_acc, amount, timeout=5):
    """Realiza una única transferencia y devuelve la latencia y el estado."""
    start_time = time.monotonic()
    try:
        with socket.create_connection((HOST, PORT), timeout=timeout) as s:
            req = {"type": "TRANSFERIR_CUENTA", "from": from_acc, "to": to_acc, "amount": amount}
            s.sendall((json.dumps(req) + "\n").encode())
            resp_raw = s.recv(4096).decode().strip()
            resp_json = json.loads(resp_raw)
            status = "OK" if resp_json.get("status") == "OK" else "ERROR"
    except Exception as e:
        # print(f"[ERROR] {e}")
        status = "ERROR"
    
    end_time = time.monotonic()
    latency_ms = (end_time - start_time) * 1000
    return latency_ms, status

def worker_thread(thread_id, latencies, success_count, failure_count):
    """El trabajo que realiza cada hilo: un número fijo de iteraciones."""
    for i in range(ITERATIONS_PER_THREAD):
        a = random.randint(1000, 1000 + MAX_ACCOUNT_ID - 1)
        b = random.randint(1000, 1000 + MAX_ACCOUNT_ID - 1)
        if a == b: b = a + 1
        amt = round(random.uniform(1, 100), 2)
        
        latency, status = do_transfer(a, b, amt)
        
        latencies.append(latency)
        if status == "OK":
            success_count.append(1)
        else:
            failure_count.append(1)

def run_test(num_threads):
    """Ejecuta una prueba para un nivel de concurrencia dado."""
    print(f"\n--- Ejecutando prueba con {num_threads} hilos concurrentes ---")
    
    latencies = []
    success_count = []
    failure_count = []
    threads = []

    start_total_time = time.monotonic()

    for i in range(num_threads):
        t = threading.Thread(target=worker_thread, args=(i, latencies, success_count, failure_count))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    end_total_time = time.monotonic()
    total_time_s = end_total_time - start_total_time

    total_success = len(success_count)
    total_failure = len(failure_count)
    total_requests = total_success + total_failure
    
    avg_latency = statistics.mean(latencies) if latencies else 0
    throughput = total_success / total_time_s if total_time_s > 0 else 0

    print(f"Prueba completada en {total_time_s:.2f} segundos.")
    print(f"  - Peticiones totales: {total_requests}")
    print(f"  - Exitosas: {total_success}")
    print(f"  - Fallidas: {total_failure}")
    print(f"  - Throughput: {throughput:.2f} TPS (transacciones por segundo)")
    print(f"  - Latencia Promedio: {avg_latency:.2f} ms")

    results.append({
        "Threads": num_threads,
        "TotalTime_s": round(total_time_s, 2),
        "SuccessCount": total_success,
        "FailureCount": total_failure,
        "TPS": round(throughput, 2),
        "AvgLatency_ms": round(avg_latency, 2)
    })

if __name__ == "__main__":
    print("Iniciando suite de pruebas de carga...")
    print(f"Asegúrate de que el clúster y el Servidor Central estén corriendo en el puerto {PORT}.")

    for threads in THREAD_LEVELS:
        run_test(threads)

    print("\n\n--- TABLA DE RESULTADOS (Formato CSV) ---")
    print("Copia y pega esto en una hoja de cálculo para generar las gráficas.")
    
    # Imprimir cabecera
    header = results[0].keys()
    print(",".join(header))
    
    # Imprimir filas
    for res in results:
        print(",".join(map(str, res.values())))