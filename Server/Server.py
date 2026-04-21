import socket
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import time
import pyodbc
import os
import base64

HOST = "0.0.0.0"
PORT = 5000
lock = threading.Lock()

clients_online = {}
files_cache = {}

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


def show_file_content(content, filename):
    win = tk.Toplevel()
    win.title(f"Файл: {filename}")

    text = tk.Text(win, wrap="word")
    text.insert("1.0", content)
    text.pack(fill=tk.BOTH, expand=True)


def handle_client(conn, addr):
    ip = addr[0]

    with lock:
        clients_online[ip] = conn

    try:
        while True:
            data = conn.recv(4096).decode()
            if not data:
                break

            for line in data.split("\n"):
                if not line:
                    continue

                if line.startswith("ONLINE|"):
                    hostname = line.split("|")[1]

                    with lock:
                        cursor.execute("""
                        IF EXISTS (SELECT 1 FROM [clients] WHERE [ip]=?)
                            UPDATE [clients] SET [last_seen]=?, [hostname]=? WHERE [ip]=?
                        ELSE
                            INSERT INTO [clients] ([ip], [last_seen], [hostname]) VALUES (?, ?, ?)
                        """, (ip, time.time(), hostname, ip, ip, time.time(), hostname))
                        conn_db.commit()

                elif line.startswith("FILES|"):
                    parts = line.split("|", 2)

                    if len(parts) < 3:
                        continue

                    path = parts[1]
                    files_str = parts[2]
                    files = files_str.split("||") if files_str else []

                    with lock:
                        files_cache[ip] = (path, files)

                elif line.startswith("FILE_CONTENT|"):
                    parts = line.split("|", 2)

                    if len(parts) < 3:
                        continue

                    filename = parts[1]
                    content = parts[2]

                    root.after(0, show_file_content, content, filename)

                elif line.startswith("FILE_RECEIVED|"):
                    filename = line.split("|")[1]
                    root.after(0, lambda: messagebox.showinfo("Успех", f"Файл {filename} доставлен"))

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

            if ip in files_cache:
                path, files = files_cache[ip]

                tree.insert(item, "end", values=(f"[{path}]", "", ""))
                tree.insert(item, "end", values=("------------------------------", "", ""))

                for f in files:
                    if f:
                        tree.insert(item, "end", values=("  • " + f, "", ""))

                tree.item(item, open=True)

    root.after(2000, update_table)


def get_selected_ip():
    selected = tree.selection()
    if not selected:
        return None

    values = tree.item(selected[0])["values"]

    if len(values) > 0 and "." in str(values[0]):
        return values[0]

    return None


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


def send_file_to_client():
    ip = get_selected_ip()
    if not ip:
        return

    filepath = filedialog.askopenfilename()
    if not filepath:
        return

    try:
        with open(filepath, "rb") as f:
            data = f.read()

        filename = os.path.basename(filepath)
        encoded = base64.b64encode(data).decode()

        with lock:
            if ip in clients_online:
                clients_online[ip].send(f"SEND_FILE|{filename}|{encoded}\n".encode())

    except:
        messagebox.showerror("Ошибка", "Не удалось отправить файл")


def on_double_click(event):
    selected = tree.selection()
    if not selected:
        return

    item = selected[0]
    values = tree.item(item)["values"]
    parent = tree.parent(item)

    if parent == "":
        ip = values[0]

        with lock:
            if ip in clients_online:
                clients_online[ip].send("GET_FILES|\n".encode())

    else:
        parent_values = tree.item(parent)["values"]
        ip = parent_values[0]

        name = values[0].replace("•", "").strip()

        with lock:
            if ip in clients_online and ip in files_cache:
                current_path = files_cache[ip][0]

                if name.startswith("[DIR]"):
                    folder = name.replace("[DIR]", "")
                    new_path = current_path + "\\" + folder
                    clients_online[ip].send(f"GET_FILES|{new_path}\n".encode())
                else:
                    full_path = current_path + "\\" + name
                    clients_online[ip].send(f"GET_FILE_CONTENT|{full_path}\n".encode())


root = tk.Tk()
root.title("Админ панель")

style = ttk.Style()
style.configure("Treeview",
                background="#0b1a3a",
                foreground="white",
                fieldbackground="#e6eef7",
                rowheight=25)

style.map('Treeview', background=[('selected', '#b3d1ff')])

tree = ttk.Treeview(root, columns=("IP", "Hostname", "Status"))

tree.heading("IP", text="IP")
tree.heading("Hostname", text="Hostname")
tree.heading("Status", text="Status")

tree.pack(fill=tk.BOTH, expand=True)

tree.bind("<Double-1>", on_double_click)

btn_frame = tk.Frame(root)
btn_frame.pack()

tk.Button(btn_frame, text="Выключить ПК", command=lambda: send_command("SHUTDOWN")).pack(side=tk.LEFT)
tk.Button(btn_frame, text="Запуск PowerShell", command=lambda: send_command("POWERSHELL|Get-Process")).pack(side=tk.LEFT)
tk.Button(btn_frame, text="Отправить файл", command=send_file_to_client).pack(side=tk.LEFT)


def on_closing():
    root.destroy()


root.protocol("WM_DELETE_WINDOW", on_closing)

threading.Thread(target=server_thread, daemon=True).start()
update_table()
root.mainloop()