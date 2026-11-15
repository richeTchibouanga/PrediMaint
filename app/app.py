"""PrédiMaint — tableau de bord de l'atelier d'usinage (étape 5, fonctions F13 à F17).

Lancement, depuis le dossier du projet :
    .venv\\Scripts\\streamlit run app/app.py
"""
import json
import sys
from datetime import datetime
from pathlib import Path

import altair as alt
import joblib
import numpy as np
import pandas as pd
import streamlit as st

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))
# Lors d'une mise à jour, Streamlit Cloud relance ce script sans redémarrer Python : les modules du projet
# (src.*) resteraient dans leur ancienne version. On les retire du cache pour toujours charger la version actuelle.
for _nom in [m for m in sys.modules if m == "src" or m.startswith("src.")]:
    del sys.modules[_nom]

from src.donnees import CAPTEURS, PLAGES, ajouter_variables, charger, separer  # noqa: E402
from src.economie import Hypotheses, bilan, courbe_couts  # noqa: E402
from src.explication import LIBELLES, expliquer, type_probable  # noqa: E402
from src.lot import NIVEAU_A_VERIFIER, ZONE_USURE, analyser_lot, lire_csv  # noqa: E402
from src.donnees import NOMS_MODES  # noqa: E402
from src.procedures import FICHE_PAR_TYPE, charger_fiches, choisir_fiche, compte_rendu, deroule  # noqa: E402
from src.surveillance import bilan as bilan_surveillance  # noqa: E402
from src.surveillance import flux_de_test, machines  # noqa: E402
from src.lot import niveau as niveau_texte  # noqa: E402

st.set_page_config(page_title="PrédiMaint — Atelier d'usinage", page_icon="🏭", layout="wide")

BLEU, ROUGE, ORANGE, VERT, GRIS = "#1f4e79", "#c0392b", "#e67e22", "#2e7d32", "#9aa5b1"
UNITES = {"temp_air": "K", "temp_process": "K", "vitesse": "tr/min", "couple": "N·m", "usure_outil": "min"}
LIMITE_SURCHARGE = {"L": 11_000, "M": 12_000, "H": 13_000}


# ---------------------------------------------------------------------------- Chargement (mis en cache)
@st.cache_resource
def charger_modele():
    return joblib.load(RACINE / "models" / "predimaint.joblib")


@st.cache_data
def charger_metadata():
    return json.loads((RACINE / "models" / "metadata.json").read_text(encoding="utf-8"))


@st.cache_data
def jeu_de_test():
    """Données de test (jamais vues à l'entraînement) et risques prédits : base de la page Économie."""
    paquet = charger_modele()
    _, X_te, _, y_te, _, _, _, d_te = separer(charger())
    proba = paquet["modele"].predict_proba(X_te[paquet["entrees"]])[:, 1]
    return d_te.reset_index(drop=True), y_te.to_numpy(), proba


PAQUET = charger_modele()
MODELE, MODELE_TYPE = PAQUET["modele"], PAQUET["modele_type"]
ENTREES, SEUIL, REFERENCE = PAQUET["entrees"], PAQUET["seuil"], PAQUET["reference"]


def risques(mesures: pd.DataFrame) -> np.ndarray:
    """Risque de panne (0 à 1) pour un tableau de machines."""
    return MODELE.predict_proba(ajouter_variables(mesures)[ENTREES])[:, 1]


def niveau(risque: float) -> tuple[str, str]:
    """Texte du niveau d'alerte (défini dans src/lot.py) et couleur associée."""
    texte = niveau_texte(risque, SEUIL)
    return texte, ROUGE if risque >= 0.6 else ORANGE if risque >= SEUIL else VERT


def pct(x: float) -> str:
    return f"{x * 100:.0f} %"


def euros(x: float) -> str:
    return f"{x:,.0f} €".replace(",", " ")


def csv_excel(df: pd.DataFrame) -> bytes:
    """CSV lisible directement par Excel en français : point-virgule, virgule décimale, UTF-8 avec BOM."""
    return df.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig")


def badge(texte: str, couleur: str) -> None:
    st.markdown(f"<div style='background:{couleur};color:white;padding:10px 14px;border-radius:8px;"
                f"font-weight:600;font-size:1.05rem'>{texte}</div>", unsafe_allow_html=True)


MACHINE_NORMALE = dict(gamme="L", temp_air=300.0, temp_process=310.0, vitesse=1500, couple=40.0, usure_outil=100)


def saisie_machine(cle: str, defauts: dict | None = None) -> pd.DataFrame:
    """Formulaire des mesures d'une machine (par défaut : une machine qui fonctionne normalement)."""
    v0 = {**MACHINE_NORMALE, **(defauts or {})}
    c1, c2, c3 = st.columns(3)
    gamme = c1.selectbox("Gamme du produit", ["L", "M", "H"], index=["L", "M", "H"].index(v0["gamme"]),
                         key=f"{cle}_gamme", help="L : qualité basse (60 % de la production), M : moyenne, H : haute")
    temp_air = c2.number_input("Température de l'air (K)", *PLAGES["temp_air"], float(v0["temp_air"]), 0.1,
                               key=f"{cle}_ta")
    temp_process = c3.number_input("Température du procédé (K)", *PLAGES["temp_process"],
                                   float(v0["temp_process"]), 0.1, key=f"{cle}_tp")
    c4, c5, c6 = st.columns(3)
    vitesse = c4.number_input("Vitesse de rotation (tr/min)", *PLAGES["vitesse"], int(v0["vitesse"]), 10,
                              key=f"{cle}_v")
    couple = c5.number_input("Couple (N·m)", *PLAGES["couple"], float(v0["couple"]), 0.5, key=f"{cle}_c")
    usure = c6.number_input("Usure de l'outil (min)", *PLAGES["usure_outil"], int(v0["usure_outil"]), 1,
                            key=f"{cle}_u")
    return pd.DataFrame([{"gamme": gamme, "temp_air": temp_air, "temp_process": temp_process,
                          "vitesse": vitesse, "couple": couple, "usure_outil": usure}])


