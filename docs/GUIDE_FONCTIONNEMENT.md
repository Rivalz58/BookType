# Guide de fonctionnement — Symphonie des données

Ce document explique **comment fonctionne l'application** et **comment
l'utiliser**, page par page, pour quelqu'un qui découvre le projet (correcteur,
membre du jury, futur utilisateur).

---

## 1. Lancer l'application

### Prérequis
- Python 3.10+
- Dépendances : `pip install -r requirements.txt`

### Démarrage
```bash
streamlit run app/Home.py
# ou, pour initialiser la base au passage :
python run.py
```
L'application s'ouvre dans le navigateur sur `http://localhost:8501`.
Au premier lancement, le fichier `symphonie.db` (base SQLite) est créé
automatiquement avec ses 6 tables, et les dossiers `storage/raw/`,
`storage/processed/`, `storage/datasets/` sont prêts à recevoir les données.

> Le dépôt Git ne contient **pas** les fichiers volumineux (romans bruts,
> textes nettoyés, modèles entraînés, base de données) : ils sont régénérés
> automatiquement en suivant les étapes ci-dessous. Une version de dataset
> (`storage/datasets/v1.0/`) est conservée à titre d'exemple du mécanisme de
> versioning.

---

## 2. Page d'accueil (`Home.py`)

Premier écran après le lancement. Elle donne une vue instantanée de l'état du
corpus :

- **5 indicateurs (KPI)** : nombre total de romans, nombre transformés, nombre
  avec features extraites, nombre de versions de dataset, nombre de modèles
  entraînés.
- **Diagramme en entonnoir** : représente combien de romans ont franchi
  chaque étape du pipeline (`ingéré` → `transformé` → `features extraites` →
  `en dataset`). Permet de repérer en un coup d'œil où se trouve le « goulot
  d'étranglement » du pipeline.
- **Tableau de navigation** vers les autres pages.

---

## 3. Bibliothèque (`1_Bibliotheque.py`)

Page de gestion du corpus, organisée en **trois onglets**.

### Onglet « Liste »
- Filtres par genre, par statut et recherche texte (titre/auteur).
- Tableau de tous les romans avec une icône représentant leur statut dans le
  pipeline.
- Suppression d'un roman (retire à la fois son fichier dans `storage/raw/` et
  ses enregistrements en base).

### Onglet « Détail »
Sélection d'un roman pour afficher sa fiche complète :
- Métadonnées (titre, auteur, genre, année, langue, source…).
- Statistiques textuelles si le roman a été transformé (nombre de mots, de
  phrases, de paragraphes, taille du vocabulaire, richesse lexicale, longueur
  moyenne de phrase).
