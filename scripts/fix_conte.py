import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import urllib.request
from pipeline.ingestion import ingerer_fichier
from database.models import init_db

init_db()

urls = [
    "https://www.gutenberg.org/cache/epub/1597/pg1597.txt",
    "https://www.gutenberg.org/files/1597/1597-0.txt",
]
contenu = None
for url in urls:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            contenu = r.read()
            print(f"Telecharge ({len(contenu)//1024} Ko)")
            break
    except Exception as e:
        print(f"Echec {url}: {e}")

if contenu:
    ok, msg, _ = ingerer_fichier(
        contenu_bytes=contenu,
        nom_fichier="pg1597.txt",
        titre="Andersen's Fairy Tales",
        auteur="Hans Christian Andersen",
        genre="conte",
        annee=1835,
        langue="anglais",
        source="https://www.gutenberg.org/ebooks/1597",
    )
    print("OK" if ok else "ERREUR", msg)
