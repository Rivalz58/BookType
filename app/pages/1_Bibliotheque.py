import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st
import pandas as pd
import json
import plotly.express as px
from database.models import init_db, get_all_romans, get_stats, get_features, get_logs_by_roman
from pipeline.ingestion import ingerer_fichier, supprimer_roman
from config import GENRES

init_db()

st.set_page_config(page_title="Bibliothèque — Symphonie des Données", page_icon="📚", layout="wide")
st.title("📚 Bibliothèque")

tab_liste, tab_detail, tab_upload = st.tabs(["📋 Liste des livres", "🔍 Détail d'un livre", "➕ Ajouter un livre"])

# ============================================================
# TAB 1 — LISTE
# ============================================================
with tab_liste:
    romans = get_all_romans()

    if not romans:
        st.info("Aucun livre dans la base.")
    else:
        # Filtres
        col_f1, col_f2, col_f3 = st.columns(3)
        genres_dispo   = ["Tous"] + sorted(set(r.genre for r in romans))
        statuts_dispo  = ["Tous", "ingere", "transforme", "features_extraites", "en_dataset"]
        filtre_genre   = col_f1.selectbox("Genre", genres_dispo)
        filtre_statut  = col_f2.selectbox("Statut", statuts_dispo)
        filtre_texte   = col_f3.text_input("Recherche titre / auteur")

        romans_filtres = romans
        if filtre_genre  != "Tous":
            romans_filtres = [r for r in romans_filtres if r.genre == filtre_genre]
        if filtre_statut != "Tous":
            romans_filtres = [r for r in romans_filtres if r.statut == filtre_statut]
        if filtre_texte:
            q = filtre_texte.lower()
            romans_filtres = [r for r in romans_filtres
                              if q in r.titre.lower() or q in r.auteur.lower()]

        st.caption(f"{len(romans_filtres)} livre(s) affiché(s) sur {len(romans)}")

        STATUT_ICO = {
            "ingere":             "🟡 ingéré",
            "transforme":         "🟠 transformé",
            "features_extraites": "🟢 features",
            "en_dataset":         "🔵 dataset",
        }

        data = [{
            "ID":      r.id_court,
            "Titre":   r.titre,
            "Auteur":  r.auteur,
            "Genre":   r.genre,
            "Année":   r.annee or "—",
            "Format":  r.format_fichier.upper(),
            "Taille":  f"{r.taille_octets/1024:.0f} Ko" if r.taille_octets else "—",
            "Statut":  STATUT_ICO.get(r.statut, r.statut),
            "Date":    r.date_upload.strftime("%Y-%m-%d"),
        } for r in romans_filtres]

        st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)

        st.markdown("---")
        st.subheader("Supprimer un livre")
        choix_suppr = st.selectbox(
            "Livre à supprimer",
            romans_filtres,
            format_func=lambda r: f"{r.id_court} — {r.titre}",
        )
        if st.button("Supprimer", type="secondary"):
            ok, msg = supprimer_roman(str(choix_suppr.id))
            (st.success if ok else st.error)(msg)
            if ok:
                st.rerun()

