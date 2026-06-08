"""
Module de transformation : extraction du texte brut, nettoyage, tokenisation.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import STORAGE_RAW, STORAGE_PROCESSED
from database.models import (
    Roman, StatistiqueTexte, LogPipeline,
    get_roman, save_stats, get_stats, add_log, update_roman_statut,
)


# --------------------------------------------------------------------------- #
#  Extraction du texte selon le format                                         #
# --------------------------------------------------------------------------- #

def _lire_txt(chemin: str) -> str:
    for enc in ("utf-8", "latin-1", "cp1252"):
        try:
            with open(chemin, "r", encoding=enc) as f:
                return f.read()
        except (UnicodeDecodeError, LookupError):
            continue
    return ""


def _lire_pdf(chemin: str) -> str:
    try:
        import PyPDF2
        texte = []
        with open(chemin, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                t = page.extract_text()
                if t:
                    texte.append(t)
        return "\n".join(texte)
    except Exception:
        return ""


def _lire_epub(chemin: str) -> str:
    try:
        import ebooklib
        from ebooklib import epub
        from html.parser import HTMLParser

        class _MLStripper(HTMLParser):
            def __init__(self):
                super().__init__()
                self.reset()
                self.fed = []
            def handle_data(self, d):
                self.fed.append(d)
            def get_data(self):
                return " ".join(self.fed)

        book   = epub.read_epub(chemin)
        textes = []
        for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
            s = _MLStripper()
            s.feed(item.get_content().decode("utf-8", errors="ignore"))
            textes.append(s.get_data())
        return "\n".join(textes)
    except Exception:
        return ""


def extraire_texte(roman: Roman) -> str:
    chemin = os.path.join(STORAGE_RAW, roman.nom_fichier)
    fmt = roman.format_fichier.lower()
    if fmt == "txt":
        return _lire_txt(chemin)
    elif fmt == "pdf":
        return _lire_pdf(chemin)
    elif fmt == "epub":
        return _lire_epub(chemin)
    return ""


# --------------------------------------------------------------------------- #
#  Nettoyage                                                                   #
# --------------------------------------------------------------------------- #

def nettoyer_texte(texte: str) -> str:
    debut = re.search(r"\*\*\* START OF (THE|THIS) PROJECT GUTENBERG", texte, re.IGNORECASE)
    fin   = re.search(r"\*\*\* END OF (THE|THIS) PROJECT GUTENBERG",   texte, re.IGNORECASE)
    if debut:
        texte = texte[debut.end():]
    if fin:
        texte = texte[:fin.start()]
    texte = re.sub(r"\r\n", "\n", texte)
    texte = re.sub(r"\n{3,}", "\n\n", texte)
    texte = re.sub(r"[ \t]+", " ", texte)
    texte = re.sub(r"[^\w\s\.,;:!?'\"\-\n]", " ", texte, flags=re.UNICODE)
    return texte.strip()


def calculer_stats(texte: str) -> dict:
    mots        = texte.split()
    phrases     = [p.strip() for p in re.split(r"[.!?]+", texte) if p.strip()]
    paragraphes = [p.strip() for p in texte.split("\n\n") if p.strip()]
    vocab_unique = len(set(m.lower() for m in mots))
    richesse     = vocab_unique / len(mots) if mots else 0.0
    long_moy     = sum(len(p.split()) for p in phrases) / len(phrases) if phrases else 0.0
    return {
        "nb_mots":            len(mots),
        "nb_phrases":         len(phrases),
        "nb_paragraphes":     len(paragraphes),
        "nb_caracteres":      len(texte),
        "vocabulaire_unique": vocab_unique,
        "richesse_lexicale":  round(richesse, 4),
        "longueur_moy_phrase": round(long_moy, 2),
    }


# --------------------------------------------------------------------------- #
#  Point d'entrée                                                              #
# --------------------------------------------------------------------------- #

def transformer_roman(roman_id_str: str) -> tuple[bool, str]:
    import uuid as _uuid
    try:
        uid = _uuid.UUID(roman_id_str)
    except ValueError:
        return False, "ID invalide"

    roman = get_roman(uid)
    if not roman:
        return False, "Roman introuvable"

    try:
        texte_brut = extraire_texte(roman)
        if not texte_brut:
            add_log(LogPipeline(roman_id=uid, etape="transformation", statut="échec",
                                message="Impossible d'extraire le texte"))
            return False, "Impossible d'extraire le texte"

        texte_propre = nettoyer_texte(texte_brut)
        stats_dict   = calculer_stats(texte_propre)

        os.makedirs(STORAGE_PROCESSED, exist_ok=True)
        nom_proc = os.path.splitext(roman.nom_fichier)[0] + "_clean.txt"
        with open(os.path.join(STORAGE_PROCESSED, nom_proc), "w", encoding="utf-8") as f:
            f.write(texte_propre)

        stats = StatistiqueTexte(roman_id=uid, **stats_dict)
        save_stats(stats)
        update_roman_statut(uid, "transforme")
        add_log(LogPipeline(roman_id=uid, etape="transformation", statut="succès",
                            message=f"Texte nettoyé : {stats_dict['nb_mots']} mots, {stats_dict['nb_phrases']} phrases"))
        return True, f"Transformation réussie ({stats_dict['nb_mots']} mots)"

    except Exception as e:
        return False, str(e)


def charger_texte_propre(roman: Roman) -> str:
    nom_proc = os.path.splitext(roman.nom_fichier)[0] + "_clean.txt"
    chemin   = os.path.join(STORAGE_PROCESSED, nom_proc)
    if not os.path.exists(chemin):
        return ""
    with open(chemin, "r", encoding="utf-8") as f:
        return f.read()