# ---------------------------------------------------------------------------- Page 1 : diagnostic (F13)
def page_diagnostic():
    st.title("🔧 Diagnostic d'une machine")
    st.caption("Saisissez les mesures relevées sur la machine : le modèle estime le risque de panne, "
               "le type de panne probable, explique sa décision et propose une action.")

    with st.expander("Charger un exemple", expanded=False):
        exemples = {
            "Machine normale": dict(gamme="L", temp_air=300.0, temp_process=310.0, vitesse=1500, couple=40.0, usure_outil=100),
            "Outil usé et effort élevé (surcharge)": dict(gamme="L", temp_air=300.0, temp_process=309.0, vitesse=1300, couple=62.0, usure_outil=205),
            "Refroidissement insuffisant (chaleur)": dict(gamme="M", temp_air=302.5, temp_process=310.5, vitesse=1330, couple=45.0, usure_outil=60),
            "Vitesse très élevée, couple faible (puissance)": dict(gamme="H", temp_air=299.0, temp_process=309.5, vitesse=2700, couple=11.0, usure_outil=30),
        }
        choix = st.radio("Exemple", list(exemples), horizontal=True, label_visibility="collapsed")
        if st.button("Appliquer l'exemple"):
            e = exemples[choix]
            for k, v in {"gamme": e["gamme"], "ta": e["temp_air"], "tp": e["temp_process"], "v": e["vitesse"],
                         "c": e["couple"], "u": e["usure_outil"]}.items():
                st.session_state[f"diag_{k}"] = v
            st.rerun()

    mesures = saisie_machine("diag")
    m = ajouter_variables(mesures).iloc[0]
    risque = float(risques(mesures)[0])
    texte, couleur = niveau(risque)

    st.divider()
    g, d = st.columns([1, 2])
    with g:
        st.metric("Risque de panne", pct(risque), help=f"Une alerte est déclenchée à partir de {pct(SEUIL)}.")
        st.progress(min(risque, 1.0))
        badge(texte, couleur)
        if mesures["usure_outil"].iloc[0] >= ZONE_USURE:
            st.warning(f"⚠️ **Zone d'usure à risque** : l'outil dépasse {ZONE_USURE} min d'usure. "
                       "Les casses d'outil surviennent au hasard entre 200 et 250 min : "
                       "**changez l'outil par précaution** (maintenance préventive).")

    with d:
        if risque >= SEUIL:
            types = type_probable(MODELE_TYPE, mesures, ENTREES)
            t0 = types.iloc[0]
            st.subheader(f"Panne probable : {t0['type']}")
            st.success(f"**Action recommandée** : {t0['action']}")
            st.dataframe(types[["type", "probabilite"]].rename(columns={"type": "Type de panne",
                                                                         "probabilite": "Probabilité"}),
                         hide_index=True, width="stretch",
                         column_config={"Probabilité": st.column_config.ProgressColumn(format="percent", min_value=0, max_value=1)})
        else:
            st.subheader("Fonctionnement normal")
            st.info("Aucune intervention n'est nécessaire pour l'instant. Poursuivre la surveillance.")
        if risque >= SEUIL or mesures["usure_outil"].iloc[0] >= ZONE_USURE:
            if st.button("🧰 Lancer l'intervention guidée", type="primary"):
                transmettre_machine(mesures)

    st.subheader("Pourquoi ce risque ?")
    expl = expliquer(MODELE, mesures, REFERENCE, ENTREES)
    expl["sens"] = np.where(expl["contribution"] >= 0, "Augmente le risque", "Diminue le risque")
    # La gamme est un texte (L, M, H) et les capteurs des nombres : on affiche tout en texte
    fmt = lambda v: v if isinstance(v, str) else f"{v:g}"
    expl["valeur"] = expl["valeur"].map(fmt)
    expl["valeur_normale"] = expl["valeur_normale"].map(fmt)
    if expl["contribution"].abs().max() < 0.01:
        st.success("Aucune mesure ne fait monter le risque : toutes les valeurs sont dans les plages habituelles "
                   "d'une machine saine.")
        afficher_indicateurs(mesures, m)
        return
    graph = alt.Chart(expl).mark_bar().encode(
        x=alt.X("contribution:Q", title="Effet sur le risque (points de probabilité)", axis=alt.Axis(format="%")),
        y=alt.Y("mesure:N", sort="-x", title=None, axis=alt.Axis(labelOverlap=False, labelLimit=220)),
        color=alt.Color("sens:N", scale=alt.Scale(domain=["Augmente le risque", "Diminue le risque"],
                                                    range=[ROUGE, VERT]), legend=alt.Legend(title=None, orient="bottom")),
        tooltip=[alt.Tooltip("mesure", title="Mesure"), alt.Tooltip("valeur", title="Valeur"),
                 alt.Tooltip("valeur_normale", title="Valeur normale"),
                 alt.Tooltip("contribution", title="Effet", format="+.1%")],
    ).properties(height=300)
    st.altair_chart(graph, width="stretch")
    st.caption("Méthode : chaque mesure est remplacée par sa valeur habituelle sur une machine saine ; "
               "la baisse du risque indique à quel point cette mesure est responsable.")
    afficher_indicateurs(mesures, m)


