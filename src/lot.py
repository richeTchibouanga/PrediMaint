"""Lecture et analyse d'un lot de relevés (fonction F14), utilisées par l'application et par les tests."""
import numpy as np
import pandas as pd

from .donnees import CAPTEURS, NOMS_MODES, PLAGES, RENOMMAGE, ajouter_variables
from .explication import ACTIONS

ZONE_USURE = 200  # minutes : au-delà, l'outil doit être changé par précaution (voir l'étape 3)


def niveau(risque: float, seuil: float) -> str:
    """Niveau d'alerte affiché pour un risque donné."""
    if risque >= 0.6:
        return "Alerte critique : intervenir rapidement"
    if risque >= seuil:
        return "Alerte : intervention à planifier"
    return "Pas d'alerte"


def lire_csv(fichier) -> pd.DataFrame:
    """Lit un fichier de relevés et vérifie son contenu. Lève ValueError avec un message clair en cas de problème.

    Colonnes acceptées : gamme, temp_air, temp_process, vitesse, couple, usure_outil
    (ou les noms d'origine du jeu AI4I 2020). Les autres colonnes (identifiant de machine…) sont conservées.
    Séparateur détecté automatiquement (virgule, point-virgule, tabulation) ; décimales avec point ou virgule.
    """
    df = pd.read_csv(fichier, sep=None, engine="python", encoding="utf-8-sig")
    df = df.rename(columns=RENOMMAGE)
    manquantes = [c for c in ["gamme"] + CAPTEURS if c not in df.columns]
    if manquantes:
        raise ValueError("Colonnes manquantes : " + ", ".join(manquantes))
    if df.empty:
        raise ValueError("Le fichier ne contient aucun relevé.")
    df["gamme"] = df["gamme"].astype(str).str.strip().str.upper()
    if not df["gamme"].isin(["L", "M", "H"]).all():
        raise ValueError("La colonne « gamme » ne doit contenir que L, M ou H.")
    for c in CAPTEURS:
        # Accepte la virgule décimale (« 300,5 ») produite par Excel en français, en plus du point.
        if not pd.api.types.is_numeric_dtype(df[c]):
            df[c] = df[c].astype(str).str.strip().str.replace(",", ".", regex=False)
        df[c] = pd.to_numeric(df[c], errors="coerce")
    if df[CAPTEURS].isna().any().any():
        raise ValueError("Certaines mesures sont vides ou ne sont pas des nombres.")
    return df


NIVEAU_A_VERIFIER = "Mesures à vérifier"
IDENTIFIANTS = ["machine", "UDI", "id_produit"]  # colonnes d'identification reconnues, affichées en premier
UNITES = {"temp_air": "K", "temp_process": "K", "vitesse": "tr/min", "couple": "N·m", "usure_outil": "min"}


def hors_plage(df: pd.DataFrame) -> pd.Series:
    """Pour chaque relevé, la liste des mesures hors des plages connues du modèle ('' si tout est normal).

    En dehors de ces plages, le modèle n'a jamais vu de données : son résultat ne serait pas fiable.
    Erreur la plus fréquente : une température en °C au lieu de kelvins (K = °C + 273,15).
    """
    def decrire(ligne):
        hors = [f"{c} = {ligne[c]:g} {UNITES[c]} (attendu {PLAGES[c][0]:g} à {PLAGES[c][1]:g})"
                for c in CAPTEURS if not PLAGES[c][0] <= ligne[c] <= PLAGES[c][1]]
        return " ; ".join(hors)
    return df.apply(decrire, axis=1)


def analyser_lot(df: pd.DataFrame, modele, modele_type, entrees: list[str], seuil: float) -> pd.DataFrame:
    """Risque, niveau, panne probable et action pour chaque machine.

    Les relevés aux mesures hors plage sont signalés « à vérifier » et placés en tête ;
    les autres sont classés du plus au moins risqué.
    """
    x = ajouter_variables(df)[entrees]
    r = modele.predict_proba(x)[:, 1]
    probas_types = np.column_stack([e.predict_proba(x)[:, 1] for e in modele_type.estimators_])
    codes = np.array(list(ACTIONS))[probas_types.argmax(axis=1)]
    out = df.copy()
    out.insert(0, "risque", r)
    out.insert(1, "niveau", [niveau(v, seuil) for v in r])
    out.insert(2, "panne_probable", np.where(r >= seuil, [NOMS_MODES[c] for c in codes], "—"))
    out.insert(3, "action", np.where(r >= seuil, [ACTIONS[c] for c in codes], "—"))
    usure = out["usure_outil"] >= ZONE_USURE
    out.loc[usure & (r < seuil), "action"] = "Zone d'usure : changer l'outil par précaution"
    verif = hors_plage(df).to_numpy()
    a_verifier = verif != ""
    out.loc[a_verifier, "risque"] = np.nan
    out.loc[a_verifier, "niveau"] = NIVEAU_A_VERIFIER
    out.loc[a_verifier, "panne_probable"] = "—"
    out.loc[a_verifier, "action"] = ["Corriger le relevé : " + v for v in verif[a_verifier]]
    out["_ordre"] = np.where(a_verifier, 2.0, out["risque"].fillna(0))
    out = out.sort_values("_ordre", ascending=False, ignore_index=True).drop(columns="_ordre")
    # L'identifiant de la machine (s'il existe) en première colonne : c'est ce que l'utilisateur cherche d'abord
    ident = [c for c in IDENTIFIANTS if c in out.columns]
    return out[ident + [c for c in out.columns if c not in ident]]
