"""
Ingère les livres restants non classifiés avec les nouveaux genres :
roman, presse, histoire + mots-clés élargis sur les genres existants.
"""
import csv, os, sys, re, threading
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding='utf-8')

from config import STORAGE_RAW
from database.models import init_db, save_roman, add_log, get_all_romans, Roman, LogPipeline

init_db()

# Genres déjà en base → on ne ré-ingère pas
deja_en_base = {r.nom_fichier for r in get_all_romans()}

# Cartographie complète — les genres spécifiques EN PREMIER, génériques à la fin
GENRE_MOTS = {
    "roman_policier":        ["detective", "crime fiction", "mystery fiction", "police", "criminal", "murder"],
    "roman_historique":      ["historical fiction", "history -- fiction", "revolution, 1789", "world war, 1914",
                              "napoleonic wars", "napoleon i", "consulate and first empire", "court and courtiers",
                              "kings and rulers", "louis xiv", "middle ages", "crusades", "hundred years' war",
                              "house of valois", "medieval period", "ancien régime"],
    "roman_aventures":       ["adventure stories", "adventure fiction", "sea stories", "pirates",
                              "discovery and exploration"],
    "roman_science_fiction":  ["science fiction", "utopia", "dystopia", "space flight", "time travel"],
    "roman_fantastique":     ["fantasy fiction", "supernatural", "magic", "ghost", "vampire", "horror",
                              "occult", "witches", "monsters", "werewolf"],
    "roman_philosophique":   ["philosophical fiction", "philosophy -- fiction", "ethics", "morality"],
    "roman_psychologique":   ["psychological fiction", "psychology", "bildungsroman", "inner life", "mental illness"],
    "roman_amour":           ["love stories", "romance", "man-woman relationships", "erotic literature",
                              "erotic fiction", "courtship", "marriage -- fiction", "romances", "love"],
    "roman_noir":            ["naturalism", "social conditions -- fiction", "poverty -- fiction",
                              "working class -- fiction", "social problems", "crime and criminals -- fiction",
                              "prostitution"],
    "roman_satirique":       ["satire", "satirical", "parody", "irony", "humour", "humor"],
    "conte":                 ["fairy tales", "fables", "folk tales", "folklore", "legends -- fiction",
                              "fairy stories", "contes de fées"],
    "nouvelle":              ["short stories", "short stories, french", "nouvelles"],
    "biographie":            ["biography", "biographie", "autobiography", "memoirs", "autobiographical",
                              "diaries", "personal narratives", "lives of", "life of"],
    "mythe_legende":         ["mythology", "myths", "legends", "epic poetry", "odyssey", "homer",
                              "greek mythology", "roman mythology", "norse mythology"],
    "poetique":              ["poetry", "poems", "french poetry", "verse", "poetic", "ballads", "sonnets", "odes"],
    "theatre":               ["drama", "plays", "french drama", "comedies", "tragedies",
                              "comedy plays", "theater", "comédie", "vaudeville"],
    "epistolaire":           ["letters", "correspondence", "epistolary", "lettres"],
    "voyage":                ["description and travel", "voyages and travels", "voyages",
                              "travelers", "travel", "discovery and exploration", "expeditions"],
    "jeunesse":              ["juvenile fiction", "children's stories", "children's literature",
                              "youth", "boys -- fiction", "girls -- fiction"],
    "essai":                 ["french essays", "essays", "history and criticism", "politics and government",
                              "political science", "economics", "sociology", "philosophy",
                              "literary criticism", "intellectual life", "social life and customs",
                              "french literature", "conduct of life", "women", "education"],
    # Génériques — après tous les spécifiques
    "presse":                ["illustrated periodicals", "periodicals", "serial publications"],
    "histoire":              ["history", "historical"],
    "roman":                 ["french fiction", "fiction"],
}

def detecter_genre(sujets):
    if not sujets.strip():
        return None
    s = sujets.lower()
    for genre, mots in GENRE_MOTS.items():
        if any(m in s for m in mots):
            return genre
    return None

def extraire_auteur(auteur_raw):
    if not auteur_raw:
        return "Inconnu"
    auteur = re.sub(r',?\s*\d{4}-\d{4}', '', auteur_raw).strip().strip(',').strip()
    parties = [p.strip() for p in auteur.split(',') if p.strip()]
    if len(parties) >= 2:
        return f"{parties[1]} {parties[0]}"
    return parties[0] if parties else "Inconnu"

# Charger les métadonnées et filtrer ce qui reste à ingérer
with open('scripts/fr_metadata.csv', encoding='utf-8') as f:
    rows = list(csv.DictReader(f))

a_ingerer = []
for r in rows:
    if r['nom_fichier'] in deja_en_base:
        continue
    genre = detecter_genre(r['sujets'])
    if not genre:
        continue
    chemin = os.path.join(STORAGE_RAW, r['nom_fichier'])
    if not os.path.exists(chemin):
        continue
    annee = int(r['annee'][:4]) if r['annee'] and r['annee'][:4].lstrip('-').isdigit() else None
    if annee and annee < 0:
        annee = None
    a_ingerer.append({
        "nom_fichier": r['nom_fichier'],
        "titre":       r['titre'][:200],
        "auteur":      extraire_auteur(r['auteur']),
        "genre":       genre,
        "annee":       annee,
        "source":      f"https://www.gutenberg.org/ebooks/{r['id']}",
        "taille":      os.path.getsize(chemin),
    })

print(f"Nouveaux livres à ingérer : {len(a_ingerer)}")

from collections import Counter
repartition = Counter(l['genre'] for l in a_ingerer)
for g, n in sorted(repartition.items(), key=lambda x: -x[1]):
    print(f"  {g:<25} {n}")

counter_lock = threading.Lock()
ok = 0

def ingerer(livre):
    global ok
    try:
        roman = Roman(
            titre=livre['titre'], auteur=livre['auteur'], genre=livre['genre'],
            annee=livre['annee'], langue="français", source=livre['source'],
            nom_fichier=livre['nom_fichier'], format_fichier="txt",
            taille_octets=livre['taille'], statut="ingere",
        )
        save_roman(roman)
        add_log(LogPipeline(roman_id=roman.id, etape="ingestion",
                            statut="succès", message="Import automatique Gutenberg"))
        with counter_lock:
            ok += 1
            if ok % 200 == 0:
                print(f"  [{ok}/{len(a_ingerer)}] {livre['titre'][:50]}")
        return True
    except Exception:
        return False

with ThreadPoolExecutor(max_workers=8) as executor:
    for f in as_completed([executor.submit(ingerer, l) for l in a_ingerer]):
        f.result()

print(f"\nIngérés : {ok}/{len(a_ingerer)}")

# Résumé final
from database.models import get_all_romans
total = len(get_all_romans())
print(f"Total en base : {total} livres")