def afficher_indicateurs(mesures: pd.DataFrame, m: pd.Series) -> None:
    """Les trois grandeurs physiques liées aux pannes, comparées à leurs limites."""
    st.subheader("Indicateurs physiques")
    lim = LIMITE_SURCHARGE[mesures["gamme"].iloc[0]]
    c1, c2, c3 = st.columns(3)
    c1.metric("Écart de température", f"{m['ecart_temp']:.1f} K".replace(".", ","),
              delta="trop faible (< 8,6 K)" if m["ecart_temp"] < 8.6 else "correct", delta_color="inverse" if m["ecart_temp"] < 8.6 else "off")
    c2.metric("Puissance", f"{m['puissance']:,.0f} W".replace(",", " "),
              delta="hors plage 3 500 – 9 000 W" if not 3500 <= m["puissance"] <= 9000 else "dans la plage",
              delta_color="inverse" if not 3500 <= m["puissance"] <= 9000 else "off")
    c3.metric("Contrainte usure × couple", f"{m['contrainte']:,.0f}".replace(",", " "),
              delta=f"au-dessus de la limite ({lim:,})".replace(",", " ") if m["contrainte"] > lim else f"limite {lim:,}".replace(",", " "),
              delta_color="inverse" if m["contrainte"] > lim else "off")


# ---------------------------------------------------------------------------- Page 2 : analyse d'un lot (F14)
def page_lot():
    st.title("📋 Analyse d'un lot de machines")
    st.caption("Importez un fichier CSV de relevés : chaque machine est évaluée et la liste est classée "
               "de la plus à la moins risquée.")
    modele_csv = pd.DataFrame([
        {"machine": "M01", "gamme": "L", "temp_air": 300.0, "temp_process": 310.0, "vitesse": 1500, "couple": 40.0,
         "usure_outil": 100},
        {"machine": "M02", "gamme": "M", "temp_air": 301.5, "temp_process": 311.0, "vitesse": 1420, "couple": 48.5,
         "usure_outil": 160},
    ])
    c1, c2 = st.columns([3, 1])
    fichier = c1.file_uploader("Fichier CSV (colonnes : gamme, temp_air, temp_process, vitesse, couple, "
                               "usure_outil — ou les noms d'origine du jeu AI4I 2020). Point-virgule ou virgule, "
                               "décimales avec virgule ou point : un fichier enregistré par Excel convient.",
                               type="csv")
    c2.download_button("Télécharger un modèle de fichier", csv_excel(modele_csv), "modele_releves.csv", "text/csv",
                       help="Fichier prêt à remplir dans Excel (une ligne par machine).")
    demo = st.toggle("Utiliser un échantillon de démonstration (200 relevés du jeu de test)", value=fichier is None)

    try:
        if fichier is not None and not demo:
            lot = lire_csv(fichier)
        elif demo:
            d_te, _, _ = jeu_de_test()
            lot = d_te.sample(200, random_state=1)[["gamme"] + CAPTEURS].reset_index(drop=True)
        else:
            st.info("Importez un fichier ou activez l'échantillon de démonstration.")
            return
    except ValueError as e:
        st.error(f"Fichier non valide : {e}")
        return

    res = analyser_lot(lot, MODELE, MODELE_TYPE, ENTREES, SEUIL)
    n_alerte = int((res["risque"] >= SEUIL).sum())
    n_usure = int(((res["usure_outil"] >= ZONE_USURE) & (res["risque"] < SEUIL)).sum())
    n_verif = int((res["niveau"] == NIVEAU_A_VERIFIER).sum())
    a, b, c, d = st.columns(4)
    a.metric("Machines analysées", len(res))
    b.metric("Alertes", n_alerte, help=f"Risque supérieur ou égal à {pct(SEUIL)}")
    c.metric("Outils à changer par précaution", n_usure, help=f"Usure ≥ {ZONE_USURE} min sans alerte du modèle")
    d.metric("Relevés à vérifier", n_verif, help="Mesures hors des plages connues du modèle : non analysées")
    if n_verif:
        st.warning(f"⚠️ **{n_verif} relevé(s) contiennent des mesures hors des plages connues du modèle.** Ils sont "
                   "placés en tête de liste et ne sont pas analysés, car le résultat ne serait pas fiable. Erreur "
                   "fréquente : une température en °C au lieu de kelvins (K = °C + 273,15).")

    filtre = st.radio("Afficher", ["Toutes les machines", "Alertes seulement", "Alertes et zone d'usure"],
                      horizontal=True)
    vue = res
    a_verifier = res["niveau"] == NIVEAU_A_VERIFIER
    if filtre == "Alertes seulement":
        vue = res[(res["risque"] >= SEUIL) | a_verifier]
    elif filtre == "Alertes et zone d'usure":
        vue = res[(res["risque"] >= SEUIL) | (res["usure_outil"] >= ZONE_USURE) | a_verifier]
    st.dataframe(vue, hide_index=True, width="stretch", height=420, column_config={
        "risque": st.column_config.ProgressColumn("Risque", format="percent", min_value=0, max_value=1),
        "machine": "Machine", "niveau": "Niveau", "panne_probable": "Panne probable", "action": "Action recommandée",
        "gamme": "Gamme", "temp_air": "T. air (K)", "temp_process": "T. procédé (K)", "vitesse": "Vitesse",
        "couple": "Couple", "usure_outil": "Usure (min)"})
    st.download_button("Télécharger les résultats (CSV)", csv_excel(res),
                       "predimaint_resultats.csv", "text/csv")


