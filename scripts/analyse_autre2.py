import csv, re, sys
from collections import Counter
sys.stdout.reconfigure(encoding='utf-8')

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
                              "literary criticism", "intellectual life"],
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

autres = [r for r in rows if not detecter_genre(r['sujets'])]
print(f"Livres encore 'autre' : {len(autres)}\n")

mots_counter = Counter()
for r in autres:
    segments = re.split(r'--|;', r['sujets'].lower())
    for seg in segments:
        seg = seg.strip().strip('-').strip()
        if seg and len(seg) > 3:
            mots_counter[seg] += 1

print("Top 60 sujets restants :")
for mot, n in mots_counter.most_common(60):
    print(f"  {n:>4}x  {mot}")
