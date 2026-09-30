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

st.set_page_config(page_title="EBM-CREATION - Production", layout="wide")
st.title("Gestion de Production EBM-CREATION")

# Inversion des onglets : Atelier en premier, Devis en second
tab_atelier, tab_devis = st.tabs(["🛠️ Fiche Atelier Laser", "💰 Devis & Tarification"])

# --- ONGLET 1 : ATELIER ---
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
        col_A, col_B = st.columns(2)
        with col_A:
            st.markdown(f"**Vitesse :** {consignes['vitesse']} mm/min")
            st.markdown(f"**Puissance (S-MAX) :** {consignes['puissance']}")
            st.markdown(f"**Mode :** {consignes['mode']}")
        with col_B:
            st.markdown(f"**Air Assist :** {consignes['air_assist']}")
            st.markdown(f"**Focale & Astuces :** {consignes['focale']}")

# --- ONGLET 2 : DEVIS ---
with tab_devis:
    st.header("Calculateur de Prix de Vente Détaillé")
    
    # Séparation en deux colonnes pour une meilleure lisibilité
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Données d'entrée")
        cout_de_revient = st.number_input("Coût de revient matière (€)", min_value=0.0, value=15.50, step=0.50)
        taux_urssaf = st.number_input("Taux URSSAF (%)", min_value=0.0, value=21.2, step=0.1)
        marge_souhaitee = st.number_input("Marge nette souhaitée (%)", min_value=0.0, value=40.0, step=1.0)
    
    # Calculs via ta formule
    facteur = 1 - ((taux_urssaf + marge_souhaitee) / 100)
    prix_vente_exact = cout_de_revient / facteur if facteur > 0 else 0
    prix_vente = math.ceil(prix_vente_exact)
    
    # Décomposition financière pour le détail
    montant_urssaf = prix_vente * (taux_urssaf / 100)
    benefice_net = prix_vente - cout_de_revient - montant_urssaf
    
    with col2:
        st.subheader("Bilan Financier")
        st.info(f"**Prix de vente recommandé : {prix_vente}.00 €** *(Exact : {prix_vente_exact:.2f} €)*")
        
        # Affichage visuel des métriques
        metrique1, metrique2, metrique3 = st.columns(3)
        metrique1.metric(label="Coût Matière", value=f"{cout_de_revient:.2f} €")
        metrique2.metric(label="Prov. URSSAF", value=f"{montant_urssaf:.2f} €")
        metrique3.metric(label="Marge Nette", value=f"{benefice_net:.2f} €")
        
    st.write("---")
    # Aperçu dynamique de la facture/devis
    st.markdown("### 📝 Aperçu Devis Client")
    st.code(f"Prestation de personnalisation laser\nTotal TTC : {prix_vente}.00 €", language="text")