# ---------------------------------------------------------------------------- Page 3 : simulation (F15)
def page_simulation():
    st.title("🔬 Simulation")
    st.caption("Partez d'une machine, faites varier une mesure et observez l'évolution du risque. "
               "Utile pour savoir jusqu'où on peut aller avant d'atteindre le seuil d'alerte.")
    mesures = saisie_machine("sim")
    libelles = {c: f"{LIBELLES[c]} ({UNITES[c]})" for c in CAPTEURS}
    var = st.selectbox("Mesure à faire varier", CAPTEURS, index=4, format_func=libelles.get)
    lo, hi = PLAGES[var]
    valeurs = np.linspace(lo, hi, 120)
    grille = pd.concat([mesures] * len(valeurs), ignore_index=True)
    grille[var] = valeurs
    courbe = pd.DataFrame({var: valeurs, "risque": risques(grille)})

    actuel = float(mesures[var].iloc[0])
    base = alt.Chart(courbe).mark_line(color=BLEU, strokeWidth=3).encode(
        x=alt.X(f"{var}:Q", title=libelles[var]), y=alt.Y("risque:Q", title="Risque de panne", axis=alt.Axis(format="%"),
                                                           scale=alt.Scale(domain=[0, 1])),
        tooltip=[alt.Tooltip(var, title=LIBELLES[var], format=".1f"), alt.Tooltip("risque", title="Risque", format=".0%")])
    seuil = alt.Chart(pd.DataFrame({"y": [SEUIL]})).mark_rule(color=ORANGE, strokeDash=[6, 4]).encode(y="y:Q")
    point = alt.Chart(pd.DataFrame({var: [actuel], "risque": [float(risques(mesures)[0])]})).mark_point(
        color=ROUGE, size=120, filled=True).encode(x=f"{var}:Q", y="risque:Q")
    calques = [base, seuil, point]
    legende = f"Ligne orange : seuil d'alerte ({pct(SEUIL)}). Point rouge : valeur actuelle."
    if var == "usure_outil":
        zone = alt.Chart(pd.DataFrame({"x": [ZONE_USURE], "x2": [hi]})).mark_rect(color=ORANGE, opacity=0.12).encode(
            x="x:Q", x2="x2:Q")
        calques.insert(0, zone)
        legende += (f" Bande orange : zone d'usure à risque (≥ {ZONE_USURE} min), où l'outil doit être changé "
                    "par précaution même si le risque calculé reste bas.")
    st.altair_chart(alt.layer(*calques).properties(height=360), width="stretch")
    st.caption(legende)

    # Zones où le risque dépasse le seuil (il peut y en avoir plusieurs : valeur trop basse ET trop haute)
    zones, debut = [], None
    for v, alerte in zip(courbe[var], courbe["risque"] >= SEUIL):
        if alerte and debut is None:
            debut = fin = v
        elif alerte:
            fin = v
        elif debut is not None:
            zones.append((debut, fin)); debut = None
    if debut is not None:
        zones.append((debut, fin))
    nombre = lambda v: f"{v:,.1f}".replace(",", " ").replace(".", ",")
    if not zones:
        st.success("Sur toute la plage étudiée, le risque reste sous le seuil d'alerte "
                   "(les autres mesures restant inchangées).")
    else:
        textes = []
        for a, b in zones:
            if a <= lo + 1e-9:
                textes.append(f"jusqu'à **{nombre(b)} {UNITES[var]}**")
            elif b >= hi - 1e-9:
                textes.append(f"à partir de **{nombre(a)} {UNITES[var]}**")
            else:
                textes.append(f"entre **{nombre(a)}** et **{nombre(b)} {UNITES[var]}**")
        st.info(f"Le modèle déclenche une alerte pour {LIBELLES[var].lower()} "
                + " et ".join(textes) + ", les autres mesures restant inchangées.")


