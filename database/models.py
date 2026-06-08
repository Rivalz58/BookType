from __future__ import annotations
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# --------------------------------------------------------------------------- #
#  Dataclasses                                                                 #
# --------------------------------------------------------------------------- #

@dataclass
class Roman:
    titre:          str
    auteur:         str           = "Inconnu"
    genre:          str           = "autre"
    annee:          Optional[int] = None
    langue:         str           = "français"
    source:         Optional[str] = None
    nom_fichier:    str           = ""
    format_fichier: str           = ""
    taille_octets:  Optional[int] = None
    statut:         str           = "ingere"
    date_upload:    datetime      = field(default_factory=datetime.utcnow)
    id:             uuid.UUID     = field(default_factory=uuid.uuid4)

    stats:    Optional["StatistiqueTexte"] = field(default=None, repr=False)
    features: Optional["FeatureTexte"]    = field(default=None, repr=False)

    @property
    def id_str(self) -> str:
        return str(self.id)

    @property
    def id_court(self) -> str:
        return str(self.id)[:8]


@dataclass
class StatistiqueTexte:
    roman_id:            uuid.UUID
    nb_mots:             int   = 0
    nb_phrases:          int   = 0
    nb_paragraphes:      int   = 0
    nb_caracteres:       int   = 0
    vocabulaire_unique:  int   = 0
    richesse_lexicale:   float = 0.0
    longueur_moy_phrase: float = 0.0
    date_calcul:         datetime = field(default_factory=datetime.utcnow)
    resume:              Optional[str] = None


@dataclass
class FeatureTexte:
    roman_id:        uuid.UUID
    top_mots:        Optional[str] = None
    vecteur_path:    Optional[str] = None
    date_extraction: datetime = field(default_factory=datetime.utcnow)


@dataclass
class VersionDataset:
    version:        str
    description:    str           = ""
    nb_romans:      int           = 0
    split_train:    float         = 0.70
    split_val:      float         = 0.15
    split_test:     float         = 0.15
    chemin_fichier: Optional[str] = None
    date_creation:  datetime      = field(default_factory=datetime.utcnow)
    est_actif:      bool          = True
    id:             uuid.UUID     = field(default_factory=uuid.uuid4)


@dataclass
class ModeleEntraine:
    nom:               str
    algorithme:        str
    dataset_id:        uuid.UUID
    dataset_version:   str
    accuracy_train:    Optional[float] = None
    accuracy_val:      Optional[float] = None
    accuracy_test:     Optional[float] = None
    chemin_modele:     Optional[str]   = None
    parametres:        Optional[str]   = None
    date_entrainement: datetime = field(default_factory=datetime.utcnow)
    id:                uuid.UUID = field(default_factory=uuid.uuid4)


@dataclass
class LogPipeline:
    roman_id: uuid.UUID
    etape:    str
    statut:   str
    message:  Optional[str] = None
    date_log: datetime = field(default_factory=datetime.utcnow)


# --------------------------------------------------------------------------- #
#  Helpers                                                                     #
# --------------------------------------------------------------------------- #

def _conn():
    from database.db import get_conn
    return get_conn()


def _parse_dt(s) -> datetime:
    if not s:
        return datetime.utcnow()
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return datetime.utcnow()


def _dt(dt: datetime) -> str:
    return dt.isoformat()


def _row_to_roman(row) -> Roman:
    return Roman(
        id=uuid.UUID(row["id"]),
        titre=row["titre"] or "",
        auteur=row["auteur"] or "Inconnu",
        genre=row["genre"] or "autre",
        annee=row["annee"],
        langue=row["langue"] or "français",
        source=row["source"],
        nom_fichier=row["nom_fichier"] or "",
        format_fichier=row["format_fichier"] or "",
        taille_octets=row["taille_octets"],
        statut=row["statut"] or "ingere",
        date_upload=_parse_dt(row["date_upload"]),
    )


