import socket
import threading
import tkinter as tk
from tkinter import ttk
import time
import pyodbc

HOST = "0.0.0.0"
PORT = 5000
lock = threading.Lock()

server = 'DESKTOP-EOO77GM\SQLEXPRESS'
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
    try:
        data = conn.recv(1024).decode()
        # Ожидаем формат "ONLINE|hostname"
        if data.startswith("ONLINE|"):
            hostname = data.split("|")[1]
            with lock:
                try:
                    cursor.execute("""
                    IF EXISTS (SELECT 1 FROM [clients] WHERE [ip]=?)
                        UPDATE [clients] SET [last_seen]=?, [hostname]=? WHERE [ip]=?
                    ELSE
                        INSERT INTO [clients] ([ip], [last_seen], [hostname]) VALUES (?, ?, ?)
                    """, (ip, time.time(), hostname, ip, ip, time.time(), hostname))
                    conn_db.commit()
                except Exception as e:
                    print(f"Ошибка работы с БД: {e}")
    except:
        pass
    finally:
        conn.close()

def server_thread():
    s = socket.socket()
    s.bind((HOST, PORT))
    s.listen()
    while True:
        conn, addr = s.accept()
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

def update_table():
    tree.delete(*tree.get_children())
    current_time = time.time()

    with lock:
        try:
            cursor.execute("SELECT [ip], [hostname], [last_seen] FROM [clients]")
            rows = cursor.fetchall()
            for ip, hostname, last_seen in rows:
                status = "ONLINE" if current_time - last_seen < 10 else "OFFLINE"
                tree.insert("", "end", values=(ip, hostname, status))
        except Exception as e:
            print(f"Ошибка при получении данных из БД: {e}")

    root.after(2000, update_table)

root = tk.Tk()
root.title("Админ панель")

tree = ttk.Treeview(root, columns=("IP", "Hostname", "Status"), show="headings")
tree.heading("IP", text="IP")
tree.heading("Hostname", text="Hostname")
tree.heading("Status", text="Status")
tree.pack(fill=tk.BOTH, expand=True)

def on_closing():
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_closing)

threading.Thread(target=server_thread, daemon=True).start()
update_table()
root.mainloop()