# ---------------------------------------------------------------------------- Page 4 : économie (F16, F9 à F12)
def page_economie():
    st.title("💶 Économie de la maintenance prédictive")
    st.caption("Comparez le coût annuel de la maintenance corrective seule (on répare après la panne) "
               "et de la maintenance prédictive (on intervient avant, grâce au modèle). "
               "Toutes les valeurs sont des hypothèses : remplacez-les par les chiffres de votre usine.")
    _, y, proba = jeu_de_test()
    d = Hypotheses()
    with st.sidebar:
        st.header("Hypothèses de coût")
        h = Hypotheses(
            duree_arret_panne_h=st.number_input("Durée d'arrêt après une panne (h)", 0.0, 72.0, d.duree_arret_panne_h, 0.5),
            cout_horaire_arret=st.number_input("Production perdue par heure d'arrêt (€)", 0.0, 10_000.0, d.cout_horaire_arret, 50.0),
            cout_reparation=st.number_input("Réparation après panne (€)", 0.0, 50_000.0, d.cout_reparation, 50.0),
            cout_piece_rebutee=st.number_input("Pièce rebutée (€)", 0.0, 10_000.0, d.cout_piece_rebutee, 10.0),
            cout_intervention_preventive=st.number_input("Intervention préventive (€)", 0.0, 10_000.0, d.cout_intervention_preventive, 10.0),
            cout_fausse_alerte=st.number_input("Fausse alerte (€)", 0.0, 5_000.0, d.cout_fausse_alerte, 10.0),
            cout_solution_an=st.number_input("Coût annuel de la solution (€)", 0.0, 500_000.0, d.cout_solution_an, 500.0),
            operations_par_an=int(st.number_input("Opérations surveillées par an", 1_000, 1_000_000, d.operations_par_an, 1_000)),
        )
    seuil = st.slider("Seuil d'alerte du modèle", 0.02, 0.95, round(SEUIL, 2), 0.01,
                      help="Plus le seuil est bas, plus le modèle alerte : moins de pannes manquées, plus de fausses alertes.")
    b = bilan(y, proba, seuil, h)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Coût d'une panne imprévue", euros(h.cout_panne))
    c2.metric("Corrective seule", euros(b["cout_corrective"]))
    c3.metric("Avec le modèle", euros(b["cout_predictive"]))
    c4.metric("Gain annuel", euros(b["gain"]), delta=f"{b['reduction'] * 100:.0f} % de réduction",
              delta_color="normal" if b["gain"] >= 0 else "inverse")

    c1, c2, c3 = st.columns(3)
    c1.metric("Pannes évitées / an", f"{b['pannes_evitees']:.0f} sur {b['pannes_par_an']:.0f}")
    c2.metric("Pannes manquées / an", f"{b['pannes_manquees']:.0f}")
    c3.metric("Fausses alertes / an", f"{b['fausses_alertes']:.0f}")

    g, dr = st.columns(2)
    with g:
        st.subheader("Coût selon le seuil d'alerte")
        c = courbe_couts(y, proba, h)
        c["cout_k"] = c["cout_predictive"] / 1000
        ligne = alt.Chart(c).mark_line(color=BLEU, strokeWidth=3).encode(
            x=alt.X("seuil:Q", title="Seuil d'alerte"), y=alt.Y("cout_k:Q", title="Coût annuel (milliers d'€)"),
            tooltip=[alt.Tooltip("seuil", format=".2f", title="Seuil"),
                     alt.Tooltip("cout_k", format=".1f", title="Coût (k€)"),
                     alt.Tooltip("fausses_alertes", format=".0f", title="Fausses alertes")])
        corr = alt.Chart(pd.DataFrame({"y": [b["cout_corrective"] / 1000]})).mark_rule(color=ROUGE, strokeDash=[6, 4]).encode(y="y:Q")
        actu = alt.Chart(pd.DataFrame({"x": [seuil]})).mark_rule(color=ORANGE).encode(x="x:Q")
        st.altair_chart((ligne + corr + actu).properties(height=300), width="stretch")
        st.caption("Ligne rouge : maintenance corrective seule. Ligne orange : seuil choisi.")
    with dr:
        st.subheader("Répartition du coût avec le modèle")
        postes = ["Pannes manquées", "Interventions préventives", "Fausses alertes", "Coût de la solution"]
        det = pd.DataFrame({"poste": postes,
                            "cout": [b["detail_predictive"][k] / 1000 for k in ["pannes_manquees", "interventions_preventives",
                                                                                "fausses_alertes", "solution"]]})
        barres = alt.Chart(det).mark_bar().encode(
            x=alt.X("cout:Q", title="Coût annuel (milliers d'€)"), y=alt.Y("poste:N", sort=postes, title=None),
            color=alt.Color("poste:N", legend=None, scale=alt.Scale(domain=postes, range=[ROUGE, BLEU, ORANGE, GRIS])),
            tooltip=[alt.Tooltip("poste", title="Poste"), alt.Tooltip("cout", format=".1f", title="Coût (k€)")])
        st.altair_chart(barres.properties(height=300), width="stretch")
    st.caption("Calcul réalisé à partir des prédictions du modèle sur 2 000 relevés jamais vus à l'entraînement, "
               "ramenées au nombre d'opérations annuel.")