- Histogramme des 30 mots les plus représentatifs (calculés lors de
  l'extraction de features).
- Historique des opérations menées sur ce roman (logs horodatés).

### Onglet « Upload »
Formulaire d'**ingestion** d'un nouveau roman :
1. Choisir un fichier `.txt`, `.pdf` ou `.epub` (50 Mo max).
2. Renseigner titre, auteur, genre (liste prédéfinie de 23 genres dans
   `config.py`), année, langue, source.
3. Valider → le fichier est copié dans `storage/raw/`, une entrée est créée
   dans la table `romans` avec le statut `ingere`, et l'opération est
   journalisée.

> **Sources de données recommandées** : romans `.txt` libres de droits issus
> de [Project Gutenberg](https://www.gutenberg.org/), en français.

---

## 4. Pipeline (`2_Pipeline.py`)

Page d'orchestration des deux premières transformations du pipeline, avec des
compteurs globaux par statut affichés en haut de page.

### Étape 1 — Transformation
- Bouton **« Transformer tous »** : traite en lot tous les romans au statut
  `ingere` (extraction du texte selon son format, nettoyage — suppression des
  en-têtes Project Gutenberg, normalisation des espaces — et calcul des
  statistiques), avec une barre de progression.
- Possibilité de transformer un roman **un par un** via un menu déroulant.
- Résultat : le texte nettoyé est écrit dans `storage/processed/*_clean.txt`,
  les statistiques sont enregistrées en base, le statut passe à `transforme`.

### Étape 2 — Extraction de features
- Même logique (lot ou unitaire) pour les romans au statut `transforme`.
- Le texte est tokenisé (mots de 3 lettres ou plus, hors *stop-words*
  français), les fréquences (TF) sont calculées, les 50 mots les plus
  fréquents sont conservés.
- Résultat : un fichier `*_features.json` est écrit dans `storage/processed/`,
  le top-50 est enregistré en base, le statut passe à `features_extraites`.

Un panneau dépliant en bas de page affiche les **logs récents**, regroupés par
étape (`ingestion`, `transformation`, `feature_extraction`, `dataset`).

---

## 5. Datasets (`3_Datasets.py`)

Page de **constitution et de versioning** des jeux de données d'entraînement.

### Création d'une version
1. Donner une description (ex : « Premier corpus équilibré, 6 genres »).
2. Régler les proportions train / validation / test à l'aide de curseurs (la
   part de test doit être ≥ 5 %, le complément est calculé automatiquement).
3. Valider → l'application sélectionne tous les romans au statut
   `features_extraites`, mélange le corpus avec une **graine aléatoire fixe**
   (pour pouvoir reproduire exactement le même découpage plus tard), répartit
   les romans selon les ratios choisis, écrit un CSV par split et un
   **`manifest.json`** immuable (description, dates, comptages, ratios, liste
   des romans inclus). La version reçoit un identifiant automatique
   (`v1.0`, `v2.0`, …), est enregistrée en base, et le statut des romans
   inclus passe à `en_dataset`.

### Historique des versions
Chaque version créée apparaît dans un panneau dépliant affichant :
- les comptages (total / train / val / test) ;
- la description et le contenu brut du manifest ;
- un aperçu des dix premières lignes du fichier `train.csv`.

> **Pourquoi un snapshot immuable ?** Une fois créée, une version de dataset
> n'est jamais modifiée : elle reste une référence stable et reproductible,
> même si le corpus continue de grossir. Cela permet de toujours savoir
> exactement quelles données ont servi à entraîner quel modèle.

---

## 6. Modèle (`4_Modele.py`)

Page d'entraînement et d'exploitation du modèle de classification de genre,
organisée en **quatre onglets**.

### Onglet « Entraînement »
- Choisir une **version de dataset** et un **algorithme** :
  régression logistique (`logistic_regression`) ou SVM linéaire (`svm`).
- Lancer l'entraînement → le pipeline construit une représentation **TF-IDF**
  du texte (10 000 mots/bi-grammes maximum) puis entraîne le classificateur ;
  les exactitudes (*accuracy*) sont calculées sur les trois ensembles
  (train/val/test) et le modèle est sauvegardé (`models/saved/*.joblib`) avec
  ses métadonnées en base.

### Onglet « Modèles entraînés »
- Tableau comparatif des modèles (algorithme, dataset utilisé, accuracies en
  pourcentage, date d'entraînement).
- Graphique en barres groupées comparant les performances train/val/test
  entre modèles.

### Onglet « Prédiction de genre »
- Choisir un roman et un modèle entraîné.
- L'application prédit le genre du roman à partir de son texte nettoyé,
  affiche la prédiction (avec un effet « ballons » 🎈 si elle correspond au
  genre réel) et un histogramme des dix genres les plus probables avec leurs
  scores de confiance.

### Onglet « Recommandation »
- Choisir un roman cible et un nombre de résultats souhaités.
- L'application calcule la **similarité cosinus** entre les vecteurs TF-IDF du
  roman cible et de tous les autres romans du corpus, et propose les *n*
  romans les plus proches stylistiquement, avec leur score de similarité
  affiché sous forme de tableau et d'histogramme.
  *(Ce module ne nécessite pas de modèle entraîné au préalable : il fonctionne
  directement sur les textes nettoyés disponibles.)*

---

## 7. Dashboard (`5_Dashboard.py`)

Tableau de bord de **supervision globale**, organisé en quatre onglets après
l'affichage des cinq indicateurs clés.

| Onglet | Contenu |
|--------|---------|
| **Corpus** | Entonnoir cumulatif du pipeline, répartition des romans par genre, courbe de croissance cumulée du corpus dans le temps |
| **Statistiques textuelles** | Distribution du nombre de mots, nuage de points « richesse lexicale vs nombre de mots » coloré par genre, tableau d'agrégats moyens par genre |
| **Modèles** | Nombre de romans par version de dataset, comparaison des accuracies train/val/test entre tous les modèles entraînés |
| **Logs** | Tableau des 30 dernières opérations journalisées (toutes étapes confondues) |

Cette page constitue le point d'entrée privilégié pour **superviser
l'ensemble du cycle de vie des données** : combien de romans sont entrés,
où ils en sont dans le pipeline, comment le corpus évolue, et comment les
modèles successifs se comparent entre eux.

---

## 8. Parcours type (« golden path »)

Pour reproduire l'expérience complète depuis un corpus vide :

1. **Bibliothèque → Upload** : déposer plusieurs romans `.txt` de Project
   Gutenberg avec leurs métadonnées (idéalement plusieurs genres représentés).
2. **Pipeline** : cliquer sur « Transformer tous », puis « Extraire features
   de tous ».
3. **Datasets** : créer une version (ex : `v1.0`) avec des ratios adaptés à
   la taille du corpus (par exemple 70 % / 15 % / 15 %).
4. **Modèle → Entraînement** : choisir la version créée et un algorithme,
   lancer l'entraînement, consulter les accuracies.
5. **Modèle → Prédiction / Recommandation** : tester le modèle sur un roman du
   corpus et explorer les recommandations.
6. **Dashboard** : visualiser l'ensemble du cycle de vie — progression du
   pipeline, répartition du corpus, comparaison des modèles, journal complet.

---

## 9. Annexe — table des correspondances « statut du roman »

| Statut | Signification | Étape qui le produit |
|--------|---------------|----------------------|
| `ingere` | Fichier stocké, métadonnées enregistrées | Ingestion (upload) |
| `transforme` | Texte extrait, nettoyé, statistiques calculées | Transformation |
| `features_extraites` | Vecteur TF / top mots calculés | Extraction de features |
| `en_dataset` | Inclus dans une version de dataset versionnée | Construction de dataset |

Ce statut est le fil conducteur de toute la supervision : il pilote
l'entonnoir de la page d'accueil, les compteurs de la page Pipeline, et les
filtres de la Bibliothèque.
