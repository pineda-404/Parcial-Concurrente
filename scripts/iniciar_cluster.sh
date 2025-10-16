#!/bin/bash

# Este script inicia todos los nodos trabajadores del clúster en segundo plano.

DB_PATH_ARG="-Ddb.path=$(pwd)/db/banco_chat.db"

echo "Iniciando clúster de nodos trabajadores (7 Java, 1 Python, 1 Go)..."

# --- Nodos para Partición 0 (Java) ---
java -cp bin:lib/sqlite-jdbc.jar $DB_PATH_ARG nodo_trabajador.NodoWorker 7001 data/particion0_replica0/cuentas_part0.txt &
java -cp bin:lib/sqlite-jdbc.jar $DB_PATH_ARG nodo_trabajador.NodoWorker 7002 data/particion0_replica1/cuentas_part0.txt &
java -cp bin:lib/sqlite-jdbc.jar $DB_PATH_ARG nodo_trabajador.NodoWorker 7003 data/particion0_replica2/cuentas_part0.txt &

# --- Nodos para Partición 1 (Java) ---
java -cp bin:lib/sqlite-jdbc.jar $DB_PATH_ARG nodo_trabajador.NodoWorker 7004 data/particion1_replica0/cuentas_part1.txt &
java -cp bin:lib/sqlite-jdbc.jar $DB_PATH_ARG nodo_trabajador.NodoWorker 7005 data/particion1_replica1/cuentas_part1.txt &
java -cp bin:lib/sqlite-jdbc.jar $DB_PATH_ARG nodo_trabajador.NodoWorker 7006 data/particion1_replica2/cuentas_part1.txt &

# --- Nodos para Partición 2 (1 Go, 1 Python, 1 Java) ---

# Nodo Go (compilado)
./bin/nodo_worker_go 7007 data/particion2_replica0/cuentas_part2.txt &

# Nodo Python
python3 src/python/nodo_trabajador/nodo_worker.py 7008 data/particion2_replica1/cuentas_part2.txt &

# Nodo Java
java -cp bin:lib/sqlite-jdbc.jar $DB_PATH_ARG nodo_trabajador.NodoWorker 7009 data/particion2_replica2/cuentas_part2.txt &


echo ""
echo "Clúster iniciado. Los nodos están corriendo en segundo plano."
echo "Espera unos segundos para que se estabilicen antes de iniciar el Servidor Central."
echo "Usa ./scripts/detener_cluster.sh para detenerlos todos."