def _row_to_version(row) -> VersionDataset:
    return VersionDataset(
        id=uuid.UUID(row["id"]),
        version=row["version"] or "",
        description=row["description"] or "",
        nb_romans=row["nb_romans"] or 0,
        split_train=float(row["split_train"] or 0.7),
        split_val=float(row["split_val"] or 0.15),
        split_test=float(row["split_test"] or 0.15),
        chemin_fichier=row["chemin_fichier"],
        date_creation=_parse_dt(row["date_creation"]),
        est_actif=bool(row["est_actif"]),
    )


def _row_to_log(row) -> LogPipeline:
    return LogPipeline(
        roman_id=uuid.UUID(row["roman_id"]) if row["roman_id"] else uuid.uuid4(),
        date_log=_parse_dt(row["date_log"]),
        etape=row["etape"] or "",
        statut=row["statut"] or "",
        message=row["message"],
    )


# --------------------------------------------------------------------------- #
#  CRUD — Romans                                                               #
# --------------------------------------------------------------------------- #

def save_roman(roman: Roman) -> None:
    conn = _conn()
    conn.execute("""
        INSERT OR REPLACE INTO romans
        (id, titre, auteur, genre, annee, langue, source, nom_fichier,
         format_fichier, taille_octets, statut, date_upload)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (str(roman.id), roman.titre, roman.auteur, roman.genre, roman.annee,
          roman.langue, roman.source, roman.nom_fichier, roman.format_fichier,
          roman.taille_octets, roman.statut, _dt(roman.date_upload)))
    conn.commit()
    conn.close()


def get_roman(roman_id: uuid.UUID) -> Optional[Roman]:
    conn = _conn()
    row = conn.execute("SELECT * FROM romans WHERE id = ?", (str(roman_id),)).fetchone()
    conn.close()
    return _row_to_roman(row) if row else None


def get_all_romans(statut: str = None) -> list[Roman]:
    conn = _conn()
    if statut:
        rows = conn.execute(
            "SELECT * FROM romans WHERE statut = ? ORDER BY date_upload DESC", (statut,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM romans ORDER BY date_upload DESC").fetchall()
    conn.close()
    return [_row_to_roman(r) for r in rows]


def update_roman_statut(roman_id: uuid.UUID, statut: str) -> None:
    conn = _conn()
    conn.execute("UPDATE romans SET statut = ? WHERE id = ?", (statut, str(roman_id)))
    conn.commit()
    conn.close()


def delete_roman(roman_id: uuid.UUID) -> None:
    conn = _conn()
    rid = str(roman_id)
    conn.execute("DELETE FROM statistiques_texte WHERE roman_id = ?", (rid,))
    conn.execute("DELETE FROM features_texte WHERE roman_id = ?", (rid,))
    conn.execute("DELETE FROM logs WHERE roman_id = ?", (rid,))
    conn.execute("DELETE FROM romans WHERE id = ?", (rid,))
    conn.commit()
    conn.close()


# --------------------------------------------------------------------------- #
#  CRUD — Statistiques                                                         #
# --------------------------------------------------------------------------- #

def save_stats(stats: StatistiqueTexte) -> None:
    conn = _conn()
    conn.execute("""
        INSERT OR REPLACE INTO statistiques_texte
        (roman_id, nb_mots, nb_phrases, nb_paragraphes, nb_caracteres,
         vocabulaire_unique, richesse_lexicale, longueur_moy_phrase, date_calcul, resume)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (str(stats.roman_id), stats.nb_mots, stats.nb_phrases, stats.nb_paragraphes,
          stats.nb_caracteres, stats.vocabulaire_unique, stats.richesse_lexicale,
          stats.longueur_moy_phrase, _dt(stats.date_calcul), stats.resume))
    conn.commit()
    conn.close()


def update_roman_resume(roman_id: uuid.UUID, resume: str) -> None:
    conn = _conn()
    conn.execute(
        "UPDATE statistiques_texte SET resume = ? WHERE roman_id = ?",
        (resume, str(roman_id))
    )
    conn.commit()
    conn.close()


