"""
Ingère dans la BDD SQLite tous les livres français téléchargés
dont le genre a pu être détecté automatiquement.
"""
import csv, os, sys, re
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding='utf-8')

from config import STORAGE_RAW
from database.models import init_db, save_roman, add_log, Roman, LogPipeline

init_db()

GENRE_MOTS = {
    "roman_policier":        ["detective", "crime fiction", "mystery fiction", "police", "criminal", "murder", "crime"],
    "roman_historique":      ["historical fiction", "history -- fiction", "revolution, 1789", "world war, 1914",
                              "napoleonic wars", "napoleon i", "consulate and first empire", "court and courtiers",
                              "kings and rulers", "louis xiv", "middle ages", "crusades", "ancien régime"],
    "roman_aventures":       ["adventure stories", "adventure fiction", "sea stories", "pirates", "discovery and exploration"],
    "roman_science_fiction":  ["science fiction", "utopia", "dystopia", "space flight", "time travel"],
    "roman_fantastique":     ["fantasy fiction", "supernatural", "magic", "ghost", "vampire", "horror", "occult",
                              "witches", "monsters", "werewolf"],
    "roman_philosophique":   ["philosophical fiction", "philosophy -- fiction", "ethics", "morality"],
    "roman_psychologique":   ["psychological fiction", "psychology", "bildungsroman", "inner life", "mental illness"],
    "roman_amour":           ["love stories", "romance", "man-woman relationships", "erotic literature",
                              "courtship", "marriage -- fiction", "romances"],
    "roman_noir":            ["naturalism", "social conditions -- fiction", "poverty -- fiction",
                              "working class -- fiction", "social problems", "crime and criminals -- fiction"],
    "roman_satirique":       ["satire", "satirical", "parody", "irony", "humour", "humor"],
    "conte":                 ["fairy tales", "fables", "folk tales", "folklore", "legends -- fiction",
                              "fairy stories", "contes de fées"],
    "nouvelle":              ["short stories", "short stories, french", "nouvelles"],
    "biographie":            ["biography", "biographie", "autobiography", "memoirs", "autobiographical",
                              "diaries", "personal narratives", "lives of", "life of"],
    "mythe_legende":         ["mythology", "myths", "legends", "epic poetry", "odyssey", "homer",
                              "greek mythology", "roman mythology", "norse mythology"],
    "poetique":              ["poetry", "poems", "french poetry", "verse", "poetic", "ballads",
                              "sonnets", "odes"],
    "theatre":               ["drama", "plays", "french drama", "comedies", "tragedies",
                              "comedy plays", "theater", "comédie", "vaudeville"],
    "epistolaire":           ["letters", "correspondence", "epistolary", "lettres"],
    "voyage":                ["description and travel", "voyages and travels", "voyages",
                              "travelers", "travel", "discovery and exploration",
                              "geography -- description", "expeditions"],
    "jeunesse":              ["juvenile fiction", "children's stories", "children's literature",
                              "youth", "boys -- fiction", "girls -- fiction"],
    "essai":                 ["french essays", "essays", "history and criticism", "politics and government",
                              "political science", "economics", "sociology", "philosophy",
                              "literary criticism", "intellectual life"],
}

def detecter_genre(sujets: str) -> str:
    if not sujets.strip():
        return None
    s = sujets.lower()
    for genre, mots in GENRE_MOTS.items():
        if any(m in s for m in mots):
            return genre
    return None

def extraire_auteur(auteur_raw: str) -> str:
    if not auteur_raw:
        return "Inconnu"
    # Format Gutenberg : "Nom, Prénom, 1800-1900" → "Prénom Nom"
    auteur = re.sub(r',?\s*\d{4}-\d{4}', '', auteur_raw).strip().strip(',').strip()
    parties = [p.strip() for p in auteur.split(',') if p.strip()]
    if len(parties) >= 2:
        return f"{parties[1]} {parties[0]}"
    return parties[0] if parties else "Inconnu"

# Charger métadonnées
with open('scripts/fr_metadata.csv', encoding='utf-8') as f:
    rows = list(csv.DictReader(f))

# Filtrer ceux avec genre détecté et fichier présent
a_ingerer = []
for r in rows:
    genre = detecter_genre(r['sujets'])
    if not genre:
        continue
    nom_fichier = r['nom_fichier']
    chemin = os.path.join(STORAGE_RAW, nom_fichier)
    if not os.path.exists(chemin):
        continue
    annee = int(r['annee'][:4]) if r['annee'] and r['annee'][:4].lstrip('-').isdigit() else None
    if annee and annee < 0:
        annee = None
    a_ingerer.append({
        "nom_fichier": nom_fichier,
        "titre":       r['titre'][:200],
        "auteur":      extraire_auteur(r['auteur']),
        "genre":       genre,
        "annee":       annee,
        "source":      f"https://www.gutenberg.org/ebooks/{r['id']}",
        "taille":      os.path.getsize(chemin),
    })

print(f"Livres à ingérer : {len(a_ingerer)}")

# Ingestion
counter_lock = threading.Lock()
ok = 0
echec = 0

def ingerer(livre):
    global ok, echec
    try:
        roman = Roman(
            titre=livre['titre'],
            auteur=livre['auteur'],
            genre=livre['genre'],
            annee=livre['annee'],
            langue="français",
            source=livre['source'],
            nom_fichier=livre['nom_fichier'],
            format_fichier="txt",
            taille_octets=livre['taille'],
            statut="ingere",
        )
        save_roman(roman)
        add_log(LogPipeline(
            roman_id=roman.id,
            etape="ingestion",
            statut="succès",
            message=f"Import automatique Gutenberg",
        ))
        with counter_lock:
            ok += 1
            if ok % 100 == 0:
                print(f"  [{ok}/{len(a_ingerer)}] {livre['titre'][:50]}")
        return True
    except Exception as e:
        with counter_lock:
            echec += 1
        return False

with ThreadPoolExecutor(max_workers=8) as executor:
    futures = [executor.submit(ingerer, l) for l in a_ingerer]
    for f in as_completed(futures):
        f.result()

print(f"\n{'='*50}")
print(f"Ingérés : {ok}  |  Échecs : {echec}")
print(f"Lance maintenant le pipeline (page 2 de l'app).")
