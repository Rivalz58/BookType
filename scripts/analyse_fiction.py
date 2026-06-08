import csv, re, sys
from collections import Counter
sys.stdout.reconfigure(encoding='utf-8')

GENRE_MOTS = {
    "roman_policier":        ["detective", "crime fiction", "mystery fiction", "police", "criminal", "murder"],
    "roman_historique":      ["historical fiction", "history -- fiction", "revolution, 1789", "world war, 1914",
                              "napoleonic wars", "napoleon i", "consulate and first empire", "court and courtiers",
                              "kings and rulers", "louis xiv", "middle ages", "crusades", "hundred years' war",
                              "house of valois", "medieval period", "ancien régime"],
    "roman_aventures":       ["adventure stories", "adventure fiction", "sea stories", "pirates"],
    "roman_science_fiction":  ["science fiction", "utopia", "dystopia", "space flight", "time travel"],
    "roman_fantastique":     ["fantasy fiction", "supernatural", "magic", "ghost", "vampire", "horror", "occult"],
    "roman_philosophique":   ["philosophical fiction", "philosophy -- fiction", "ethics", "morality"],
    "roman_psychologique":   ["psychological fiction", "psychology", "bildungsroman", "inner life", "mental illness"],
    "roman_amour":           ["love stories", "romance", "man-woman relationships", "erotic literature",
                              "erotic fiction", "courtship", "marriage -- fiction", "romances", "love"],
    "roman_noir":            ["naturalism", "social conditions -- fiction", "poverty -- fiction",
                              "working class -- fiction", "social problems", "crime and criminals -- fiction",
                              "prostitution"],
    "roman_satirique":       ["satire", "satirical", "parody", "irony", "humour", "humor"],
    "conte":                 ["fairy tales", "fables", "folk tales", "folklore", "legends -- fiction", "fairy stories"],
    "nouvelle":              ["short stories", "short stories, french", "nouvelles"],
    "biographie":            ["biography", "autobiography", "memoirs", "autobiographical", "diaries", "personal narratives"],
    "mythe_legende":         ["mythology", "myths", "legends", "epic poetry", "odyssey", "homer"],
    "poetique":              ["poetry", "poems", "french poetry", "verse", "poetic", "ballads"],
    "theatre":               ["drama", "plays", "french drama", "comedies", "tragedies", "comedy plays", "theater"],
    "epistolaire":           ["letters", "correspondence", "epistolary"],
    "voyage":                ["description and travel", "voyages and travels", "travelers", "travel", "expeditions"],
    "jeunesse":              ["juvenile fiction", "children's stories", "children's literature", "youth"],
    "essai":                 ["french essays", "essays", "history and criticism", "politics and government",
                              "political science", "economics", "sociology", "philosophy",
                              "literary criticism", "intellectual life", "social life and customs",
                              "french literature", "conduct of life"],
}

def detecter_genre(sujets):
    if not sujets.strip():
        return None
    s = sujets.lower()
    for genre, mots in GENRE_MOTS.items():
        if any(m in s for m in mots):
            return genre
    return None

with open('scripts/fr_metadata.csv', encoding='utf-8') as f:
    rows = list(csv.DictReader(f))

# Livres avec "fiction" mais sans genre détecté
fiction_sans_genre = [r for r in rows
                      if not detecter_genre(r['sujets'])
                      and ('fiction' in r['sujets'].lower())]

print(f"Livres 'fiction' sans genre détecté : {len(fiction_sans_genre)}\n")

# Extraire tous leurs sujets (hors "fiction", "french fiction", "france")
mots = Counter()
for r in fiction_sans_genre:
    segs = re.split(r'--|;', r['sujets'].lower())
    for s in segs:
        s = s.strip().strip('-').strip()
        if s and len(s) > 3 and s not in ('fiction','french fiction','france','paris (france)','paris','19th century','20th century','18th century','17th century'):
            mots[s] += 1

print("Sujets associés (hors france/fiction/siècle) :")
for m, n in mots.most_common(60):
    print(f"  {n:>4}x  {m}")
