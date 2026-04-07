import socket
import winreg
import os
import sys
import time
import platform

HOST = "127.0.0.1"
PORT = 5000

hostname = platform.node()

def send_online():
    try:
        s = socket.socket()
        s.connect((HOST, PORT))
        s.send(f"ONLINE|{hostname}".encode())
        s.close()
    except:
        pass

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

add_to_startup()

try:
    while True:
        send_online()
        time.sleep(5)
except KeyboardInterrupt:
    print("Клиент закрыт пользователем")