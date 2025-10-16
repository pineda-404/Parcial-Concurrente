
package main

import (
	"bufio"
	"database/sql"
	"encoding/json"
	"fmt"
	"log"
	"net"
	"os"
	"strconv"
	"strings"
	"sync"
	"time"

	_ "github.com/mattn/go-sqlite3"
)

// DB_PATH es la ruta a la base de datos SQLite.
const DB_PATH = "db/banco_chat.db"

// NodoWorker contiene el estado de un nodo trabajador.
type NodoWorker struct {
	port         int
	dataFile     string
	cuentas      map[int]float64
	preparedOps  map[string][]interface{}
	mu           sync.Mutex
}

// NewNodoWorker crea e inicializa una nueva instancia de NodoWorker.
func NewNodoWorker(port int, dataFile string) (*NodoWorker, error) {
	w := &NodoWorker{
		port:        port,
		dataFile:    dataFile,
		cuentas:     make(map[int]float64),
		preparedOps: make(map[string][]interface{}),
	}
	err := w.loadData()
	if err != nil {
		return nil, err
	}
	return w, nil
}

// loadData carga las cuentas desde el archivo de datos a memoria.
func (w *NodoWorker) loadData() error {
	log.Printf("[Nodo-%d] Cargando datos desde %s...", w.port, w.dataFile)
	file, err := os.Open(w.dataFile)
	if err != nil {
		if os.IsNotExist(err) {
			log.Printf("[Nodo-%d] Archivo de datos no encontrado, se creará uno nuevo.", w.port)
			// Asegurarse de que el directorio exista
			if err := os.MkdirAll(w.dataFile[:len(w.dataFile)-len(strings.Split(w.dataFile, "/")[len(strings.Split(w.dataFile, "/"))-1])], 0755); err != nil {
                return err
            }
			file, err = os.Create(w.dataFile)
			if err != nil {
				return err
			}
			file.Close()
			return nil
		}
		return err
	}
	defer file.Close()

	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line == "" {
			continue
		}
		parts := strings.Split(line, ",")
		if len(parts) != 2 {
			log.Printf("[Nodo-%d] [WARN] Línea inválida ignorada: %s", w.port, line)
			continue
		}
		id, err := strconv.Atoi(parts[0])
		if err != nil {
			log.Printf("[Nodo-%d] [WARN] ID inválido en línea: %s", w.port, line)
			continue
		}
		balance, err := strconv.ParseFloat(parts[1], 64)
		if err != nil {
			log.Printf("[Nodo-%d] [WARN] Saldo inválido en línea: %s", w.port, line)
			continue
		}
		w.cuentas[id] = balance
	}
	log.Printf("[Nodo-%d] %d cuentas cargadas en memoria.", w.port, len(w.cuentas))
	return scanner.Err()
}

// persistToDisk guarda el estado actual de las cuentas a disco.
func (w *NodoWorker) persistToDisk() error {
	w.mu.Lock()
	defer w.mu.Unlock()

	file, err := os.Create(w.dataFile)
	if err != nil {
		return err
	}
	defer file.Close()

	writer := bufio.NewWriter(file)
	for id, balance := range w.cuentas {
		_, err := writer.WriteString(fmt.Sprintf("%d,%.2f\n", id, balance))
		if err != nil {
			return err
		}
	}
	return writer.Flush()
}

// registrarTransaccionDB registra una transacción en la base de datos SQLite.
func (w *NodoWorker) registrarTransaccionDB(idCuenta int, tipo string, monto float64) {
	db, err := sql.Open("sqlite3", DB_PATH)
	if err != nil {
		log.Printf("[Nodo-%d] [WARN] No se pudo abrir SQLite: %v", w.port, err)
		return
	}
	defer db.Close()

	stmt, err := db.Prepare("INSERT INTO Transacciones(id_cuenta, tipo, monto, fecha) VALUES (?, ?, ?, ?)")
	if err != nil {
		log.Printf("[Nodo-%d] [WARN] No se pudo preparar statement SQLite: %v", w.port, err)
		return
	}
	defer stmt.Close()

	_, err = stmt.Exec(idCuenta, tipo, monto, time.Now().Format("2006-01-02 15:04:05"))
	if err != nil {
		log.Printf("[Nodo-%d] [WARN] No se pudo ejecutar insert en SQLite: %v", w.port, err)
	}
}

// handleConnection maneja una conexión de cliente entrante.
func (w *NodoWorker) handleConnection(conn net.Conn) {
	defer conn.Close()
	log.Printf("[Nodo-%d] Conexión aceptada desde %s", w.port, conn.RemoteAddr())
	reader := bufio.NewReader(conn)

	for {
		message, err := reader.ReadString('\n')
		if err != nil {
			// log.Printf("[Nodo-%d] Error leyendo de la conexión: %v", w.port, err)
			return
		}

		message = strings.TrimSpace(message)
		log.Printf("[Nodo-%d] Recibido: %s", w.port, message)

		var req map[string]interface{}
		if err := json.Unmarshal([]byte(message), &req); err != nil {
			log.Printf("[Nodo-%d] Error decodificando JSON: %v", w.port, err)
			continue
		}

		var response []byte
		reqType, _ := req["type"].(string)

		switch strings.ToUpper(reqType) {
		case "PREPARE_TRANSFER", "PREPARE_CREATE", "PREPARE_DELETE":
			response = w.handlePrepare(req)
		case "COMMIT":
			response = w.handleCommit(req)
		case "ABORT":
			response = w.handleAbort(req)
		case "CONSULTAR_CUENTA":
			response = w.handleQuery(req)
		case "SUM_PARTITION":
			response = w.handleSum(req)
		default:
			response, _ = json.Marshal(map[string]string{"status": "ERROR", "error": "TIPO_DESCONOCIDO"})
			response = append(response, '\n')
		}
		conn.Write(response)
	}
}

