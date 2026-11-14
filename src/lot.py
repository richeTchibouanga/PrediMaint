"""Lecture et analyse d'un lot de relevés (fonction F14), utilisées par l'application et par les tests."""
import numpy as np
import pandas as pd

from .donnees import CAPTEURS, NOMS_MODES, RENOMMAGE, ajouter_variables
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
        df[c] = pd.to_numeric(df[c], errors="coerce")
    if df[CAPTEURS].isna().any().any():
        raise ValueError("Certaines mesures sont vides ou ne sont pas des nombres.")
    return df


def analyser_lot(df: pd.DataFrame, modele, modele_type, entrees: list[str], seuil: float) -> pd.DataFrame:
    """Risque, niveau, panne probable et action pour chaque machine, de la plus à la moins risquée."""
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
    return out.sort_values("risque", ascending=False, ignore_index=True)
