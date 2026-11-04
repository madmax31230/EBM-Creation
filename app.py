import streamlit as st
import math
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="EBM Gestion", layout="centered")
st.title("EBM-CREATION : Gestion & Chiffrage")

# --- DONNÉES TRANSPORTEURS ---
TARIFS_TRANSPORTEURS = {
    "Mondial Relay (Point Relais)": {
        "max_l_w_h_cm": 150, 
        "max_length_cm": 120, 
        "grille": [(0.25, 4.15), (0.5, 4.15), (1.0, 5.99), (2.0, 7.99), (5.0, 15.99)]
    },
    "Colissimo (Point Retrait)": {
        "max_l_w_h_cm": 150, 
        "max_length_cm": 100,
        "grille": [(0.25, 4.79), (0.5, 6.89), (1.0, 8.89), (2.0, 10.49), (5.0, 16.69)]
    },
    "Colissimo (Domicile)": {
        "max_l_w_h_cm": 150, 
        "max_length_cm": 100,
        "grille": [(0.25, 5.49), (0.5, 7.59), (1.0, 9.59), (2.0, 11.19), (5.0, 17.39)]
    }
}

def obtenir_tarif_transporteur(transporteur, poids_kg, l, w, h):
    infos = TARIFS_TRANSPORTEURS[transporteur]
    if (l + w + h) > infos["max_l_w_h_cm"] or max(l, w, h) > infos["max_length_cm"]:
        return None, "Gabarit dépassé"
    for poids_max, prix in infos["grille"]:
        if poids_kg <= poids_max:
            return prix, "OK"
    return None, "Poids > 5 kg"

# --- INITIALISATION SESSION ---
if "historique" not in st.session_state:
    st.session_state.historique = []

# --- INTERFACE ---
tab_calcul, tab_compta = st.tabs(["🧮 Calculateur", "📊 Comptabilité"])

with tab_calcul:
    st.sidebar.header("Paramètres (Micro-entreprise)")
    taux_horaire = st.sidebar.number_input("Taux horaire MO (€/h)", value=25.0, step=5.0)
    cout_machine_heure = st.sidebar.number_input("Frais machine (€/h)", value=3.0, step=0.5)
    taux_urssaf = st.sidebar.slider("Charges URSSAF (%)", 0.0, 25.0, 12.3) 
    marge_souhaitee = st.sidebar.slider("Marge bénéficiaire nette (%)", 0, 100, 30)

    st.header("1. Création / Produit")
    materiau = st.selectbox("Support", ["Verre / Miroir", "Bois", "Acrylique", "Impression 3D"])

    col1, col2 = st.columns(2)
    with col1:
        prix_achat = st.number_input("Prix d'achat du support (€)", value=10.0, step=1.0)
        conso_extra = st.number_input("Consommables (€)", value=1.5, step=0.5)
    with col2:
        temps_prepa = st.number_input("Temps de préparation (min)", value=15, step=5)
        temps_gravure = st.number_input("Temps machine (min)", value=20, step=5)

    # Calcul Produit
    cout_matiere = prix_achat + conso_extra
    cout_main_oeuvre = (temps_prepa / 60) * taux_horaire
    cout_utilisation_machine = (temps_gravure / 60) * cout_machine_heure
    cout_de_revient_produit = cout_matiere + cout_main_oeuvre + cout_utilisation_machine

    facteur = 1 - ((taux_urssaf + marge_souhaitee) / 100)
    prix_vente_produit_exact = cout_de_revient_produit / facteur if facteur > 0 else 0
    prix_vente_produit = math.ceil(prix_vente_produit_exact)

    st.divider()
    st.header("2. Expédition & Paiement")
    
    livraison = st.toggle("📦 Ajouter une expédition")
    tarif_transporteur = 0.0
    cout_emballage = 0.0
    statut_livraison = "Non"
    
    if livraison:
        col_dim, col_poids, col_trans = st.columns(3)
        with col_dim:
            l = st.number_input("L (cm)", value=20)
            w = st.number_input("l (cm)", value=15)
            h = st.number_input("h (cm)", value=10)
        with col_poids:
            poids = st.number_input("Poids (kg)", value=0.45, step=0.1)
            cout_emballage = st.number_input("Carton/Calage (€)", value=1.20, step=0.10)
        with col_trans:
            choix_transporteur = st.selectbox("Réseau", list(TARIFS_TRANSPORTEURS.keys()))
        
        tarif_brut, statut = obtenir_tarif_transporteur(choix_transporteur, poids, l, w, h)
        if tarif_brut is not None:
            tarif_transporteur = tarif_brut
            st.caption(f"✅ Tarif d'affranchissement trouvé : {tarif_transporteur} €")
            statut_livraison = choix_transporteur
        else:
            st.error(f"⚠️ {statut}")

    paiement_stripe = st.toggle("💳 Paiement via Stripe (absorption des frais)")

    # --- CALCULS FINAUX ---
    montant_cible_net = prix_vente_produit + tarif_transporteur + cout_emballage
    
    if paiement_stripe:
        # Formule inverse : (Cible + Frais Fixes) / (1 - Pourcentage)
        prix_final_client = (montant_cible_net + 0.25) / (1 - 0.015)
        frais_bancaires = prix_final_client - montant_cible_net
    else:
        prix_final_client = montant_cible_net
        frais_bancaires = 0.0

    prix_final_client = round(prix_final_client, 2)
    
    # Calculs Compta
    cout_total = cout_de_revient_produit + tarif_transporteur + cout_emballage + frais_bancaires
    montant_urssaf = prix_final_client * (taux_urssaf / 100)
    benef_net = prix_final_client - cout_total - montant_urssaf

    st.divider()
    st.subheader(f"🏷️ Total à facturer au client : {prix_final_client} €")
    if livraison:
        st.write(f"*(Inclut {tarif_transporteur + cout_emballage:.2f} € de logistique)*")
    if paiement_stripe:
        st.write(f"*(Inclut {frais_bancaires:.2f} € de frais Stripe)*")

    if st.button("✅ Valider et ajouter à la comptabilité"):
        st.session_state.historique.append({
            "Date": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "Projet": materiau,
            "Livraison": statut_livraison,
            "CA (€)": prix_final_client,
            "Coûts (€)": round(cout_total, 2),
            "URSSAF (€)": round(montant_urssaf, 2),
            "Bénéfice (€)": round(benef_net, 2)
        })
        st.success("Projet enregistré ! Va dans l'onglet Comptabilité.")

with tab_compta:
    st.header("📊 Suivi Comptable EBM-CREATION")
    
    if len(st.session_state.historique) > 0:
        df = pd.DataFrame(st.session_state.historique)
        
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
        
        st.info("⚠️ Note : Ces données restent en mémoire tant que l'onglet du navigateur est ouvert.")
        
        if st.button("🗑️ Vider l'historique comptable"):
            st.session_state.historique = []
            st.rerun()
    else:
        st.info("Aucune vente enregistrée. Calcule et valide un projet dans l'onglet 🧮 Calculateur.")
