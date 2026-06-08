import csv, re, sys
from collections import Counter
sys.stdout.reconfigure(encoding='utf-8')

with open('scripts/fr_metadata.csv', encoding='utf-8') as f:
    rows = list(csv.DictReader(f))

# Extraire tous les segments de sujets de tous les livres
mots_counter = Counter()
vides = 0
for r in rows:
    s = r['sujets'].strip()
    if not s:
        vides += 1
        continue
    segments = re.split(r'--|;', s.lower())
    for seg in segments:
        seg = seg.strip().strip('-').strip()
        if seg and len(seg) > 3:
            mots_counter[seg] += 1

print(f"Livres sans aucun sujet (vraiment 'autre') : {vides}")
print(f"\nTop 100 segments de sujets (tous livres confondus) :")
for mot, n in mots_counter.most_common(100):
    print(f"  {n:>5}x  {mot}")
