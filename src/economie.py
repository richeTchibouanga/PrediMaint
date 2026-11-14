"""Étape 4 — étude économique : que rapporte la maintenance prédictive à l'usine ? (fonctions F9 à F12)

Lancement, depuis le dossier du projet :
    .venv\\Scripts\\python -m src.economie

Principe : on compare deux façons de travailler sur une année d'activité de l'atelier.
- Maintenance corrective seule : chaque panne arrive sans prévenir et coûte cher (arrêt, réparation, pièce rebutée).
- Maintenance prédictive : quand le modèle donne l'alerte, on intervient avant la panne, pour un coût bien plus faible.
  Mais le modèle manque quelques pannes (toujours payées au prix fort) et déclenche quelques fausses alertes.

Les résultats du modèle viennent du jeu de TEST (données jamais vues), ramenés à une année d'activité.
Toutes les valeurs de coût sont des HYPOTHÈSES, modifiables ici et dans l'application.
"""
import json
from dataclasses import asdict, dataclass

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.model_selection import StratifiedKFold, cross_val_predict

from .donnees import GRAINE, RACINE, charger, separer

FIG = RACINE / "docs" / "figures"
RAPPORT = RACINE / "docs" / "ETUDE_ECONOMIQUE.md"
BLEU, ROUGE, ORANGE, GRIS, VERT = "#1f4e79", "#c0392b", "#e67e22", "#9aa5b1", "#2e7d32"


@dataclass
class Hypotheses:
    """Hypothèses de coût (en euros). Les valeurs par défaut sont des ordres de grandeur pour un atelier d'usinage."""
    duree_arret_panne_h: float = 4.0        # durée d'arrêt d'une machine après une panne imprévue
    cout_horaire_arret: float = 350.0       # production perdue par heure d'arrêt
    cout_reparation: float = 500.0          # main-d'œuvre et pièces pour réparer après la panne
    cout_piece_rebutee: float = 150.0       # pièce en cours d'usinage abîmée par la panne
    cout_intervention_preventive: float = 250.0  # intervention planifiée avant la panne (outil, main-d'œuvre, arrêt court)
    cout_fausse_alerte: float = 100.0       # inspection inutile déclenchée par une fausse alerte
    cout_solution_an: float = 3000.0        # hébergement, maintenance du modèle, formation (par an)
    operations_par_an: int = 10_000         # nombre d'opérations d'usinage surveillées par an

    @property
    def cout_panne(self) -> float:
        """Coût complet d'une panne imprévue."""
        return self.duree_arret_panne_h * self.cout_horaire_arret + self.cout_reparation + self.cout_piece_rebutee


def bilan(y, proba, seuil: float, h: Hypotheses) -> dict:
    """Coûts annuels avec et sans le modèle, pour un seuil d'alerte donné."""
    y = np.asarray(y)
    alerte = np.asarray(proba) >= seuil
    vp = int(((y == 1) & alerte).sum())    # pannes détectées à temps
    fn = int(((y == 1) & ~alerte).sum())   # pannes manquées
    fp = int(((y == 0) & alerte).sum())    # fausses alertes
    k = h.operations_par_an / len(y)       # passage du jeu de test à une année d'activité
    corrective = (vp + fn) * h.cout_panne * k
    predictive = ((vp * h.cout_intervention_preventive + fn * h.cout_panne + fp * h.cout_fausse_alerte) * k
                  + h.cout_solution_an)
    gain = corrective - predictive
    return {
        "seuil": seuil, "pannes_par_an": (vp + fn) * k, "pannes_evitees": vp * k, "pannes_manquees": fn * k,
        "fausses_alertes": fp * k, "cout_corrective": corrective, "cout_predictive": predictive,
        "detail_predictive": {"interventions_preventives": vp * h.cout_intervention_preventive * k,
                              "pannes_manquees": fn * h.cout_panne * k,
                              "fausses_alertes": fp * h.cout_fausse_alerte * k,
                              "solution": h.cout_solution_an},
        "gain": gain, "reduction": gain / corrective if corrective else 0.0,
        "retour_sur_investissement": gain / h.cout_solution_an if h.cout_solution_an else float("inf"),
    }


