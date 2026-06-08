import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

STORAGE_RAW       = os.path.join(BASE_DIR, "storage", "raw")
STORAGE_PROCESSED = os.path.join(BASE_DIR, "storage", "processed")
STORAGE_DATASETS  = os.path.join(BASE_DIR, "storage", "datasets")
MODELS_DIR        = os.path.join(BASE_DIR, "models", "saved")

DB_PATH = os.path.join(BASE_DIR, "symphonie.db")

ALLOWED_EXTENSIONS = {".txt", ".pdf", ".epub"}
MAX_FILE_SIZE_MB   = 50

GENRES = [
    "roman_policier",
    "roman_historique",
    "roman_aventures",
    "roman_science_fiction",
    "roman_fantastique",
    "roman_philosophique",
    "roman_psychologique",
    "roman_amour",
    "roman_noir",
    "roman_satirique",
    "conte",
    "nouvelle",
    "biographie",
    "mythe_legende",
    "poetique",
    "theatre",
    "epistolaire",
    "voyage",
    "jeunesse",
    "essai",
    "presse",
    "histoire",
    "autre",
]
