# scripts/arqueo.py
import socket
import json

CENTRAL_SERVER = ("127.0.0.1", 6000)

def main():
    print(f"Conectando con el Servidor Central en {CENTRAL_SERVER} para el arqueo...")
    try:
        with socket.create_connection(CENTRAL_SERVER, timeout=10) as s:
            msg = json.dumps({"type": "ARQUEO"}) + "\n"
            s.sendall(msg.encode())
            resp = s.recv(4096).decode().strip()
            j = json.loads(resp)
            
            if j.get("status") == "OK":
                total = j.get("total_balance")
                print("\n==================================")
                print(f"  ARQUEO COMPLETADO CON ÉXITO")
                print(f"  SALDO TOTAL DEL SISTEMA: {total:.2f}")
                print("==================================\n")
            else:
                print("\n>> ERROR DURANTE EL ARQUEO:")
                print(f">> {j.get('error', 'Respuesta de error inesperada.')}")

    except Exception as e:
        print(f"\n>> ERROR DE CONEXIÓN:")
        print(f">> No se pudo conectar al Servidor Central: {e}")

if __name__ == "__main__":
    main()