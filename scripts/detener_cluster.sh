#!/bin/bash

# Este script detiene todos los procesos de nodos trabajadores.

echo "Deteniendo todos los nodos del clúster..."

# Usar pkill para encontrar y detener los procesos por su línea de comando
# Esto es más seguro que matar todos los procesos de 'java' o 'go'
pkill -f "nodo_trabajador.NodoWorker"
pkill -f "nodo_worker_go"
pkill -f "python3 src/python/nodo_trabajador/nodo_worker.py"

echo "Procesos de nodos detenidos."
