"""
Renomme les fichiers pgXXXX.txt avec le vrai titre extrait de la première ligne.
Ex: "The Project Gutenberg eBook of Le Côté de Guermantes" → "Le Côté de Guermantes.txt"
Met aussi à jour scripts/fr_metadata.csv.
"""
import os, re, csv, sys
sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import STORAGE_RAW

INVALID_CHARS = re.compile(r'[\\/:*?"<>|]')

def extraire_titre(chemin: str) -> str | None:
    for enc in ("utf-8", "latin-1", "cp1252"):
        try:
            with open(chemin, "r", encoding=enc) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    # "The Project Gutenberg eBook of TITRE"
                    m = re.search(r'Project Gutenberg[^\n]*? [Ee][Bb]ook of (.+)', line, re.IGNORECASE)
                    if not m:
                        m = re.search(r'Project Gutenberg[^\n]*? of (.+)', line, re.IGNORECASE)
                    if m:
                        titre = m.group(1).strip().rstrip(',;:.')
                        return titre
                    # Si la première ligne non vide ne correspond pas, on arrête
                    break
            break
        except Exception:
            continue
    return None

def sanitize(nom: str) -> str:
    nom = INVALID_CHARS.sub(' ', nom)
    nom = re.sub(r'\s+', ' ', nom).strip()
    return nom[:120]  # Windows max 255 chars, on garde de la marge

# Charger le catalogue pour garder la correspondance id → nouveau nom
fichiers = sorted(f for f in os.listdir(STORAGE_RAW) if re.match(r'^pg\d+\.txt$', f))
print(f"{len(fichiers)} fichiers à traiter...\n")

renommes = 0
echecs   = 0
noms_utilises = set(os.listdir(STORAGE_RAW))
id_to_newname = {}

for nom_ancien in fichiers:
    chemin = os.path.join(STORAGE_RAW, nom_ancien)
    book_id = re.search(r'pg(\d+)\.txt', nom_ancien).group(1)

    titre = extraire_titre(chemin)
    if not titre:
        echecs += 1
        id_to_newname[book_id] = nom_ancien  # garde l'ancien nom
        continue

    nom_propre = sanitize(titre) + ".txt"

    # Déduplication : si le nom existe déjà, ajoute l'ID
    if nom_propre in noms_utilises and nom_propre != nom_ancien:
        nom_propre = sanitize(titre) + f" (pg{book_id}).txt"

    if nom_propre == nom_ancien:
        id_to_newname[book_id] = nom_propre
        noms_utilises.add(nom_propre)
        continue

    nouveau_chemin = os.path.join(STORAGE_RAW, nom_propre)
    try:
        os.rename(chemin, nouveau_chemin)
        noms_utilises.add(nom_propre)
        noms_utilises.discard(nom_ancien)
        id_to_newname[book_id] = nom_propre
        renommes += 1
        if renommes % 200 == 0:
            print(f"  {renommes} renommés... dernier: {nom_propre[:60]}")
    except Exception as e:
        echecs += 1
        id_to_newname[book_id] = nom_ancien
        print(f"  ERREUR {nom_ancien}: {e}")

print(f"\nRenommés : {renommes}  |  Échecs : {echecs}")

# Mettre à jour fr_metadata.csv
meta_path = "scripts/fr_metadata.csv"
if os.path.exists(meta_path):
    rows = []
    with open(meta_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            bid = row["id"]
            if bid in id_to_newname:
                row["nom_fichier"] = id_to_newname[bid]
            rows.append(row)
    with open(meta_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"fr_metadata.csv mis à jour.")

print("\nTerminé.")
