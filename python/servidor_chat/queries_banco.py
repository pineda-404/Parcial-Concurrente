import sqlite3
from datetime import datetime
import os

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DB = os.path.join(BASE, "db", "banco_chat.db")

def conn():
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    return sqlite3.connect(DB)

# ------------------ Query 1: CONSULTAR_CUENTA ------------------ #
def consultar_cuenta(id_cuenta):
    try:
        c = conn()
        cur = c.cursor()
        cur.execute("SELECT id_cliente, saldo, fecha_apertura FROM Cuentas WHERE id_cuenta=?", (id_cuenta,))
        r = cur.fetchone()
        c.close()
        if not r:
            return {"status": "ERROR", "error": "Cuenta no existe"}
        return {"status": "OK", "id_cuenta": id_cuenta, "id_cliente": r[0], "saldo": float(r[1]), "fecha_apertura": r[2]}
    except Exception as e:
        return {"status": "ERROR", "error": str(e)}

# ------------------ Query 2: TRANSFERIR_CUENTA ------------------ #
def transferir_cuenta(id_origen, id_destino, monto):
    try:
        c = conn()
        cur = c.cursor()
        cur.execute("SELECT saldo FROM Cuentas WHERE id_cuenta=?", (id_origen,))
        r1 = cur.fetchone()
        cur.execute("SELECT saldo FROM Cuentas WHERE id_cuenta=?", (id_destino,))
        r2 = cur.fetchone()
        if not r1 or not r2:
            c.close()
            return {"status": "ERROR", "error": "Una de las cuentas no existe"}
        if float(r1[0]) < monto:
            c.close()
            return {"status": "ERROR", "error": "Saldo insuficiente"}
        nuevo_origen = float(r1[0]) - monto
        nuevo_destino = float(r2[0]) + monto
        cur.execute("UPDATE Cuentas SET saldo=? WHERE id_cuenta=?", (nuevo_origen, id_origen))
        cur.execute("UPDATE Cuentas SET saldo=? WHERE id_cuenta=?", (nuevo_destino, id_destino))
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur.execute("INSERT INTO Transacciones (id_cuenta, tipo, monto, fecha) VALUES (?, ?, ?, ?)",
                    (id_origen, "Transferencia salida", -monto, fecha))
        cur.execute("INSERT INTO Transacciones (id_cuenta, tipo, monto, fecha) VALUES (?, ?, ?, ?)",
                    (id_destino, "Transferencia entrada", monto, fecha))
        c.commit()
        c.close()
        return {"status": "OK", "mensaje": f"Transferencia de S/.{monto:.2f} completada exitosamente."}
    except Exception as e:
        return {"status": "ERROR", "error": str(e)}

# ------------------ Query 3: ESTADO_PAGO_PRESTAMO ------------------ #
def estado_pago_prestamo_by_account(id_cuenta):
    try:
        c = conn()
        cur = c.cursor()
        cur.execute("SELECT id_cliente FROM Cuentas WHERE id_cuenta=?", (id_cuenta,))
        r = cur.fetchone()
        if not r:
            c.close()
            return {"status": "ERROR", "error": "No existe la cuenta indicada"}
        id_cliente = r[0]
        cur.execute("SELECT id_prestamo, monto, monto_pendiente, estado, fecha_solicitud FROM Prestamos WHERE id_cliente=?", (id_cliente,))
        rows = cur.fetchall()
        c.close()
        if not rows:
            return {"status": "OK", "data": []}
        data = []
        for p in rows:
            data.append({
                "id_prestamo": p[0],
                "monto_total": float(p[1]),
                "monto_pendiente": float(p[2]),
                "estado": p[3],
                "fecha_solicitud": p[4]
            })
        return {"status": "OK", "data": data}
    except Exception as e:
        return {"status": "ERROR", "error": str(e)}
