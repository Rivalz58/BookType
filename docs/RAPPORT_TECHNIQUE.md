# Rapport technique — Symphonie des données

**Projet fil rouge — Master 1 Intelligence Artificielle**
**Intervenant référent :** Najib AL AWAR
**Auteur :** Vincent Lopes
**Dépôt Git :** https://github.com/Rivalz58/BookType

---

## 1. Contexte et objectif

Le projet *Symphonie des données* a pour but de concevoir une plateforme complète
de gestion du **cycle de vie de données littéraires** : collecte de romans (TXT,
PDF, EPUB), stockage, structuration, transformation, constitution de jeux de
données versionnés, puis alimentation d'un modèle de classification de genre
littéraire par apprentissage automatique.

Le thème retenu — un corpus de romans en français issus de Project Gutenberg —
s'inscrit dans le cadre fixé par l'intervenant (architecture de gestion de
données pour un projet d'IA, pipeline ingestion → transformation → features →
dataset → modèle, traçabilité et versioning). Il correspond à une déclinaison
« texte » du scénario *Registre de datasets et traçabilité avancée* suggéré
dans la présentation du projet, avec un accent fort sur la traçabilité du
cycle de vie (table `logs`), le versioning des datasets (snapshots immuables
`vX.0`) et la supervision visuelle (tableau de bord Streamlit).

---

## 2. Architecture de la plateforme

### 2.1 Vue d'ensemble

La plateforme est une application **Streamlit** (Python) organisée en quatre
grands blocs, séparant clairement le **stockage des fichiers** (object storage
local) du **stockage des métadonnées** (base relationnelle SQLite) :

```
symphonie-des-donnees/
│
├── symphonie.db                # Base de données SQLite (créée au premier lancement)
├── config.py                   # Configuration globale (chemins, formats, genres)
├── run.py                      # Point d'entrée (init BDD + lancement Streamlit)
│
├── database/
│   ├── db.py                   # Connexion SQLite + création des tables (DDL)
│   └── models.py               # Dataclasses (Roman, StatistiqueTexte, ...) + CRUD
│
├── storage/                    # Object storage local — séparé de la BDD
│   ├── raw/                    # Fichiers bruts uploadés (.txt/.pdf/.epub)
│   ├── processed/              # Textes nettoyés (_clean.txt) + vecteurs (_features.json)
│   └── datasets/               # Snapshots de datasets versionnés (vX.0/)
│
├── pipeline/
│   ├── ingestion.py            # Upload, validation, écriture BDD
│   ├── transformation.py       # Extraction texte, nettoyage, statistiques
│   ├── feature_extraction.py   # Tokenisation, fréquences TF, top mots
│   └── dataset_builder.py      # Split train/val/test, CSV + manifest, versioning
│
├── models/
│   ├── trainer.py              # Entraînement TF-IDF + LR/SVM, prédiction
│   ├── recommender.py          # Recommandation par similarité cosinus (TF-IDF)
│   └── saved/                  # Modèles sérialisés (.joblib)
│
└── app/                        # Interface Streamlit
    ├── Home.py                 # Accueil : KPI + entonnoir de progression
    └── pages/
        ├── 1_Bibliotheque.py   # Liste / détail / upload des romans
        ├── 2_Pipeline.py       # Orchestration transformation + features
        ├── 3_Datasets.py       # Création et historique des versions de dataset
        ├── 4_Modele.py         # Entraînement, comparaison, prédiction, recommandation
        └── 5_Dashboard.py      # Supervision globale (corpus, stats, modèles, logs)
```

### 2.2 Flux de données (architecture logique)

