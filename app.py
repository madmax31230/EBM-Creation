import os
import json
import math
from datetime import datetime
import pandas as pd
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="EBM-CREATION | Gestion & Stocks", layout="wide")
st.title("EBM-CREATION : Gestion, Stocks & Remboursement")

# --- CONNEXION GOOGLE SHEETS ---
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

DEFAULT_SHEET_URL = "https://docs.google.com/spreadsheets/d/1V9JjgNViq1WLOmWSDg-D0PkTFvg5mV64DGv4rBBXSy4/edit"

@st.cache_resource
def get_gspread_client():
    creds_dict = None
    if "GOOGLE_CREDENTIALS_JSON" in os.environ:
        creds_dict = json.loads(os.environ["GOOGLE_CREDENTIALS_JSON"])
    elif "gcp_service_account" in st.secrets:
        creds_dict = dict(st.secrets["gcp_service_account"])
    if not creds_dict:
        return None
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)

def get_spreadsheet():
    client = get_gspread_client()
    if client is None:
        return None
    sheet_url = os.environ.get("GOOGLE_SHEET_URL", st.secrets.get("GOOGLE_SHEET_URL", DEFAULT_SHEET_URL))
    return client.open_by_url(sheet_url)

def to_float(val):
    if val is None or val == "":
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).replace("€", "").replace("\xa0", "").replace(" ", "").replace(",", ".").strip()
    try:
        return float(s)
    except ValueError:
        return 0.0

def lire_table(ws, header_keyword, stop_keywords=None):
    """Lit un tableau à partir de la ligne contenant header_keyword jusqu'à une ligne vide ou stop_keywords."""
    values = ws.get_all_values()
    header_idx = None
    for i, row in enumerate(values):
        if any(header_keyword.lower() == c.strip().lower() for c in row):
            header_idx = i
            break
    if header_idx is None:
        return pd.DataFrame(), None, []
    headers = [h.strip() for h in values[header_idx]]
    data_rows = []
    row_numbers = []
    for r_idx in range(header_idx + 1, len(values)):
        row = values[r_idx]
        first_cell = row[0].strip() if row else ""
        joined = " ".join(c.strip() for c in row if c.strip())
        if not joined:
            if data_rows:
                break
            continue
        if first_cell.upper().startswith("TOTAL"):
            break
        if stop_keywords and any(k.lower() in joined.lower() for k in stop_keywords):
            break
        padded = row + [""] * (len(headers) - len(row))
        data_rows.append(padded[:len(headers)])
        row_numbers.append(r_idx + 1)
    return pd.DataFrame(data_rows, columns=headers), header_idx + 1, row_numbers

def trouver_prochaine_ligne_vide(ws, start_row, col_check=1):
    values = ws.get_all_values()
    for r in range(start_row - 1, len(values)):
        row = values[r]
        val = row[col_check - 1].strip() if len(row) >= col_check else ""
        if val == "":
            return r + 1
    return len(values) + 1

# --- BARRE LATÉRALE : PARAMÈTRES & CONNEXION ---
st.sidebar.header("⚙️ Paramètres EBM-CREATION")
taux_horaire = st.sidebar.number_input("Taux horaire MO (€/h)", value=25.0, step=5.0)
cout_machine_heure = st.sidebar.number_input("Frais machine (€/h)", value=3.0, step=0.5)
taux_urssaf = st.sidebar.slider("Charges URSSAF (%)", 0.0, 25.0, 12.3)
marge_souhaitee = st.sidebar.slider("Marge bénéficiaire nette (%)", 0, 100, 30)

sh = None
try:
    sh = get_spreadsheet()
except Exception as e:
    st.sidebar.error(f"Erreur connexion Google Sheets : {e}")

if sh:
    st.sidebar.success("✅ Synchronisé avec Google Sheets")
    if st.sidebar.button("🔄 Actualiser les données"):
        st.cache_data.clear()
        st.rerun()
else:
    st.sidebar.warning("⚠️ Mode hors-ligne : configure GOOGLE_CREDENTIALS_JSON sur Render pour activer la synchro Google Sheets.")

