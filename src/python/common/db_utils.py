# db_sqlite.py (colócalo en python/chat_gui/)
import sqlite3
from datetime import datetime
import random
import os

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "db", "banco_chat.db"))

def conectar():
    return sqlite3.connect(DB_PATH)

def inicializar_bd():
    conn = conectar()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS ClienteChat (
            id_cliente_chat INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            fecha_conexion TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS MensajesChat (
            id_mensaje INTEGER PRIMARY KEY AUTOINCREMENT,
            id_cliente_chat INTEGER,
            mensaje TEXT,
            respuesta TEXT,
            fecha_envio TEXT,
            tipo_mensaje TEXT,
            FOREIGN KEY(id_cliente_chat) REFERENCES ClienteChat(id_cliente_chat)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS AvisosServidor (
            id_aviso INTEGER PRIMARY KEY AUTOINCREMENT,
            id_cliente INTEGER,
            tipo_aviso TEXT,
            contenido TEXT,
            fecha_envio TEXT,
            FOREIGN KEY(id_cliente) REFERENCES ClienteChat(id_cliente_chat)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS Cuentas (
            id_cuenta INTEGER PRIMARY KEY,
            id_cliente INTEGER,
            saldo REAL,
            fecha_apertura TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS Transacciones (
            id_transaccion INTEGER PRIMARY KEY AUTOINCREMENT,
            id_cuenta INTEGER,
            tipo TEXT,
            monto REAL,
            fecha TEXT,
            FOREIGN KEY(id_cuenta) REFERENCES Cuentas(id_cuenta)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS Prestamos (
            id_prestamo INTEGER PRIMARY KEY AUTOINCREMENT,
            id_cliente INTEGER,
            monto REAL,
            monto_pendiente REAL,
            estado TEXT,
            fecha_solicitud TEXT
        )
    """)

    conn.commit()
    conn.close()

# Si ejecutas este archivo directamente, inicializa
if __name__ == "__main__":
    inicializar_bd()
    print("DB inicializada en", DB_PATH)
