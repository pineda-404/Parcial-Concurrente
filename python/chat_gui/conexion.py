# python/cliente_gui/conexion.py
import socket
import json
from . import db_sqlite   # asume paquete python/cliente_gui
import os

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 6000

def enviar_request(payload: dict, timeout: float = 3.0) -> dict:
    """Envía payload (dict) al ServidorChat y devuelve dict de respuesta.
       Si falla la conexión, intenta dar fallback usando sqlite local."""
    try:
        with socket.create_connection((SERVER_HOST, SERVER_PORT), timeout=timeout) as s:
            s.sendall((json.dumps(payload) + "\n").encode("utf-8"))
            data = s.recv(8192).decode("utf-8").strip()
            if not data:
                return {"status":"ERROR", "error":"SIN_RESPUESTA"}
            try:
                return json.loads(data)
            except Exception:
                return {"status":"ERROR", "error":"RESPUESTA_NO_JSON", "raw": data}
    except Exception as e:
        # fallback: intenta interpretar pedido localmente
        t = payload.get("type","").upper()
        if t == "CHAT_MESSAGE":
            txt = payload.get("message","").lower()
            if "transacc" in txt:
                rows = db_sqlite.obtener_transacciones(limit=10)
                return {"status":"OK", "type":"TRANSACTIONS", "data":[{"id":r[0],"cuenta":r[1],"tipo":r[2],"monto":r[3],"fecha":r[4]} for r in rows]}
            return {"status":"OK", "reply":"Servidor chat no disponible. Intenta más tarde."}
        elif t == "CONSULTAR_CUENTA":
            try:
                return queries_local_consultar(int(payload.get("account")))
            except Exception as ex:
                return {"status":"ERROR", "error": str(ex)}
        else:
            return {"status":"ERROR", "error": f"NO_SERVER: {e}"}

# local helper (only for simple consult)
def queries_local_consultar(account):
    conn = db_sqlite.get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id_cliente, saldo, fecha_apertura FROM Cuentas WHERE id_cuenta=?", (account,))
    r = cur.fetchone()
    conn.close()
    if r:
        return {"status":"OK","account":account,"id_cliente":r[0],"balance":float(r[1])}
    return {"status":"ERROR","error":"NO_EXISTE_CUENTA"}
