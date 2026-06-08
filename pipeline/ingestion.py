"""
Module d'ingestion : upload, validation et stockage des fichiers bruts.
"""
import os
from datetime import datetime
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import STORAGE_RAW, ALLOWED_EXTENSIONS, MAX_FILE_SIZE_MB
from database.models import Roman, LogPipeline, save_roman, delete_roman as db_delete, add_log, get_all_romans


def valider_fichier(nom_fichier: str, taille_octets: int) -> tuple[bool, str]:
    ext = os.path.splitext(nom_fichier)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"Extension '{ext}' non autorisée. Formats acceptés : {ALLOWED_EXTENSIONS}"
    if taille_octets > MAX_FILE_SIZE_MB * 1024 * 1024:
        return False, f"Fichier trop volumineux ({taille_octets/1024/1024:.1f} Mo). Maximum : {MAX_FILE_SIZE_MB} Mo"
    return True, "OK"


def _generer_nom_unique(nom_fichier: str) -> str:
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    base, ext = os.path.splitext(nom_fichier)
    return f"{base}_{timestamp}{ext}"


def ingerer_fichier(
    contenu_bytes: bytes,
    nom_fichier:   str,
    titre:         str,
    auteur:        str  = "Inconnu",
    genre:         str  = "autre",
    annee:         int  = None,
    langue:        str  = "français",
    source:        str  = None,
) -> tuple[bool, str, str | None]:
    """
    Valide, stocke le fichier brut et enregistre les métadonnées dans la base de données.
    Retourne (succès, message, roman_id_str).
    """
    taille = len(contenu_bytes)
    valide, msg = valider_fichier(nom_fichier, taille)
    if not valide:
        return False, msg, None

    os.makedirs(STORAGE_RAW, exist_ok=True)
    nom_stockage = _generer_nom_unique(nom_fichier)
    chemin_dest  = os.path.join(STORAGE_RAW, nom_stockage)

    with open(chemin_dest, "wb") as f:
        f.write(contenu_bytes)

    ext = os.path.splitext(nom_fichier)[1].lower().lstrip(".")

    roman = Roman(
        titre=titre,
        auteur=auteur,
        genre=genre,
        annee=annee,
        langue=langue,
        source=source,
        nom_fichier=nom_stockage,
        format_fichier=ext,
        taille_octets=taille,
        statut="ingere",
    )

    try:
        save_roman(roman)
        add_log(LogPipeline(
            roman_id=roman.id,
            etape="ingestion",
            statut="succès",
            message=f"Fichier '{nom_fichier}' stocké sous '{nom_stockage}' ({taille} octets)",
        ))
    except Exception as e:
        os.remove(chemin_dest)
        return False, f"Erreur BDD : {e}", None

    return True, f"Roman '{titre}' ingéré (id={roman.id_court})", roman.id_str


def supprimer_roman(roman_id_str: str) -> tuple[bool, str]:
    import uuid as _uuid
    try:
        uid = _uuid.UUID(roman_id_str)
    except ValueError:
        return False, "ID invalide"

    from database.models import get_roman
    roman = get_roman(uid)
    if not roman:
        return False, "Roman introuvable"

    chemin = os.path.join(STORAGE_RAW, roman.nom_fichier)
    if os.path.exists(chemin):
        os.remove(chemin)

    try:
        db_delete(uid)
        return True, f"Roman '{roman.titre}' supprimé"
    except Exception as e:
        return False, str(e)
