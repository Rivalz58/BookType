"""
Module d'extraction de features : TF-IDF, mots-clés, vecteurs numériques.
"""
import os
import json
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import STORAGE_PROCESSED
from database.models import (
    FeatureTexte, LogPipeline,
    get_roman, save_features, add_log, update_roman_statut,
)
from pipeline.transformation import charger_texte_propre

STOPWORDS_FR = {
    # Articles
    "le","la","les","un","une","des","du","de","l",
    # Pronoms personnels
    "je","tu","il","elle","nous","vous","ils","elles","on",
    "me","te","se","lui","leur","y","en","moi","toi","soi",
    # Pronoms relatifs / interrogatifs
    "que","qui","quoi","dont","où","quel","quelle","quels","quelles",
    "lequel","laquelle","lesquels","lesquelles",
    # Prépositions
    "à","au","aux","de","du","des","en","dans","sur","sous","par",
    "pour","avec","sans","vers","chez","entre","parmi","selon",
    "contre","depuis","pendant","avant","après","durant",
    # Conjonctions
    "et","ou","mais","donc","or","ni","car","que","si","comme",
    "quand","lorsque","puisque","bien","quoique","tandis","alors",
    # Verbes auxiliaires et copules très fréquents
    "est","sont","était","étaient","sera","seront","serait","seraient",
    "être","avoir","été","ayant","étant",
    "fait","font","faisait","faire","dit","disait","dire",
    "peut","peuvent","pouvait","pouvoir","doit","doivent","fallait",
    "alla","allait","aller","vint","venir","venait",
    "avait","avaient","aura","aurait","eut","eurent",
    "fut","furent",
    "avais","avait","avaient","avons","avez","aurai","aurais",
    "étais","était","étions","étiez","étaient",
    # Adverbes courants
    "ne","pas","plus","moins","très","bien","mal","aussi","même",
    "encore","toujours","jamais","souvent","parfois","déjà","enfin",
    "puis","ainsi","donc","alors","pourtant","cependant","néanmoins",
    "voilà","voici","oui","non","si","tout","tous","toute","toutes",
    "trop","peu","beaucoup","assez","presque","seulement","notamment",
    # Déterminants démonstratifs / possessifs
    "ce","cet","cette","ces","mon","ma","mes","ton","ta","tes",
    "son","sa","ses","notre","nos","votre","vos","leur","leurs",
    "celui","celle","ceux","celles","ceci","cela","ça",
    # Autres petits mots
    "lors","lors","dès","car","car","via","etc",
}


def _tokeniser(texte: str) -> list[str]:
    import re
    mots = re.findall(r"\b[a-zàâäéèêëîïôöùûüç]{3,}\b", texte.lower())
    return [m for m in mots if m not in STOPWORDS_FR]


def extraire_features(roman_id_str: str) -> tuple[bool, str]:
    import uuid as _uuid
    try:
        uid = _uuid.UUID(roman_id_str)
    except ValueError:
        return False, "ID invalide"

    roman = get_roman(uid)
    if not roman:
        return False, "Roman introuvable"

    try:
        texte = charger_texte_propre(roman)
        if not texte:
            add_log(LogPipeline(roman_id=uid, etape="feature_extraction", statut="échec",
                                message="Texte propre introuvable — lancez d'abord la transformation"))
            return False, "Texte propre introuvable"

        tokens = _tokeniser(texte)
        if not tokens:
            return False, "Aucun token extrait"

        freq: dict[str, int] = {}
        for t in tokens:
            freq[t] = freq.get(t, 0) + 1
        n  = len(tokens)
        tf = {t: c / n for t, c in freq.items()}

        top50      = sorted(tf.items(), key=lambda x: x[1], reverse=True)[:50]
        top50_dict = {mot: round(score, 6) for mot, score in top50}

        os.makedirs(STORAGE_PROCESSED, exist_ok=True)
        nom_vect    = os.path.splitext(roman.nom_fichier)[0] + "_features.json"
        chemin_vect = os.path.join(STORAGE_PROCESSED, nom_vect)
        with open(chemin_vect, "w", encoding="utf-8") as f:
            json.dump({"top_tf": top50_dict, "nb_tokens": n}, f, ensure_ascii=False, indent=2)

        feat = FeatureTexte(
            roman_id=uid,
            top_mots=json.dumps(top50_dict, ensure_ascii=False),
            vecteur_path=chemin_vect,
        )
        save_features(feat)
        update_roman_statut(uid, "features_extraites")
        add_log(LogPipeline(roman_id=uid, etape="feature_extraction", statut="succès",
                            message=f"Top-50 mots extraits ({n} tokens)"))
        return True, f"Features extraites ({n} tokens)"

    except Exception as e:
        return False, str(e)


def charger_features_fichier(roman: "Roman") -> dict:
    from database.models import get_features
    feat = get_features(roman.id)
    if not feat or not feat.vecteur_path:
        return {}
    if not os.path.exists(feat.vecteur_path):
        return {}
    with open(feat.vecteur_path, "r", encoding="utf-8") as f:
        return json.load(f)
