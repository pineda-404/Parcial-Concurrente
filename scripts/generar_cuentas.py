# scripts/generar_cuentas.py
import os
import random
import math

ROOT = "data"
PARTITIONS = 2          # ajusta si quieres más
REPLICATION_FACTOR = 2  # replicar cada partición en 2 réplicas (ajusta)
ACCOUNTS = 10000
START_ID = 1000

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)

def partition_for(acc_id, partitions):
    return acc_id % partitions

def write_partitions(partitions, replicas_map):
    # replicas_map: dict partition -> list of replica_dir paths
    for p, dirs in replicas_map.items():
        # collect accounts belonging to partition p
        pass

def main():
    # generate accounts
    accounts = []
    for i in range(ACCOUNTS):
        acc_id = START_ID + i
        balance = round(random.uniform(50.0, 5000.0), 2)
        # format "id,balance"
        accounts.append((acc_id, balance))

    # prepare dirs
    replicas_map = {}
    for p in range(PARTITIONS):
        replicas_map[p] = []
        for r in range(REPLICATION_FACTOR):
            d = os.path.join(ROOT, f"particion{p}_replica{r}")
            ensure_dir(d)
            replicas_map[p].append(d)

    # distribute accounts across partitions and write to each replica file
    for acc_id, balance in accounts:
        p = partition_for(acc_id, PARTITIONS)
        # write to **all** replicas for partition p
        for replica_dir in replicas_map[p]:
            fn = os.path.join(replica_dir, f"cuentas_part{p}.txt")
            with open(fn, "a", encoding="utf-8") as f:
                f.write(f"{acc_id},{balance:.2f}\n")

    print(f"Generadas {ACCOUNTS} cuentas en {PARTITIONS} particiones con {REPLICATION_FACTOR} réplicas.")
    print("Directorios creados en 'data/'")

if __name__ == "__main__":
    main()
