import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st
import pandas as pd
from database.models import init_db, get_all_romans, get_all_versions
from pipeline.dataset_builder import construire_dataset, charger_manifest

init_db()

st.set_page_config(page_title="Datasets — Symphonie des Données", page_icon="🗂️", layout="wide")
st.title("🗂️ Datasets versionnés")
st.caption("Chaque version est un snapshot immuable (CSV + manifest JSON) des livres prêts à l'entraînement.")
st.markdown("---")

versions  = get_all_versions()
nb_prets  = len(get_all_romans(statut="features_extraites"))

col_new, col_hist = st.columns([1, 2])

# --------------------------------------------------------------------------- #
#  Créer une version                                                           #
# --------------------------------------------------------------------------- #
with col_new:
    st.subheader("Créer une version")
    st.info(f"{nb_prets} livre(s) avec features disponibles")

    with st.form("form_dataset"):
        description = st.text_area("Description", placeholder="Ex : Corpus principal v1")
        split_train = st.slider("Train %", 50, 90, 70) / 100
        split_val   = st.slider("Val %",    5, 30, 15) / 100
        split_test  = round(1.0 - split_train - split_val, 2)
        st.metric("Test %", f"{split_test*100:.0f}%")
        submit = st.form_submit_button("Créer", type="primary", disabled=(nb_prets == 0))

    if submit:
        if split_test < 0.05:
            st.error("La part test doit être ≥ 5%.")
        else:
            with st.spinner("Construction…"):
                ok, msg, version = construire_dataset(description, split_train, split_val, split_test)
            (st.success if ok else st.error)(msg)
            if ok:
                st.rerun()

# --------------------------------------------------------------------------- #
#  Historique                                                                  #
# --------------------------------------------------------------------------- #
with col_hist:
    st.subheader("Historique des versions")
    if not versions:
        st.info("Aucune version créée.")
    else:
        for v in versions:
            with st.expander(f"**{v.version}** — {v.nb_romans} livres — {v.date_creation.strftime('%Y-%m-%d')}"):
                manifest = charger_manifest(v.version)
                if manifest:
                    splits = manifest.get("splits", {})
                    ca, cb, cc, cd = st.columns(4)
                    ca.metric("Total",  v.nb_romans)
                    cb.metric("Train",  splits.get("train", 0))
                    cc.metric("Val",    splits.get("val",   0))
                    cd.metric("Test",   splits.get("test",  0))
                    if v.description:
                        st.caption(v.description)
                    with st.expander("Manifest JSON"):
                        st.json(manifest)

                    csv_path = os.path.join(v.chemin_fichier, "train.csv")
                    if os.path.exists(csv_path):
                        import pandas as pd
                        df = pd.read_csv(csv_path)
                        cols = [c for c in ["titre","auteur","genre","nb_mots"] if c in df.columns]
                        st.dataframe(df[cols].head(10), use_container_width=True, hide_index=True)
                else:
                    st.warning("Manifest introuvable.")
