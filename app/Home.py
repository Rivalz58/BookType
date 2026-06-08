import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from database.models import init_db, get_all_romans, get_all_versions, get_all_modeles

st.set_page_config(
    page_title="Symphonie des Données",
    page_icon="📚",
    layout="wide",
)

try:
    init_db()
    db_ok = True
except Exception as e:
    db_ok = False
    db_err = str(e)

st.title("📚 Symphonie des Données")
st.caption("Plateforme de gestion de corpus littéraires pour l'IA — Master 1 Intelligence Artificielle")

if not db_ok:
    st.error(f"Initialisation de la base de données impossible : {db_err}")
    st.stop()

romans   = get_all_romans()
versions = get_all_versions()
modeles  = get_all_modeles()

nb_transformes       = sum(1 for r in romans if r.statut != "ingere")
nb_features_extraites = sum(1 for r in romans if r.statut in ("features_extraites", "en_dataset"))
nb_en_dataset        = sum(1 for r in romans if r.statut == "en_dataset")

st.markdown("---")
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("📖 Livres",          len(romans))
col2.metric("⚙️ Transformés",     nb_transformes)
col3.metric("🔬 Features",        nb_features_extraites)
col4.metric("🗂️ Datasets",        len(versions))
col5.metric("🤖 Modèles",         len(modeles))

st.markdown("---")

col_a, col_b = st.columns(2)

with col_a:
    st.subheader("Navigation")
    st.markdown("""
| Page | Description |
|------|-------------|
| 📚 **Bibliothèque** | Consulter les livres, voir les stats par livre |
| ⚙️ **Pipeline** | Transformer et extraire les features |
| 🗂️ **Datasets** | Créer et versionner les datasets |
| 🤖 **Modèle** | Entraîner et tester le classificateur |
| 📊 **Dashboard** | Visualiser les données et performances |
""")

with col_b:
    st.subheader("État du pipeline")
    total = len(romans)
    if total > 0:
        import plotly.graph_objects as go
        etapes = ["Ingérés", "Transformés", "Features", "En dataset"]
        valeurs = [
            total,
            nb_transformes,
            nb_features_extraites,
            nb_en_dataset,
        ]
        fig = go.Figure(go.Funnel(
            y=etapes, x=valeurs,
            textinfo="value+percent initial",
            marker_color=["#3498db", "#e67e22", "#2ecc71", "#9b59b6"],
        ))
        fig.update_layout(height=250, margin=dict(t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Aucun livre dans la base. Commencez par la page Bibliothèque.")
