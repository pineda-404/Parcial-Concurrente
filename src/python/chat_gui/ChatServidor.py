import socket
import threading
import json
from datetime import datetime
import sys
import os

# Añadir el directorio raíz del proyecto al path para permitir imports absolutos desde src
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
sys.path.append(ROOT_DIR)

from src.python.common.db_utils import conectar, inicializar_bd

CENTRAL_HOST = "127.0.0.1"
CENTRAL_PORT = 6000

HOST = "127.0.0.1"
PORT = 8085

inicializar_bd()


def forward_to_central(payload: dict, timeout=4):
    try:
        with socket.create_connection((CENTRAL_HOST, CENTRAL_PORT), timeout=timeout) as s:
            s.sendall((json.dumps(payload) + "\n").encode())
            data = s.recv(65536).decode().strip()
            if not data:
                return {"status": "ERROR", "error": "sin respuesta del central"}
            try:
                return json.loads(data)
            except Exception:
                return {"status": "ERROR", "error": "respuesta no JSON del central", "raw": data}
    except Exception as e:
        return {"status": "ERROR", "error": "central inalcanzable: " + str(e)}


def registrar_aviso_local(id_cliente, tipo_aviso, contenido):
    try:
        conn = conectar()
        cur = conn.cursor()
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur.execute("""
            INSERT INTO AvisosServidor (id_cliente, tipo_aviso, contenido, fecha_envio)
            VALUES (?, ?, ?, ?)
        """, (id_cliente, tipo_aviso, contenido, fecha))
        conn.commit()
        conn.close()
    except Exception as e:
        print("[WARN] registrar_aviso_local:", e)


def registrar_mensaje_local(id_cliente_chat, mensaje, respuesta, tipo="chat"):
    try:
        conn = conectar()
        cur = conn.cursor()
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur.execute("""
            INSERT INTO MensajesChat (id_cliente_chat, mensaje, respuesta, fecha_envio, tipo_mensaje)
            VALUES (?, ?, ?, ?, ?)
        """, (id_cliente_chat, mensaje, respuesta, fecha, tipo))
        conn.commit()
        conn.close()
    except Exception as e:
        print("[WARN] registrar_mensaje_local:", e)


def handle_connection(conn, addr):
    print(f"[SERVER] Nueva conexión desde {addr}")
    with conn:
        try:
            data = conn.recv(65536)
            if not data:
                return
            raw = data.decode().strip()
            try:
                mensaje = json.loads(raw)
            except Exception:
                resp = {"status": "ERROR", "error": "JSON mal formado"}
                conn.sendall((json.dumps(resp) + "\n").encode())
                return

            print("[DEBUG] Recibido:", mensaje)
            tipo = (mensaje.get("type") or "").upper()

            # Tipos reenviados al ServidorCentral (Java)
            if tipo in (
                "CONSULTAR_CUENTA",
                "TRANSFERIR_CUENTA",
                "ESTADO_PAGO_PRESTAMO",
                "CONSULTAR_TRANSACCIONES",  # 🔹 agregado
                "ARQUEO",
                "SUM_PARTITION",
            ):
                central_resp = forward_to_central(mensaje)
                registrar_aviso_local(1, "REENVIO_CENTRAL", f"{mensaje} -> {central_resp}")
                try:
                    if "message" in mensaje:
                        registrar_mensaje_local(
                            mensaje.get("id_cliente_chat", 1),
                            mensaje.get("message"),
                            str(central_resp),
                        )
                except Exception:
                    pass
                conn.sendall((json.dumps(central_resp) + "\n").encode())
                return

            if tipo == "CHAT_MESSAGE":
                text = mensaje.get("message", "")
                respuesta = {"status": "OK", "reply": "Recibido: " + text}
                registrar_mensaje_local(mensaje.get("id_cliente_chat", 1), text, respuesta["reply"])
                conn.sendall((json.dumps(respuesta) + "\n").encode())
                return

            resp = {"status": "ERROR", "error": f"Tipo desconocido: {tipo}"}
            conn.sendall((json.dumps(resp) + "\n").encode())

        except Exception as e:
            print("[ERROR] handle_connection:", e)
            try:
                conn.sendall((json.dumps({"status": "ERROR", "error": str(e)}) + "\n").encode())
            except:
                pass


def start_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        print(f"[SERVER] ChatServidor escuchando en {HOST}:{PORT}")
        while True:
            c, a = s.accept()
            t = threading.Thread(target=handle_connection, args=(c, a), daemon=True)
            t.start()


if __name__ == "__main__":
    start_server()
