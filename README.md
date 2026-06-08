# Symphonie des Données — Corpus Littéraire
**Master 1 Intelligence Artificielle — Projet fil rouge**
Intervenant : Najib AL AWAR

---

## Présentation

**Symphonie des Données** est une plateforme de gestion du cycle de vie de données littéraires (romans).
Elle collecte, stocke, structure et orchestre des textes (TXT, PDF, EPUB) pour alimenter un modèle de classification de genre littéraire par apprentissage automatique.

La plateforme s'appuie sur **SQLite** (SGBD relationnel) pour le stockage des métadonnées et des logs, en séparant clairement le stockage des fichiers bruts (object storage local).

> **Documents du rendu :**
> - [`docs/RAPPORT_TECHNIQUE.md`](docs/RAPPORT_TECHNIQUE.md) — rapport technique (architecture, BDD, pipeline, choix techniques, intégration ML)
> - [`docs/GUIDE_FONCTIONNEMENT.md`](docs/GUIDE_FONCTIONNEMENT.md) — guide de fonctionnement et d'utilisation de l'application, page par page
> - [`docs/PRESENTATION.pptx`](docs/PRESENTATION.pptx) — support de soutenance (17 slides : introduction, architecture, BDD, pipeline, modèles, démo, conclusion), généré depuis [`docs/PRESENTATION.md`](docs/PRESENTATION.md) via [Marp](https://marp.app/)

---

## Architecture de la plateforme

```
symphonie-des-donnees/
│
├── symphonie.db                # Base de données SQLite (générée au premier lancement)
├── config.py                   # Configuration globale (chemins, DB)
│
├── database/
│   ├── db.py                   # Connexion SQLite + création des tables
│   └── models.py               # Dataclasses + fonctions CRUD
│
├── storage/                    # Object Storage local (séparé de la BDD)
│   ├── raw/                    # Fichiers bruts uploadés
│   ├── processed/              # Textes nettoyés + vecteurs features JSON
│   └── datasets/               # Datasets versionnés (vX.0/)
│
├── pipeline/
│   ├── ingestion.py            # Upload, validation, écriture BDD
│   ├── transformation.py       # Extraction texte, nettoyage, stats → BDD
│   ├── feature_extraction.py   # TF-IDF, top mots → BDD
│   └── dataset_builder.py      # Construction CSV versionné → BDD
│
├── models/
│   ├── trainer.py              # Entraînement TF-IDF + LR/SVM → BDD
│   └── saved/                  # Modèles sérialisés (.joblib)
│
└── app/
    ├── Home.py                 # Page d'accueil + statut BDD
    └── pages/
        ├── 1_Bibliotheque.py   # Bibliothèque : liste, détail, upload
        ├── 2_Pipeline.py       # Transformation + extraction features
        ├── 3_Datasets.py       # Versioning des datasets
        ├── 4_Modele.py         # Entraînement + prédiction
        └── 5_Dashboard.py      # Supervision complète
```

---

## Schéma de base de données (SQLite — `symphonie.db`)

### Pourquoi SQLite ?
- **SGBD relationnel** : respect des contraintes d'intégrité (clés étrangères, unicité)
- **Sans infrastructure** : aucun serveur à démarrer, fichier unique portable
- **SQL standard** : requêtes simples et lisibles, pas d'ALLOW FILTERING
- **Intégré Python** : module `sqlite3` de la bibliothèque standard

### Tables

#### Table `romans` (PK : `id`)
| Colonne | Type | Description |
|---------|------|-------------|
| id | TEXT PK | UUID unique (uuid4) |
| titre | TEXT | Titre du roman |
| auteur | TEXT | Auteur |
| genre | TEXT | Genre littéraire |
| annee | INTEGER | Année de publication |
| langue | TEXT | Langue du texte |
| source | TEXT | URL ou source d'origine |
| nom_fichier | TEXT | Nom du fichier dans `storage/raw/` |
| format_fichier | TEXT | txt / pdf / epub |
| taille_octets | INTEGER | Taille du fichier |
| statut | TEXT | ingere / transforme / features_extraites / en_dataset |
| date_upload | TEXT | Date d'ingestion (ISO) |

#### Table `statistiques_texte` (PK : `roman_id`, FK → `romans`)
| Colonne | Type | Description |
|---------|------|-------------|
| roman_id | TEXT PK/FK | Référence vers `romans` |
| nb_mots | INTEGER | Nombre de mots |
| nb_phrases | INTEGER | Nombre de phrases |
| nb_paragraphes | INTEGER | Nombre de paragraphes |
| nb_caracteres | INTEGER | Nombre de caractères |
| vocabulaire_unique | INTEGER | Taille du vocabulaire |
| richesse_lexicale | REAL | vocab_unique / nb_mots |
| longueur_moy_phrase | REAL | Longueur moyenne des phrases |

#### Table `features_texte` (PK : `roman_id`, FK → `romans`)
| Colonne | Type | Description |
|---------|------|-------------|
| roman_id | TEXT PK/FK | Référence vers `romans` |
| top_mots | TEXT (JSON) | Top-50 mots TF (dictionnaire JSON) |
| vecteur_path | TEXT | Chemin vers le fichier JSON complet |

#### Table `versions_dataset` (PK : `id`)
| Colonne | Type | Description |
|---------|------|-------------|
| id | TEXT PK | UUID unique |
| version | TEXT UNIQUE | Ex : v1.0, v2.0 |
| description | TEXT | Description du snapshot |
| nb_romans | INTEGER | Nombre de romans inclus |
| split_train/val/test | REAL | Ratios de découpage |
| chemin_fichier | TEXT | Dossier local contenant les CSV + manifest |
| date_creation | TEXT | Date de création (ISO) |

#### Table `modeles_entraines` (PK : `id`, FK → `versions_dataset`)
| Colonne | Type | Description |
|---------|------|-------------|
| id | TEXT PK | UUID unique |
| algorithme | TEXT | logistic_regression / svm |
| dataset_version | TEXT | Version de dataset utilisée |
| accuracy_train/val/test | REAL | Métriques de performance |
| chemin_modele | TEXT | Chemin vers le .joblib |
| parametres | TEXT (JSON) | Hyperparamètres |

#### Table `logs` (PK : `id` AUTOINCREMENT)
| Colonne | Type | Description |
|---------|------|-------------|
| id | INTEGER PK | Identifiant auto-incrémenté |
| roman_id | TEXT FK | Référence vers `romans` |
| date_log | TEXT | Horodatage (ISO) |
| etape | TEXT | ingestion / transformation / feature_extraction / dataset |
| statut | TEXT | succès / échec |
| message | TEXT | Détail du log |

---

## Pipeline de données

```
[Utilisateur]
    │  Upload fichier + métadonnées
    ▼
[Ingestion] — pipeline/ingestion.py
    • Validation (extension, taille)
    • Stockage → storage/raw/
    • INSERT INTO romans
    • INSERT INTO logs
    │
    ▼
[Transformation] — pipeline/transformation.py
    • Extraction texte (txt/pdf/epub)
    • Nettoyage (Gutenberg headers, espaces)
    • Statistiques (mots, phrases, richesse)
    • Stockage → storage/processed/_clean.txt
    • INSERT INTO statistiques_texte
    • UPDATE romans SET statut = 'transforme'
    │
    ▼
[Extraction features] — pipeline/feature_extraction.py
    • Tokenisation (suppression stopwords)
    • Calcul TF normalisé
    • Top-50 mots + vecteur JSON
    • Stockage → storage/processed/_features.json
    • INSERT INTO features_texte
    • UPDATE romans SET statut = 'features_extraites'
    │
    ▼
[Construction dataset] — pipeline/dataset_builder.py
    • Rassemblement des romans prêts
    • Découpage train/val/test (paramétrable)
    • Génération CSV par split + manifest.json immuable
    • Stockage → storage/datasets/vX.0/
    • INSERT INTO versions_dataset
    │
    ▼
[Entraînement modèle IA] — models/trainer.py
    • Chargement textes depuis CSV
    • Pipeline TF-IDF (10k features, bigrammes) + LR ou SVM
    • Métriques accuracy train/val/test
    • Sauvegarde modèle → models/saved/.joblib
    • INSERT INTO modeles_entraines
    │
    ▼
[Prédiction] — models/trainer.py::predire()
    • Chargement modèle joblib
    • Prédiction genre + probabilités
```

---

## Installation et lancement

### Prérequis
- Python 3.10+

### 1. Installer les dépendances Python
```bash
pip install -r requirements.txt
```

### 2. Lancer l'application
```bash
streamlit run app/Home.py
```
L'application s'ouvre sur `http://localhost:8501`.
La base de données SQLite (`symphonie.db`) est créée automatiquement au premier lancement.

---

## Utilisation pas à pas

1. **Upload** — Déposer des romans `.txt` de Project Gutenberg, renseigner titre/auteur/genre
2. **Pipeline** — "Transformer tous" puis "Extraire features de tous"
3. **Datasets** — Créer une version (ex: v1.0) avec les ratios train/val/test souhaités
4. **Modèle** — Choisir le dataset et l'algorithme, lancer l'entraînement
5. **Dashboard** — Visualiser métriques, entonnoir, performances des modèles

### Sources de données recommandées
- **Project Gutenberg** — romans libres de droits (format `.txt`)
- Genres : `roman`, `policier`, `science-fiction`, `aventure`, `romance`, `philosophie`, `autre`

---

## Choix techniques justifiés

| Choix | Justification |
|-------|--------------|
| **SQLite** | SGBD relationnel intégré à Python, sans serveur ni Docker — adapté à un prototype local avec contraintes d'intégrité (clés étrangères) |
| **Séparation fichiers / BDD** | SQLite stocke les métadonnées, `storage/` stocke les binaires → pattern object storage |
| **UUIDs comme PK (TEXT)** | Identifiants universellement uniques, évite les conflits en cas d'import/export |
| **Table `logs` unifiée** | Une seule table indexable par `roman_id` ou par `etape` — SQL standard avec ORDER BY |
| **Snapshots immuables** | Chaque `vX.0` = dossier figé + manifest JSON → reproductibilité garantie |
| **TF-IDF + Logistic Regression** | Baseline solide pour classification de texte, interprétable, rapide |

---

## Critères d'évaluation couverts

| Critère | Couverture |
|---------|-----------|
| Architecture de la plateforme | Schéma dossiers + diagramme pipeline dans ce README |
| Modélisation BDD relationnelle | 6 tables SQLite documentées avec clés primaires et clés étrangères |
| Pipeline robuste | 4 étapes : ingestion → transformation → features → dataset |
| Intégration avec l'entraînement | `trainer.py` connecté aux datasets versionnés |
| Versioning datasets | Snapshots `vX.0` immuables avec manifest JSON |
| Visualisation | Dashboard Streamlit avec entonnoir, scatter, histogrammes, comparaison modèles |
| Traçabilité | Table `logs` avec filtre par roman et par étape |
| Séparation fichiers / métadonnées | Object storage local (`storage/`) + base relationnelle (`symphonie.db`) |
