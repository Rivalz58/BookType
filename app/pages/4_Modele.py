import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st
import pandas as pd
import json
import plotly.express as px
import plotly.graph_objects as go
from database.models import init_db, get_all_romans, get_all_versions
from models.trainer import entrainer_modele, lister_modeles, predire

init_db()

st.set_page_config(page_title="Modèle IA — Symphonie des Données", page_icon="🤖", layout="wide")
st.title("🤖 Modèle IA")
st.caption("Classification de genre littéraire et recommandation de livres similaires.")
st.caption("Entraîne un classificateur TF-IDF + Régression Logistique / SVM sur un dataset versionné.")
st.markdown("---")

tab_train, tab_modeles, tab_predict, tab_reco = st.tabs([
    "🏋️ Entraînement", "📊 Modèles entraînés", "🔮 Prédiction genre", "📖 Recommandation"
])

# ============================================================
#  TAB 1 — ENTRAÎNEMENT
# ============================================================
with tab_train:
    versions = get_all_versions()
    if not versions:
        st.warning("Créez d'abord un dataset (page Datasets).")
    else:
        col_form, col_info = st.columns([1, 1])

        with col_form:
            st.subheader("Lancer un entraînement")
            with st.form("form_modele"):
                version_choisie = st.selectbox(
                    "Dataset",
                    [v.version for v in versions],
                    format_func=lambda v: f"{v} — {next(x.nb_romans for x in versions if x.version==v)} livres",
                )
                algo = st.radio("Algorithme", ["logistic_regression", "svm"], horizontal=True)
                submit = st.form_submit_button("Lancer l'entraînement", type="primary")

            if submit:
                with st.spinner("Entraînement en cours…"):
                    ok, msg, modele_id = entrainer_modele(version_choisie, algo)
                (st.success if ok else st.error)(("✅ " if ok else "❌ ") + msg)
                if ok:
                    st.rerun()

        with col_info:
            st.subheader("Comment ça fonctionne ?")
            st.markdown("""
1. Les textes du dataset sont chargés
2. **TF-IDF** vectorise chaque texte (10 000 features, bigrammes)
3. Le classificateur apprend à associer les features au genre
4. Les métriques sont calculées sur train / val / test
""")

# ============================================================
#  TAB 2 — MODÈLES ENTRAÎNÉS
# ============================================================
with tab_modeles:
    modeles = lister_modeles()
    if not modeles:
        st.info("Aucun modèle entraîné pour l'instant.")
    else:
        df_m = pd.DataFrame(modeles)[["nom","algo","dataset","acc_train","acc_val","acc_test","date"]]
        df_m.columns = ["Nom","Algo","Dataset","Train","Val","Test","Date"]
        for col in ["Train","Val","Test"]:
            df_m[col] = df_m[col].apply(lambda x: f"{x:.1%}" if x is not None else "—")
        st.dataframe(df_m, use_container_width=True, hide_index=True)

        st.markdown("---")
        fig = go.Figure()
        for m in modeles:
            fig.add_trace(go.Bar(
                name=m["nom"],
                x=["Train","Val","Test"],
                y=[m["acc_train"] or 0, m["acc_val"] or 0, m["acc_test"] or 0],
            ))
        fig.update_layout(
            barmode="group",
            yaxis_tickformat=".0%",
            yaxis_range=[0,1],
            title="Comparaison des performances",
            height=400,
        )
        st.plotly_chart(fig, use_container_width=True)

