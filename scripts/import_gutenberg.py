"""
Télécharge 20 œuvres du domaine public depuis Project Gutenberg
et les ingère directement dans la base de données SQLite.
Un livre par genre littéraire.
"""
import sys, os, time, urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pipeline.ingestion import ingerer_fichier
from database.models import init_db

init_db()

LIVRES = [
    {"id": 1661,  "titre": "The Adventures of Sherlock Holmes", "auteur": "Arthur Conan Doyle",    "genre": "roman_policier",      "annee": 1892, "langue": "anglais"},
    {"id": 558,   "titre": "The Thirty-Nine Steps",             "auteur": "John Buchan",            "genre": "roman_espionnage",    "annee": 1915, "langue": "anglais"},
    {"id": 13951, "titre": "Les Trois Mousquetaires",           "auteur": "Alexandre Dumas",         "genre": "roman_historique",    "annee": 1844, "langue": "français"},
    {"id": 5097,  "titre": "Vingt mille lieues sous les mers",  "auteur": "Jules Verne",             "genre": "roman_aventures",     "annee": 1870, "langue": "français"},
    {"id": 35,    "titre": "The Time Machine",                  "auteur": "H.G. Wells",              "genre": "roman_science_fiction","annee": 1895, "langue": "anglais"},
    {"id": 84,    "titre": "Frankenstein",                      "auteur": "Mary Shelley",            "genre": "roman_fantastique",   "annee": 1818, "langue": "anglais"},
    {"id": 4650,  "titre": "Candide",                           "auteur": "Voltaire",                "genre": "roman_philosophique", "annee": 1759, "langue": "français"},
    {"id": 174,   "titre": "The Picture of Dorian Gray",        "auteur": "Oscar Wilde",             "genre": "roman_psychologique", "annee": 1890, "langue": "anglais"},
    {"id": 1342,  "titre": "Pride and Prejudice",               "auteur": "Jane Austen",             "genre": "roman_amour",         "annee": 1813, "langue": "anglais"},
    {"id": 5711,  "titre": "Germinal",                          "auteur": "Emile Zola",              "genre": "roman_noir",          "annee": 1885, "langue": "français"},
    {"id": 829,   "titre": "Gulliver's Travels",                "auteur": "Jonathan Swift",          "genre": "roman_satirique",     "annee": 1726, "langue": "anglais"},
    {"id": 20972, "titre": "Histoires ou Contes du temps passé","auteur": "Charles Perrault",        "genre": "conte",               "annee": 1697, "langue": "français"},
    {"id": 209,   "titre": "The Turn of the Screw",             "auteur": "Henry James",             "genre": "nouvelle",            "annee": 1898, "langue": "anglais"},
    {"id": 65434, "titre": "Les Rêveries du promeneur solitaire","auteur": "Jean-Jacques Rousseau", "genre": "autobiographie",      "annee": 1782, "langue": "français"},
    {"id": 37635, "titre": "Victor Hugo: His Life and Work",    "auteur": "G. Barnett Smith",        "genre": "biographie",          "annee": 1885, "langue": "anglais"},
    {"id": 1727,  "titre": "The Odyssey",                       "auteur": "Homer",                   "genre": "mythe_legende",       "annee": -800, "langue": "anglais"},
    {"id": 6099,  "titre": "Les Fleurs du Mal",                 "auteur": "Charles Baudelaire",      "genre": "poetique",            "annee": 1857, "langue": "français"},
    {"id": 1524,  "titre": "Hamlet",                            "auteur": "William Shakespeare",     "genre": "theatre",             "annee": 1603, "langue": "anglais"},
    {"id": 52006, "titre": "Les Liaisons dangereuses",          "auteur": "Pierre Choderlos de Laclos","genre": "epistolaire",       "annee": 1782, "langue": "français"},
    {"id": 11,    "titre": "Alice's Adventures in Wonderland",  "auteur": "Lewis Carroll",           "genre": "autre",               "annee": 1865, "langue": "anglais"},
]


def telecharger(book_id: int) -> tuple[bytes | None, str | None]:
    urls = [
        f"https://www.gutenberg.org/cache/epub/{book_id}/pg{book_id}.txt",
        f"https://www.gutenberg.org/files/{book_id}/{book_id}-0.txt",
        f"https://www.gutenberg.org/files/{book_id}/{book_id}.txt",
    ]
    for url in urls:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read(), url
        except Exception:
            continue
    return None, None


ok_count = 0
for livre in LIVRES:
    print(f"[DL] {livre['titre']} ({livre['genre']})...", end=" ", flush=True)
    contenu, source_url = telecharger(livre["id"])

    if not contenu:
        print("❌ téléchargement impossible")
        continue

    annee = livre["annee"] if livre["annee"] > 0 else None
    succes, msg, _ = ingerer_fichier(
        contenu_bytes=contenu,
        nom_fichier=f"pg{livre['id']}.txt",
        titre=livre["titre"],
        auteur=livre["auteur"],
        genre=livre["genre"],
        annee=annee,
        langue=livre["langue"],
        source=f"https://www.gutenberg.org/ebooks/{livre['id']}",
    )
    if succes:
        ko = round(len(contenu) / 1024)
        print(f"OK ({ko} Ko)")
        ok_count += 1
    else:
        print(f"ERREUR {msg}")

    time.sleep(1)

print(f"\n{'='*50}")
print(f"Résultat : {ok_count}/{len(LIVRES)} livres ingérés avec succès.")
print("Lance le pipeline (page 2) pour transformer et extraire les features.")