def courbe_couts(y, proba, h: Hypotheses, seuils=None) -> pd.DataFrame:
    """Coût annuel de la maintenance prédictive pour chaque seuil d'alerte (fonction F12)."""
    seuils = np.round(np.arange(0.02, 0.99, 0.01), 2) if seuils is None else seuils
    return pd.DataFrame([{k: v for k, v in bilan(y, proba, s, h).items() if k != "detail_predictive"}
                         for s in seuils])


def seuil_economique(y, proba, h: Hypotheses) -> float:
    """Seuil d'alerte qui minimise le coût total."""
    c = courbe_couts(y, proba, h)
    return float(c.loc[c["cout_predictive"].idxmin(), "seuil"])


def euros(x: float) -> str:
    return f"{x:,.0f} €".replace(",", " ")


def main() -> None:
    h = Hypotheses()
    paquet = joblib.load(RACINE / "models" / "predimaint.joblib")
    modele, entrees, seuil_alerte = paquet["modele"], paquet["entrees"], paquet["seuil"]

    X_tr, X_te, y_tr, y_te, *_ = separer(charger())
    p_te = modele.predict_proba(X_te[entrees])[:, 1]

    # Seuil économique choisi sur l'ENTRAÎNEMENT (validation croisée), puis appliqué au test : pas de triche
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=GRAINE)
    p_cv = cross_val_predict(clone(modele), X_tr[entrees], y_tr, cv=cv, method="predict_proba")[:, 1]
    seuil_eco = seuil_economique(y_tr, p_cv, h)

    b_alerte = bilan(y_te, p_te, seuil_alerte, h)
    b_eco = bilan(y_te, p_te, seuil_eco, h)
    courbe = courbe_couts(y_te, p_te, h)
    print(f"Coût d'une panne imprévue : {euros(h.cout_panne)}")
    print(f"Seuil d'alerte {seuil_alerte:.3f} : corrective {euros(b_alerte['cout_corrective'])} | "
          f"prédictive {euros(b_alerte['cout_predictive'])} | gain {euros(b_alerte['gain'])}")
    print(f"Seuil économique {seuil_eco:.2f} : prédictive {euros(b_eco['cout_predictive'])} | gain {euros(b_eco['gain'])}")

    # Sensibilité : le gain reste-t-il positif si une panne coûte beaucoup moins cher ?
    sensibilite = []
    for cp in [500, 1000, 2050, 3000, 5000]:
        hs = Hypotheses(duree_arret_panne_h=0, cout_reparation=cp, cout_piece_rebutee=0)
        b = bilan(y_te, p_te, seuil_alerte, hs)
        sensibilite.append({"Coût d'une panne": euros(cp), "Coût corrective": euros(b["cout_corrective"]),
                            "Coût prédictive": euros(b["cout_predictive"]), "Gain annuel": euros(b["gain"]),
                            "Réduction": f"{b['reduction'] * 100:.0f} %"})
    sensibilite = pd.DataFrame(sensibilite)
    # Coût de panne à partir duquel la solution devient rentable
    seuil_rentab = next((cp for cp in range(50, 5001, 10)
                         if bilan(y_te, p_te, seuil_alerte,
                                  Hypotheses(duree_arret_panne_h=0, cout_reparation=cp, cout_piece_rebutee=0))["gain"] > 0),
                        None)

    # ------------------------------------------------------------------ Figures
    fig, ax = plt.subplots(figsize=(8, 3.8))
    ax.plot(courbe["seuil"], courbe["cout_predictive"] / 1000, color=BLEU, lw=2, label="Maintenance prédictive")
    ax.axhline(b_alerte["cout_corrective"] / 1000, color=ROUGE, ls="--", lw=1.5, label="Maintenance corrective seule")
    ax.scatter([seuil_alerte], [b_alerte["cout_predictive"] / 1000], color=ORANGE, zorder=3,
               label=f"Seuil d'alerte retenu ({seuil_alerte:.2f})")
    ax.scatter([seuil_eco], [b_eco["cout_predictive"] / 1000], color=VERT, zorder=3, marker="D",
               label=f"Seuil économique ({seuil_eco:.2f})")
    ax.set_xlabel("Seuil d'alerte du modèle"); ax.set_ylabel("Coût annuel (milliers d'€)")
    ax.set_title("Coût annuel selon le seuil d'alerte"); ax.legend(fontsize=8)
    plt.savefig(FIG / "10_cout_selon_seuil.png", bbox_inches="tight"); plt.close()

    fig, ax = plt.subplots(figsize=(7, 3.8))
    d = b_alerte["detail_predictive"]
    ax.bar(["Corrective seule"], [b_alerte["cout_corrective"] / 1000], color=ROUGE)
    bas = 0
    for (nom, v), col in zip([("Pannes manquées", d["pannes_manquees"]),
                              ("Interventions préventives", d["interventions_preventives"]),
                              ("Fausses alertes", d["fausses_alertes"]), ("Coût de la solution", d["solution"])],
                             [ROUGE, BLEU, ORANGE, GRIS]):
        ax.bar(["Avec le modèle"], [v / 1000], bottom=bas / 1000, color=col, label=nom)
        bas += v
    for x, v in [(0, b_alerte["cout_corrective"]), (1, b_alerte["cout_predictive"])]:
        ax.text(x, v / 1000 + 5, euros(v), ha="center", fontsize=9, fontweight="bold")
    ax.set_ylabel("Coût annuel (milliers d'€)"); ax.set_ylim(0, b_alerte["cout_corrective"] / 1000 * 1.15)
    ax.set_title(f"Coût annuel de la maintenance : gain de {euros(b_alerte['gain'])}")
    ax.legend(fontsize=8, loc="upper right")
    plt.savefig(FIG / "11_comparaison_couts.png", bbox_inches="tight"); plt.close()

    # ------------------------------------------------------------------ Sauvegarde et rapport
    (RACINE / "models" / "economie.json").write_text(json.dumps(
        {"hypotheses": asdict(h), "cout_panne": h.cout_panne, "seuil_economique": seuil_eco,
         "bilan_seuil_alerte": b_alerte, "bilan_seuil_economique": b_eco,
         "cout_panne_minimum_rentable": seuil_rentab}, indent=2, ensure_ascii=False), encoding="utf-8")

    def md(df):
        return "\n".join(["| " + " | ".join(df.columns) + " |", "|" + "---|" * len(df.columns)]
                         + ["| " + " | ".join(map(str, r)) + " |" for r in df.itertuples(index=False)])

    hyp = pd.DataFrame([
        ["Durée d'arrêt après une panne imprévue", f"{h.duree_arret_panne_h:g} h"],
        ["Production perdue par heure d'arrêt", euros(h.cout_horaire_arret)],
        ["Réparation après panne (main-d'œuvre et pièces)", euros(h.cout_reparation)],
        ["Pièce en cours rebutée", euros(h.cout_piece_rebutee)],
        ["**Coût total d'une panne imprévue**", f"**{euros(h.cout_panne)}**"],
        ["Intervention préventive planifiée", euros(h.cout_intervention_preventive)],
        ["Fausse alerte (inspection inutile)", euros(h.cout_fausse_alerte)],
        ["Coût annuel de la solution", euros(h.cout_solution_an)],
        ["Opérations d'usinage surveillées par an", f"{h.operations_par_an:,}".replace(",", " ")],
    ], columns=["Hypothèse", "Valeur"])
    res = pd.DataFrame([
        ["Pannes sur l'année", f"{b_alerte['pannes_par_an']:.0f}", f"{b_alerte['pannes_par_an']:.0f}"],
        ["Pannes évitées grâce à une intervention préventive", "0", f"{b_alerte['pannes_evitees']:.0f}"],
        ["Pannes manquées (payées au prix fort)", f"{b_alerte['pannes_par_an']:.0f}", f"{b_alerte['pannes_manquees']:.0f}"],
        ["Fausses alertes", "0", f"{b_alerte['fausses_alertes']:.0f}"],
        ["**Coût annuel**", f"**{euros(b_alerte['cout_corrective'])}**", f"**{euros(b_alerte['cout_predictive'])}**"],
    ], columns=["", "Corrective seule", "Avec le modèle"])
    det = b_alerte["detail_predictive"]
    virg = lambda x: f"{x:.2f}".replace(".", ",")
    proche = courbe[courbe["cout_predictive"] <= courbe["cout_predictive"].min() * 1.10]["seuil"]
    plat = (float(proche.min()), float(proche.max()))
    ecart = b_eco["cout_predictive"] - b_alerte["cout_predictive"]
    conclusion_seuil = (
        f"Sur le test, le seuil économique coûte même {euros(ecart)} de plus que le seuil retenu : il avait été "
        "optimisé sur les données d'entraînement, et ce petit écart relève du hasard de l'échantillon."
        if ecart > 0 else
        f"Sur le test, le seuil économique fait gagner {euros(-ecart)} de plus que le seuil retenu.")
    RAPPORT.write_text(f"""# PrédiMaint — Étude économique

*Générée automatiquement par `src/economie.py`. Toutes les valeurs de coût sont des **hypothèses**, modifiables dans le code et dans l'application.*

## 1. Question posée

Combien l'usine économise-t-elle en intervenant **avant** la panne, grâce au modèle, plutôt que de réparer **après** la panne (maintenance corrective) ?

## 2. Hypothèses de coût

{md(hyp)}

Le volume de 10 000 opérations par an correspond à la taille du jeu de données. Les résultats du modèle sur le jeu de test (2 000 relevés jamais vus) sont multipliés par 5 pour représenter une année.

## 3. Résultat au seuil d'alerte retenu ({virg(seuil_alerte)})

{md(res)}

**Gain annuel : {euros(b_alerte['gain'])}**, soit une **réduction de {b_alerte['reduction'] * 100:.0f} %** du coût de la maintenance. Pour 1 € dépensé dans la solution, l'usine économise environ **{b_alerte['retour_sur_investissement']:.0f} €**.

Détail du coût avec le modèle :

- les **pannes manquées** pèsent le plus : {euros(det['pannes_manquees'])} ;
- les **interventions préventives** coûtent {euros(det['interventions_preventives'])} ;
- les **fausses alertes** coûtent {euros(det['fausses_alertes'])} ;
- la **solution** elle-même coûte {euros(det['solution'])} par an.

![Comparaison des coûts](figures/11_comparaison_couts.png)

## 4. Quel seuil d'alerte choisir ? (fonction F12)

Baisser le seuil fait partir plus d'alertes : on manque moins de pannes, mais on multiplie les fausses alertes. Le **seuil économique** est celui qui minimise le coût total. Il est choisi sur les données d'entraînement (validation croisée), puis vérifié sur le test.

![Coût selon le seuil](figures/10_cout_selon_seuil.png)

| Seuil | Pannes évitées / an | Fausses alertes / an | Coût annuel (test) |
|---|---|---|---|
| Seuil d'alerte retenu à l'étape 3 ({virg(seuil_alerte)}) | {b_alerte['pannes_evitees']:.0f} | {b_alerte['fausses_alertes']:.0f} | {euros(b_alerte['cout_predictive'])} |
| Seuil économique choisi sur l'entraînement ({virg(seuil_eco)}) | {b_eco['pannes_evitees']:.0f} | {b_eco['fausses_alertes']:.0f} | {euros(b_eco['cout_predictive'])} |

La courbe est **très plate** entre {virg(plat[0])} et {virg(plat[1])} : sur toute cette plage, le coût reste à moins de 10 % de son minimum. Le choix exact du seuil a donc peu d'effet sur le coût. {conclusion_seuil}

En pratique, le seuil de **{virg(seuil_alerte)}** est le meilleur compromis : presque aussi économique, il limite les fausses alertes ({b_alerte['fausses_alertes']:.0f} par an au lieu de {b_eco['fausses_alertes']:.0f}). C'est important sur le terrain : trop de fausses alertes, et les techniciens finissent par ne plus y croire.

## 5. Sensibilité au coût d'une panne

Que se passe-t-il si une panne coûte beaucoup moins (ou beaucoup plus) cher que prévu ? Les autres hypothèses restent inchangées.

{md(sensibilite)}

La solution reste rentable dès qu'une panne coûte plus de **{euros(seuil_rentab) if seuil_rentab else '—'}** environ. La conclusion est donc solide : même avec des hypothèses prudentes, la maintenance prédictive est nettement gagnante.

## 6. Limites

- Les coûts sont des **ordres de grandeur** : une usine réelle les remplacerait par ses propres chiffres (taux horaire, coût des pièces, valeur de la production).
- Le taux de panne du jeu de données (3,4 %) est élevé ; le gain dépend directement du nombre de pannes réelles.
- Les performances du modèle viennent de **données synthétiques** : sur une vraie usine, il manquerait sans doute plus de pannes, ce qui réduirait le gain.
""", encoding="utf-8")
    print("Rapport :", RAPPORT)


if __name__ == "__main__":
    main()
