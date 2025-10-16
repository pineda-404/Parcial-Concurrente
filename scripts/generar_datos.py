# python/scripts/generar_cuentas_10000.py
import os, random, argparse, json, sqlite3
from datetime import datetime
from pathlib import Path

DEFAULT_DB_DIR = Path("data")
CONFIG = "config/nodos_config.json"

def load_config():
    with open(CONFIG,"r") as f:
        return json.load(f)

def ensure(path):
    os.makedirs(path, exist_ok=True)

def main(total=10000):
    cfg = load_config()
    partitions = cfg["partitions"]
    rep_factor = cfg["replication_factor"]
    
    # create accounts list
    print(f"Generando {total} cuentas en memoria...")
    accounts = []
    for i in range(1000, 1000 + total):
        # (id_cuenta, id_cliente, saldo, fecha)
        accounts.append((i, i - 900, round(random.uniform(100.0, 10000.0), 2), datetime.now().strftime("%Y-%m-%d")))

    # --- NUEVA LÓGICA: Poblar la base de datos SQLite ---
    db_path = Path("db/banco_chat.db")
    print(f"Poblando la base de datos SQLite en {db_path}...")
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        print("Limpiando la tabla 'Cuentas' en SQLite...")
        cursor.execute("DELETE FROM Cuentas;")
        
        # Preparar datos para la inserción masiva
        cuentas_para_db = [(acc[0], acc[1], acc[2], acc[3]) for acc in accounts]
        
        print(f"Insertando {len(cuentas_para_db)} registros en la tabla 'Cuentas'...")
        cursor.executemany("INSERT INTO Cuentas (id_cuenta, id_cliente, saldo, fecha_apertura) VALUES (?, ?, ?, ?)", cuentas_para_db)
        
        conn.commit()
        conn.close()
        print("Tabla 'Cuentas' en SQLite poblada exitosamente.")
    except Exception as e:
        print(f"[ERROR] No se pudo poblar la base de datos SQLite: {e}")
    # --- FIN DE LA NUEVA LÓGICA ---

    # for each partition index, write to each replica location (directories based on config)
    for p in range(partitions):
        # gather replica nodes for this partition
        nodes = cfg["partitions_map"].get(str(p), [])
        if not nodes:
            print(f"[WARN] Partición {p} sin nodos.")
            continue
        # create file content for accounts belonging to this partition
        part_accs = [a for a in accounts if (a[0] % partitions) == p]
        # Replicas are now identified by their full node object, not just index
        for node_info in nodes:
            # Construct path based on partition and replica index derived from node id or order
            # This part of your script might need adjustment depending on how you map node IDs to replica indices.
            # Assuming a simple mapping for now, e.g., replica_index is the order in the list.
            replica_index = nodes.index(node_info)
            dirpath = Path(f"data/particion{p}_replica{replica_index}")
            ensure(dirpath)
            filep = dirpath / f"cuentas_part{p}.txt"
            with open(filep, "w", encoding="utf-8") as fw:
                for acc in part_accs:
                    fw.write(f"{acc[0]},{acc[2]}\n")  # id,saldo
            print(f"Wrote {len(part_accs)} accounts to {filep}")

if __name__ == "__main__":
    import sys
    n = 10000
    if len(sys.argv) > 1:
        n = int(sys.argv[1])
    main(n)
    print("Hecho.")
