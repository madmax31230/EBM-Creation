import streamlit as st

st.set_page_config(page_title="Tarificateur EBM", layout="centered")
st.title("Calculateur de Prix - Gravure Laser")

# Paramètres fixes
st.sidebar.header("Paramètres (Micro-entreprise)")
taux_horaire = st.sidebar.number_input("Taux horaire main d'œuvre (€/h)", value=35.0, step=5.0)
cout_machine_heure = st.sidebar.number_input("Frais machine (€/h)", value=3.0, step=0.5)
taux_urssaf = st.sidebar.slider("Charges URSSAF (%)", 0.0, 25.0, 12.3) 
marge_souhaitee = st.sidebar.slider("Marge bénéficiaire nette (%)", 0, 100, 30)

# Saisie du projet
st.header("Nouveau Projet")
materiau = st.selectbox("Support", ["Verre / Miroir", "Bois", "Acrylique"])

col1, col2 = st.columns(2)
with col1:
    prix_achat = st.number_input("Prix d'achat du support (€)", value=10.0, step=1.0)
    conso_extra = st.number_input("Consommables (€)", value=1.5, step=0.5)
with col2:
    temps_prepa = st.number_input("Temps de préparation (min)", value=15, step=5)
    temps_gravure = st.number_input("Temps de gravure (min)", value=20, step=5)

# Calculs
cout_matiere = prix_achat + conso_extra
cout_main_oeuvre = (temps_prepa / 60) * taux_horaire
cout_utilisation_machine = (temps_gravure / 60) * cout_machine_heure
cout_de_revient = cout_matiere + cout_main_oeuvre + cout_utilisation_machine

facteur = 1 - ((taux_urssaf + marge_souhaitee) / 100)
prix_vente = cout_de_revient / facteur if facteur > 0 else 0

st.divider()

# Résultat
st.subheader(f"🏷️ Prix de vente conseillé : {prix_vente:.2f} €")
st.write(f"- **Coût de revient sec :** {cout_de_revient:.2f} €")
st.write(f"- **Provision URSSAF ({taux_urssaf}%) :** {(prix_vente * taux_urssaf / 100):.2f} €")
st.write(f"- **Bénéfice net :** {(prix_vente * marge_souhaitee / 100):.2f} €")

st.divider()

# Bloc Tiime
st.subheader("📝 Préparation pour Tiime")
description_tiime = f"""Prestation de gravure laser personnalisée.
- Support : {materiau}
- Préparation et adaptation du fichier graphique
- Paramétrage et gravure laser
- Finitions et nettoyage

Visuel fourni en annexe à titre indicatif (photo non contractuelle). Le rendu final de la gravure peut légèrement varier en fonction des caractéristiques naturelles du support."""

st.text_area("Texte à copier/coller dans Tiime :", value=description_tiime, height=180)
st.metric(label="Prix de vente (TTC) à saisir", value=f"{prix_vente:.2f} €")
