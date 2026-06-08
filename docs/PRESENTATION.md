---
marp: true
title: Symphonie des données
paginate: true
---

<!--
Diaporama au format Markdown (compatible Marp : https://marp.app/).
Conversion en PPTX/PDF :  npx @marp-team/marp-cli docs/PRESENTATION.md -o presentation.pptx
Sinon : copier le contenu de chaque slide dans PowerPoint / Google Slides.
-->

# Symphonie des données

### Une plateforme de gestion du cycle de vie de données littéraires

Master 1 Intelligence Artificielle — Projet fil rouge
Intervenant : Najib AL AWAR
Vincent Lopes

---

## 1. Introduction

- Les modèles d'IA ont besoin de **données structurées, tracées et versionnées** pour être entraînés sérieusement.
- Ce projet propose de construire, de bout en bout, une plateforme qui **collecte, stocke, transforme et exploite un corpus de romans** pour entraîner un modèle de classification de genre littéraire.
- Objectif pédagogique : appliquer concrètement les notions de **base de données relationnelle, pipeline de données, versioning et machine learning** dans un cas d'usage cohérent.

---

## 2. Présentation du projet

**Symphonie des données** est une application **Streamlit** qui couvre tout le cycle de vie d'un corpus littéraire :

```
Upload de romans → Nettoyage et analyse du texte → Extraction de
caractéristiques → Constitution de jeux de données versionnés →
Entraînement d'un modèle de classification → Prédiction et
recommandation → Supervision visuelle complète
```

- Stockage des **fichiers bruts** séparé du stockage des **métadonnées** (SQLite).
- Chaque étape est **journalisée** (table `logs`) → traçabilité de bout en bout.
- Chaque jeu de données est **versionné** sous forme de snapshot immuable (`v1.0`, `v2.0`…).

---

## 3. Objectif du projet

> **Permettre d'analyser un livre avant de le lire**, pour savoir plus précisément s'il va nous plaire — **sans se faire spoiler**.

- À partir du seul **style d'écriture** d'un roman (vocabulaire, longueur de phrases, richesse lexicale, mots les plus représentatifs…), le système peut :
  - **prédire son genre littéraire** ;
  - **recommander des romans stylistiquement proches** d'un livre qu'on a aimé.
- Aucune information sur l'intrigue n'est utilisée : uniquement des caractéristiques **statistiques et lexicales** du texte → on se fait une idée du livre **sans rien savoir de l'histoire**.
- C'est ce besoin « métier » qui justifie l'architecture : il faut un corpus propre, structuré, versionné, pour entraîner un modèle fiable et reproductible.

---

## 4. Source des données

- **[Project Gutenberg](https://www.gutenberg.org/)** — bibliothèque numérique de livres **libres de droits**, avec un large catalogue de romans en français.
- Pourquoi cette source :
  - fichiers texte (`.txt`) propres et disponibles gratuitement ;
  - métadonnées (titre, auteur, année…) facilement accessibles ;
  - usage légal et reproductible pour un projet pédagogique.
- Le projet inclut des scripts dédiés (`scripts/import_gutenberg.py`, `scripts/download_all_fr.py`, `scripts/ingest_all_fr.py`…) pour **collecter et importer** un corpus francophone varié (plus de 20 genres représentés : policier, science-fiction, fantastique, conte, théâtre, biographie, essai…).

---

## 5. Description de la pipeline

Le cœur de la plateforme : une chaîne de traitement en **quatre étapes**, chacune journalisée et matérialisée par un **statut** sur le roman.

```
[Ingestion]  →  [Transformation]  →  [Extraction de features]  →  [Construction de dataset]
  ingere          transforme            features_extraites           en_dataset
```

| Étape | Module | Rôle |
|---|---|---|
| Ingestion | `pipeline/ingestion.py` | Validation, stockage du fichier brut, écriture en base |
| Transformation | `pipeline/transformation.py` | Extraction du texte, nettoyage, calcul de statistiques |
| Extraction de features | `pipeline/feature_extraction.py` | Tokenisation, fréquences (TF), top mots |
| Construction de dataset | `pipeline/dataset_builder.py` | Split train/val/test, snapshot versionné (CSV + manifest) |

Chaque étape écrit dans la table `logs` → on peut **rejouer l'historique complet** de chaque roman.

---

## 6. Modélisation de la base de données

Une base **SQLite** relationnelle (`symphonie.db`) stocke uniquement les **métadonnées** (jamais le contenu des fichiers) — 6 tables reliées par des clés étrangères :

```
romans (PK id) ──(1,1)── statistiques_texte    (statistiques du texte)
       │        ──(1,1)── features_texte        (top mots, vecteur TF)
       │        ──(0,N)── logs                  (traçabilité par étape)
       │
versions_dataset (PK id) ──(1,N)── modeles_entraines (FK dataset_id)
```

- **`romans`** : table centrale — titre, auteur, genre, fichier, et un champ **`statut`** qui matérialise la progression dans le pipeline (`ingere → transforme → features_extraites → en_dataset`).
- **UUID en clé primaire** : identifiants uniques générés côté application, robustes à l'import/export.
- **`logs`** unifiée : une seule table, requêtable par roman ou par étape — traçabilité complète.
- **`modeles_entraines` ↔ `versions_dataset`** : chaque modèle reste lié à la version exacte de dataset qui l'a entraîné → reproductibilité garantie.

---

## 7. Types de données absorbées

La plateforme accepte trois formats de fichiers, normalisés en un texte unique pour la suite du pipeline :

| Format | Exemple | Méthode d'extraction |
|---|---|---|
| **`.txt`** | *Les Trois Mousquetaires* (Gutenberg, encodage `latin-1`) | Lecture directe avec détection d'encodage en cascade (`utf-8` → `latin-1` → `cp1252`) |
| **`.pdf`** | Roman numérisé / exporté en PDF | `PyPDF2` — extraction page par page |
| **`.epub`** | Livre numérique au format `.epub` | `ebooklib` + nettoyeur HTML maison (suppression des balises) |

➜ Quel que soit le format d'origine, le résultat est un **texte brut unique**, ensuite nettoyé (suppression des en-têtes Project Gutenberg, normalisation des espaces) et stocké dans `storage/processed/*_clean.txt`.

---

## 8. Action sur les données — l'ingestion (1/4)

Avant tout stockage, le fichier est **validé** (extension autorisée, taille ≤ 50 Mo) :

```python
def valider_fichier(nom_fichier: str, taille_octets: int) -> tuple[bool, str]:
    ext = os.path.splitext(nom_fichier)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"Extension '{ext}' non autorisée."
    if taille_octets > MAX_FILE_SIZE_MB * 1024 * 1024:
        return False, f"Fichier trop volumineux ({taille_octets/1024/1024:.1f} Mo)."
    return True, "OK"
```

- Le fichier validé est **renommé avec un horodatage** (évite les collisions), copié dans `storage/raw/`, puis une ligne est créée dans la table `romans` avec le statut `ingere` et un log `ingestion / succès`.

---

## 9. Action sur les données — le nettoyage (2/4)

Le texte brut extrait est **nettoyé** avant d'être analysé : suppression des en-têtes/pieds de page Project Gutenberg, normalisation des sauts de ligne et des espaces, filtrage des caractères non textuels.

```python
def nettoyer_texte(texte: str) -> str:
    debut = re.search(r"\*\*\* START OF (THE|THIS) PROJECT GUTENBERG", texte, re.IGNORECASE)
    fin   = re.search(r"\*\*\* END OF (THE|THIS) PROJECT GUTENBERG",   texte, re.IGNORECASE)
    if debut: texte = texte[debut.end():]
    if fin:   texte = texte[:fin.start()]
    texte = re.sub(r"\r\n", "\n", texte)
    texte = re.sub(r"\n{3,}", "\n\n", texte)
    texte = re.sub(r"[ \t]+", " ", texte)
    return texte.strip()
```

➜ Le texte propre est ensuite analysé pour produire des **statistiques** : nombre de mots, de phrases, de paragraphes, taille du vocabulaire, **richesse lexicale** (`vocabulaire_unique / nb_mots`), longueur moyenne des phrases.

---

## 10. Action sur les données — l'extraction de features (3/4)

Le texte est **tokenisé** (mots ≥ 3 lettres, hors *stop-words* français faits sur mesure), puis on calcule la **fréquence normalisée (TF)** de chaque mot et on conserve les 50 plus fréquents :

```python
tokens = _tokeniser(texte)                     # filtrage des mots-outils (le, la, et, que…)
freq = {}
for t in tokens:
    freq[t] = freq.get(t, 0) + 1
n  = len(tokens)
tf = {t: c / n for t, c in freq.items()}       # fréquence normalisée
top50 = sorted(tf.items(), key=lambda x: x[1], reverse=True)[:50]
```

➜ Ce vecteur (top mots + nombre de tokens) est écrit en JSON dans `storage/processed/` et résumé en base — c'est la **signature stylistique** du roman, utilisée plus loin pour la prédiction et la recommandation.

---

## 11. Action sur les données — versioning du dataset (4/4)

Une fois les features extraites, les romans peuvent être assemblés en un **jeu de données versionné**, immuable et reproductible :

```python
random.seed(42)                 # graine fixe → mélange reproductible
random.shuffle(romans_prets)
n = len(romans_prets)
n_train = int(n * split_train)
n_val   = int(n * split_val)
train, val, test = romans_prets[:n_train], romans_prets[n_train:n_train+n_val], romans_prets[n_train+n_val:]
# → écriture de train.csv / val.csv / test.csv + manifest.json (description, ratios, IDs inclus)
```

➜ Chaque version (`v1.0`, `v2.0`…) est **figée** : son contenu ne change jamais, ce qui garantit qu'on peut toujours retrouver **exactement** quelles données ont servi à entraîner un modèle donné.

---

## 12. Les modèles — classification de genre (1/2)

**Objectif** : prédire le genre littéraire d'un roman à partir de son seul style d'écriture (et non de son intrigue).

**Approche** : `TF-IDF` (vectorisation du texte) + classificateur linéaire — une *baseline* simple, rapide et interprétable pour la classification de texte.

```python
clf = LinearSVC(max_iter=2000, C=1.0) if algo == "svm" else \
      LogisticRegression(max_iter=1000, C=1.0, solver="lbfgs")

pipe = Pipeline([
    ("tfidf", TfidfVectorizer(max_features=10000, ngram_range=(1, 2),
                              sublinear_tf=True, min_df=1)),
    ("clf", clf),
])
pipe.fit(X_train, y_train)
```

- Deux algorithmes au choix : **Régression Logistique** ou **SVM linéaire**.
- Le pipeline complet (vectoriseur + classificateur) est sauvegardé (`.joblib`) et relié en base à la version exacte du dataset utilisée → **traçabilité du modèle**.

---

## 13. Les modèles — prédiction et recommandation (2/2)

**Prédiction** : recharge le modèle entraîné et prédit le genre d'un roman, avec ses probabilités par genre :

```python
pipe = joblib.load(modele.chemin_modele)
pred = pipe.predict([texte[:5000]])[0]
proba = dict(zip(pipe.classes_, pipe.predict_proba([texte[:5000]])[0]))
```

**Recommandation** : ne nécessite **aucun entraînement** — calcule directement la **similarité cosinus** entre les vecteurs TF-IDF de tous les romans déjà nettoyés :

```python
matrice = TfidfVectorizer(max_features=8000, ngram_range=(1, 2), min_df=2).fit_transform(textes)
scores  = cosine_similarity(matrice[index_cible], matrice).flatten()
meilleurs = np.argsort(scores)[::-1][1:n+1]      # les n romans les plus proches
```

➜ « Tu as aimé ce roman ? Voici ceux qui lui ressemblent le plus, stylistiquement. »

---

## 14. Visualisation et supervision — outils

L'ensemble du cycle de vie est **visualisable en direct** grâce à :

- **Streamlit** : framework Python pour construire une interface web multipage interactive sans développement front-end séparé (formulaires, tableaux, onglets, barres de progression…).
- **Plotly / Plotly Express** : graphiques interactifs — diagrammes en entonnoir (`Funnel`), histogrammes, nuages de points, barres groupées, courbes de croissance.
- **Pandas** : agrégation et mise en forme des données (groupements par genre, statistiques moyennes, fusion de tableaux).

Cinq pages dédiées : **Bibliothèque** (corpus), **Pipeline** (orchestration), **Datasets** (versioning), **Modèle** (entraînement/prédiction/recommandation) et **Dashboard** (supervision globale).

---

## 15. Le tableau de bord (Dashboard)

Vue d'ensemble du cycle de vie des données, en quatre volets :

| Volet | Visualisations |
|---|---|
| **Corpus** | Entonnoir cumulatif du pipeline, répartition par genre, croissance du corpus dans le temps |
| **Statistiques textuelles** | Distribution du nombre de mots, richesse lexicale vs longueur (nuage de points coloré par genre) |
| **Modèles** | Comparaison des accuracies train/val/test entre tous les modèles entraînés |
| **Logs** | Journal des 30 dernières opérations (toutes étapes confondues) |

➜ En un coup d'œil : combien de romans sont entrés, où ils en sont dans le pipeline, comment le corpus grandit, et comment les modèles successifs se comparent.

---

## 16. Démonstration

Je vais maintenant présenter l'application en direct, avec un exemple concret :

1. **Bibliothèque** : un roman du corpus (ex. *Les Trois Mousquetaires*, Alexandre Dumas) — sa fiche, ses statistiques, ses mots les plus représentatifs.
2. **Pipeline** : suivi de la transformation et de l'extraction de features.
3. **Datasets** : la version `v1.0`, son manifest, sa répartition train/val/test.
4. **Modèle** : entraînement d'un classificateur, comparaison des performances.
5. **Prédiction** : « à quel genre ce roman appartient-il, selon le modèle ? »
6. **Recommandation** : « quels romans ressemblent stylistiquement à celui-ci ? »
7. **Dashboard** : vue globale du cycle de vie du corpus.

---

## 17. Conclusion

- Une plateforme complète couvrant **tout le cycle de vie de la donnée** : ingestion → transformation → features → dataset versionné → modèle → prédiction/recommandation → supervision.
- Une **architecture de données rigoureuse** : séparation stricte fichiers/métadonnées, base relationnelle normalisée (6 tables, clés étrangères, UUID), traçabilité unifiée (`logs`), versioning immuable (`vX.0` + manifest).
- Une **réponse concrète à un besoin** : permettre de se faire une idée d'un livre — son genre, des suggestions similaires — sans rien savoir de son intrigue.
- Une base solide et **extensible** : ajouter de nouveaux romans, de nouvelles versions de dataset et de nouveaux modèles ne casse jamais l'historique existant.

### Merci de votre attention — questions ?
