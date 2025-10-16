import socket
import json

HOST = '127.0.0.1'
PORT = 6000

def menu():
    print("\n--- CLIENTE BANCO ---")
    print("1. Consultar cuenta")
    print("2. Transferir dinero")
    print("3. Crear cuenta")
    print("4. Eliminar cuenta")
    print("5. Salir")

def enviar(mensaje):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        s.sendall((json.dumps(mensaje) + "\n").encode())
        data = s.recv(4096).decode()
        print("[Respuesta]:", data)

def main():
    while True:
        menu()
        op = input("Seleccione: ")
        if op == "1":
            acc = input("Número de cuenta: ")
            enviar({"type":"CONSULTAR_CUENTA","account":int(acc)})
        elif op == "2":
            f = input("Cuenta origen: ")
            t = input("Cuenta destino: ")
            amt = input("Monto: ")
            enviar({"type":"TRANSFERIR_CUENTA","from":int(f),"to":int(t),"amount":float(amt)})
        elif op == "3":
            acc = input("Cuenta nueva: ")
            init = input("Saldo inicial: ")
            enviar({"type":"CREAR_CUENTA","account":int(acc),"initial":float(init)})
        elif op == "4":
            acc = input("Cuenta a eliminar: ")
            enviar({"type":"ELIMINAR_CUENTA","account":int(acc)})
        elif op == "5":
            break
        else:
            print("Opción inválida.")

if __name__ == "__main__":
    main()
