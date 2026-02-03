#!/usr/bin/env python3
"""
Script de demarrage rapide FLOOSE
Usage: python3 start.py
"""

import subprocess
import sys
import os

# Se placer dans le bon repertoire
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Tuer les anciennes instances sur le port 5003
subprocess.run("lsof -ti:5003 | xargs kill -9 2>/dev/null", shell=True)

print("""
╔═══════════════════════════════════════════╗
║           FLOOSE - Demarrage              ║
╠═══════════════════════════════════════════╣
║  URL:      http://localhost:5003          ║
║  Login:    demo@floose.com / Demo123!     ║
║  Banking:  http://localhost:5003/banking  ║
╚═══════════════════════════════════════════╝
""")

# Lancer l'application
subprocess.run([sys.executable, "run.py"])
