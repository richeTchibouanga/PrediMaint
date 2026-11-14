"""Explication d'une prédiction et action de maintenance recommandée (fonctions F8 et F13).

Méthode d'explication, simple et compréhensible par un technicien :
pour chaque mesure, on la remplace par une valeur « normale » (la médiane des machines sans panne),
on recalcule le risque, et on regarde de combien il baisse. Plus la baisse est forte,
plus cette mesure est responsable du risque.
"""
import pandas as pd

from .donnees import CAPTEURS, MODES, NOMS_MODES, ajouter_variables

LIBELLES = {
    "gamme": "Gamme du produit", "temp_air": "Température de l'air",
    "temp_process": "Température du procédé", "vitesse": "Vitesse de rotation",
    "couple": "Couple", "usure_outil": "Usure de l'outil",
}

ACTIONS = {
    "TWF": "Planifier le changement d'outil.",
    "HDF": "Vérifier le refroidissement et la ventilation ; augmenter la vitesse si possible.",
    "PWF": "Contrôler les paramètres de coupe et l'alimentation du moteur.",
    "OSF": "Réduire la charge et changer l'outil usé.",
}


def probabilite(modele, mesures: pd.DataFrame, entrees: list[str]) -> float:
    """Risque de panne (entre 0 et 1) pour une seule machine décrite par ses mesures brutes."""
    return float(modele.predict_proba(ajouter_variables(mesures)[entrees])[0, 1])


def expliquer(modele, mesures: pd.DataFrame, reference: dict, entrees: list[str]) -> pd.DataFrame:
    """Contribution de chaque mesure au risque : risque actuel − risque si la mesure était normale."""
    risque = probabilite(modele, mesures, entrees)
    lignes = []
    for col in ["gamme"] + CAPTEURS:
        modifie = mesures.copy()
        modifie[col] = reference[col]
        lignes.append({
            "mesure": LIBELLES[col],
            "valeur": mesures[col].iloc[0],
            "valeur_normale": reference[col],
            "contribution": risque - probabilite(modele, modifie, entrees),
        })
    return pd.DataFrame(lignes).sort_values("contribution", ascending=False, ignore_index=True)


def type_probable(modele_type, mesures: pd.DataFrame, entrees: list[str]) -> pd.DataFrame:
    """Probabilité de chaque type de panne prévisible, du plus au moins probable."""
    x = ajouter_variables(mesures)[entrees]
    probas = [est.predict_proba(x)[0, 1] for est in modele_type.estimators_]
    return (pd.DataFrame({"code": MODES, "type": [NOMS_MODES[m] for m in MODES],
                          "probabilite": probas, "action": [ACTIONS[m] for m in MODES]})
            .sort_values("probabilite", ascending=False, ignore_index=True))
