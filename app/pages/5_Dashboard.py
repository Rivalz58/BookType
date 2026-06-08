import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from database.models import init_db, get_all_romans, get_all_versions, get_all_modeles, get_recent_logs, get_stats

init_db()

st.set_page_config(page_title="Dashboard — Symphonie des Données", page_icon="📊", layout="wide")
st.title("📊 Dashboard de supervision")
st.caption("Visualisation du cycle de vie des données.")
st.markdown("---")

romans   = get_all_romans()
versions = get_all_versions()
modeles  = get_all_modeles()
logs     = get_recent_logs(limit=30)

if not romans:
    st.info("Aucune donnée disponible.")
    st.stop()

# --------------------------------------------------------------------------- #
#  KPIs                                                                        #
# --------------------------------------------------------------------------- #
statuts = {}
for r in romans:
    statuts[r.statut] = statuts.get(r.statut, 0) + 1

c1,c2,c3,c4,c5 = st.columns(5)
c1.metric("Total",            len(romans))
c2.metric("🟡 Ingérés",       statuts.get("ingere",0))
c3.metric("🟠 Transformés",   statuts.get("transforme",0))
c4.metric("🟢 Features",      statuts.get("features_extraites",0))
c5.metric("🔵 En dataset",    statuts.get("en_dataset",0))

st.markdown("---")

tab_corpus, tab_stats, tab_modeles, tab_logs = st.tabs(
    ["📚 Corpus", "📈 Statistiques textuelles", "🤖 Modèles", "📋 Logs"]
)

# ============================================================
#  TAB 1 — CORPUS
# ============================================================
with tab_corpus:
    df = pd.DataFrame([{
        "genre":  r.genre,
        "langue": r.langue,
        "statut": r.statut,
        "annee":  r.annee,
        "taille": (r.taille_octets or 0) / 1024,
        "date":   r.date_upload,
    } for r in romans])

    col_a, col_b = st.columns(2)

    with col_a:
        # Entonnoir
        etapes = ["ingere","transforme","features_extraites","en_dataset"]
        labels = ["1. Ingéré","2. Transformé","3. Features","4. En dataset"]
        cumuls = [sum(statuts.get(e,0) for e in etapes[i:]) for i in range(len(etapes))]
        fig = go.Figure(go.Funnel(
            y=labels, x=cumuls,
            textinfo="value+percent initial",
            marker_color=["#3498db","#e67e22","#2ecc71","#9b59b6"],
        ))
        fig.update_layout(title="Entonnoir du pipeline", height=320)
        st.plotly_chart(fig, use_container_width=True)

    with col_b:
        # Répartition par genre
        genre_counts = df["genre"].value_counts().reset_index()
        genre_counts.columns = ["genre","count"]
        fig2 = px.bar(genre_counts, x="count", y="genre", orientation="h",
                      title="Livres par genre", color="count",
                      color_continuous_scale="Blues", labels={"count":"Livres","genre":"Genre"})
        fig2.update_layout(height=320, coloraxis_showscale=False, yaxis={"autorange":"reversed"})
        st.plotly_chart(fig2, use_container_width=True)

    # Croissance du corpus
    df_time = df.sort_values("date").reset_index(drop=True)
    df_time["cumul"] = range(1, len(df_time)+1)
    fig3 = px.area(df_time, x="date", y="cumul",
                   title="Croissance du corpus dans le temps",
                   labels={"date":"Date","cumul":"Livres cumulés"})
    st.plotly_chart(fig3, use_container_width=True)

# ============================================================
#  TAB 2 — STATISTIQUES TEXTUELLES
# ============================================================
with tab_stats:
    romans_avec_stats = [r for r in romans if r.statut in ("transforme","features_extraites","en_dataset")]

    if not romans_avec_stats:
        st.info("Lancez le pipeline pour voir les statistiques textuelles.")
    else:
        stats_rows = []
        for r in romans_avec_stats:
            s = get_stats(r.id)
            if s:
                stats_rows.append({
                    "titre":   r.titre,
                    "genre":   r.genre,
                    "nb_mots": s.nb_mots,
                    "richesse": s.richesse_lexicale,
                    "long_phrase": s.longueur_moy_phrase,
                })
        df_s = pd.DataFrame(stats_rows)

        col_s1, col_s2 = st.columns(2)
        with col_s1:
            fig = px.histogram(df_s, x="nb_mots", nbins=30,
                               title="Distribution du nombre de mots",
                               color_discrete_sequence=["#3498db"])
            st.plotly_chart(fig, use_container_width=True)
        with col_s2:
            fig = px.scatter(df_s, x="nb_mots", y="richesse", color="genre",
                             hover_data=["titre"],
                             title="Richesse lexicale vs Nombre de mots",
                             labels={"nb_mots":"Mots","richesse":"Richesse lexicale"})
            st.plotly_chart(fig, use_container_width=True)

        agg = df_s.groupby("genre").agg(
            Livres=("titre","count"),
            Mots_moy=("nb_mots","mean"),
            Richesse_moy=("richesse","mean"),
            Phrase_moy=("long_phrase","mean"),
        ).round(2).reset_index()
        agg.columns = ["Genre","Livres","Mots moy.","Richesse moy.","Phrase moy."]
        st.dataframe(agg, use_container_width=True, hide_index=True)

# ============================================================
#  TAB 3 — MODÈLES
# ============================================================
with tab_modeles:
    if not modeles:
        st.info("Aucun modèle entraîné.")
    else:
        if versions:
            df_ver = pd.DataFrame([{"Version":v.version,"Livres":v.nb_romans,
                                    "Date":v.date_creation.strftime("%Y-%m-%d")} for v in versions])
            fig = px.bar(df_ver, x="Version", y="Livres", color="Version",
                         title="Livres par version de dataset")
            st.plotly_chart(fig, use_container_width=True)

        df_mod = pd.DataFrame([{
            "Modèle": m["nom"], "Train": m["acc_train"] or 0,
            "Val":    m["acc_val"]   or 0, "Test": m["acc_test"] or 0,
        } for m in modeles])
        df_melt = df_mod.melt(id_vars="Modèle", var_name="Split", value_name="Accuracy")
        fig = px.bar(df_melt, x="Modèle", y="Accuracy", color="Split", barmode="group",
                     title="Accuracy par modèle",
                     color_discrete_map={"Train":"#3498db","Val":"#e67e22","Test":"#2ecc71"})
        fig.update_layout(yaxis_tickformat=".0%", yaxis_range=[0,1])
        st.plotly_chart(fig, use_container_width=True)

# ============================================================
#  TAB 4 — LOGS
# ============================================================
with tab_logs:
    if not logs:
        st.info("Aucun log disponible.")
    else:
        df_logs = pd.DataFrame([{
            "Date":    l.date_log.strftime("%Y-%m-%d %H:%M:%S"),
            "Roman":   str(l.roman_id)[:8],
            "Étape":   l.etape,
            "Statut":  "✅" if l.statut == "succès" else "❌",
            "Message": l.message,
        } for l in logs])
        st.dataframe(df_logs, use_container_width=True, hide_index=True)
