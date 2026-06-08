"""Point d'entrée alternatif : initialise la BDD puis lance Streamlit."""
import os
import sys
import subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database.models import init_db

init_db()
print("Base de données initialisée.")

app_path = os.path.join(os.path.dirname(__file__), "app", "Home.py")
subprocess.run([sys.executable, "-m", "streamlit", "run", app_path])
