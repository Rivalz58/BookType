import csv, sys
sys.stdout.reconfigure(encoding='utf-8')

with open('scripts/fr_metadata.csv', encoding='utf-8') as f:
    rows = list(csv.DictReader(f))

mots = ["spy", "espionage", "secret service", "intelligence"]
print("Livres matchant les mots-clés espionnage:\n")
for r in rows:
    s = r['sujets'].lower()
    matched = [m for m in mots if m in s]
    if matched:
        print(f"  {r['titre'][:60]}")
        print(f"    mot: {matched} | sujets: {r['sujets'][:100]}")
        print()
