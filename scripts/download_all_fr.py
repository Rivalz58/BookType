"""
Télécharge tous les livres français de Project Gutenberg (4 107 textes).
- Sauvegarde dans storage/raw/
- Génère scripts/fr_metadata.csv pour l'ingestion ultérieure
- Reprend là où il s'est arrêté si interrompu
- 3 threads parallèles, 1 req/s max par thread
"""
import csv, os, sys, time, threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import STORAGE_RAW

os.makedirs(STORAGE_RAW, exist_ok=True)

# --- Charger le catalogue ---
print("Lecture du catalogue...", flush=True)
fr_books = []
with open("scripts/pg_catalog.csv", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        if row["Language"] == "fr" and row["Type"] == "Text":
            fr_books.append({
                "id":      row["Text#"],
                "titre":   row["Title"].replace("\n", " ").strip(),
                "auteur":  row["Authors"].strip(),
                "sujets":  row["Subjects"].strip(),
                "annee":   row["Issued"][:4] if row["Issued"] else "",
            })

print(f"{len(fr_books)} livres français trouvés.\n", flush=True)

# --- Vérifier ce qui est déjà téléchargé ---
deja = {f for f in os.listdir(STORAGE_RAW) if f.startswith("pg") and f.endswith(".txt")}
a_telecharger = [b for b in fr_books if f"pg{b['id']}.txt" not in deja]
print(f"Déjà téléchargés : {len(deja)}  |  Restants : {len(a_telecharger)}\n", flush=True)

# --- Métadonnées ---
METADATA_PATH = "scripts/fr_metadata.csv"
metadata_lock = threading.Lock()

def ecrire_metadata(livre, taille_ko):
    with metadata_lock:
        exists = os.path.exists(METADATA_PATH)
        with open(METADATA_PATH, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if not exists:
                w.writerow(["id", "nom_fichier", "titre", "auteur", "annee", "sujets"])
            w.writerow([
                livre["id"],
                f"pg{livre['id']}.txt",
                livre["titre"],
                livre["auteur"],
                livre["annee"],
                livre["sujets"],
            ])

# --- Compteurs ---
counter_lock = threading.Lock()
ok = len(deja)
echec = 0
total = len(fr_books)

def telecharger(livre):
    global ok, echec
    bid = livre["id"]
    dest = os.path.join(STORAGE_RAW, f"pg{bid}.txt")
    if os.path.exists(dest):
        return True

    urls = [
        f"https://www.gutenberg.org/cache/epub/{bid}/pg{bid}.txt",
        f"https://www.gutenberg.org/files/{bid}/{bid}-0.txt",
        f"https://www.gutenberg.org/files/{bid}/{bid}.txt",
    ]
    for url in urls:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=20) as r:
                contenu = r.read()
            with open(dest, "wb") as f:
                f.write(contenu)
            ecrire_metadata(livre, len(contenu) // 1024)
            with counter_lock:
                ok += 1
                if ok % 50 == 0:
                    pct = ok / total * 100
                    print(f"  [{ok}/{total} — {pct:.0f}%] dernier: {livre['titre'][:50]}", flush=True)
            time.sleep(0.5)
            return True
        except Exception:
            time.sleep(0.5)
            continue

    with counter_lock:
        echec += 1
    return False

# --- Téléchargement parallèle ---
print("Démarrage du téléchargement (3 threads)...", flush=True)
print("Le script peut être interrompu (Ctrl+C) et relancé — il reprend automatiquement.\n", flush=True)

debut = time.time()
try:
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(telecharger, livre): livre for livre in a_telecharger}
        for future in as_completed(futures):
            future.result()
except KeyboardInterrupt:
    print("\nInterrompu. Relancez le script pour continuer.")

duree = time.time() - debut
print(f"\n{'='*55}")
print(f"Terminé en {duree/60:.1f} min")
print(f"Téléchargés au total : {ok}/{total}")
print(f"Échecs : {echec}")
print(f"Métadonnées : scripts/fr_metadata.csv")
print(f"\nLancez ensuite : py scripts/ingest_all_fr.py")
