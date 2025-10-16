import tkinter as tk
from tkinter import ttk, simpledialog
import socket, json, threading, os, sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from db_sqlite import conectar

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8085  # Puerto ChatServidor


# ------------------ Funciones auxiliares ------------------ #

def send_to_server(payload, timeout=4):
    try:
        with socket.create_connection((SERVER_HOST, SERVER_PORT), timeout=timeout) as s:
            s.sendall((json.dumps(payload) + "\n").encode())
            data = s.recv(65536).decode().strip()
            if not data:
                return {"status": "ERROR", "error": "sin respuesta"}
            try:
                return json.loads(data)
            except:
                return {"status": "ERROR", "error": "respuesta no JSON", "raw": data}
    except Exception as e:
        return {"status": "ERROR", "error": str(e)}


def get_history(limit=100):
    try:
        conn = conectar()
        cur = conn.cursor()
        cur.execute("SELECT fecha_envio, mensaje, respuesta FROM MensajesChat ORDER BY fecha_envio DESC LIMIT ?", (limit,))
        rows = cur.fetchall()
        conn.close()
        return rows[::-1]
    except Exception:
        return []


# ------------------ Clase principal GUI ------------------ #

class ChatGUI:
    def __init__(self, root):
        self.root = root
        root.title("Chat Banco - Consultas de Cliente")
        root.geometry("960x600")
        root.configure(bg="#f4f6f9")

        main = tk.Frame(root, bg="#f4f6f9")
        main.pack(fill=tk.BOTH, expand=True)

        chat_frame = tk.Frame(main, bg="white", bd=2, relief="groove")
        chat_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)

        tk.Label(chat_frame, text="Chat Banco", font=("Segoe UI", 12, "bold"), bg="white").pack(anchor="w", padx=10, pady=(5,0))
        self.txt = tk.Text(chat_frame, height=15, state="disabled", wrap=tk.WORD, bg="white", fg="#222")
        self.txt.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0,5))

        entry_frame = tk.Frame(main, bg="#f4f6f9")
        entry_frame.pack(fill=tk.X, padx=10, pady=(0,10))

        self.entry = tk.Entry(entry_frame, font=("Segoe UI", 10))
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0,6))
        self.entry.bind("<Return>", lambda e: self.send_msg())

        tk.Button(entry_frame, text="Enviar", bg="#0078d7", fg="white", relief="flat",
                  command=self.send_msg, width=12).pack(side=tk.LEFT)

        action_frame = tk.Frame(main, bg="#f4f6f9")
        action_frame.pack(fill=tk.X, padx=10, pady=4)
        for text, cmd in [
            ("Consultar cuenta", self.ask_consultar_cuenta),
            ("Ver transacciones", self.ask_transacciones),
            ("Estado préstamo", self.ask_estado_prestamo),
            ("Historial", self.load_history),
            ("Limpiar", self.clear_chat)
        ]:
            tk.Button(action_frame, text=text, command=cmd, width=18, bg="#e1e5ea",
                      relief="groove").pack(side=tk.LEFT, padx=5)

        self.table_frame = tk.Frame(main, bg="#f4f6f9")
        self.table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.tree = ttk.Treeview(self.table_frame, columns=("c1","c2","c3","c4"), show="headings")
        self.tree.pack(fill=tk.BOTH, expand=True)
        self._init_table(["ID", "Descripción", "Monto", "Fecha"])

        self.load_history()

    # ------------------ Métodos auxiliares ------------------ #

    def _init_table(self, headers):
        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = [f"c{i}" for i in range(1, len(headers)+1)]
        for i, h in enumerate(headers, start=1):
            self.tree.heading(f"c{i}", text=h)
            self.tree.column(f"c{i}", width=150, anchor="center")

    def _fill_table(self, rows):
        self.tree.delete(*self.tree.get_children())
        for row in rows:
            self.tree.insert("", "end", values=row)

    def append_text(self, txt, sender="system"):
        self.txt.config(state="normal")
        ts = datetime.now().strftime("[%H:%M:%S] ")
        prefix = "Tú: " if sender == "you" else "ChatB: "
        color = "#0078d7" if sender == "you" else "#000"
        self.txt.insert(tk.END, ts + prefix + txt + "\n", sender)
        self.txt.tag_config(sender, foreground=color)
        self.txt.config(state="disabled")
        self.txt.see(tk.END)

    def clear_chat(self):
        self.txt.config(state="normal")
        self.txt.delete("1.0", tk.END)
        self.txt.config(state="disabled")
        self._init_table(["ID", "Descripción", "Monto", "Fecha"])

    # ------------------ Cargar historial ------------------ #

    def load_history(self):
        self.txt.config(state="normal")
        self.txt.delete("1.0", tk.END)
        for t, m, resp in get_history(200):
            self.txt.insert(tk.END, f"[{t}] Tú: {m}\n")
            if resp:
                self.txt.insert(tk.END, f"[{t}] ChatB: {resp}\n")
        self.txt.config(state="disabled")

    # ------------------ Envío de mensajes ------------------ #

    def send_msg(self):
        msg = self.entry.get().strip()
        if not msg:
            return
        self.append_text(msg, "you")
        self.entry.delete(0, tk.END)
        payload = {"type": "CHAT_MESSAGE", "id_cliente_chat": 1, "message": msg}
        threading.Thread(target=self._send_and_store, args=(payload, msg), daemon=True).start()

    def _send_and_store(self, payload, raw_msg):
        resp = send_to_server(payload)
        reply_text = str(resp.get("reply", resp))
        self.append_text(reply_text, "server")

    # ------------------ Acciones de consulta ------------------ #

    def ask_consultar_cuenta(self):
        acc = simpledialog.askinteger("Consultar cuenta", "Ingrese ID de cuenta:", parent=self.root)
        if not acc: return
        self.append_text(f"Consultando cuenta {acc}...", "you")
        payload = {"type": "CONSULTAR_CUENTA", "account": acc}
        threading.Thread(target=self._do_query_and_show, args=(payload, "cuenta"), daemon=True).start()

    def ask_transacciones(self):
        acc = simpledialog.askinteger("Ver transacciones", "Ingrese ID de cuenta:", parent=self.root)
        if not acc: return
        self.append_text(f"Obteniendo transacciones de la cuenta {acc}...", "you")
        payload = {"type": "CONSULTAR_TRANSACCIONES", "account": acc}
        threading.Thread(target=self._do_query_and_show, args=(payload, "transacciones"), daemon=True).start()

    def ask_estado_prestamo(self):
        acc = simpledialog.askinteger("Estado préstamo", "Ingrese ID de cuenta:", parent=self.root)
        if not acc: return
        self.append_text(f"Consultando préstamos de {acc}...", "you")
        payload = {"type": "ESTADO_PAGO_PRESTAMO", "account": acc}
        threading.Thread(target=self._do_query_and_show, args=(payload, "prestamos"), daemon=True).start()

    # ------------------ Mostrar respuestas ------------------ #

    def _do_query_and_show(self, payload, mode):
        resp = send_to_server(payload)
        if not isinstance(resp, dict):
            self.append_text("Error de conexión o formato inválido", "server")
            return

        if resp.get("status") != "OK":
            self.append_text(str(resp), "server")
            return

        if mode == "cuenta":
            self._init_table(["Cuenta", "Saldo", "Cliente", "Fecha"])
            row = (
                resp.get("account"),
                resp.get("balance"),
                resp.get("cliente", "N/A"),
                datetime.now().strftime("%Y-%m-%d"),
            )
            self._fill_table([row])
            saldo = row[1] if row[1] is not None else 0.0
            self.append_text(f"Saldo disponible en cuenta {row[0]}: S/. {saldo:.2f}", "server")

        elif mode == "transacciones":
            self._init_table(["ID", "Concepto", "Monto", "Fecha"])
            data = resp.get("data", [])
            rows = [(d.get("id_transaccion","-"), d.get("tipo","-"), d.get("monto","-"), d.get("fecha","-")) for d in data]
            self._fill_table(rows)
            self.append_text(f"{len(rows)} transacciones encontradas.", "server")

        elif mode == "prestamos":
            self._init_table(["ID", "Monto pendiente", "Estado", "Fecha"])
            data = resp.get("data", [])
            rows = [(p.get("id_prestamo","-"), p.get("monto_pendiente","-"), p.get("estado","-"), p.get("fecha_solicitud","-")) for p in data]
            self._fill_table(rows)
            self.append_text(f"{len(rows)} préstamos encontrados.", "server")


if __name__ == "__main__":
    root = tk.Tk()
    app = ChatGUI(root)
    root.mainloop()
