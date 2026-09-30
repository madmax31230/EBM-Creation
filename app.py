import streamlit as st
import math

# Dictionnaire des réglages validés en atelier
MATERIAUX_LASER = {
    "carton": {
        "nom": "Carton ondulé", "vitesse": "800 - 1000", "puissance": "60% - 70%", 
        "mode": "M3 (Ligne Centrale)", "air_assist": "MAX", "focale": "Cran 'Cutting'"
    },
    "verre_sable": {
        "nom": "Verre transparent (Sablage)", "vitesse": "1000 - 1200", "puissance": "70% - 85%", 
        "mode": "M4", "air_assist": "OFF", "focale": "Cran 1 + Peinture noire"
    },
    "miroir_dos": {
        "nom": "Miroir (par le dos)", "vitesse": "1500 - 2000", "puissance": "40% - 50%", 
        "mode": "M4 (1bit Pointillisme)", "air_assist": "OUI", "focale": "Cran 1 + Négatif + Symétrie"
    },
    "marbre": {
        "nom": "Marbre (Plaque)", "vitesse": "1000 - 1500", "puissance": "80% - 100%", 
        "mode": "M4", "air_assist": "OUI", "focale": "Cran 1 (Peinture si marbre clair)"
    }
}

# Configuration de la page
st.set_page_config(page_title="EBM-CREATION - Devis & Atelier")
st.title("Gestion de Production EBM-CREATION")

# Création des onglets
tab_devis, tab_atelier = st.tabs(["💰 Devis & Tarification", "🛠️ Fiche Atelier Laser"])

# --- ONGLET 1 : DEVIS ---
with tab_devis:
    st.header("Calculateur de Prix de Vente")
    
    # Saisie des valeurs (avec des valeurs par défaut)
    cout_de_revient = st.number_input("Coût de revient matière (€)", min_value=0.0, value=15.50)
    taux_urssaf = st.number_input("Taux URSSAF (%)", min_value=0.0, value=21.2)
    marge_souhaitee = st.number_input("Marge nette souhaitée (%)", min_value=0.0, value=40.0)
    
    # Ton code de calcul exact
    facteur = 1 - ((taux_urssaf + marge_souhaitee) / 100)
    prix_vente_exact = cout_de_revient / facteur if facteur > 0 else 0
    prix_vente = math.ceil(prix_vente_exact)
    
    st.success(f"Prix de vente recommandé : **{prix_vente}.00 €**")

# --- ONGLET 2 : ATELIER ---
with tab_atelier:
    st.header("Paramètres Creality Falcon2 22W")
    
    choix_mat = st.selectbox(
        "Sélectionner un matériau en production :", 
        options=list(MATERIAUX_LASER.keys()),
        format_func=lambda x: MATERIAUX_LASER[x]["nom"]
    )
    
    if choix_mat:
        consignes = MATERIAUX_LASER[choix_mat]
        st.write("---")
        st.markdown(f"**Vitesse :** {consignes['vitesse']} mm/min")
        st.markdown(f"**Puissance (S-MAX) :** {consignes['puissance']}")
        st.markdown(f"**Mode :** {consignes['mode']}")
        st.markdown(f"**Air Assist :** {consignes['air_assist']}")
        st.markdown(f"**Focale & Astuces :** {consignes['focale']}")
