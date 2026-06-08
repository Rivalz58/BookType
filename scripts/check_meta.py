import csv, sys
sys.stdout.reconfigure(encoding='utf-8')

with open('scripts/fr_metadata.csv', encoding='utf-8') as f:
    rows = list(csv.DictReader(f))

print(f"Total: {len(rows)} lignes\n")
print("Exemples de sujets Gutenberg:")
for r in rows[:10]:
    titre = r['titre'][:45]
    sujets = r['sujets'][:100]
    print(f"  {titre}")
    print(f"    -> {sujets}")
    print()
