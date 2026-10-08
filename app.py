import streamlit as st
import math
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="EBM Gestion", layout="centered")
st.title("EBM-CREATION : Gestion & Chiffrage")

# Initialisation d'un historique de session (pour stocker les ventes en compta)
if "historique" not in st.session_state:
    st.session_state.historique = []

# Création des deux onglets
tab_calcul, tab_compta = st.tabs(["🧮 Calculateur", "📊 Comptabilité"])

# ==========================================
# ONGLET 1 : CALCULATEUR
# ==========================================
with tab_calcul:
    # Paramètres de l'entreprise
    st.sidebar.header("Paramètres (Micro-entreprise)")
    taux_horaire = st.sidebar.number_input("Taux horaire MO (€/h)", value=25.0, step=5.0)
    cout_machine_heure = st.sidebar.number_input("Frais machine (€/h)", value=3.0, step=0.5)
    taux_urssaf = st.sidebar.slider("Charges URSSAF (%)", 0.0, 25.0, 12.3) 
    marge_souhaitee = st.sidebar.slider("Marge bénéficiaire nette (%)", 0, 100, 30)

    st.header("Nouveau Projet")
    materiau = st.selectbox("Support", ["Verre / Miroir", "Bois", "Acrylique", "Impression 3D"])

    col1, col2 = st.columns(2)
    with col1:
        prix_achat = st.number_input("Prix d'achat du support (€)", value=10.0, step=1.0)
        conso_extra = st.number_input("Consommables (€)", value=1.5, step=0.5)
    with col2:
        temps_prepa = st.number_input("Temps de préparation (min)", value=15, step=5)
        temps_gravure = st.number_input("Temps machine (min)", value=20, step=5)

    # Calculs
    cout_matiere = prix_achat + conso_extra
    cout_main_oeuvre = (temps_prepa / 60) * taux_horaire
    cout_utilisation_machine = (temps_gravure / 60) * cout_machine_heure
    cout_de_revient = cout_matiere + cout_main_oeuvre + cout_utilisation_machine

    facteur = 1 - ((taux_urssaf + marge_souhaitee) / 100)
    prix_vente_exact = cout_de_revient / facteur if facteur > 0 else 0
    
    # Arrondi à l'euro supérieur (ex: 44.12 € -> 45.00 €)
    prix_vente = math.ceil(prix_vente_exact)
    
    # Calcul des parts réelles après arrondi
    montant_urssaf = prix_vente * (taux_urssaf / 100)
    benef_net = prix_vente - cout_de_revient - montant_urssaf

    st.divider()
    st.subheader(f"🏷️ Prix de vente conseillé : {prix_vente} €")
    st.write(f"*(Coût de revient sec : {cout_de_revient:.2f} €)*")
    
    # Bouton pour envoyer vers la compta
    if st.button("✅ Valider et ajouter à la comptabilité"):
        st.session_state.historique.append({
            "Date": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "Projet": materiau,
            "CA (€)": prix_vente,
            "Coût (€)": round(cout_de_revient, 2),
            "URSSAF (€)": round(montant_urssaf, 2),
            "Bénéfice (€)": round(benef_net, 2)
        })
        st.success("Projet enregistré ! Va dans l'onglet Comptabilité pour voir le résumé.")

# ==========================================
# ONGLET 2 : COMPTABILITÉ
# ==========================================
with tab_compta:
    st.header("📊 Suivi Comptable EBM-CREATION")
    
    if len(st.session_state.historique) > 0:
        # Transformation des données en tableau (DataFrame Pandas)
        df = pd.DataFrame(st.session_state.historique)
        
        # Affichage des métriques globales
        ca_total = df["CA (€)"].sum()
        urssaf_total = df["URSSAF (€)"].sum()
        benef_total = df["Bénéfice (€)"].sum()
        
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("Chiffre d'Affaires", f"{ca_total:.2f} €")
        col_b.metric("Provision URSSAF", f"{urssaf_total:.2f} €")
        col_c.metric("Bénéfice Net Total", f"{benef_total:.2f} €")
        
        st.divider()
        st.subheader("Livre des recettes (Session en cours)")
        st.dataframe(df, use_container_width=True)
        
        st.info("⚠️ Note : Ces données restent en mémoire tant que l'onglet du navigateur est ouvert. Si tu rafraîchis la page, le tableau repartira à zéro.")
        
        if st.button("🗑️ Vider l'historique comptable"):
            st.session_state.historique = []
            st.rerun()
    else:
        st.info("Aucune vente enregistrée. Calcule et valide un projet dans l'onglet 🧮 Calculateur pour alimenter ta comptabilité.")
