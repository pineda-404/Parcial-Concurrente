
# Sistema Bancario Distribuido Multi-lenguaje

Este proyecto es una simulación de un sistema bancario distribuido, diseñado para ser tolerante a fallos y consistente, implementado en Java, Python y Go.

El sistema demuestra la coordinación de servicios distribuidos a través de un protocolo de Confirmación en Dos Fases (2PC), replicación de datos para alta disponibilidad, y una arquitectura multi-lenguaje donde nodos escritos en diferentes lenguajes interoperan dentro del mismo clúster.

---

## Arquitectura

El sistema se compone de las siguientes partes principales:

1.  **Servidor Central (Java):** Actúa como el coordinador principal del clúster. Recibe todas las peticiones de los clientes, determina a qué nodos de datos enviar la operación y orquesta el protocolo 2PC para garantizar la consistencia en las transacciones que modifican datos (transferencias, etc.).

2.  **Nodos Trabajadores (Java, Python y Go):** Son los servidores que componen el clúster de datos. El conjunto de datos (saldos de cuentas) está particionado y replicado a través de estos nodos. Cada nodo es responsable de un subconjunto de los datos y opera de forma independiente, esperando órdenes del Servidor Central.

3.  **Almacenamiento Dual:**
    *   **Archivos de Texto (`.txt`):** Utilizados por los Nodos Trabajadores para almacenar los saldos de las cuentas. Simulan un almacén de datos de alto rendimiento cargado en memoria.
    *   **Base de Datos SQLite (`db/`):** Utilizada para almacenar datos relacionales y de auditoría, como la relación entre clientes y sus cuentas, el registro de préstamos, y un historial de transacciones.

4.  **Clientes (Python):**
    *   **Cliente de Terminal:** Una interfaz de línea de comandos para realizar operaciones bancarias directas.
    *   **Cliente GUI:** Una interfaz gráfica de usuario (con Tkinter) para consultas de usuario, que se comunica a través de un servidor proxy/BFF también en Python.

## Tecnologías Utilizadas

*   **Lenguajes:** Java, Python, Go
*   **Base de Datos:** SQLite3
*   **Protocolos:** TCP/IP Sockets, JSON para comunicación entre servicios.
*   **Automatización:** Scripts de Shell (`.sh`)

---

## Requisitos Previos

Para compilar y ejecutar este proyecto, necesitarás tener instalado:

*   Java JDK (versión 11 o superior)
*   Python (versión 3.8 o superior)
*   Go (versión 1.20 o superior)
*   Un compilador de C como `gcc` (requerido por el driver de Go para SQLite).
*   `zip` (opcional, para crear backups).

## Instrucciones de Instalación y Ejecución

Sigue estos pasos desde la raíz del proyecto.

### 1. Preparar el Entorno de Go

Si es la primera vez que clonas el proyecto, prepara el módulo de Go y descarga las dependencias.

```bash
go mod init examen-parcial
go get github.com/mattn/go-sqlite3
```

### 2. Compilar los Componentes

Compila los ejecutables de Java y Go.

```bash
# Compilar código Java
javac -d bin/ -cp lib/sqlite-jdbc.jar src/java/servidor_central/ServidorCentral.java src/java/nodo_trabajador/NodoWorker.java

# Compilar código Go
go build -o bin/nodo_worker_go src/go/nodo_worker/main.go
```

### 3. Preparar los Datos

Este script creará los archivos `.txt` distribuidos y poblará la base de datos SQLite con 10,000 cuentas. También puedes usar el script `poblar_db_ejemplos.py` para cargar solo datos de préstamos para pruebas.

```bash
python3 scripts/generar_datos.py
```

### 4. Ejecutar el Sistema

El sistema debe ser levantado en orden: primero el clúster de datos, luego los servidores principales.

**Paso 4.1: Iniciar el clúster de 9 nodos (en segundo plano)**

Este script lanza los 7 nodos Java, 1 nodo Python y 1 nodo Go.

```bash
./scripts/iniciar_cluster.sh
```

**Paso 4.2: Iniciar el Servidor Central (en una nueva terminal)**

```bash
java -cp bin:lib/sqlite-jdbc.jar -Ddb.path=$(pwd)/db/banco_chat.db servidor_central.ServidorCentral 6000 config/nodos_config.json
```

**Paso 4.3: Iniciar el Servidor de Chat (en una nueva terminal)**

```bash
python3 src/python/chat_gui/ChatServidor.py
```

### 5. Usar los Clientes

Una vez que todos los servidores estén corriendo, puedes usar los clientes para interactuar con el sistema.

*   **Cliente con Interfaz Gráfica (en una nueva terminal):**
    ```bash
    python3 src/python/chat_gui/ChatCliente.py
    ```
*   **Cliente de Terminal (en una nueva terminal):**
    ```bash
    python3 src/python/cliente_banco/BancoCliente.py
    ```

### 6. Detener el Clúster

Cuando termines, puedes detener todos los procesos de los nodos trabajadores con un solo comando. (Nota: esto no detiene el Servidor Central ni el de Chat, que deben ser detenidos con `Ctrl+C` en sus respectivas terminales).

```bash
./scripts/detener_cluster.sh
```

---

## Estructura del Proyecto

*   `src/`: Contiene todo el código fuente, organizado por lenguaje (`java`, `python`, `go`).
*   `bin/`: Almacena los archivos compilados y ejecutables (`.class`, `nodo_worker_go`).
*   `config/`: Archivos de configuración, como la topología del clúster.
*   `db/`: Contiene el archivo de la base de datos SQLite y su esquema SQL.
*   `lib/`: Librerías de Java (`.jar`).
*   `scripts/`: Scripts de utilidad para generar datos, realizar pruebas, e iniciar/detener el clúster.
