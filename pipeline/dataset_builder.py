"""
Module de construction et de versioning des datasets.
Chaque version est un snapshot immuable : CSV + manifest JSON.
"""
import os
import json
import csv
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import STORAGE_DATASETS, STORAGE_PROCESSED
from database.models import (
    VersionDataset, LogPipeline,
    get_all_romans, get_stats, save_version, get_all_versions,
    get_version_by_name, count_versions, add_log, update_roman_statut,
)
from pipeline.transformation import charger_texte_propre


def _prochaine_version() -> str:
    n = count_versions()
    return f"v{n + 1}.0"


def construire_dataset(
    description: str  = "",
    split_train: float = 0.70,
    split_val:   float = 0.15,
    split_test:  float = 0.15,
) -> tuple[bool, str, str | None]:
    assert abs(split_train + split_val + split_test - 1.0) < 1e-6

    romans = get_all_romans(statut="features_extraites")
    if not romans:
        return False, "Aucun roman avec statut 'features_extraites' disponible", None

    version          = _prochaine_version()
    dossier_version  = os.path.join(STORAGE_DATASETS, version)
    os.makedirs(dossier_version, exist_ok=True)

    lignes = []
    for roman in romans:
        texte = charger_texte_propre(roman)
        if not texte:
            continue
        stats = get_stats(roman.id)
        lignes.append({
            "roman_id":        str(roman.id),
            "titre":           roman.titre,
            "auteur":          roman.auteur,
            "genre":           roman.genre,
            "annee":           roman.annee or "",
            "langue":          roman.langue,
            "nb_mots":         stats.nb_mots if stats else 0,
            "richesse":        stats.richesse_lexicale if stats else 0,
            "long_moy_phrase": stats.longueur_moy_phrase if stats else 0,
            "texte_path":      os.path.join(STORAGE_PROCESSED,
                                            os.path.splitext(roman.nom_fichier)[0] + "_clean.txt"),
        })

    if not lignes:
        return False, "Aucune ligne valide à inclure dans le dataset", None

    import random
    random.seed(42)
    random.shuffle(lignes)

    n     = len(lignes)
    n_tr  = max(1, int(n * split_train))
    n_val = max(1, int(n * split_val))
    splits = {
        "train": lignes[:n_tr],
        "val":   lignes[n_tr:n_tr + n_val],
        "test":  lignes[n_tr + n_val:],
    }

    fieldnames = list(lignes[0].keys())
    for split_name, rows in splits.items():
        if not rows:
            continue
        csv_path = os.path.join(dossier_version, f"{split_name}.csv")
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    manifest = {
        "version":       version,
        "description":   description,
        "date_creation": datetime.utcnow().isoformat(),
        "nb_romans":     n,
        "splits":        {k: len(v) for k, v in splits.items()},
        "split_ratios":  {"train": split_train, "val": split_val, "test": split_test},
        "romans":        [r["roman_id"] for r in lignes],
    }
    with open(os.path.join(dossier_version, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    v_obj = VersionDataset(
        version=version,
        description=description,
        nb_romans=n,
        split_train=split_train,
        split_val=split_val,
        split_test=split_test,
        chemin_fichier=dossier_version,
    )
    save_version(v_obj)

    for roman in romans:
        update_roman_statut(roman.id, "en_dataset")
        add_log(LogPipeline(roman_id=roman.id, etape="dataset", statut="succès",
                            message=f"Inclus dans dataset {version}"))

    return True, f"Dataset {version} créé ({n} romans)", version


def charger_manifest(version: str) -> dict:
    v = get_version_by_name(version)
    if not v or not v.chemin_fichier:
        return {}
    chemin = os.path.join(v.chemin_fichier, "manifest.json")
    if not os.path.exists(chemin):
        return {}
    with open(chemin, "r", encoding="utf-8") as f:
        return json.load(f)
