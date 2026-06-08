"""
Système de recommandation de livres par similarité cosinus sur vecteurs TF-IDF.
Aucun entraînement nécessaire — utilise les textes nettoyés déjà calculés.
"""
import os
import sys
import uuid
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import STORAGE_PROCESSED
from database.models import get_all_romans


def _charger_textes():
    """Charge tous les textes nettoyés disponibles. Retourne (textes, romans)."""
    romans = [r for r in get_all_romans()
              if r.statut in ("features_extraites", "en_dataset", "transforme")]

    textes, romans_valides = [], []
    for r in romans:
        nom = os.path.splitext(r.nom_fichier)[0] + "_clean.txt"
        chemin = os.path.join(STORAGE_PROCESSED, nom)
        if os.path.exists(chemin):
            with open(chemin, "r", encoding="utf-8") as f:
                textes.append(f.read()[:15000])
            romans_valides.append(r)

    return textes, romans_valides


def construire_index():
    """Construit la matrice TF-IDF sur tous les livres transformés."""
    from sklearn.feature_extraction.text import TfidfVectorizer

    textes, romans = _charger_textes()
    if len(textes) < 2:
        return None, []

    tfidf = TfidfVectorizer(
        max_features=8000,
        ngram_range=(1, 2),
        sublinear_tf=True,
        min_df=2,
    )
    matrix = tfidf.fit_transform(textes)
    return matrix, romans


def recommander(roman_id_str: str, n: int = 10) -> list[tuple]:
    """
    Retourne les N livres les plus similaires au livre donné.
    Chaque entrée : (roman, score_similarite)
    """
    uid = uuid.UUID(roman_id_str)
    matrix, romans = construire_index()

    if matrix is None:
        return []

    idx = next((i for i, r in enumerate(romans) if r.id == uid), None)
    if idx is None:
        return []

    from sklearn.metrics.pairwise import cosine_similarity
    scores = cosine_similarity(matrix[idx], matrix)[0]

    indices = np.argsort(scores)[::-1]
    indices = [i for i in indices if i != idx][:n]

    return [(romans[i], round(float(scores[i]), 4)) for i in indices]


def livres_similaires_par_texte(texte: str, n: int = 10) -> list[tuple]:
    """
    Recommande des livres à partir d'un texte libre (pas forcément dans la base).
    """
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    textes, romans = _charger_textes()
    if len(textes) < 2:
        return []

    tous_textes = textes + [texte[:15000]]
    tfidf = TfidfVectorizer(max_features=8000, ngram_range=(1, 2), sublinear_tf=True, min_df=1)
    matrix = tfidf.fit_transform(tous_textes)

    scores = cosine_similarity(matrix[-1], matrix[:-1])[0]
    indices = np.argsort(scores)[::-1][:n]

    return [(romans[i], round(float(scores[i]), 4)) for i in indices]
