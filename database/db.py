import sqlite3
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_PATH

_SCHEMA = """
CREATE TABLE IF NOT EXISTS romans (
    id             TEXT PRIMARY KEY,
    titre          TEXT NOT NULL,
    auteur         TEXT DEFAULT 'Inconnu',
    genre          TEXT DEFAULT 'autre',
    annee          INTEGER,
    langue         TEXT DEFAULT 'français',
    source         TEXT,
    nom_fichier    TEXT,
    format_fichier TEXT,
    taille_octets  INTEGER,
    statut         TEXT DEFAULT 'ingere',
    date_upload    TEXT
);

CREATE TABLE IF NOT EXISTS statistiques_texte (
    roman_id            TEXT PRIMARY KEY,
    nb_mots             INTEGER DEFAULT 0,
    nb_phrases          INTEGER DEFAULT 0,
    nb_paragraphes      INTEGER DEFAULT 0,
    nb_caracteres       INTEGER DEFAULT 0,
    vocabulaire_unique  INTEGER DEFAULT 0,
    richesse_lexicale   REAL    DEFAULT 0.0,
    longueur_moy_phrase REAL    DEFAULT 0.0,
    date_calcul         TEXT,
    resume              TEXT,
    FOREIGN KEY (roman_id) REFERENCES romans(id)
);

CREATE TABLE IF NOT EXISTS features_texte (
    roman_id        TEXT PRIMARY KEY,
    top_mots        TEXT,
    vecteur_path    TEXT,
    date_extraction TEXT,
    FOREIGN KEY (roman_id) REFERENCES romans(id)
);

CREATE TABLE IF NOT EXISTS versions_dataset (
    id             TEXT PRIMARY KEY,
    version        TEXT UNIQUE,
    description    TEXT DEFAULT '',
    nb_romans      INTEGER DEFAULT 0,
    split_train    REAL    DEFAULT 0.7,
    split_val      REAL    DEFAULT 0.15,
    split_test     REAL    DEFAULT 0.15,
    chemin_fichier TEXT,
    date_creation  TEXT,
    est_actif      INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS modeles_entraines (
    id                TEXT PRIMARY KEY,
    nom               TEXT,
    algorithme        TEXT,
    dataset_id        TEXT,
    dataset_version   TEXT,
    accuracy_train    REAL,
    accuracy_val      REAL,
    accuracy_test     REAL,
    chemin_modele     TEXT,
    parametres        TEXT,
    date_entrainement TEXT,
    FOREIGN KEY (dataset_id) REFERENCES versions_dataset(id)
);

CREATE TABLE IF NOT EXISTS logs (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    roman_id TEXT,
    date_log TEXT,
    etape    TEXT,
    statut   TEXT,
    message  TEXT,
    FOREIGN KEY (roman_id) REFERENCES romans(id)
);
"""


def get_conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init_schema() -> None:
    conn = get_conn()
    conn.executescript(_SCHEMA)
    conn.commit()
    conn.close()
