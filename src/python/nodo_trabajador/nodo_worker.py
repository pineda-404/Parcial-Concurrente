
import socket
import threading
import json
import sys
import os
import sqlite3
from datetime import datetime

# --- Configuración ---
# Ruta a la base de datos SQLite, asumimos que el script se corre desde la raíz del proyecto
DB_PATH = "db/banco_chat.db"

class NodoWorker:
    def __init__(self, port, data_file_path):
        self.port = port
        self.data_file = data_file_path
        self.cuentas = {}
        self.prepared_ops = {}
        self.lock = threading.Lock()
        self._load_data()

    def _load_data(self):
        """Carga las cuentas desde el archivo de datos a memoria."""
        print(f"[Nodo-{self.port}] Cargando datos desde {self.data_file}...")
        try:
            if not os.path.exists(self.data_file):
                print(f"[Nodo-{self.port}] Archivo de datos no encontrado, se creará uno nuevo.")
                os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
                with open(self.data_file, 'w') as f:
                    pass # Crear archivo vacío
                return

            with open(self.data_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        parts = line.split(',')
                        acc_id = int(parts[0])
                        balance = float(parts[1])
                        self.cuentas[acc_id] = balance
                    except (ValueError, IndexError) as e:
                        print(f"[Nodo-{self.port}] [WARN] Línea inválida ignorada: {line} - {e}")
            print(f"[Nodo-{self.port}] {len(self.cuentas)} cuentas cargadas en memoria.")
        except Exception as e:
            print(f"[Nodo-{self.port}] [ERROR] Fallo al cargar datos: {e}")
            sys.exit(1)

    def _persist_to_disk(self):
        """Guarda el estado actual de las cuentas en memoria al archivo de datos."""
        with self.lock:
            try:
                with open(self.data_file, 'w') as f:
                    for acc_id, balance in self.cuentas.items():
                        f.write(f"{acc_id},{balance:.2f}\n")
            except Exception as e:
                print(f"[Nodo-{self.port}] [ERROR] Fallo al persistir datos a disco: {e}")


    def _registrar_transaccion_db(self, id_cuenta, tipo, monto):
        """Registra una transacción en la base de datos central de SQLite."""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO Transacciones(id_cuenta, tipo, monto, fecha) VALUES (?, ?, ?, ?)",
                (id_cuenta, tipo, monto, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            )
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[Nodo-{self.port}] [WARN] No se pudo registrar la transacción en SQLite: {e}")

    def _json_response(self, data):
        """Codifica un diccionario a una cadena JSON para la respuesta."""
        return (json.dumps(data) + '\n').encode()

    def _handle_prepare(self, req):
        """Lógica para la fase de PREPARE del 2PC."""
        tx_id = req.get("tx_id")
        if not tx_id:
            return self._json_response({"status": "ERROR", "error": "Falta tx_id"})

        with self.lock:
            try:
                req_type = req.get("type", "").lower()
                ops_to_prepare = []

                if "transfer" in req_type:
                    from_acc = int(req["from"])
                    to_acc = int(req["to"])
                    amount = float(req["amount"])

                    # Validar y preparar débito si este nodo maneja la cuenta de origen
                    if from_acc in self.cuentas:
                        if self.cuentas[from_acc] < amount:
                            return self._json_response({"status": "ERROR", "tx_id": tx_id, "error": "Saldo insuficiente"})
                        ops_to_prepare.append(("debit", from_acc, amount))
                    
                    # Preparar crédito si este nodo maneja la cuenta de destino
                    if to_acc in self.cuentas:
                        ops_to_prepare.append(("credit", to_acc, amount))

                elif "create" in req_type:
                    acc = int(req["account"])
                    initial = float(req["initial"])
                    if acc in self.cuentas:
                        return self._json_response({"status": "ERROR", "tx_id": tx_id, "error": "Cuenta ya existe"})
                    ops_to_prepare.append(("create", acc, initial))

                elif "delete" in req_type:
                    acc = int(req["account"])
                    if acc not in self.cuentas:
                        return self._json_response({"status": "ERROR", "tx_id": tx_id, "error": "Cuenta no existe"})
                    ops_to_prepare.append(("delete", acc, 0))
                
                self.prepared_ops[tx_id] = ops_to_prepare
                return self._json_response({"status": "READY", "tx_id": tx_id})

            except Exception as e:
                print(f"[Nodo-{self.port}] [ERROR] en PREPARE: {e}")
                return self._json_response({"status": "ERROR", "tx_id": tx_id, "error": str(e)})

    def _handle_commit(self, req):
        """Lógica para la fase de COMMIT del 2PC."""
        tx_id = req.get("tx_id")
        if not tx_id or tx_id not in self.prepared_ops:
            return self._json_response({"status": "ERROR", "tx_id": tx_id, "error": "COMMIT_FAIL: Transacción no preparada"})

        with self.lock:
            ops = self.prepared_ops.get(tx_id, [])
            for op in ops:
                op_type, acc, amount = op
                if op_type == "debit":
                    self.cuentas[acc] -= amount
                    self._registrar_transaccion_db(acc, "Débito", -amount)
                elif op_type == "credit":
                    self.cuentas[acc] = self.cuentas.get(acc, 0.0) + amount
                    self._registrar_transaccion_db(acc, "Crédito", amount)
                elif op_type == "create":
                    self.cuentas[acc] = amount
                    self._registrar_transaccion_db(acc, "Creación de cuenta", amount)
                elif op_type == "delete":
                    del self.cuentas[acc]
                    self._registrar_transaccion_db(acc, "Eliminación de cuenta", 0)
            
            self._persist_to_disk()
            del self.prepared_ops[tx_id]
        
        return self._json_response({"status": "COMMITTED", "tx_id": tx_id})

    def _handle_abort(self, req):
        """Lógica para la fase de ABORT del 2PC."""
        tx_id = req.get("tx_id")
        if tx_id in self.prepared_ops:
            with self.lock:
                del self.prepared_ops[tx_id]
        return self._json_response({"status": "ABORTED", "tx_id": tx_id})

    def _handle_query(self, req):
        """Maneja una consulta de saldo."""
        try:
            acc = int(req["account"])
            if acc in self.cuentas:
                balance = self.cuentas[acc]
                return self._json_response({"status": "OK", "account": acc, "balance": balance})
            else:
                return self._json_response({"status": "ERROR", "error": "NO_EXISTE_CUENTA"})
        except (KeyError, ValueError) as e:
            return self._json_response({"status": "ERROR", "error": f"Petición de consulta inválida: {e}"})

    def _handle_sum(self, req):
        """Maneja una petición de suma de partición para el arqueo."""
        total = sum(self.cuentas.values())
        return self._json_response({"status": "OK", "sum": total})

    def handle_connection(self, conn, addr):
        """Maneja una conexión de cliente en un hilo."""
        print(f"[Nodo-{self.port}] Conexión aceptada desde {addr}")
        try:
            with conn:
                # Usamos un buffer para leer líneas completas
                buffer = ""
                while True:
                    data = conn.recv(1024)
                    if not data:
                        break
                    buffer += data.decode('utf-8')
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        line = line.strip()
                        if not line:
                            continue
                        
                        print(f"[Nodo-{self.port}] Recibido: {line}")
                        try:
                            req = json.loads(line)
                            req_type = req.get("type", "").upper()

                            response = None
                            if "PREPARE" in req_type:
                                response = self._handle_prepare(req)
                            elif req_type == "COMMIT":
                                response = self._handle_commit(req)
                            elif req_type == "ABORT":
                                response = self._handle_abort(req)
                            elif req_type == "CONSULTAR_CUENTA":
                                response = self._handle_query(req)
                            elif req_type == "SUM_PARTITION":
                                response = self._handle_sum(req)
                            else:
                                response = self._json_response({"status": "ERROR", "error": "TIPO_DESCONOCIDO"})
                            
                            conn.sendall(response)

                        except json.JSONDecodeError:
                            conn.sendall(self._json_response({"status": "ERROR", "error": "JSON mal formado"}))
                        except Exception as e:
                            print(f"[Nodo-{self.port}] [ERROR] Inesperado en handle_connection: {e}")
                            conn.sendall(self._json_response({"status": "ERROR", "error": "Excepción en el nodo"}))
        except ConnectionResetError:
            print(f"[Nodo-{self.port}] Conexión cerrada abruptamente por {addr}")
        except Exception as e:
            print(f"[Nodo-{self.port}] [ERROR] Fallo en la conexión con {addr}: {e}")
        finally:
            print(f"[Nodo-{self.port}] Conexión con {addr} cerrada.")


    def start(self):
        """Inicia el servidor del nodo trabajador."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(('127.0.0.1', self.port))
            s.listen()
            print(f"[Nodo-{self.port}] Nodo trabajador de PYTHON escuchando en el puerto {self.port}")
            while True:
                conn, addr = s.accept()
                thread = threading.Thread(target=self.handle_connection, args=(conn, addr))
                thread.daemon = True
                thread.start()

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Uso: python python/nodo_worker.py <port> <data_file_path>")
        sys.exit(1)
    
    try:
        port = int(sys.argv[1])
        data_file = sys.argv[2]
        
        worker = NodoWorker(port, data_file)
        worker.start()
    except ValueError:
        print("Error: El puerto debe ser un número entero.")
        sys.exit(1)
    except Exception as e:
        print(f"Error al iniciar el nodo: {e}")
        sys.exit(1)