```
[Utilisateur] ── upload fichier + métadonnées ──▶ [Ingestion]
                                                       │ validation (extension, taille)
                                                       │ écriture → storage/raw/
                                                       │ INSERT romans + logs
                                                       ▼
                                                 [Transformation]
                                                       │ extraction texte (txt/pdf/epub)
                                                       │ nettoyage (en-têtes Gutenberg, espaces)
                                                       │ calcul statistiques textuelles
                                                       │ écriture → storage/processed/*_clean.txt
                                                       │ INSERT statistiques_texte + UPDATE statut
                                                       ▼
                                              [Extraction de features]
                                                       │ tokenisation (suppression stopwords FR)
                                                       │ calcul TF normalisé, top-50 mots
                                                       │ écriture → storage/processed/*_features.json
                                                       │ INSERT features_texte + UPDATE statut
                                                       ▼
                                             [Construction de dataset]
                                                       │ sélection des romans prêts
                                                       │ split train/val/test (graine fixe = 42)
                                                       │ écriture → storage/datasets/vX.0/*.csv + manifest.json
                                                       │ INSERT versions_dataset + UPDATE statut
                                                       ▼
                                            [Entraînement du modèle IA]
                                                       │ pipeline TF-IDF (10k features, bi-grammes) + LR/SVM
                                                       │ métriques accuracy train/val/test
                                                       │ sauvegarde → models/saved/*.joblib
                                                       │ INSERT modeles_entraines
                                                       ▼
                                                  [Prédiction / Recommandation]
                                                       • predire(roman, modèle) → genre + probabilités
                                                       • recommander(roman, n) → similarité cosinus TF-IDF
```

À chaque étape, une entrée est ajoutée dans la table `logs`, ce qui assure une
**traçabilité complète** consultable depuis la page *Dashboard* et la fiche de
chaque roman.

### 2.3 Séparation stockage fichiers / métadonnées

C'est une contrainte explicite du cahier des charges. Elle est respectée de
façon stricte :

- **`storage/`** (object storage local) contient uniquement des **binaires et
  fichiers texte** : romans bruts, textes nettoyés, vecteurs JSON de features,
  CSV de datasets versionnés.
- **`symphonie.db`** (SQLite) contient uniquement des **métadonnées** :
  identifiants, titres, statuts, statistiques, chemins vers les fichiers,
  hyperparamètres, métriques, logs.

Chaque enregistrement en base référence son fichier via un chemin
(`nom_fichier`, `vecteur_path`, `chemin_fichier`, `chemin_modele`), ce qui
permet de retrouver le binaire correspondant sans dupliquer son contenu en
base — un pattern *object storage + métadonnées relationnelles* classique en
ingénierie de données.

---

## 3. Modélisation de la base de données

La base SQLite (`symphonie.db`) comporte **6 tables** liées par des clés
étrangères, créées au démarrage par `database/db.py` (`init_db`).

### 3.1 Schéma relationnel (vue logique)

```
romans (1) ────┬──────────────(1,1)── statistiques_texte
   id (PK)     │
               ├──────────────(1,1)── features_texte
               │
               └──────────────(0,N)── logs

versions_dataset (1) ───(1,N)─── modeles_entraines
       id (PK)                        dataset_id (FK)
```

### 3.2 Détail des tables

| Table | Clé(s) | Rôle |
|-------|--------|------|
| `romans` | PK `id` (UUID) | Référentiel central : titre, auteur, genre, année, langue, source, fichier associé, format, taille, **statut** (`ingere` → `transforme` → `features_extraites` → `en_dataset`), date d'upload |
| `statistiques_texte` | PK/FK `roman_id` → `romans` | Statistiques calculées à la transformation : nb mots, phrases, paragraphes, caractères, vocabulaire unique, richesse lexicale, longueur moyenne de phrase |
| `features_texte` | PK/FK `roman_id` → `romans` | Top-50 mots (TF, JSON) + chemin vers le vecteur complet (`storage/processed/*_features.json`) |
| `versions_dataset` | PK `id` (UUID), UNIQUE `version` | Snapshot immuable d'un jeu de données : description, nb de romans, ratios train/val/test, chemin du dossier, date de création |
| `modeles_entraines` | PK `id` (UUID), FK `dataset_id` → `versions_dataset` | Modèle entraîné : algorithme, version de dataset utilisée, accuracy train/val/test, chemin du `.joblib`, hyperparamètres (JSON) |
| `logs` | PK `id` (auto-incrément), FK `roman_id` → `romans` | Journal unifié : horodatage, étape (`ingestion`/`transformation`/`feature_extraction`/`dataset`), statut (`succès`/`échec`), message |

