import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st
import pandas as pd
from database.models import init_db, get_all_romans, get_logs_by_etape
from pipeline.transformation import transformer_roman
from pipeline.feature_extraction import extraire_features

init_db()

st.set_page_config(page_title="Pipeline — Symphonie des Données", page_icon="⚙️", layout="wide")
st.title("⚙️ Pipeline de traitement")
st.caption("Transformez les livres ingérés pour les préparer à l'entraînement du modèle.")
st.markdown("---")

romans_ingeres     = get_all_romans(statut="ingere")
romans_transformes = get_all_romans(statut="transforme")
tous_romans        = get_all_romans()

# --------------------------------------------------------------------------- #
#  Compteurs globaux                                                           #
# --------------------------------------------------------------------------- #
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total livres",      len(tous_romans))
c2.metric("🟡 À transformer",  len(romans_ingeres))
c3.metric("🟠 À extraire",     len(romans_transformes))
c4.metric("🟢 Prêts",          sum(1 for r in tous_romans if r.statut in ("features_extraites","en_dataset")))

st.markdown("---")

# --------------------------------------------------------------------------- #
#  Étape 1 — Transformation                                                   #
# --------------------------------------------------------------------------- #
st.subheader("Étape 1 — Transformation du texte")
st.caption("Extrait le texte brut, nettoie le contenu et calcule les statistiques (nb mots, phrases, richesse lexicale).")

col_info, col_btn = st.columns([3, 1])
col_info.info(f"{len(romans_ingeres)} livre(s) en attente")

if col_btn.button("Transformer tous", type="primary", disabled=not romans_ingeres, key="transf_tous"):
    bar = st.progress(0)
    res = []
    for i, r in enumerate(romans_ingeres):
        ok, msg = transformer_roman(str(r.id))
        res.append({"Livre": r.titre[:60], "Statut": "✅" if ok else "❌", "Message": msg})
        bar.progress((i+1) / len(romans_ingeres))
    st.dataframe(pd.DataFrame(res), use_container_width=True, hide_index=True)
    st.rerun()

with st.expander("Transformer un livre spécifique"):
    choix = st.selectbox("Livre", [r for r in tous_romans if r.statut == "ingere"],
                         format_func=lambda r: r.titre, key="transf_un")
    if st.button("Transformer", key="btn_transf_un"):
        ok, msg = transformer_roman(str(choix.id))
        (st.success if ok else st.error)(msg)
        st.rerun()

st.markdown("---")

# --------------------------------------------------------------------------- #
#  Étape 2 — Extraction de features                                           #
# --------------------------------------------------------------------------- #
st.subheader("Étape 2 — Extraction de features")
st.caption("Calcule les fréquences TF des mots (après suppression des stopwords) et génère le vecteur de features.")

col_info2, col_btn2 = st.columns([3, 1])
col_info2.info(f"{len(romans_transformes)} livre(s) prêts")

if col_btn2.button("Extraire features de tous", type="primary", disabled=not romans_transformes, key="feat_tous"):
    bar2 = st.progress(0)
    res2 = []
    for i, r in enumerate(romans_transformes):
        ok, msg = extraire_features(str(r.id))
        res2.append({"Livre": r.titre[:60], "Statut": "✅" if ok else "❌", "Message": msg})
        bar2.progress((i+1) / len(romans_transformes))
    st.dataframe(pd.DataFrame(res2), use_container_width=True, hide_index=True)
    st.rerun()

with st.expander("Extraire features d'un livre spécifique"):
    choix2 = st.selectbox("Livre", [r for r in tous_romans if r.statut == "transforme"],
                          format_func=lambda r: r.titre, key="feat_un")
    if st.button("Extraire", key="btn_feat_un"):
        ok, msg = extraire_features(str(choix2.id))
        (st.success if ok else st.error)(msg)
        st.rerun()

st.markdown("---")

# --------------------------------------------------------------------------- #
#  Logs récents                                                                #
# --------------------------------------------------------------------------- #
with st.expander("Logs du pipeline"):
    col_l1, col_l2 = st.columns(2)
    with col_l1:
        st.caption("Transformation")
        for l in get_logs_by_etape("transformation", limit=8):
            ico = "✅" if l.statut == "succès" else "❌"
            st.write(f"{ico} {l.date_log.strftime('%H:%M')} — {l.message}")
    with col_l2:
        st.caption("Extraction features")
        for l in get_logs_by_etape("feature_extraction", limit=8):
            ico = "✅" if l.statut == "succès" else "❌"
            st.write(f"{ico} {l.date_log.strftime('%H:%M')} — {l.message}")
