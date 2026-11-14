"""Surveillance en continu SIMULÉE : des relevés réels défilent comme s'ils arrivaient des capteurs.

Les relevés viennent du jeu de TEST (jamais vus par le modèle), rangés dans leur ordre d'origine (UDI).
Trois extraits de 30 relevés jouent le rôle de trois machines de l'atelier. À chaque « top » de l'horloge
simulée, chaque machine reçoit un nouveau relevé, et le modèle calcule le risque, sans aucune saisie.

Limite à connaître : dans ce jeu de données, chaque relevé est indépendant. Les mesures ne se dégradent pas
progressivement avant une panne ; l'alerte apparaît au relevé où les conditions de panne sont réunies.
"""
import numpy as np
import pandas as pd

from .donnees import MODES, charger, separer

# Machine simulée → (premier relevé de l'extrait, nombre de relevés)
SEGMENTS = {
    "Machine 1": (30, 30),
    "Machine 2": (750, 30),
    "Machine 3": (1640, 30),
}


def flux_de_test(modele, modele_type, entrees) -> pd.DataFrame:
    """Relevés du jeu de test dans leur ordre d'origine, avec le risque et le type de panne prévus."""
    _, X_te, _, y_te, _, _, _, d_te = separer(charger())
    probas_types = np.column_stack([e.predict_proba(X_te[entrees])[:, 1] for e in modele_type.estimators_])
    flux = d_te.assign(risque=modele.predict_proba(X_te[entrees])[:, 1],
                       type_prevu=np.array(MODES)[probas_types.argmax(axis=1)])
    return flux.sort_values("UDI").reset_index(drop=True)


def machines(flux: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Les extraits du flux qui jouent le rôle des machines, numérotés « relevé 1, 2, 3… »."""
    out = {}
    for nom, (debut, longueur) in SEGMENTS.items():
        seg = flux.iloc[debut:debut + longueur].reset_index(drop=True)
        out[nom] = seg.assign(releve=np.arange(1, len(seg) + 1))
    return out


def bilan(seg: pd.DataFrame, seuil: float) -> dict:
    """Pannes réelles détectées ou manquées, et fausses alertes, sur les relevés déjà reçus."""
    alerte = seg["risque"] >= seuil
    panne = seg["panne"] == 1
    return {"releves": len(seg), "pannes": int(panne.sum()), "detectees": int((alerte & panne).sum()),
            "manquees": int((~alerte & panne).sum()), "fausses_alertes": int((alerte & ~panne).sum())}
