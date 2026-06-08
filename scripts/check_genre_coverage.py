import csv, sys
sys.stdout.reconfigure(encoding='utf-8')

GENRE_MOTS = {
    "roman_policier":       ["detective", "crime fiction", "mystery", "police", "criminal", "murder"],
    "roman_espionnage":     ["spy", "espionage", "secret service", "intelligence"],
    "roman_historique":     ["historical fiction", "history -- fiction", "histoire -- roman"],
    "roman_aventures":      ["adventure", "sea stories", "voyages", "pirates", "exploration"],
    "roman_science_fiction":["science fiction", "space", "future", "utopia", "dystopia"],
    "roman_fantastique":    ["fantasy", "supernatural", "magic", "ghost", "vampire", "horror"],
    "roman_philosophique":  ["philosophical", "philosophy", "ethics", "morality"],
    "roman_psychologique":  ["psychological", "psychology", "bildungsroman", "inner life"],
    "roman_amour":          ["love stories", "romance", "man-woman relationships", "amour"],
    "roman_noir":           ["naturalism", "social conditions", "poverty", "working class", "zola"],
    "roman_satirique":      ["satire", "satirical", "parody", "irony", "humour"],
    "conte":                ["fairy tales", "fables", "folk tales", "contes", "legends -- fiction"],
    "nouvelle":             ["short stories", "nouvelles"],
    "autobiographie":       ["autobiography", "memoirs", "autobiographie", "confessions"],
    "biographie":           ["biography", "biographie", "life of", "lives of"],
    "mythe_legende":        ["mythology", "myths", "legends", "epic", "odyssey", "homer"],
    "poetique":             ["poetry", "poems", "poésie", "verse", "poetic"],
    "theatre":              ["drama", "plays", "comedies", "tragedies", "theatre"],
    "epistolaire":          ["letters", "correspondence", "epistolary", "lettres"],
}

def detecter_genre(sujets: str) -> str:
    s = sujets.lower()
    for genre, mots in GENRE_MOTS.items():
        if any(m in s for m in mots):
            return genre
    return "autre"

with open('scripts/fr_metadata.csv', encoding='utf-8') as f:
    rows = list(csv.DictReader(f))

compteur = {}
for r in rows:
    g = detecter_genre(r['sujets'])
    compteur[g] = compteur.get(g, 0) + 1

total = len(rows)
detectes = total - compteur.get("autre", 0)
print(f"Total livres : {total}")
print(f"Genre detecte : {detectes} ({detectes/total*100:.0f}%)")
print(f"Tomberont en 'autre' : {compteur.get('autre',0)} ({compteur.get('autre',0)/total*100:.0f}%)\n")
print("Répartition par genre détecté :")
for g, n in sorted(compteur.items(), key=lambda x: -x[1]):
    print(f"  {g:<25} {n:>5} livres")