# ============================================================
# TAB 2 — DÉTAIL PAR LIVRE
# ============================================================
with tab_detail:
    romans = get_all_romans()
    if not romans:
        st.info("Aucun livre dans la base.")
    else:
        livre = st.selectbox(
            "Choisir un livre",
            romans,
            format_func=lambda r: f"{r.titre} — {r.auteur} ({r.genre})",
            key="detail_livre",
        )

        if livre:
            col_info, col_stats = st.columns([1, 2])

            with col_info:
                st.subheader(livre.titre)
                st.markdown(f"**Auteur :** {livre.auteur}")
                st.markdown(f"**Genre :** `{livre.genre}`")
                st.markdown(f"**Année :** {livre.annee or '—'}")
                st.markdown(f"**Langue :** {livre.langue}")
                st.markdown(f"**Format :** {livre.format_fichier.upper()}")
                st.markdown(f"**Taille :** {livre.taille_octets/1024:.0f} Ko" if livre.taille_octets else "**Taille :** —")
                if livre.source:
                    st.markdown(f"**Source :** {livre.source}")

                STATUT_COLOR = {
                    "ingere":             "🟡",
                    "transforme":         "🟠",
                    "features_extraites": "🟢",
                    "en_dataset":         "🔵",
                }
                st.markdown(f"**Statut :** {STATUT_COLOR.get(livre.statut,'')} `{livre.statut}`")

            with col_stats:
                s = get_stats(livre.id)
                if s:
                    st.subheader("Statistiques textuelles")
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Mots",          f"{s.nb_mots:,}")
                    c2.metric("Phrases",       f"{s.nb_phrases:,}")
                    c3.metric("Paragraphes",   f"{s.nb_paragraphes:,}")
                    c4, c5, c6 = st.columns(3)
                    c4.metric("Vocab. unique", f"{s.vocabulaire_unique:,}")
                    c5.metric("Richesse lex.", f"{s.richesse_lexicale:.3f}")
                    c6.metric("Moy. phrase",   f"{s.longueur_moy_phrase:.1f} mots")
                else:
                    st.info("Pas encore transformé — lancez le pipeline pour voir les stats.")

            # Top mots
            feat = get_features(livre.id)
            if feat and feat.top_mots:
                st.markdown("---")
                st.subheader("Mots les plus représentatifs")
                top_mots = json.loads(feat.top_mots)
                top30 = dict(list(top_mots.items())[:30])
                fig = px.bar(
                    x=list(top30.values()),
                    y=list(top30.keys()),
                    orientation="h",
                    labels={"x": "Score TF", "y": "Mot"},
                    color=list(top30.values()),
                    color_continuous_scale="Blues",
                )
                fig.update_layout(
                    yaxis={"autorange": "reversed"},
                    height=600,
                    showlegend=False,
                    coloraxis_showscale=False,
                )
                st.plotly_chart(fig, use_container_width=True)

            # Logs
            logs = get_logs_by_roman(livre.id, limit=10)
            if logs:
                st.markdown("---")
                st.subheader("Historique")
                for l in logs:
                    ico = "✅" if l.statut == "succès" else "❌"
                    st.caption(f"{ico} {l.date_log.strftime('%Y-%m-%d %H:%M')} — [{l.etape}] {l.message}")

# ============================================================
# TAB 3 — UPLOAD
# ============================================================
with tab_upload:
    st.subheader("Ajouter un livre")
    with st.form("form_upload", clear_on_submit=True):
        fichier = st.file_uploader("Fichier (TXT, PDF, EPUB)", type=["txt", "pdf", "epub"])

        col1, col2 = st.columns(2)
        titre  = col1.text_input("Titre *")
        auteur = col2.text_input("Auteur")

        col3, col4, col5 = st.columns(3)
        genre  = col3.selectbox("Genre", GENRES)
        annee  = col4.number_input("Année", min_value=0, max_value=2100, value=0, step=1)
        langue = col5.selectbox("Langue", ["français", "anglais", "espagnol", "autre"])

        source    = st.text_input("Source / URL")
        submitted = st.form_submit_button("Uploader", type="primary")

    if submitted:
        if not fichier:
            st.error("Sélectionnez un fichier.")
        elif not titre.strip():
            st.error("Le titre est obligatoire.")
        else:
            with st.spinner("Ingestion en cours…"):
                ok, msg, _ = ingerer_fichier(
                    contenu_bytes=fichier.read(),
                    nom_fichier=fichier.name,
                    titre=titre.strip(),
                    auteur=auteur.strip() or "Inconnu",
                    genre=genre,
                    annee=int(annee) if annee else None,
                    langue=langue,
                    source=source.strip() or None,
                )
            (st.success if ok else st.error)(msg)