# ============================================================
#  TAB 3 — PRÉDICTION
# ============================================================
with tab_predict:
    modeles = lister_modeles()
    romans_dispo = [r for r in get_all_romans()
                    if r.statut in ("transforme","features_extraites","en_dataset")]

    if not modeles:
        st.info("Entraînez d'abord un modèle.")
    elif not romans_dispo:
        st.info("Aucun livre transformé disponible.")
    else:
        col_r, col_m = st.columns(2)
        roman_choisi  = col_r.selectbox("Livre à classer", romans_dispo,
                                        format_func=lambda r: f"{r.titre} ({r.genre})",
                                        key="pred_roman")
        modele_choisi = col_m.selectbox("Modèle", modeles,
                                        format_func=lambda m: f"{m['nom']} ({m['algo']})",
                                        key="pred_modele")

        if st.button("Prédire le genre", type="primary"):
            ok, resultat = predire(str(roman_choisi.id), modele_choisi["id"])
            if ok:
                data = json.loads(resultat)
                pred  = data.get("prediction","?")
                proba = data.get("probabilites")

                col_pred, col_reel = st.columns(2)
                col_pred.metric("Genre prédit", pred)
                col_reel.metric("Genre réel",   roman_choisi.genre)

                if pred == roman_choisi.genre:
                    st.success("Prédiction correcte !")
                    st.balloons()
                else:
                    st.warning("Prédiction incorrecte.")

                if proba:
                    proba_sorted = dict(sorted(proba.items(), key=lambda x: -x[1])[:10])
                    fig = px.bar(
                        x=list(proba_sorted.values()),
                        y=list(proba_sorted.keys()),
                        orientation="h",
                        labels={"x":"Probabilité","y":"Genre"},
                        color=list(proba_sorted.values()),
                        color_continuous_scale="Greens",
                    )
                    fig.update_layout(
                        yaxis={"autorange":"reversed"},
                        xaxis_tickformat=".0%",
                        height=400,
                        showlegend=False,
                        coloraxis_showscale=False,
                    )
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.error(resultat)

# ============================================================
#  TAB 4 — RECOMMANDATION
# ============================================================
with tab_reco:
    st.subheader("Recommandation de livres similaires")
    st.caption("Trouve les livres les plus proches par similarité de contenu (cosinus sur vecteurs TF-IDF).")

    romans_dispo = [r for r in get_all_romans()
                    if r.statut in ("transforme", "features_extraites", "en_dataset")]

    if len(romans_dispo) < 2:
        st.info("Il faut au moins 2 livres transformés pour générer des recommandations.")
    else:
        col_r, col_n = st.columns([3, 1])
        livre_cible = col_r.selectbox(
            "Choisir un livre",
            romans_dispo,
            format_func=lambda r: f"{r.titre} — {r.auteur} ({r.genre})",
            key="reco_livre",
        )
        nb_reco = col_n.slider("Nombre de recommandations", 3, 20, 10)

        if st.button("Trouver des livres similaires", type="primary"):
            with st.spinner("Calcul des similarités en cours…"):
                from models.recommender import recommander
                resultats = recommander(str(livre_cible.id), n=nb_reco)

            if not resultats:
                st.warning("Impossible de calculer les recommandations. Vérifiez que les textes sont transformés.")
            else:
                st.markdown(f"**Livres similaires à :** *{livre_cible.titre}* ({livre_cible.genre})")
                st.markdown("---")

                # Tableau des résultats
                df_reco = pd.DataFrame([{
                    "Titre":       r.titre,
                    "Auteur":      r.auteur,
                    "Genre":       r.genre,
                    "Année":       r.annee or "—",
                    "Similarité":  f"{score:.1%}",
                } for r, score in resultats])
                st.dataframe(df_reco, use_container_width=True, hide_index=True)

                # Graphique
                fig = px.bar(
                    x=[score for _, score in resultats],
                    y=[r.titre[:40] for r, _ in resultats],
                    orientation="h",
                    labels={"x": "Similarité", "y": "Livre"},
                    color=[score for _, score in resultats],
                    color_continuous_scale="Blues",
                    title=f"Similarité avec « {livre_cible.titre[:40]} »",
                )
                fig.update_layout(
                    yaxis={"autorange": "reversed"},
                    xaxis_tickformat=".0%",
                    height=max(300, nb_reco * 35),
                    coloraxis_showscale=False,
                )
                st.plotly_chart(fig, use_container_width=True)