### 3.3 Choix de modélisation justifiés

| Choix | Justification |
|-------|---------------|
| **SQLite** | SGBD relationnel intégré à Python (`sqlite3`), sans serveur ni conteneur — adapté à un prototype local tout en respectant les contraintes d'intégrité (clés primaires, clés étrangères, unicité) |
| **UUID (TEXT) comme clé primaire** | Identifiants universellement uniques générés côté application, robustes en cas d'import/export ou de fusion de bases, sans dépendre d'un compteur centralisé |
| **Statut (`statut`) sur `romans`** | Simple machine à états qui matérialise la progression d'un roman dans le pipeline et alimente directement les indicateurs (entonnoir, KPI) |
| **Table `logs` unifiée** | Une seule table indexable par `roman_id` ou par `etape`, requêtable en SQL standard (`ORDER BY`, `WHERE`) — alternative plus simple et plus traçable que des logs dispersés par module |
| **`versions_dataset` / `modeles_entraines` séparées et liées par FK** | Permet d'associer chaque modèle entraîné à la version de dataset exacte qui l'a produit — essentiel pour la reproductibilité et l'audit |
| **Chemins de fichiers stockés en base, contenu hors base** | Respecte la séparation fichiers/métadonnées : la base reste légère et portable, les binaires restent dans l'object storage |

---

## 4. Pipeline de données

Le pipeline est composé de quatre étapes successives, chacune implémentée dans
un module dédié sous `pipeline/`, orchestrées depuis l'interface Streamlit
(pages *Bibliothèque*, *Pipeline*, *Datasets*).

### 4.1 Ingestion (`pipeline/ingestion.py`)

- **Validation** : extension autorisée (`.txt`, `.pdf`, `.epub`, configurable
  dans `config.py`) et taille maximale (50 Mo).
- **Stockage** : le fichier est renommé avec un horodatage (évite les
  collisions) et copié dans `storage/raw/`.
- **Enregistrement** : création d'un `Roman` (statut `ingere`) et d'un log
  `ingestion / succès` (ou suppression du fichier et retour d'erreur en cas
  d'échec d'écriture en base — gestion transactionnelle simple mais robuste).

### 4.2 Transformation (`pipeline/transformation.py`)