def get_stats(roman_id: uuid.UUID) -> Optional[StatistiqueTexte]:
    conn = _conn()
    row = conn.execute(
        "SELECT * FROM statistiques_texte WHERE roman_id = ?", (str(roman_id),)
    ).fetchone()
    conn.close()
    if not row:
        return None
    return StatistiqueTexte(
        roman_id=uuid.UUID(row["roman_id"]),
        nb_mots=row["nb_mots"] or 0,
        nb_phrases=row["nb_phrases"] or 0,
        nb_paragraphes=row["nb_paragraphes"] or 0,
        nb_caracteres=row["nb_caracteres"] or 0,
        vocabulaire_unique=row["vocabulaire_unique"] or 0,
        richesse_lexicale=float(row["richesse_lexicale"] or 0),
        longueur_moy_phrase=float(row["longueur_moy_phrase"] or 0),
        date_calcul=_parse_dt(row["date_calcul"]),
        resume=row["resume"],
    )


# --------------------------------------------------------------------------- #
#  CRUD — Features                                                             #
# --------------------------------------------------------------------------- #

def save_features(feat: FeatureTexte) -> None:
    conn = _conn()
    conn.execute("""
        INSERT OR REPLACE INTO features_texte (roman_id, top_mots, vecteur_path, date_extraction)
        VALUES (?, ?, ?, ?)
    """, (str(feat.roman_id), feat.top_mots, feat.vecteur_path, _dt(feat.date_extraction)))
    conn.commit()
    conn.close()


def get_features(roman_id: uuid.UUID) -> Optional[FeatureTexte]:
    conn = _conn()
    row = conn.execute(
        "SELECT * FROM features_texte WHERE roman_id = ?", (str(roman_id),)
    ).fetchone()
    conn.close()
    if not row:
        return None
    return FeatureTexte(
        roman_id=uuid.UUID(row["roman_id"]),
        top_mots=row["top_mots"],
        vecteur_path=row["vecteur_path"],
        date_extraction=_parse_dt(row["date_extraction"]),
    )


# --------------------------------------------------------------------------- #
#  CRUD — Versions dataset                                                     #
# --------------------------------------------------------------------------- #

def save_version(v: VersionDataset) -> None:
    conn = _conn()
    conn.execute("""
        INSERT OR REPLACE INTO versions_dataset
        (id, version, description, nb_romans, split_train, split_val, split_test,
         chemin_fichier, date_creation, est_actif)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (str(v.id), v.version, v.description, v.nb_romans, v.split_train, v.split_val,
          v.split_test, v.chemin_fichier, _dt(v.date_creation), int(v.est_actif)))
    conn.commit()
    conn.close()


def get_all_versions() -> list[VersionDataset]:
    conn = _conn()
    rows = conn.execute(
        "SELECT * FROM versions_dataset ORDER BY date_creation DESC"
    ).fetchall()
    conn.close()
    return [_row_to_version(r) for r in rows]


def get_version_by_name(version: str) -> Optional[VersionDataset]:
    conn = _conn()
    row = conn.execute(
        "SELECT * FROM versions_dataset WHERE version = ?", (version,)
    ).fetchone()
    conn.close()
    return _row_to_version(row) if row else None


def count_versions() -> int:
    conn = _conn()
    row = conn.execute("SELECT COUNT(*) FROM versions_dataset").fetchone()
    conn.close()
    return row[0] if row else 0


# --------------------------------------------------------------------------- #
#  CRUD — Modèles entraînés                                                    #
# --------------------------------------------------------------------------- #

def save_modele(m: ModeleEntraine) -> None:
    conn = _conn()
    conn.execute("""
        INSERT OR REPLACE INTO modeles_entraines
        (id, nom, algorithme, dataset_id, dataset_version, accuracy_train,
         accuracy_val, accuracy_test, chemin_modele, parametres, date_entrainement)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (str(m.id), m.nom, m.algorithme, str(m.dataset_id), m.dataset_version,
          m.accuracy_train, m.accuracy_val, m.accuracy_test,
          m.chemin_modele, m.parametres, _dt(m.date_entrainement)))
    conn.commit()
    conn.close()


