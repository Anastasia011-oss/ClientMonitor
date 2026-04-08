import socket
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import time
import pyodbc

HOST = "0.0.0.0"
PORT = 5000
lock = threading.Lock()

clients_online = {}

server = 'DESKTOP-EOO77GM\\SQLEXPRESS'
database = 'ClientMonitorDB'

conn_str = f'DRIVER={{ODBC Driver 17 for SQL Server}};' \
           f'SERVER={server};DATABASE={database};Trusted_Connection=yes'

try:
    conn_db = pyodbc.connect(conn_str)
    cursor = conn_db.cursor()
except Exception as e:
    print(f"Ошибка подключения к базе: {e}")
    exit(1)


def handle_client(conn, addr):
    ip = addr[0]

    with lock:
        clients_online[ip] = conn

    try:
        while True:
            data = conn.recv(1024).decode()
            if not data:
                break

            if data.startswith("ONLINE|"):
                hostname = data.split("|")[1]

                with lock:
                    cursor.execute("""
                    IF EXISTS (SELECT 1 FROM [clients] WHERE [ip]=?)
                        UPDATE [clients] SET [last_seen]=?, [hostname]=? WHERE [ip]=?
                    ELSE
                        INSERT INTO [clients] ([ip], [last_seen], [hostname]) VALUES (?, ?, ?)
                    """, (ip, time.time(), hostname, ip, ip, time.time(), hostname))
                    conn_db.commit()

    except:
        pass
    finally:
        with lock:
            if ip in clients_online:
                del clients_online[ip]
        conn.close()


def server_thread():
    s = socket.socket()
    s.bind((HOST, PORT))
    s.listen()

    while True:
        conn, addr = s.accept()
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()


def update_table():
    selected_ip = None

    selected = tree.selection()
    if selected:
        selected_ip = tree.item(selected[0])["values"][0]

    tree.delete(*tree.get_children())
    current_time = time.time()

    with lock:
        cursor.execute("SELECT [ip], [hostname], [last_seen] FROM [clients]")
        rows = cursor.fetchall()

        for ip, hostname, last_seen in rows:
            status = "ONLINE" if current_time - last_seen < 10 else "OFFLINE"
            item = tree.insert("", "end", values=(ip, hostname, status))

            if ip == selected_ip:
                tree.selection_set(item)

    root.after(2000, update_table)


def get_selected_ip():
    selected = tree.selection()
    if not selected:
        messagebox.showwarning("Ошибка", "Выберите клиента")
        return None

    return tree.item(selected[0])["values"][0]


def send_command(cmd):
    ip = get_selected_ip()
    if not ip:
        return

    with lock:
        if ip in clients_online:
            try:
                clients_online[ip].send((cmd + "\n").encode())
            except:
                messagebox.showerror("Ошибка", "Не удалось отправить")
        else:
            messagebox.showerror("Ошибка", "Клиент оффлайн")


root = tk.Tk()
root.title("Админ панель")

tree = ttk.Treeview(root, columns=("IP", "Hostname", "Status"), show="headings")
tree.heading("IP", text="IP")
tree.heading("Hostname", text="Hostname")
tree.heading("Status", text="Status")
tree.pack(fill=tk.BOTH, expand=True)

btn_frame = tk.Frame(root)
btn_frame.pack()

tk.Button(btn_frame, text="Выключить ПК", command=lambda: send_command("SHUTDOWN")).pack(side=tk.LEFT, padx=5, pady=5)

tk.Button(btn_frame, text="Запуск PowerShell", command=lambda: send_command("POWERSHELL|Get-Process")).pack(side=tk.LEFT, padx=5, pady=5)


def on_closing():
    root.destroy()


root.protocol("WM_DELETE_WINDOW", on_closing)

threading.Thread(target=server_thread, daemon=True).start()
update_table()
root.mainloop()