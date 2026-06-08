import csv, re, sys
from collections import Counter
sys.stdout.reconfigure(encoding='utf-8')

GENRE_MOTS = {
    "roman_policier":        ["detective", "crime fiction", "mystery fiction", "police", "criminal", "murder"],
    "roman_historique":      ["historical fiction", "history -- fiction", "revolution, 1789", "world war, 1914",
                              "napoleonic wars", "napoleon i", "consulate and first empire", "court and courtiers",
                              "kings and rulers", "louis xiv", "middle ages", "crusades", "hundred years' war",
                              "house of valois", "medieval period", "biographical fiction", "knights and knighthood",
                              "franco-prussian war", "wars of the vendée", "louis xvi"],
    "roman_aventures":       ["adventure stories", "adventure fiction", "sea stories", "pirates"],
    "roman_science_fiction":  ["science fiction", "utopia", "dystopia", "space flight", "time travel"],
    "roman_fantastique":     ["fantasy fiction", "supernatural", "magic", "ghost", "vampire", "horror",
                              "occult", "gothic fiction", "devil", "good and evil"],
    "roman_philosophique":   ["philosophical fiction", "philosophy -- fiction", "ethics", "morality",
                              "didactic fiction", "christian fiction", "clergy"],
    "roman_psychologique":   ["psychological fiction", "psychology", "bildungsroman", "inner life", "mental illness"],
    "roman_amour":           ["love stories", "romance", "man-woman relationships", "erotic literature",
                              "erotic fiction", "courtship", "marriage -- fiction", "romances", "love",
                              "domestic fiction", "adultery", "courtesans"],
    "roman_noir":            ["naturalism", "social conditions -- fiction", "poverty -- fiction",
                              "working class -- fiction", "social problems", "crime and criminals -- fiction",
                              "prostitution", "slave trade"],
    "roman_satirique":       ["satire", "satirical", "parody", "irony", "humour", "humor"],
    "conte":                 ["fairy tales", "fables", "folk tales", "folklore", "legends -- fiction", "fairy stories"],
    "nouvelle":              ["short stories", "short stories, french", "nouvelles"],
    "biographie":            ["biography", "autobiography", "memoirs", "autobiographical",
                              "diaries", "personal narratives", "lives of", "life of"],
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
    "presse":                ["illustrated periodicals", "periodicals", "serial publications"],
    "histoire":              ["history", "historical"],
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

compteur = Counter()
for r in rows:
    g = detecter_genre(r['sujets']) or "non_classifiable"
    compteur[g] += 1

total = len(rows)
classifies = total - compteur["non_classifiable"]

print(f"Total livres : {total}")
print(f"Avec genre détecté : {classifies} ({classifies/total*100:.0f}%)")
print(f"Non classifiables  : {compteur['non_classifiable']} ({compteur['non_classifiable']/total*100:.0f}%)\n")
print("Répartition :")
for g, n in sorted(compteur.items(), key=lambda x: -x[1]):
    print(f"  {g:<25} {n:>5}")
