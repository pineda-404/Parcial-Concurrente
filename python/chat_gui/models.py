import sqlite3
from datetime import datetime
from db_sqlite import DB_PATH

def get_connection():
    return sqlite3.connect(DB_PATH)

# ---------------- CHAT -----------------

def registrar_cliente(nombre):
    conn = get_connection()
    cur = conn.cursor()
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute("INSERT INTO ClienteChat (nombre, fecha_conexion) VALUES (?, ?)", (nombre, fecha))
    conn.commit()
    conn.close()

def guardar_mensaje(id_cliente, mensaje, respuesta=None, tipo="texto"):
    conn = get_connection()
    cur = conn.cursor()
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute("""
        INSERT INTO MensajesChat (id_cliente_chat, mensaje, respuesta, fecha_envio, tipo_mensaje)
        VALUES (?, ?, ?, ?, ?)
    """, (id_cliente, mensaje, respuesta, fecha, tipo))
    conn.commit()
    conn.close()

def obtener_mensajes():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM MensajesChat ORDER BY fecha_envio ASC")
    rows = cur.fetchall()
    conn.close()
    return rows

# ---------------- BANCO -----------------

def crear_cuenta(id_cliente, saldo_inicial):
    conn = get_connection()
    cur = conn.cursor()
    fecha = datetime.now().strftime("%Y-%m-%d")
    cur.execute("INSERT INTO Cuentas (id_cliente, saldo, fecha_apertura) VALUES (?, ?, ?)",
                (id_cliente, saldo_inicial, fecha))
    conn.commit()
    conn.close()

def registrar_transaccion(id_cuenta, tipo, monto):
    conn = get_connection()
    cur = conn.cursor()
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute("INSERT INTO Transacciones (id_cuenta, tipo, monto, fecha) VALUES (?, ?, ?, ?)",
                (id_cuenta, tipo, monto, fecha))
    conn.commit()
    conn.close()
