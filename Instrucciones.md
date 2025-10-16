
# Instrucciones para el Equipo - Proyecto Banco Distribuido

**Fecha:** 16 de Octubre, 2025

**Propósito:** Este documento explica la arquitectura final del proyecto y detalla los últimos pasos que debemos completar como equipo para la entrega final.

---

## 1. Resumen de la Arquitectura Final

El proyecto que tenemos es una simulación de un sistema bancario distribuido. La programación ya está terminada y el sistema es completamente funcional. La estructura de archivos fue refactorizada para que fuera más clara y profesional. 

La lógica principal se basa en estos componentes:

*   **`ServidorCentral` (Java):** Es el cerebro del sistema. Orquesta todo, recibe peticiones y aplica el protocolo de Confirmación en Dos Fases (2PC) para que las transacciones sean consistentes.

*   **`Nodos Trabajadores` (Java, Python y Go):** Son el clúster de datos. Tenemos 9 nodos en total (7 en Java, 1 en Python, 1 en Go) para cumplir el requisito de 3 lenguajes. Estos nodos almacenan los saldos de las cuentas en archivos `.txt` para simular un sistema de alto rendimiento.

*   **Base de Datos `SQLite` (`db/banco_chat.db`):** Es nuestro "libro de contabilidad". **Importante:** No es un duplicado de los `.txt`. Su función es guardar datos relacionales que los `.txt` no pueden manejar:
    *   La relación entre un **cliente** y sus múltiples **cuentas**.
    *   El registro de **préstamos** de cada cliente.
    *   Un historial de transacciones para auditoría.

*   **Clientes (Python):** Tenemos dos clientes. Uno de terminal (`cliente_banco`) para operaciones directas y uno con interfaz gráfica (`chat_gui`) para consultas, el cual usa un pequeño servidor intermediario en Python para comunicarse con el `ServidorCentral`.

> **Para entender cómo compilar y ejecutar todo, el documento principal es `README.md`.**

---

## 2. Pasos Finales para la Entrega (Nuestra Tarea)

La parte de programación ya está resuelta. Ahora nos toca completar los entregables que pide el PDF.

### Tarea 1: Generar Gráficas de Rendimiento (¡MUY IMPORTANTE!)

El PDF nos pide evaluar el rendimiento del sistema y presentar los resultados en gráficas. Para esto, se mejoró el script `scripts/load_tester.py`.

**Pasos a seguir:**

1.  Asegúrense de que todo el sistema esté corriendo (los 9 nodos, el servidor central, etc.), siguiendo las instrucciones del `README.md`.

2.  En una nueva terminal, ejecuten el script de pruebas:
    ```bash
    python3 scripts/load_tester.py
    ```

3.  El script tardará unos minutos y al final imprimirá en la misma terminal una **tabla de resultados en formato CSV**. Copien toda esa tabla (desde la cabecera `Threads,TotalTime_s...` hasta la última línea de números).

4.  Abran una hoja de cálculo (**Google Sheets** o **Microsoft Excel**).

5.  Peguen los datos copiados. Deberían separarse en columnas automáticamente.

6.  Con los datos en la hoja de cálculo, creen **dos gráficos de líneas**:
    *   **Gráfico 1 (Rendimiento/Throughput):**
        *   **Eje X:** La columna `Threads`.
        *   **Eje Y:** La columna `TPS` (Transacciones Por Segundo).
    *   **Gráfico 2 (Latencia):**
        *   **Eje X:** La columna `Threads`.
        *   **Eje Y:** La columna `AvgLatency_ms` (Latencia Promedio en milisegundos).

¡Estos dos gráficos son un entregable fundamental!

### Tarea 2: Completar el Informe Técnico (`informe_proyecto.tex`)

Ya existe un borrador muy completo del informe en el archivo `informe_proyecto.tex`. 

**Pasos a seguir:**

1.  Necesitan compilar este archivo para generar el PDF. La forma más fácil es subir el archivo `informe_proyecto.tex` a **Overleaf** (un editor de LaTeX online y gratuito) y él generará el PDF por ustedes.

2.  El informe tiene una sección llamada "Resultados y Gráficas" con un marcador de posición. **Deben tomar las imágenes de los gráficos que crearon en el paso anterior e insertarlas en esa sección del documento.**

3.  Junto a las gráficas, deben escribir un breve párrafo analizando los resultados. Por ejemplo: *"Como se observa en la Gráfica 1, el rendimiento del sistema escala linealmente hasta los 100 hilos, donde alcanza un máximo de X transacciones por segundo. A partir de ese punto, se estabiliza, lo que sugiere que..."*

### Tarea 3: Preparar la Presentación (Diapositivas)

Usando el `informe_proyecto.tex` como guía, creen las diapositivas para la exposición. Es clave que incluyan diagramas simples de la arquitectura y del flujo del protocolo 2PC para que la explicación sea fácil de seguir.

---

¡Ya estamos en la recta final! La parte más difícil de la programación está hecha. Solo nos queda ejecutar las pruebas y documentar el gran trabajo que se ha hecho. ¡Vamos a por ello!