def get_all_modeles() -> list[ModeleEntraine]:
    conn = _conn()
    rows = conn.execute(
        "SELECT * FROM modeles_entraines ORDER BY date_entrainement DESC"
    ).fetchall()
    conn.close()
    return [ModeleEntraine(
        id=uuid.UUID(r["id"]),
        nom=r["nom"] or "",
        algorithme=r["algorithme"] or "",
        dataset_id=uuid.UUID(r["dataset_id"]) if r["dataset_id"] else uuid.uuid4(),
        dataset_version=r["dataset_version"] or "",
        accuracy_train=float(r["accuracy_train"]) if r["accuracy_train"] is not None else None,
        accuracy_val=float(r["accuracy_val"])   if r["accuracy_val"]   is not None else None,
        accuracy_test=float(r["accuracy_test"]) if r["accuracy_test"]  is not None else None,
        chemin_modele=r["chemin_modele"],
        parametres=r["parametres"],
        date_entrainement=_parse_dt(r["date_entrainement"]),
    ) for r in rows]


def get_modele(modele_id: uuid.UUID) -> Optional[ModeleEntraine]:
    conn = _conn()
    row = conn.execute(
        "SELECT * FROM modeles_entraines WHERE id = ?", (str(modele_id),)
    ).fetchone()
    conn.close()
    if not row:
        return None
    return ModeleEntraine(
        id=uuid.UUID(row["id"]),
        nom=row["nom"] or "",
        algorithme=row["algorithme"] or "",
        dataset_id=uuid.UUID(row["dataset_id"]) if row["dataset_id"] else uuid.uuid4(),
        dataset_version=row["dataset_version"] or "",
        accuracy_train=float(row["accuracy_train"]) if row["accuracy_train"] is not None else None,
        accuracy_val=float(row["accuracy_val"])   if row["accuracy_val"]   is not None else None,
        accuracy_test=float(row["accuracy_test"]) if row["accuracy_test"]  is not None else None,
        chemin_modele=row["chemin_modele"],
        parametres=row["parametres"],
        date_entrainement=_parse_dt(row["date_entrainement"]),
    )


# --------------------------------------------------------------------------- #
#  CRUD — Logs                                                                 #
# --------------------------------------------------------------------------- #

def add_log(log: LogPipeline) -> None:
    conn = _conn()
    conn.execute("""
        INSERT INTO logs (roman_id, date_log, etape, statut, message)
        VALUES (?, ?, ?, ?, ?)
    """, (str(log.roman_id), _dt(log.date_log), log.etape, log.statut, log.message))
    conn.commit()
    conn.close()


def get_logs_by_roman(roman_id: uuid.UUID, limit: int = 50) -> list[LogPipeline]:
    conn = _conn()
    rows = conn.execute(
        "SELECT * FROM logs WHERE roman_id = ? ORDER BY date_log DESC LIMIT ?",
        (str(roman_id), limit)
    ).fetchall()
    conn.close()
    return [_row_to_log(r) for r in rows]


def get_logs_by_etape(etape: str, limit: int = 30) -> list[LogPipeline]:
    conn = _conn()
    rows = conn.execute(
        "SELECT * FROM logs WHERE etape = ? ORDER BY date_log DESC LIMIT ?",
        (etape, limit)
    ).fetchall()
    conn.close()
    return [_row_to_log(r) for r in rows]


def get_recent_logs(limit: int = 50) -> list[LogPipeline]:
    conn = _conn()
    rows = conn.execute(
        "SELECT * FROM logs ORDER BY date_log DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [_row_to_log(r) for r in rows]


# --------------------------------------------------------------------------- #
#  Init                                                                        #
# --------------------------------------------------------------------------- #

def init_db() -> None:
    from database.db import init_schema
    init_schema()