- **Extraction de texte** selon le format : lecture directe pour le TXT
  (avec détection d'encodage en cascade `utf-8` / `latin-1` / `cp1252`),
  `PyPDF2` pour le PDF, `ebooklib` + un *stripper* HTML maison pour l'EPUB.
- **Nettoyage** : suppression des en-têtes/pieds de page Project Gutenberg
  (`*** START/END OF ... PROJECT GUTENBERG ***` via expression régulière),
  normalisation des sauts de ligne et des espaces, filtrage des caractères
  non textuels.
- **Statistiques** : nombre de mots, de phrases (découpage sur `.!?`), de
  paragraphes (double saut de ligne), de caractères, taille du vocabulaire
  unique, richesse lexicale (`vocab_unique / nb_mots`), longueur moyenne de
  phrase.
- **Sortie** : texte nettoyé écrit dans `storage/processed/<nom>_clean.txt`,
  statistiques insérées en base, statut du roman mis à jour (`transforme`).

### 4.3 Extraction de features (`pipeline/feature_extraction.py`)

- **Tokenisation** : expression régulière restreinte aux mots de 3 lettres ou
  plus (alphabet français, accents inclus), filtrage par une **liste de
  stop-words français faite sur mesure** (articles, pronoms, prépositions,
  conjonctions, auxiliaires, adverbes courants…).
- **Fréquence (TF)** : comptage des occurrences puis normalisation par le
  nombre total de tokens, sélection des 50 mots les plus fréquents.
- **Sortie** : vecteur complet (top-50 + nombre de tokens) écrit en JSON dans
  `storage/processed/<nom>_features.json`, top-50 et chemin enregistrés en
  base, statut mis à jour (`features_extraites`).

### 4.4 Construction de dataset (`pipeline/dataset_builder.py`)

- **Sélection** : uniquement les romans au statut `features_extraites`.
- **Découpage reproductible** : mélange aléatoire à **graine fixe
  (`random.seed(42)`)**, puis répartition selon les ratios `train/val/test`
  choisis par l'utilisateur (somme contrôlée = 1.0).
- **Snapshot immuable** : écriture d'un CSV par split et d'un `manifest.json`
  contenant description, dates, comptages, ratios et liste des IDs de romans
  inclus — garantissant la **reproductibilité** d'une version donnée.
- **Versioning** : génération automatique d'un identifiant incrémental
  `vN.0`, enregistrement en base (`versions_dataset`), mise à jour du statut
  des romans (`en_dataset`) et journalisation de chaque inclusion.

Chaque étape journalise systématiquement son résultat (`succès`/`échec`) dans
la table `logs`, ce qui permet de retracer a posteriori tout le parcours d'un
roman dans le pipeline (visible dans l'onglet *Logs* du Dashboard et dans la
fiche détail de chaque roman).

---

## 5. Intégration avec l'entraînement du modèle

### 5.1 Entraînement (`models/trainer.py`)

- **Chargement** : les textes nettoyés sont chargés depuis les CSV du dataset
  versionné sélectionné (split `train`/`val`/`test`), tronqués à 5000
  caractères pour limiter le coût de calcul.
- **Pipeline scikit-learn** : `TfidfVectorizer` (10 000 features maximum,
  bi-grammes `ngram_range=(1,2)`, pondération `sublinear_tf`) suivi d'un
  classificateur au choix : **Régression Logistique** (`solver=lbfgs`) ou
  **SVM linéaire** (`LinearSVC`).
- **Évaluation** : *accuracy* calculée séparément sur `train`, `val` et
  `test`.
- **Persistance** : le pipeline complet (vectoriseur + classificateur) est
  sérialisé avec `joblib` dans `models/saved/`, et un enregistrement
  `ModeleEntraine` est créé en base (algorithme, version de dataset,
  métriques, chemin du fichier, hyperparamètres en JSON) — ce qui **relie
  explicitement chaque modèle à la version exacte du dataset qui l'a
  produit**, condition de la traçabilité et de la reproductibilité demandées.

### 5.2 Prédiction et recommandation

- **`predire(roman, modèle)`** : recharge le pipeline `.joblib`, prédit le
  genre du roman à partir de son texte nettoyé et renvoie, lorsque c'est
  possible, les probabilités par genre (`predict_proba`).
- **`recommander(roman, n)`** (`models/recommender.py`) : système de
  recommandation **sans entraînement préalable**, fondé sur la similarité
  cosinus entre vecteurs TF-IDF (bi-grammes, `min_df=2`) calculés à la volée
  sur l'ensemble des textes nettoyés disponibles ; renvoie les *n* romans les
  plus proches d'un roman donné. Une variante (`livres_similaires_par_texte`)
  permet de recommander à partir d'un texte libre non présent en base.

### 5.3 Boucle d'alimentation continue

L'architecture permet une **alimentation continue** du modèle : chaque
nouveau roman ingéré peut être transformé, vu ses features extraites, intégré
dans une nouvelle version de dataset (`v2.0`, `v3.0`…), puis utilisé pour
ré-entraîner un nouveau modèle — sans jamais modifier les versions
précédentes (snapshots immuables), ce qui permet de comparer objectivement les
performances d'un modèle à l'autre au fil de la croissance du corpus (page
*Modèle*, onglet *Modèles entraînés*).

---

## 6. Visualisation et supervision

L'interface Streamlit assure la couverture du critère « visualisation des
flux et indicateurs » :

- **Page d'accueil** : 5 indicateurs clés (KPI) et un **diagramme en
  entonnoir** (Plotly `Funnel`) montrant la progression du corpus à travers
  les quatre statuts du pipeline.
- **Bibliothèque** : recherche/filtrage du corpus, fiche détail d'un roman
  (statistiques, histogramme des mots les plus représentatifs, historique des
  logs).
- **Pipeline** : suivi en direct des transformations et extractions (barres de
  progression, compteurs par statut, logs récents par étape).
- **Datasets** : historique des versions avec métriques de répartition,
  aperçu du manifest et des CSV.
- **Modèle** : comparaison des accuracies train/val/test entre modèles
  (graphique en barres groupées), prédiction interactive avec probabilités,
  recommandation par similarité.
- **Dashboard** : vue globale — entonnoir cumulatif, répartition par genre,
  croissance du corpus dans le temps, distribution des statistiques
  textuelles (histogrammes, nuage de points richesse lexicale / longueur),
  comparaison des modèles, et consultation des derniers logs.

---

## 7. Choix techniques justifiés (synthèse)

| Choix | Justification |
|-------|---------------|
| **Streamlit** | Permet de construire rapidement une interface multipage interactive en Python pur, sans développement front-end séparé — adapté à un prototype de supervision de données |
| **SQLite** | SGBD relationnel sans serveur, fichier unique portable, intégré à la bibliothèque standard Python, avec contraintes d'intégrité (clés étrangères, unicité) |
| **Séparation fichiers / BDD** | `storage/` pour les binaires, `symphonie.db` pour les métadonnées → pattern *object storage* respecté de bout en bout |
| **UUID comme clés primaires** | Unicité garantie sans coordination centrale, robustesse à l'import/export |
| **Snapshots immuables `vX.0` + manifest JSON** | Reproductibilité et auditabilité des jeux de données — chaque modèle reste traçable jusqu'à la version exacte qui l'a entraîné |
| **TF-IDF + Régression Logistique / SVM linéaire** | Référence (*baseline*) solide, rapide à entraîner et interprétable pour une tâche de classification de texte multi-classes |
| **Graine aléatoire fixe (`seed=42`) pour les splits** | Reproductibilité des jeux de données générés à partir du même corpus |
| **Table `logs` unifiée** | Traçabilité homogène et requêtable en SQL standard, sans dépendance à un système de logs externe |

---

## 8. Démonstration / état du prototype

Le prototype est pleinement fonctionnel de bout en bout :

1. Upload de romans `.txt` (Project Gutenberg, corpus francophone) avec
   saisie des métadonnées (titre, auteur, genre, année, langue, source).
2. Transformation en lot (extraction, nettoyage, statistiques).
3. Extraction des features (TF, top mots) en lot.
4. Construction d'une première version de dataset versionné (`v1.0`,
   conservée dans le dépôt sous `storage/datasets/v1.0/` à titre
   d'illustration du mécanisme de versioning).
5. Entraînement de modèles (régression logistique et SVM) avec comparaison
   des performances train/val/test.
6. Prédiction du genre d'un roman et recommandation de romans similaires.
7. Supervision complète via le tableau de bord (entonnoir, statistiques,
   comparaison de modèles, journal des opérations).

> Les données volumineuses (`storage/raw/`, `storage/processed/`, modèles
> `.joblib`, base `symphonie.db`) ne sont pas versionnées dans le dépôt Git
> (voir `.gitignore`) car elles dépassent largement les limites raisonnables
> d'un dépôt de code ; elles sont entièrement régénérées en relançant le
> pipeline depuis l'interface (voir `README.md`, section *Utilisation pas à
> pas*, et `docs/GUIDE_FONCTIONNEMENT.md`).

---

## 9. Conclusion

Le projet couvre l'ensemble des objectifs pédagogiques fixés : une
architecture de gestion de données séparant clairement fichiers et
métadonnées, une base relationnelle normalisée et documentée, un pipeline
robuste en quatre étapes journalisées, un mécanisme de versioning immuable
des datasets, une intégration directe avec l'entraînement et la prédiction
d'un modèle de classification, et une interface de supervision visuelle
complète couvrant tout le cycle de vie de la donnée — de l'ingestion brute
jusqu'à l'exploitation par le modèle d'IA.