# ---------------------------------------------------------------------------- Page 5 : à propos (F17)
def page_a_propos():
    meta = charger_metadata()
    t = meta["test"]
    st.title("ℹ️ À propos de PrédiMaint")
    st.markdown("""
**PrédiMaint** est un outil d'aide à la décision pour la **maintenance prédictive** d'un atelier d'usinage.
À partir des mesures des capteurs d'une machine-outil, il estime le risque de panne, identifie le type de panne
probable, explique sa décision et recommande une action de maintenance. Il chiffre aussi le gain économique
par rapport à une maintenance uniquement corrective.
""")
    st.subheader("Performances du modèle (sur 2 000 relevés jamais vus)")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Pannes détectées (rappel)", pct(t["rappel"]), help="Objectif ≥ 85 %")
    c2.metric("Alertes justifiées (précision)", pct(t["precision"]), help="Objectif ≥ 70 %")
    c3.metric("F1", f"{t['f1']:.2f}".replace(".", ","), help="Objectif ≥ 0,75")
    c4.metric("Bon type de panne", pct(meta["type_correct"]))
    st.markdown(f"""
Modèle : **{meta['modele']}**, entraîné sur la gamme, 5 capteurs et 3 variables issues de la physique de l'usinage
(écart de température, puissance, contrainte usure × couple). Seuil d'alerte : **{pct(meta['seuil_alerte'])}**.

### Données
**AI4I 2020 Predictive Maintenance Dataset** — UCI Machine Learning Repository, S. Matzka (2020),
DOI [10.24432/C5HS5C](https://doi.org/10.24432/C5HS5C), licence CC BY 4.0. 10 000 relevés, 339 pannes (3,4 %).

### Limites à connaître
- Les données sont **synthétiques** : certaines pannes y suivent des règles exactes. Sur une vraie usine, les
  performances seraient plus faibles et le modèle devrait être réentraîné sur ses propres données.
- Les **casses d'outil** surviennent au hasard entre 200 et 250 min d'usure : l'application recommande un
  changement préventif dans cette zone plutôt que d'essayer de prédire l'instant exact.
- Les **pannes aléatoires** ne peuvent pas être anticipées par les capteurs.
- Les **coûts** de la page Économie sont des hypothèses modifiables.

### Auteur
Jean de Dieu Riche TCHIBOUANGA — technicien en maintenance industrielle en reconversion vers la data et l'IA.
""")


# ---------------------------------------------------------------------------- Page 6 : intervention guidée
def transmettre_machine(mesures: pd.DataFrame) -> None:
    """Envoie la machine affichée vers la page Intervention guidée."""
    st.session_state["intervention_machine"] = mesures.iloc[0].to_dict()
    st.session_state["intervention_n"] = st.session_state.get("intervention_n", 0) + 1
    st.switch_page(PAGE_INTERVENTION)


def diagnostic_machine(mesures: pd.DataFrame) -> dict:
    risque = float(risques(mesures)[0])
    code_type = type_probable(MODELE_TYPE, mesures, ENTREES).iloc[0]["code"] if risque >= SEUIL else None
    return {"risque": risque, "niveau": niveau(risque)[0], "type": code_type}


def page_intervention():
    fiches = charger_fiches()
    st.title("🧰 Intervention guidée")
    st.caption("À partir du diagnostic, l'application déroule la bonne procédure : consignation, protection, "
               "intervention, puis remise en service. Cochez chaque étape et téléchargez le compte rendu.")
    st.warning("Procédures **types** rédigées pour ce projet de démonstration : dans une usine, elles sont "
               "remplacées par les procédures de l'entreprise, qui restent la référence.", icon="⚠️")
    guide = fiches["GUIDE-01"]
    with st.expander(f"📖 {guide.code} — {guide.titre}"):
        st.markdown("\n".join(f"{i}. {e}" for i, e in enumerate(guide.etapes, 1)))

    n = st.session_state.get("intervention_n", 0)
    transmise = st.session_state.get("intervention_machine")
    st.subheader("1. Machine")
    if transmise:
        st.caption("Mesures transmises depuis la page Diagnostic (modifiables).")
    mesures = saisie_machine(f"int{n}", transmise)
    diag = diagnostic_machine(mesures)
    c1, c2, c3 = st.columns(3)
    c1.metric("Risque de panne", pct(diag["risque"]))
    with c2:
        badge(diag["niveau"], niveau(diag["risque"])[1])
    c3.metric("Panne probable", NOMS_MODES[diag["type"]] if diag["type"] else "—")

    st.subheader("2. Fiche d'intervention")
    propose = choisir_fiche(diag["risque"], SEUIL, diag["type"], float(mesures["usure_outil"].iloc[0]), ZONE_USURE)
    codes = list(FICHE_PAR_TYPE.values())
    if propose is None:
        st.success("Aucune intervention n'est nécessaire : pas d'alerte et outil hors de la zone d'usure.")
        if not st.toggle("Réaliser quand même une intervention (inspection, changement d'outil…)",
                         key=f"int{n}_force"):
            return
        propose = FICHE_PAR_TYPE["RNF"]
    else:
        raison = ("type de panne prédit par le modèle" if diag["risque"] >= SEUIL
                  else f"usure de l'outil ≥ {ZONE_USURE} min (règle préventive)")
        st.info(f"Fiche proposée : **{propose} — {fiches[propose].titre}** ({raison}).")
    code = st.selectbox("Fiche à suivre", codes, index=codes.index(propose),
                        format_func=lambda c: f"{c} — {fiches[c].titre}", key=f"int{n}_fiche_{propose}")

    st.subheader("3. Déroulé")
    sequence = deroule(code)
    faites = {}
    for i, fiche in enumerate(sequence, 1):
        if i > 1 and not all(faites[sequence[0].code]):
            st.info("🔒 Les étapes suivantes s'affichent une fois la **consignation** (SEC-01) entièrement validée.")
            for f in sequence[i - 1:]:
                faites[f.code] = [False] * len(f.etapes)
            break
        with st.container(border=True):
            st.markdown(f"#### {i}. {fiche.code} — {fiche.titre}")
            st.caption(f"⏱️ {fiche.meta.get('Durée estimée', '—')} · 👷 {fiche.meta.get('Intervenant', '—')}")
            with st.expander("Quand l'utiliser · Sécurité · Outillage"):
                for nom in ["Quand l'utiliser", "Sécurité", "Outillage et pièces"]:
                    st.markdown(f"**{nom}**\n\n" + "\n".join(f"- {e}" for e in fiche.section(nom)))
            faites[fiche.code] = [st.checkbox(f"{j}. {e}", key=f"int{n}_{code}_{fiche.code}_{j}")
                                  for j, e in enumerate(fiche.etapes, 1)]
            st.markdown("**Vérification** : " + " · ".join(fiche.section("Vérification")))

    total = sum(len(v) for v in faites.values())
    cochees = sum(sum(v) for v in faites.values())
    st.progress(cochees / total if total else 0.0, text=f"Avancement : {cochees} étapes sur {total}")
    if total and cochees == total:
        st.success("✅ Intervention terminée. Relevez les nouvelles mesures et relancez un diagnostic.")

    st.subheader("4. Compte rendu")
    c1, c2 = st.columns([1, 2])
    technicien = c1.text_input("Technicien", key=f"int{n}_tech")
    observations = c2.text_area("Observations (pièces changées, anomalies…)", key=f"int{n}_obs", height=100)
    texte = compte_rendu(mesures.iloc[0].to_dict(), diag, code, faites, technicien, observations)
    st.download_button("📄 Télécharger le compte rendu", texte.encode("utf-8"),
                       f"compte_rendu_{code}_{datetime.now():%Y%m%d_%H%M}.md", "text/markdown")
    with st.expander("Aperçu du compte rendu"):
        st.markdown(texte)


