# python/scripts/generar_cuentas_10000.py
import os, random, argparse, json
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
    accounts = []
    for i in range(1000, 1000 + total):
        accounts.append((i, i-900, round(random.uniform(100.0, 10000.0), 2), datetime.now().strftime("%Y-%m-%d")))
    # for each partition index, write to each replica location (directories based on config)
    for p in range(partitions):
        # gather replica nodes for this partition
        nodes = cfg["partitions_map"].get(str(p), [])
        if not nodes:
            print(f"[WARN] Partición {p} sin nodos.")
            continue
        # create file content for accounts belonging to this partition
        part_accs = [a for a in accounts if (a[0] % partitions) == p]
        for replica_index, node in enumerate(nodes):
            # path: data/particion{p}_replica{replica_index}/cuentas_part{p}.txt
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
