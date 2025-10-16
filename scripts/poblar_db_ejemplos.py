
import sqlite3
import os

# Construir la ruta a la base de datos desde la ubicación del script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "db", "banco_chat.db"))

def poblar_db():
    """Limpia y puebla las tablas Cuentas y Prestamos con datos de ejemplo."""
    print(f"Conectando a la base de datos en {DB_PATH}...")
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # --- Limpiar datos antiguos para evitar duplicados ---
        print("Limpiando tablas Cuentas y Prestamos...")
        cursor.execute("DELETE FROM Prestamos;")
        cursor.execute("DELETE FROM Cuentas;")

        # --- Insertar datos de ejemplo ---
        cuentas_ejemplo = [
            # (id_cuenta, id_cliente, saldo, fecha_apertura)
            (1000, 1, 5200.50, '2023-01-15'),
            (1001, 2, 8100.00, '2023-02-20'),
            (1002, 1, 1500.75, '2023-03-10') # El cliente 1 tiene dos cuentas
        ]
        
        prestamos_ejemplo = [
            # (id_cliente, monto, monto_pendiente, estado, fecha_solicitud)
            (1, 10000.0, 4500.0, 'Activo', '2023-05-01'),      # Préstamo del cliente 1
            (1, 5000.0, 0.0, 'Cancelado', '2022-11-11'),       # Otro préstamo del cliente 1
            (2, 15000.0, 12500.0, 'Activo', '2023-08-09'),     # Préstamo del cliente 2
            (2, 2000.0, 2000.0, 'Vencido', '2022-01-01')       # Otro préstamo del cliente 2
        ]

        print("Insertando cuentas de ejemplo...")
        cursor.executemany("INSERT INTO Cuentas (id_cuenta, id_cliente, saldo, fecha_apertura) VALUES (?, ?, ?, ?)", cuentas_ejemplo)

        print("Insertando préstamos de ejemplo...")
        cursor.executemany("INSERT INTO Prestamos (id_cliente, monto, monto_pendiente, estado, fecha_solicitud) VALUES (?, ?, ?, ?, ?)", prestamos_ejemplo)

        conn.commit()
        conn.close()
        print("¡Base de datos poblada con éxito!")

    except Exception as e:
        print(f"Ocurrió un error: {e}")

if __name__ == "__main__":
    poblar_db()
