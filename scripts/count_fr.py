import csv, sys
sys.stdout.reconfigure(encoding='utf-8')

fr_books = []
with open('scripts/pg_catalog.csv', encoding='utf-8') as f:
    for row in csv.DictReader(f):
        if row['Language'] == 'fr' and row['Type'] == 'Text':
            fr_books.append(row)

print(f"Livres francais disponibles: {len(fr_books)}")
print("Exemples:")
for r in fr_books[:10]:
    bid = r['Text#']
    titre = r['Title'][:60]
    auteur = r['Authors'][:40]
    print(f"  ID {bid}: {titre} | {auteur}")