# ---------------------------------------------------------------------------- Page 7 : surveillance en continu
@st.cache_data
def machines_simulees() -> dict:
    return machines(flux_de_test(MODELE, MODELE_TYPE, ENTREES))


def page_surveillance():
    st.title("📡 Surveillance en continu (simulation)")
    st.caption("Dans une usine, les mesures arrivent automatiquement des capteurs : personne ne les saisit. "
               "Cette page le simule : des relevés réels défilent sur 3 machines, le modèle calcule le risque "
               "à chaque nouveau relevé et une alerte apparaît dès qu'une machine passe le seuil.")
    with st.expander("ℹ️ Comment fonctionne cette simulation, et ses limites"):
        st.markdown(
            "- **Les relevés** viennent du jeu de test AI4I 2020 (jamais vus par le modèle), rejoués dans leur "
            "ordre d'origine. Chaque machine reçoit 30 relevés successifs.\n"
            "- **Dans une vraie usine**, ils viendraient des capteurs via la commande numérique ou un automate, "
            "puis une passerelle IoT ; le calcul serait identique.\n"
            "- **La vérité terrain est connue** : une croix rouge marque chaque relevé où une panne a réellement "
            "eu lieu, pour juger le modèle.\n"
            "- **Limite** : dans ce jeu de données, chaque relevé est indépendant, sans dégradation progressive. "
            "L'alerte apparaît donc au relevé où les conditions de panne sont réunies, c'est-à-dire **avant de "
            "lancer l'opération à risque**, et non plusieurs heures à l'avance. Prévoir une panne longtemps à "
            "l'avance demanderait des mesures suivies dans le temps (durée de vie restante).")

    simu = machines_simulees()
    total = max(len(m) for m in simu.values())
    st.session_state.setdefault("surv_pos", 0)
    st.session_state.setdefault("surv_marche", False)

    # Les boutons agissent via on_click : l'état est mis à jour AVANT l'affichage, donc les boutons
    # « Démarrer » et « Pause » sont toujours grisés à bon escient.
    def demarrer():
        if st.session_state["surv_pos"] >= total:
            st.session_state["surv_pos"] = 0
        st.session_state["surv_marche"] = True

    def mettre_en_pause():
        st.session_state["surv_marche"] = False

    def recommencer():
        st.session_state["surv_pos"] = 0
        st.session_state["surv_marche"] = False

    c1, c2, c3, c4 = st.columns([1, 1, 1, 2])
    c1.button("▶️ Démarrer", on_click=demarrer, disabled=st.session_state["surv_marche"], width="stretch")
    c2.button("⏸️ Pause", on_click=mettre_en_pause, disabled=not st.session_state["surv_marche"], width="stretch")
    c3.button("⏮️ Recommencer", on_click=recommencer, width="stretch")
    vitesse = c4.select_slider("Un nouveau relevé toutes les", [0.5, 1.0, 2.0, 3.0], value=1.0,
                               format_func=lambda v: f"{v:g} s")

    @st.fragment(run_every=vitesse)
    def tableau_de_bord():
        if st.session_state["surv_marche"]:
            st.session_state["surv_pos"] = min(st.session_state["surv_pos"] + 1, total)
            if st.session_state["surv_pos"] >= total:
                st.session_state["surv_marche"] = False
                st.rerun()  # rafraîchit aussi les boutons et la partie « Traiter une alerte »
        pos = st.session_state["surv_pos"]
        st.progress(pos / total, text=f"Relevé {pos} sur {total}"
                    + (" — en cours" if st.session_state["surv_marche"] else (" — terminé" if pos == total else " — en pause")))
        if pos == 0:
            st.info("Cliquez sur **Démarrer** : les relevés vont arriver automatiquement.")
            return

        colonnes = st.columns(len(simu))
        journal = []
        for col, (nom, seg) in zip(colonnes, simu.items()):
            vus = seg.iloc[:pos]
            dernier = vus.iloc[-1]
            r = float(dernier["risque"])
            with col, st.container(border=True):
                st.markdown(f"**{nom}**")
                badge(niveau(r)[0], niveau(r)[1])
                st.metric("Risque actuel", pct(r))
                st.caption(f"Gamme {dernier['gamme']} · {dernier['vitesse']:g} tr/min · {dernier['couple']:g} N·m · "
                           f"usure {dernier['usure_outil']:g} min")
                if dernier["usure_outil"] >= ZONE_USURE:
                    st.caption(f"⚠️ Outil en zone d'usure (≥ {ZONE_USURE} min) : changement préventif.")
                courbe = alt.Chart(vus).mark_line(color=BLEU, point=alt.OverlayMarkDef(size=18)).encode(
                    x=alt.X("releve:Q", title="Relevé", scale=alt.Scale(domain=[1, total])),
                    y=alt.Y("risque:Q", title="Risque", axis=alt.Axis(format="%"), scale=alt.Scale(domain=[0, 1])),
                    tooltip=[alt.Tooltip("releve", title="Relevé"), alt.Tooltip("risque", title="Risque", format=".0%")])
                seuil = alt.Chart(pd.DataFrame({"y": [SEUIL]})).mark_rule(color=ORANGE, strokeDash=[5, 4]).encode(y="y:Q")
                pannes = alt.Chart(vus[vus["panne"] == 1]).mark_point(shape="cross", color=ROUGE, size=140,
                                                                         filled=True).encode(x="releve:Q", y="risque:Q")
                st.altair_chart(alt.layer(courbe, seuil, pannes).properties(height=180), width="stretch")
                b = bilan_surveillance(vus, SEUIL)
                st.caption(f"Pannes réelles : {b['pannes']} · détectées : {b['detectees']} · "
                           f"fausses alertes : {b['fausses_alertes']}")
            for _, l in vus[vus["risque"] >= SEUIL].iterrows():
                journal.append({"Relevé": int(l["releve"]), "Machine": nom, "Risque": float(l["risque"]),
                                "Panne prévue": NOMS_MODES[l["type_prevu"]],
                                "Panne réelle ?": "oui" if l["panne"] == 1 else "non (fausse alerte)"})

        st.subheader(f"Journal des alertes ({len(journal)})")
        if journal:
            st.dataframe(pd.DataFrame(journal).sort_values(["Relevé", "Machine"], ascending=[False, True]),
                         hide_index=True, width="stretch",
                         column_config={"Risque": st.column_config.ProgressColumn(format="percent", min_value=0,
                                                                                  max_value=1)})
        else:
            st.caption("Aucune alerte pour l'instant.")
        if pos == total:
            tot = [bilan_surveillance(seg, SEUIL) for seg in simu.values()]
            st.success(f"Simulation terminée : {sum(t['detectees'] for t in tot)} pannes réelles détectées sur "
                       f"{sum(t['pannes'] for t in tot)}, {sum(t['fausses_alertes'] for t in tot)} fausses alertes, "
                       f"sur {sum(t['releves'] for t in tot)} relevés.")

    tableau_de_bord()

    st.subheader("Traiter une alerte")
    pos = st.session_state["surv_pos"]
    en_alerte = {nom: seg.iloc[pos - 1] for nom, seg in simu.items() if pos and seg.iloc[pos - 1]["risque"] >= SEUIL}
    if st.session_state["surv_marche"]:
        st.caption("Mettez la simulation en pause pour ouvrir l'intervention guidée d'une machine en alerte.")
    elif not en_alerte:
        st.caption("Aucune machine en alerte au relevé actuel.")
    else:
        nom = st.selectbox("Machine en alerte", list(en_alerte))
        if st.button("🧰 Lancer l'intervention guidée pour cette machine", type="primary"):
            l = en_alerte[nom]
            transmettre_machine(pd.DataFrame([{c: l[c] for c in ["gamme", "temp_air", "temp_process", "vitesse",
                                                                  "couple", "usure_outil"]}]))


PAGE_INTERVENTION = st.Page(page_intervention, title="Intervention guidée", icon="🧰", url_path="intervention")
pages = [
    st.Page(page_diagnostic, title="Diagnostic d'une machine", icon="🔧", url_path="diagnostic", default=True),
    st.Page(page_lot, title="Analyse d'un lot", icon="📋", url_path="lot"),
    PAGE_INTERVENTION,
    st.Page(page_surveillance, title="Surveillance en continu", icon="📡", url_path="surveillance"),
    st.Page(page_simulation, title="Simulation", icon="🔬", url_path="simulation"),
    st.Page(page_economie, title="Économie", icon="💶", url_path="economie"),
    st.Page(page_a_propos, title="À propos", icon="ℹ️", url_path="a-propos"),
]
with st.sidebar:
    st.markdown("## 🏭 PrédiMaint")
    st.caption("Maintenance prédictive d'un atelier d'usinage")
st.navigation(pages).run()
