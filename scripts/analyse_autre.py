import csv, re, sys
from collections import Counter
sys.stdout.reconfigure(encoding='utf-8')

GENRE_MOTS = {
    "roman_policier":       ["detective", "crime fiction", "mystery", "police", "criminal", "murder"],
    "roman_espionnage":     ["spy", "espionage", "secret service"],
    "roman_historique":     ["historical fiction", "history -- fiction", "histoire -- roman"],
    "roman_aventures":      ["adventure", "sea stories", "voyages", "pirates", "exploration"],
    "roman_science_fiction":["science fiction", "space", "future", "utopia", "dystopia"],
    "roman_fantastique":    ["fantasy", "supernatural", "magic", "ghost", "vampire", "horror"],
    "roman_philosophique":  ["philosophical", "philosophy", "ethics", "morality"],
    "roman_psychologique":  ["psychological", "psychology", "bildungsroman", "inner life"],
    "roman_amour":          ["love stories", "romance", "man-woman relationships"],
    "roman_noir":           ["naturalism", "social conditions", "poverty", "working class"],
    "roman_satirique":      ["satire", "satirical", "parody", "irony", "humour"],
    "conte":                ["fairy tales", "fables", "folk tales", "legends -- fiction"],
    "nouvelle":             ["short stories", "nouvelles"],
    "autobiographie":       ["autobiography", "memoirs", "autobiographie", "confessions"],
    "biographie":           ["biography", "biographie", "life of", "lives of"],
    "mythe_legende":        ["mythology", "myths", "legends", "epic", "odyssey"],
    "poetique":             ["poetry", "poems", "verse", "poetic"],
    "theatre":              ["drama", "plays", "comedies", "tragedies"],
    "epistolaire":          ["letters", "correspondence", "epistolary"],
}

def detecter_genre(sujets):
    s = sujets.lower()
    for genre, mots in GENRE_MOTS.items():
        if any(m in s for m in mots):
            return genre
    return "autre"

with open('scripts/fr_metadata.csv', encoding='utf-8') as f:
    rows = list(csv.DictReader(f))

autres = [r for r in rows if detecter_genre(r['sujets']) == 'autre']
print(f"Livres 'autre' : {len(autres)}\n")

# Extraire tous les mots-clés des sujets
mots_counter = Counter()
for r in autres:
    sujets = r['sujets'].lower()
    # Extraire les segments avant "--" ou ";"
    segments = re.split(r'--|;', sujets)
    for seg in segments:
        seg = seg.strip().strip('-').strip()
        if seg and len(seg) > 3 and 'fiction' not in seg and 'france' not in seg:
            mots_counter[seg] += 1

print("Top 50 sujets dans les livres 'autre' :")
for mot, n in mots_counter.most_common(50):
    print(f"  {n:>5}x  {mot}")
