"""
build.py — genera server.exe y client.exe con PyInstaller.

Uso:
    python build.py

Requisito previo:
    pip install pyinstaller

Los ejecutables quedan en la carpeta dist/.
"""

import os
import subprocess
import sys

# --------------------------------------------------------------------------
# server.exe  — ventana de consola visible (no --windowed)
# --------------------------------------------------------------------------
server_cmd = [
    sys.executable, "-m", "PyInstaller",
    "--onefile",                      # un único .exe
    "--console",                      # muestra la consola (logs del servidor)
    "--name", "server",
    "--add-data", f"assets{os.pathsep}assets",    # incluye la carpeta assets
    "--hidden-import", "scipy",
    "--icon", "danger.ico",
    "src/server.py",
]

# --------------------------------------------------------------------------
# client.exe  — sin consola (ventana pygame limpia)
# --------------------------------------------------------------------------
client_cmd = [
    sys.executable, "-m", "PyInstaller",
    "--onefile",
    "--windowed",                     # oculta la consola
    "--name", "Oh no, Ships!",
    "--add-data", f"assets{os.pathsep}assets",    # incluye la carpeta assets
    "--hidden-import", "pygame",
    "--hidden-import", "websockets",
    "--hidden-import", "pandas",
    "--hidden-import", "numpy",
    "--collect-all", "pygame_gui",
    "--collect-all", "pygame",
    "--runtime-hook", "pygame_compat_hook.py",
    "--icon", "taira.ico",
    "src/main.py",
]

# print("=" * 60)
# print("Compilando server.exe ...")
# print("=" * 60)
# subprocess.run(server_cmd, check=True)

print()
print("=" * 60)
print("Compilando client.exe ...")
print("=" * 60)
subprocess.run(client_cmd, check=True)

print()
print("Listo. Ejecutables en la carpeta dist/")