// handlePrepare maneja la fase de PREPARE del 2PC.
func (w *NodoWorker) handlePrepare(req map[string]interface{}) []byte {
	w.mu.Lock()
	defer w.mu.Unlock()

	txID, _ := req["tx_id"].(string)
	opsToPrepare := []interface{}{}
	reqType, _ := req["type"].(string)

	switch strings.ToUpper(reqType) {
	case "PREPARE_TRANSFER":
		fromAcc := int(req["from"].(float64))
		toAcc := int(req["to"].(float64))
		amount := req["amount"].(float64)

		if balance, ok := w.cuentas[fromAcc]; ok {
			if balance < amount {
				return jsonResponse(map[string]interface{}{"status": "ERROR", "tx_id": txID, "error": "Saldo insuficiente"})
			}
			opsToPrepare = append(opsToPrepare, []interface{}{"debit", fromAcc, amount})
		}
		if _, ok := w.cuentas[toAcc]; ok {
			opsToPrepare = append(opsToPrepare, []interface{}{"credit", toAcc, amount})
		}
	// ... Lógica similar para CREATE y DELETE
	}

	w.preparedOps[txID] = opsToPrepare
	return jsonResponse(map[string]interface{}{"status": "READY", "tx_id": txID})
}

// handleCommit maneja la fase de COMMIT del 2PC.
func (w *NodoWorker) handleCommit(req map[string]interface{}) []byte {
	w.mu.Lock()
	defer w.mu.Unlock()

	txID, _ := req["tx_id"].(string)
	ops, ok := w.preparedOps[txID]
	if !ok {
		return jsonResponse(map[string]interface{}{"status": "ERROR", "tx_id": txID, "error": "COMMIT_FAIL: Transacción no preparada"})
	}

	for _, op := range ops {
		opSlice := op.([]interface{})
		opType := opSlice[0].(string)
		acc := opSlice[1].(int)
		amount := opSlice[2].(float64)

		switch opType {
		case "debit":
			w.cuentas[acc] -= amount
			w.registrarTransaccionDB(acc, "Débito", -amount)
		case "credit":
			w.cuentas[acc] += amount
			w.registrarTransaccionDB(acc, "Crédito", amount)
		}
	}

	if err := w.persistToDisk(); err != nil {
        log.Printf("[Nodo-%d] [ERROR] Fallo al persistir en commit: %v", w.port, err)
        // En un sistema real, se necesitaría una estrategia de recuperación aquí.
        delete(w.preparedOps, txID) // Limpiar para evitar re-intentos fallidos
        return jsonResponse(map[string]interface{}{"status": "ERROR", "tx_id": txID, "error": "PERSIST_FAIL"})
    }

	delete(w.preparedOps, txID)
	return jsonResponse(map[string]interface{}{"status": "COMMITTED", "tx_id": txID})
}

// handleAbort maneja la fase de ABORT del 2PC.
func (w *NodoWorker) handleAbort(req map[string]interface{}) []byte {
	w.mu.Lock()
	defer w.mu.Unlock()
	txID, _ := req["tx_id"].(string)
	delete(w.preparedOps, txID)
	return jsonResponse(map[string]interface{}{"status": "ABORTED", "tx_id": txID})
}

// handleQuery maneja una consulta de saldo.
func (w *NodoWorker) handleQuery(req map[string]interface{}) []byte {
	acc := int(req["account"].(float64))
	if balance, ok := w.cuentas[acc]; ok {
		return jsonResponse(map[string]interface{}{"status": "OK", "account": acc, "balance": balance})
	} else {
		return jsonResponse(map[string]interface{}{"status": "ERROR", "error": "NO_EXISTE_CUENTA"})
	}
}

// handleSum maneja una suma de partición para el arqueo.
func (w *NodoWorker) handleSum(req map[string]interface{}) []byte {
	var total float64
	for _, balance := range w.cuentas {
		total += balance
	}
	return jsonResponse(map[string]interface{}{"status": "OK", "sum": total})
}

// jsonResponse es un helper para crear respuestas JSON.
func jsonResponse(data map[string]interface{}) []byte {
	resp, err := json.Marshal(data)
	if err != nil {
		log.Printf("Error creando respuesta JSON: %v", err)
		// Fallback a un error JSON manual
		return []byte("{\"status\":\"ERROR\",\"error\":\"JSON_RESPONSE_ERROR\"}\n")
	}
	return append(resp, '\n')
}

// start inicia el servidor del nodo trabajador.
func (w *NodoWorker) start() {
	listener, err := net.Listen("tcp", fmt.Sprintf(":%d", w.port))
	if err != nil {
		log.Fatalf("Fallo al escuchar en el puerto %d: %v", w.port, err)
	}
	defer listener.Close()
	log.Printf("[Nodo-%d] Nodo trabajador de GO escuchando en el puerto %d", w.port, w.port)

	for {
		conn, err := listener.Accept()
		if err != nil {
			log.Printf("Fallo al aceptar conexión: %v", err)
			continue
		}
		go w.handleConnection(conn)
	}
}

func main() {
	if len(os.Args) != 3 {
		fmt.Println("Uso: go run . <port> <data_file_path>")
		os.Exit(1)
	}

	port, err := strconv.Atoi(os.Args[1])
	if err != nil {
		log.Fatalf("Puerto inválido: %v", err)
	}

	dataFile := os.Args[2]

	worker, err := NewNodoWorker(port, dataFile)
	if err != nil {
		log.Fatalf("Fallo al crear el nodo trabajador: %v", err)
	}

	worker.start()
}
