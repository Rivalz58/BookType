"""
Module ML : entraînement d'un classificateur de genre littéraire.
Algorithme : TF-IDF (sklearn) + Régression Logistique / SVM.
"""
import os
import sys
import json
import csv
import joblib
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import MODELS_DIR
from database.models import (
    ModeleEntraine, get_version_by_name, get_all_modeles, get_modele, save_modele,
)


def _charger_split(dossier: str, split: str) -> tuple[list[str], list[str]]:
    chemin = os.path.join(dossier, f"{split}.csv")
    if not os.path.exists(chemin):
        return [], []
    textes, labels = [], []
    with open(chemin, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            texte_path = row.get("texte_path", "")
            if os.path.exists(texte_path):
                with open(texte_path, "r", encoding="utf-8") as tf:
                    textes.append(tf.read()[:5000])
            else:
                textes.append(row.get("titre", "") + " " + row.get("auteur", ""))
            labels.append(row.get("genre", "autre"))
    return textes, labels


def entrainer_modele(version: str, algo: str = "logistic_regression") -> tuple[bool, str, str | None]:
    from sklearn.pipeline import Pipeline
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.svm import LinearSVC
    from sklearn.metrics import accuracy_score

    v_obj = get_version_by_name(version)
    if not v_obj:
        return False, f"Version '{version}' introuvable", None

    dossier = v_obj.chemin_fichier
    X_train, y_train = _charger_split(dossier, "train")
    X_val,   y_val   = _charger_split(dossier, "val")
    X_test,  y_test  = _charger_split(dossier, "test")

    if not X_train:
        return False, "Données d'entraînement vides", None

    try:
        clf = LinearSVC(max_iter=2000, C=1.0) if algo == "svm" else \
              LogisticRegression(max_iter=1000, C=1.0, solver="lbfgs", multi_class="auto")

        pipe = Pipeline([
            ("tfidf", TfidfVectorizer(max_features=10000, ngram_range=(1, 2),
                                      sublinear_tf=True, min_df=1)),
            ("clf", clf),
        ])
        pipe.fit(X_train, y_train)

        acc_train = accuracy_score(y_train, pipe.predict(X_train))
        acc_val   = accuracy_score(y_val,  pipe.predict(X_val))  if X_val  else None
        acc_test  = accuracy_score(y_test, pipe.predict(X_test)) if X_test else None

        os.makedirs(MODELS_DIR, exist_ok=True)
        timestamp  = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        nom_modele = f"modele_{version}_{algo}_{timestamp}.joblib"
        chemin_mod = os.path.join(MODELS_DIR, nom_modele)
        joblib.dump(pipe, chemin_mod)

        params = json.dumps({
            "algo": algo, "max_features": 10000,
            "ngram_range": "(1,2)", "nb_train": len(X_train),
        })

        m_obj = ModeleEntraine(
            nom=f"modele_{version}_{algo}",
            algorithme=algo,
            dataset_id=v_obj.id,
            dataset_version=version,
            accuracy_train=round(acc_train, 4),
            accuracy_val=round(acc_val, 4)  if acc_val  is not None else None,
            accuracy_test=round(acc_test, 4) if acc_test is not None else None,
            chemin_modele=chemin_mod,
            parametres=params,
        )
        save_modele(m_obj)

        msg = (f"Modèle entraîné — train: {acc_train:.2%}"
               + (f", val: {acc_val:.2%}"   if acc_val  is not None else "")
               + (f", test: {acc_test:.2%}" if acc_test is not None else ""))
        return True, msg, str(m_obj.id)

    except Exception as e:
        return False, str(e), None


def predire(roman_id_str: str, modele_id_str: str) -> tuple[bool, str]:
    import uuid as _uuid
    from pipeline.transformation import charger_texte_propre
    from database.models import get_roman

    try:
        roman  = get_roman(_uuid.UUID(roman_id_str))
        modele = get_modele(_uuid.UUID(modele_id_str))
    except ValueError:
        return False, "ID invalide"

    if not roman or not modele:
        return False, "Roman ou modèle introuvable"

    texte = charger_texte_propre(roman)
    if not texte:
        return False, "Texte propre introuvable"

    pipe = joblib.load(modele.chemin_modele)
    pred = pipe.predict([texte[:5000]])[0]
    proba = None
    if hasattr(pipe, "predict_proba"):
        try:
            p = pipe.predict_proba([texte[:5000]])[0]
            proba = dict(zip(pipe.classes_, [round(float(x), 3) for x in p]))
        except Exception:
            pass
    return True, json.dumps({"prediction": pred, "probabilites": proba}, ensure_ascii=False)


def lister_modeles() -> list[dict]:
    return [{
        "id":        str(m.id),
        "nom":       m.nom,
        "algo":      m.algorithme,
        "dataset":   m.dataset_version,
        "acc_train": m.accuracy_train,
        "acc_val":   m.accuracy_val,
        "acc_test":  m.accuracy_test,
        "date":      m.date_entrainement.strftime("%Y-%m-%d %H:%M"),
        "chemin":    m.chemin_modele,
    } for m in get_all_modeles()]