# --- DONNÉES TRANSPORTEURS ---
TARIFS_TRANSPORTEURS = {
    "Mondial Relay (Point Relais)": {
        "max_l_w_h_cm": 150, "max_length_cm": 120,
        "grille": [(0.25, 4.15), (0.5, 4.15), (1.0, 5.99), (2.0, 7.99), (5.0, 15.99)]
    },
    "Colissimo (Point Retrait)": {
        "max_l_w_h_cm": 150, "max_length_cm": 100,
        "grille": [(0.25, 4.79), (0.5, 6.89), (1.0, 8.89), (2.0, 10.49), (5.0, 16.69)]
    },
    "Colissimo (Domicile)": {
        "max_l_w_h_cm": 150, "max_length_cm": 100,
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

if "historique" not in st.session_state:
    st.session_state.historique = []

# --- ONGLETS ALIGNÉS SUR LE GOOGLE SHEETS ---
tab_stocks, tab_remb, tab_lots, tab_calcul, tab_compta = st.tabs([
    "📦 Stocks & Ventes",
    "💶 Avance & Remboursement",
    "🔨 Lots Enchères",
    "🧮 Calculateur Création",
    "📒 Comptabilité Hors Enchères"
])

# ==============================================================================
# ONGLET 1 : STOCKS & ENREGISTREMENT DES VENTES (Suivi Stocks & Plateformes)
# ==============================================================================
with tab_stocks:
    st.header("📦 Suivi des Stocks & Ventes Multi-Plateformes")
    if sh:
        ws_stocks = sh.worksheet("Suivi Stocks & Plateformes")
        df_stocks, _, _ = lire_table(ws_stocks, "Référence lot", stop_keywords=["2. SYNTHÈSE", "3. JOURNAL"])

        if not df_stocks.empty:
            st.subheader("1. État des stocks en temps réel")
            st.dataframe(df_stocks, use_container_width=True, hide_index=True)

            st.divider()
            st.subheader("2. Enregistrer une vente / sortie de stock")
            refs_dispo = df_stocks["Référence lot"].tolist()
            labels_refs = {
                r["Référence lot"]: f"{r['Référence lot']} — {r['Désignation article'][:45]} (Reste : {r['Stock restant']})"
                for _, r in df_stocks.iterrows()
            }

            with st.form("form_sortie_vente"):
                c1, c2, c3 = st.columns(3)
                with c1:
                    date_vente = st.date_input("Date de vente", value=datetime.now())
                    ref_choisie = st.selectbox("Référence lot", refs_dispo, format_func=lambda x: labels_refs.get(x, x))
                with c2:
                    plateforme = st.selectbox("Plateforme", ["Vinted Pro", "Leboncoin Pro", "eBay", "SumUp", "Vente directe / Marché"])
                    qte_vendue = st.number_input("Quantité vendue", min_value=1, value=1, step=1)
                with c3:
                    ca_brut = st.number_input("Prix de vente encaissé (€)", min_value=0.0, value=25.0, step=1.0)
                    frais_vente = st.number_input("Frais port / comm. vendeur (€)", min_value=0.0, value=0.0, step=0.5)
                notes_vente = st.text_input("Notes (acheteur, suivi colis, etc.)")

                if st.form_submit_button("✅ Enregistrer la vente dans Google Sheets"):
                    ligne_art = df_stocks[df_stocks["Référence lot"] == ref_choisie].iloc[0]
                    designation = ligne_art["Désignation article"]
                    cout_u = to_float(ligne_art["Coût unitaire (€)"])
                    net_encaisse = round(ca_brut - frais_vente, 2)
                    cout_sortie = round(cout_u * qte_vendue, 2)
                    marge_hors_urssaf = round(net_encaisse - cout_sortie, 2)

                    # Recherche de la section "3. JOURNAL DES SORTIES"
                    all_vals = ws_stocks.get_all_values()
                    journal_header_row = None
                    for idx, r in enumerate(all_vals):
                        if any("date de vente" == c.strip().lower() for c in r):
                            journal_header_row = idx + 1
                            break
                    if journal_header_row:
                        target_row = trouver_prochaine_ligne_vide(ws_stocks, journal_header_row + 1, col_check=1)
                        nouvelle_ligne = [
                            date_vente.strftime("%d/%m/%Y"),
                            ref_choisie,
                            designation,
                            plateforme,
                            int(qte_vendue),
                            round(ca_brut, 2),
                            round(frais_vente, 2),
                            net_encaisse,
                            cout_sortie,
                            marge_hors_urssaf,
                            notes_vente
                        ]
                        ws_stocks.update(f"A{target_row}:K{target_row}", [nouvelle_ligne], value_input_option="USER_ENTERED")
                        st.success(f"Vente enregistrée sur {plateforme} ({ca_brut:.2f} €) ! Recharge pour voir les totaux à jour.")
                    else:
                        st.error("Section Journal des sorties introuvable dans l'onglet Suivi Stocks & Plateformes.")
    else:
        st.info("Connecte Google Sheets pour afficher et mettre à jour tes stocks en temps réel.")

# ==============================================================================
# ONGLET 2 : SYNTHÈSE & REMBOURSEMENT DE L'AVANCE (Synthèse & Remboursement)
# ==============================================================================
with tab_remb:
    st.header("💶 Suivi du Remboursement de l'Avance Personnelle")
    if sh:
        ws_lots = sh.worksheet("Suivi Lots & Reventes")
        df_lots, _, _ = lire_table(ws_lots, "Date d'achat")

        ws_remb = sh.worksheet("Synthèse & Remboursement")
        df_virements, header_vir_row, _ = lire_table(ws_remb, "Date du virement")

        avance_initiale = sum(to_float(x) for x in df_lots["Coût total avec port (€)"]) if not df_lots.empty else 451.74
        ca_total = sum(to_float(x) for x in df_lots["CA brut encaissé (€)"]) if not df_lots.empty else 0.0
        frais_vente_total = sum(to_float(x) for x in df_lots["Frais port & comm. vente (€)"]) if not df_lots.empty else 0.0
        urssaf_total = sum(to_float(x) for x in df_lots["Cotisations URSSAF 12,3% (€)"]) if not df_lots.empty else 0.0

        cumul_rembourse = sum(to_float(x) for x in df_virements["Montant viré (€)"]) if not df_virements.empty else 0.0
        reste_a_rembourser = max(0.0, round(avance_initiale - cumul_rembourse, 2))
        treso_nette_ebm = round(ca_total - frais_vente_total - urssaf_total - cumul_rembourse, 2)

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Avance initiale totale", f"{avance_initiale:.2f} €")
        k2.metric("Déjà remboursé (Perso)", f"{cumul_rembourse:.2f} €")
        k3.metric("Reste à rembourser", f"{reste_a_rembourser:.2f} €")
        k4.metric("Trésorerie nette EBM", f"{treso_nette_ebm:.2f} €")

        st.progress(min(1.0, cumul_rembourse / avance_initiale if avance_initiale > 0 else 0.0))

        st.divider()
        st.subheader("Journal des virements de remboursement (SumUp Pro → Compte Perso)")
        if not df_virements.empty:
            st.dataframe(df_virements, use_container_width=True, hide_index=True)

        with st.form("form_virement_remb"):
            c1, c2, c3 = st.columns(3)
            with c1:
                date_vir = st.date_input("Date du virement", value=datetime.now())
            with c2:
                libelle_vir = st.text_input("Libellé / Référence", value="Remboursement partiel avance stock enchères")
            with c3:
                montant_vir = st.number_input("Montant viré (€)", min_value=0.0, value=50.0, step=5.0)
            justif_vir = st.text_input("Note / Justificatif bancaire", value="Virement SumUp vers compte perso")

            if st.form_submit_button("💸 Ajouter ce virement de remboursement"):
                if header_vir_row:
                    target_row = trouver_prochaine_ligne_vide(ws_remb, header_vir_row + 1, col_check=2)
                    num_ligne = (target_row - header_vir_row)
                    ws_remb.update(
                        f"A{target_row}:E{target_row}",
                        [[num_ligne, date_vir.strftime("%d/%m/%Y"), libelle_vir, round(montant_vir, 2), justif_vir]],
                        value_input_option="USER_ENTERED"
                    )
                    st.success(f"Virement de {montant_vir:.2f} € enregistré ! Actualise pour mettre à jour les compteurs.")
    else:
        st.info("Connecte Google Sheets pour piloter le remboursement des 451,74 €.")

# ==============================================================================
# ONGLET 3 : LOTS ENCHÈRES (Suivi Lots & Reventes)
# ==============================================================================
with tab_lots:
    st.header("🔨 Lots aux Enchères (ADN Enchères)")
    if sh:
        ws_lots = sh.worksheet("Suivi Lots & Reventes")
        df_lots, header_lots_row, _ = lire_table(ws_lots, "Date d'achat")
        if not df_lots.empty:
            st.dataframe(df_lots, use_container_width=True, hide_index=True)

        with st.expander("➕ Ajouter un nouveau lot acheté aux enchères"):
            with st.form("form_nouveau_lot"):
                c1, c2, c3 = st.columns(3)
                with c1:
                    d_achat = st.date_input("Date d'achat", value=datetime.now())
                    maison = st.text_input("Maison de vente", value="ADN Enchères")
                    n_fact = st.text_input("N° Facture")
                    bordereau = st.text_input("Bordereau")
                with c2:
                    n_lot = st.text_input("N° Lot")
                    ref_lot = st.text_input("Référence lot")
                    designation = st.text_input("Désignation")
                    qte = st.number_input("Quantité", min_value=1, value=1, step=1)
                with c3:
                    adj = st.number_input("Adjudication (€)", min_value=0.0, value=20.0, step=1.0)
                    frais_ach = st.number_input("Frais acheteur (€)", min_value=0.0, value=5.20, step=0.5)
                    port_ach = st.number_input("Frais de livraison (€)", min_value=0.0, value=0.0, step=0.5)
                    notes_lot = st.text_input("Canal / Notes")

                if st.form_submit_button("💾 Enregistrer le lot"):
                    if header_lots_row:
                        target_row = trouver_prochaine_ligne_vide(ws_lots, header_lots_row + 1, col_check=1)
                        row_data = [
                            d_achat.strftime("%d/%m/%Y"), maison, n_fact, bordereau, n_lot, ref_lot,
                            designation, int(qte), round(adj, 2), round(frais_ach, 2),
                            f"=I{target_row}+J{target_row}", round(port_ach, 2),
                            f"=K{target_row}+L{target_row}", f"=M{target_row}/H{target_row}",
                            0, 0, f"=O{target_row}*0.123", f"=O{target_row}-P{target_row}-Q{target_row}-M{target_row}",
                            "En stock", notes_lot
                        ]
                        ws_lots.update(f"A{target_row}:T{target_row}", [row_data], value_input_option="USER_ENTERED")
                        st.success("Nouveau lot ajouté dans Suivi Lots & Reventes !")
    else:
        st.info("Connecte Google Sheets pour afficher tes lots aux enchères.")

# ==============================================================================
# ONGLET 4 : CALCULATEUR CRÉATION & EXPÉDITION (Ton outil initial conservé)
# ==============================================================================
with tab_calcul:
    st.header("🧮 Calculateur Création Laser / 3D & Expédition")
    materiau = st.selectbox("Support", ["Verre / Miroir", "Bois", "Acrylique", "Impression 3D"])

    col1, col2 = st.columns(2)
    with col1:
        prix_achat = st.number_input("Prix d'achat du support (€)", value=10.0, step=1.0)
        conso_extra = st.number_input("Consommables (€)", value=1.5, step=0.5)
    with col2:
        temps_prepa = st.number_input("Temps de préparation (min)", value=15, step=5)
        temps_gravure = st.number_input("Temps machine (min)", value=20, step=5)

    cout_matiere = prix_achat + conso_extra
    cout_main_oeuvre = (temps_prepa / 60) * taux_horaire
    cout_utilisation_machine = (temps_gravure / 60) * cout_machine_heure
    cout_de_revient_produit = cout_matiere + cout_main_oeuvre + cout_utilisation_machine

    facteur = 1 - ((taux_urssaf + marge_souhaitee) / 100)
    prix_vente_produit = math.ceil(cout_de_revient_produit / facteur if facteur > 0 else 0)

    st.divider()
    st.subheader("Expédition & Paiement")
    livraison = st.toggle("📦 Ajouter une expédition")
    tarif_transporteur = 0.0
    cout_emballage = 0.0
    statut_livraison = "Main propre"

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
            statut_livraison = choix_transporteur
        else:
            st.error(f"⚠️ {statut}")

    methode_paiement = st.selectbox(
        "💳 Méthode de paiement",
        [
            "🤖 Optimisation Auto (Vente à distance)",
            "Espèces / Virement (Sans frais)",
            "SumUp - Terminal TPE (1,75%)",
            "SumUp - Lien en ligne (2,50%)",
            "Stripe - En ligne (1,5% + 0,25€)"
        ]
    )

    montant_cible_net = prix_vente_produit + tarif_transporteur + cout_emballage
    taux_pct = 0.0
    frais_fixe = 0.0
    processeur_choisi = methode_paiement

    if "Optimisation Auto" in methode_paiement:
        if montant_cible_net < 24.38:
            taux_pct = 0.025
            processeur_choisi = "SumUp - Lien en ligne (Automatique)"
        else:
            taux_pct = 0.015
            frais_fixe = 0.25
            processeur_choisi = "Stripe (Automatique)"
    elif "Stripe" in methode_paiement:
        taux_pct = 0.015
        frais_fixe = 0.25
    elif "TPE" in methode_paiement:
        taux_pct = 0.0175
    elif "Lien en ligne" in methode_paiement:
        taux_pct = 0.025

    if taux_pct > 0 or frais_fixe > 0:
        prix_final_client = (montant_cible_net + frais_fixe) / (1 - taux_pct)
        frais_bancaires = prix_final_client - montant_cible_net
    else:
        prix_final_client = montant_cible_net
        frais_bancaires = 0.0

    prix_final_client = round(prix_final_client, 2)
    cout_total = cout_de_revient_produit + tarif_transporteur + cout_emballage + frais_bancaires
    montant_urssaf = prix_final_client * (taux_urssaf / 100)
    benef_net = prix_final_client - cout_total - montant_urssaf

    st.divider()
    if "Optimisation Auto" in methode_paiement:
        st.info(f"💡 Processeur optimal : **{processeur_choisi}**")
    st.subheader(f"🏷️ Total à facturer au client : {prix_final_client} €")

    client_nom = st.text_input("Client / Référence commande (optionnel)", value="Client particulier")
    if st.button("✅ Enregistrer dans le Livre des Recettes (Google Sheets)"):
        if sh:
            ws_compta = sh.worksheet("Comptabilité EBM-CREATION")
            _, header_rec_row, _ = lire_table(ws_compta, "Date d'encaissement")
            if header_rec_row:
                target_row = trouver_prochaine_ligne_vide(ws_compta, header_rec_row + 1, col_check=2)
                num_rec = target_row - header_rec_row
                ws_compta.update(
                    f"A{target_row}:J{target_row}",
                    [[
                        num_rec,
                        datetime.now().strftime("%d/%m/%Y"),
                        f"REC-{datetime.now().strftime('%Y%m%d')}-{num_rec}",
                        client_nom,
                        f"Création {materiau} ({statut_livraison})",
                        processeur_choisi.split(" (")[0].split(" -")[0],
                        prix_final_client,
                        0.0,
                        prix_final_client,
                        f"Compte Pro SumUp | Coût revient {cout_total:.2f} €"
                    ]],
                    value_input_option="USER_ENTERED"
                )
                st.success("Recette enregistrée directement dans l'onglet Comptabilité EBM-CREATION !")
        else:
            st.session_state.historique.append({
                "Date": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "Projet": materiau,
                "CA (€)": prix_final_client,
                "URSSAF (€)": round(montant_urssaf, 2),
                "Bénéfice (€)": round(benef_net, 2)
            })
            st.success("Enregistré en mémoire locale (active Google Sheets pour la sauvegarde permanente).")

# ==============================================================================
# ONGLET 5 : COMPTABILITÉ HORS ENCHÈRES (Comptabilité EBM-CREATION)
# ==============================================================================
with tab_compta:
    st.header("📒 Livre des Recettes & Registre des Achats (Hors Enchères)")
    if sh:
        ws_compta = sh.worksheet("Comptabilité EBM-CREATION")
        df_recettes, _, _ = lire_table(ws_compta, "Date d'encaissement", stop_keywords=["2. REGISTRE"])
        df_achats, _, _ = lire_table(ws_compta, "Fournisseur")

        st.subheader("1. Livre des recettes (Création / Gravure / 3D / Services)")
        if not df_recettes.empty:
            st.dataframe(df_recettes, use_container_width=True, hide_index=True)

        st.divider()
        st.subheader("2. Registre des achats hors enchères (LightBurn, Action, fournitures)")
        if not df_achats.empty:
            st.dataframe(df_achats, use_container_width=True, hide_index=True)
    elif len(st.session_state.historique) > 0:
        st.dataframe(pd.DataFrame(st.session_state.historique), use_container_width=True)
    else:
        st.info("Connecte Google Sheets pour consulter le livre des recettes et le registre des achats.")
