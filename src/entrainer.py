"""Étape 3 — comparaison des modèles, choix du seuil d'alerte, évaluation finale et sauvegarde.

Lancement, depuis le dossier du projet :
    .venv\\Scripts\\python -m src.entrainer

Démarche :
1. Séparer les données : 80 % pour l'entraînement, 20 % gardés de côté pour le test final.
2. Sur les 80 %, comparer 3 algorithmes, avec et sans les variables dérivées (validation croisée à 5 plis).
3. Choisir le meilleur selon la PR-AUC, puis le seuil d'alerte qui garde au moins 85 % de pannes détectées.
4. Entraîner le modèle choisi sur les 80 %, puis le tester UNE SEULE FOIS sur les 20 % jamais vus.
5. Entraîner le modèle « type de panne », mesurer l'importance des variables, sauvegarder, écrire le rapport.
"""
import json
import platform
from datetime import date

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import sklearn
from sklearn.base import clone
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (average_precision_score, confusion_matrix, f1_score, precision_recall_curve,
                             precision_score, recall_score)
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.multioutput import MultiOutputClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .donnees import CAPTEURS, ENTREES, ENTREES_BRUTES, GRAINE, MODES, NOMS_MODES, RACINE, charger, separer


CIBLE_RAPPEL = 0.85
DOSSIER_MODELES = RACINE / "models"
FIG = RACINE / "docs" / "figures"
RAPPORT = RACINE / "docs" / "RESULTATS_MODELE.md"
BLEU, ROUGE, GRIS = "#1f4e79", "#c0392b", "#9aa5b1"
JEUX = {"capteurs seuls": ENTREES_BRUTES, "capteurs + variables dérivées": ENTREES}


def candidats() -> dict:
    """Les trois algorithmes comparés. Tous compensent le déséquilibre en donnant plus de poids aux pannes."""
    return {
        "Régression logistique": make_pipeline(
            StandardScaler(), LogisticRegression(class_weight="balanced", max_iter=5000)),
        "Forêt aléatoire": RandomForestClassifier(
            n_estimators=300, min_samples_leaf=2, class_weight="balanced_subsample",
            random_state=GRAINE, n_jobs=-1),
        "Gradient boosting": HistGradientBoostingClassifier(
            max_iter=300, learning_rate=0.1, class_weight="balanced", random_state=GRAINE),
    }


def metriques(y, proba, seuil: float = 0.5) -> dict:
    pred = (proba >= seuil).astype(int)
    return {"rappel": recall_score(y, pred), "precision": precision_score(y, pred, zero_division=0),
            "f1": f1_score(y, pred), "pr_auc": average_precision_score(y, proba)}


def choisir_seuil(y, proba, rappel_min: float = CIBLE_RAPPEL) -> float:
    """Parmi les seuils qui détectent au moins `rappel_min` des pannes, prend celui qui maximise le F1."""
    prec, rap, seuils = precision_recall_curve(y, proba)
    prec, rap = prec[:-1], rap[:-1]
    f1 = 2 * prec * rap / (prec + rap + 1e-12)
    possibles = np.where(rap >= rappel_min)[0]
    return float(seuils[possibles[np.argmax(f1[possibles])]])


def tableau_md(df: pd.DataFrame) -> str:
    """Tableau Markdown simple (sans dépendance supplémentaire)."""
    lignes = ["| " + " | ".join(df.columns) + " |", "|" + "---|" * len(df.columns)]
    lignes += ["| " + " | ".join(str(v) for v in row) + " |" for row in df.itertuples(index=False)]
    return "\n".join(lignes)


def pct(x: float) -> str:
    return f"{x * 100:.1f} %".replace(".", ",")


def main() -> None:
    DOSSIER_MODELES.mkdir(exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ 1. Séparation entraînement / test
    df = charger()
    X_tr, X_te, y_tr, y_te, M_tr, M_te, d_tr, d_te = separer(df)
    print(f"Entraînement : {len(X_tr)} relevés ({y_tr.sum()} pannes) | Test : {len(X_te)} relevés ({y_te.sum()} pannes)")

    # ------------------------------------------------------------------ 2. Comparaison par validation croisée
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=GRAINE)
    resultats, probas_cv = [], {}
    for jeu, colonnes in JEUX.items():
        for nom, modele in candidats().items():
            p = cross_val_predict(clone(modele), X_tr[colonnes], y_tr, cv=cv, method="predict_proba")[:, 1]
            probas_cv[(nom, jeu)] = p
            resultats.append({"Modèle": nom, "Variables": jeu, **metriques(y_tr, p)})
            print(f"  {nom:22s} | {jeu:30s} | PR-AUC {resultats[-1]['pr_auc']:.3f}")
    comparaison = pd.DataFrame(resultats)

    # ------------------------------------------------------------------ 3. Choix du modèle et du seuil
    meilleur = comparaison.loc[comparaison["pr_auc"].idxmax()]
    nom, jeu = meilleur["Modèle"], meilleur["Variables"]
    colonnes = JEUX[jeu]
    seuil = choisir_seuil(y_tr, probas_cv[(nom, jeu)])
    print(f"Modèle retenu : {nom} ({jeu}) — seuil d'alerte {seuil:.3f}")

    # ------------------------------------------------------------------ 4. Test final, une seule fois
    modele = clone(candidats()[nom]).fit(X_tr[colonnes], y_tr)
    p_te = modele.predict_proba(X_te[colonnes])[:, 1]
    alerte = (p_te >= seuil).astype(int)
    test = metriques(y_te, p_te, seuil)
    test_05 = metriques(y_te, p_te, 0.5)
    cm = confusion_matrix(y_te, alerte)
    print("Test :", {k: round(v, 3) for k, v in test.items()})

    # Détection par type de panne (sur le jeu de test)
    detection = []
    for mode in MODES + ["RNF"]:
        masque = (d_te[mode] == 1).values & (y_te == 1).values
        if masque.sum():
            detection.append({"Type de panne": NOMS_MODES[mode], "Pannes dans le test": int(masque.sum()),
                              "Détectées": int(alerte[masque].sum()), "Taux": pct(alerte[masque].mean())})
    sans_type = (y_te == 1).values & (d_te[MODES + ["RNF"]].sum(axis=1) == 0).values
    if sans_type.sum():
        detection.append({"Type de panne": "Sans type indiqué", "Pannes dans le test": int(sans_type.sum()),
                          "Détectées": int(alerte[sans_type].sum()), "Taux": pct(alerte[sans_type].mean())})
    detection = pd.DataFrame(detection)
    seulement_rnf = (y_te == 1).values & (d_te["RNF"] == 1).values & (d_te[MODES].sum(axis=1) == 0).values
    prev = (y_te == 1).values & ~seulement_rnf & ~sans_type
    rappel_previsible = alerte[prev].mean()

    # ------------------------------------------------------------------ 5. Modèle « type de panne »
    modele_type = MultiOutputClassifier(HistGradientBoostingClassifier(
        max_iter=300, class_weight="balanced", random_state=GRAINE)).fit(X_tr[colonnes], M_tr)
    avec_type = (M_te.sum(axis=1) > 0).values
    probas_types = np.column_stack([e.predict_proba(X_te[colonnes])[:, 1] for e in modele_type.estimators_])
    type_predit = np.array(MODES)[probas_types.argmax(axis=1)]
    bon_type = np.array([M_te.iloc[i][t] == 1 for i, t in enumerate(type_predit)])
    precision_type = bon_type[avec_type].mean()
    print(f"Type de panne correct (pannes avec type connu) : {precision_type:.1%}")

    # ------------------------------------------------------------------ 6. Importance des variables
    imp = permutation_importance(modele, X_te[colonnes], y_te, scoring="average_precision",
                                 n_repeats=10, random_state=GRAINE)
    importance = (pd.DataFrame({"variable": colonnes, "importance": imp.importances_mean})
                  .sort_values("importance", ascending=True))

    # ------------------------------------------------------------------ 7. Figures
    fig, ax = plt.subplots(figsize=(8, 3.6))
    piv = comparaison.pivot(index="Modèle", columns="Variables", values="pr_auc").loc[list(candidats())]
    xs = np.arange(len(piv))
    for k, (j, col) in enumerate(zip(JEUX, [GRIS, BLEU])):
        ax.bar(xs + (k - 0.5) * 0.38, piv[j], 0.38, label=j, color=col)
        for x, v in zip(xs, piv[j]):
            ax.text(x + (k - 0.5) * 0.38, v + 0.01, f"{v:.2f}", ha="center", fontsize=8)
    ax.set_xticks(xs, piv.index); ax.set_ylim(0, 1.1); ax.set_ylabel("PR-AUC (validation croisée)")
    ax.set_title("Comparaison des modèles : apport des variables dérivées"); ax.legend(fontsize=8, loc="lower right")
    plt.savefig(FIG / "07_comparaison_modeles.png", bbox_inches="tight"); plt.close()

    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    prec, rap, _ = precision_recall_curve(y_te, p_te)
    axes[0].plot(rap, prec, color=BLEU, lw=2)
    axes[0].scatter([test["rappel"]], [test["precision"]], color=ROUGE, zorder=3,
                    label=f"Seuil retenu ({seuil:.2f})")
    axes[0].set_xlabel("Rappel (pannes détectées)"); axes[0].set_ylabel("Précision (alertes justifiées)")
    axes[0].set_title(f"Courbe précision-rappel (test) — PR-AUC {test['pr_auc']:.3f}"); axes[0].legend()
    axes[1].imshow(cm, cmap="Blues")
    noms = ["Sans panne", "Panne"]
    for i in range(2):
        for j in range(2):
            axes[1].text(j, i, cm[i, j], ha="center", va="center", fontsize=14,
                         color="white" if cm[i, j] > cm.max() / 2 else "black")
    axes[1].set_xticks([0, 1], ["Pas d'alerte", "Alerte"]); axes[1].set_yticks([0, 1], noms)
    axes[1].set_xlabel("Prédiction du modèle"); axes[1].set_ylabel("Réalité"); axes[1].grid(False)
    axes[1].set_title("Matrice de confusion (test)")
    plt.savefig(FIG / "08_performance_test.png", bbox_inches="tight"); plt.close()

    fig, ax = plt.subplots(figsize=(7, 3.8))
    ax.barh(importance["variable"], importance["importance"], color=BLEU)
    ax.set_xlabel("Baisse de la PR-AUC quand la variable est brouillée")
    ax.set_title("Importance des variables (test)")
    plt.savefig(FIG / "09_importance_variables.png", bbox_inches="tight"); plt.close()

    # ------------------------------------------------------------------ 8. Sauvegarde
    sains = d_tr[y_tr.values == 0]
    reference = {c: float(sains[c].median()) for c in CAPTEURS}
    reference["gamme"] = "L"
    joblib.dump({"modele": modele, "modele_type": modele_type, "entrees": colonnes, "seuil": seuil,
                 "reference": reference, "nom_modele": nom}, DOSSIER_MODELES / "predimaint.joblib")
    meta = {
        "date": date.today().isoformat(), "modele": nom, "variables": jeu, "entrees": colonnes,
        "seuil_alerte": seuil, "test": test, "test_seuil_0_5": test_05,
        "matrice_confusion": cm.tolist(), "rappel_pannes_previsibles": float(rappel_previsible),
        "type_correct": float(precision_type), "reference": reference,
        "versions": {"python": platform.python_version(), "scikit-learn": sklearn.__version__,
                     "pandas": pd.__version__, "numpy": np.__version__},
        "graine": GRAINE, "taille_test": len(X_te),
    }
    (DOSSIER_MODELES / "metadata.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

    # ------------------------------------------------------------------ 9. Rapport (livrable L3)
    comp_md = comparaison.assign(**{c: comparaison[c].map(lambda v: f"{v:.3f}") for c in
                                    ["rappel", "precision", "f1", "pr_auc"]})
    comp_md = comp_md.rename(columns={"rappel": "Rappel", "precision": "Précision", "f1": "F1", "pr_auc": "PR-AUC"})
    tn, fp, fn, tp = cm.ravel()
    pr = comparaison.set_index(["Modèle", "Variables"])["pr_auc"]
    gains = {m: (pr[(m, "capteurs seuls")], pr[(m, "capteurs + variables dérivées")]) for m in candidats()}
    f = lambda v: f"{v:.2f}".replace(".", ",")
    arbres = [m for m in gains if m != "Régression logistique"]
    commentaire_comparaison = (
        "Les variables dérivées (écart de température, puissance, contrainte) améliorent nettement les modèles "
        "à base d'arbres : PR-AUC de " + " et ".join(f"{f(gains[m][0])} à {f(gains[m][1])} ({m.lower()})" for m in arbres)
        + f". La régression logistique reste faible ({f(gains['Régression logistique'][0])} puis "
        f"{f(gains['Régression logistique'][1])}) : les pannes dépendent de seuils, parfois des deux côtés "
        "(puissance trop faible **ou** trop forte), ce qu'un modèle linéaire ne sait pas représenter. "
        "La forêt aléatoire et le gradient boosting sont très proches ; le choix se fait sur la PR-AUC.")
    note_rnf = ("" if (detection["Type de panne"] == NOMS_MODES["RNF"]).any()
                else "Le jeu de test ne contient aucune panne aléatoire seule.\n\n")
    ligne_twf = detection[detection["Type de panne"] == NOMS_MODES["TWF"]]
    top3 = ", ".join(importance.sort_values("importance", ascending=False)["variable"].head(3))
    taux_twf = (f"{ligne_twf['Détectées'].iloc[0]} sur {ligne_twf['Pannes dans le test'].iloc[0]}"
                if len(ligne_twf) else "aucune")
    cibles = pd.DataFrame([
        {"Indicateur": "Rappel (pannes détectées)", "Cible": "≥ 85 %", "Résultat": pct(test["rappel"]),
         "Atteint": "✅" if test["rappel"] >= 0.85 else "❌"},
        {"Indicateur": "Précision (alertes justifiées)", "Cible": "≥ 70 %", "Résultat": pct(test["precision"]),
         "Atteint": "✅" if test["precision"] >= 0.70 else "❌"},
        {"Indicateur": "F1-score", "Cible": "≥ 0,75", "Résultat": f"{test['f1']:.3f}".replace(".", ","),
         "Atteint": "✅" if test["f1"] >= 0.75 else "❌"},
        {"Indicateur": "PR-AUC", "Cible": "À maximiser", "Résultat": f"{test['pr_auc']:.3f}".replace(".", ","),
         "Atteint": "—"},
    ])
    RAPPORT.write_text(f"""# PrédiMaint — Rapport de performances du modèle

*Généré automatiquement par `src/entrainer.py` le {meta['date']} — graine aléatoire {GRAINE}.*

## 1. Démarche

- Données : AI4I 2020 (10 000 relevés, 339 pannes). **80 %** pour l'entraînement ({len(X_tr)} relevés), **20 %** gardés pour le test final ({len(X_te)} relevés, {int(y_te.sum())} pannes), séparation stratifiée.
- Comparaison de 3 algorithmes, **avec et sans** les variables dérivées, par validation croisée à 5 plis sur les données d'entraînement.
- Choix du modèle selon la **PR-AUC**, adaptée aux données déséquilibrées.
- Seuil d'alerte choisi sur la validation croisée : **{f'{seuil:.3f}'.replace('.', ',')}**. C'est le seuil qui maximise le F1 tout en détectant au moins 85 % des pannes.
- Test final réalisé **une seule fois**, sur des données jamais vues par le modèle.
- Entrées : gamme, 5 capteurs et 3 variables dérivées. Les colonnes TWF à RNF ne sont **jamais** utilisées en entrée.

## 2. Comparaison des modèles (validation croisée, seuil 0,5)

{tableau_md(comp_md)}

![Comparaison des modèles](figures/07_comparaison_modeles.png)

**Modèle retenu : {nom}, avec les variables dérivées.**

{commentaire_comparaison}

## 3. Résultats sur le jeu de test

{tableau_md(cibles)}

Au seuil retenu, sur {len(X_te)} relevés de test :

- **{tp} pannes détectées** sur {tp + fn} ;
- **{fn} pannes manquées** ;
- **{fp} fausses alertes** ;
- **{tn} relevés normaux** correctement laissés sans alerte.

![Performance sur le test](figures/08_performance_test.png)

### Détection par type de panne

{tableau_md(detection)}

{note_rnf}En excluant les pannes **imprévisibles par nature** (pannes aléatoires seules et pannes sans type indiqué), le modèle détecte **{pct(rappel_previsible)}** des pannes.

**Pannes d'usure de l'outil : seulement {taux_twf} détectées.** Ces pannes se produisent à un moment tiré au hasard entre environ 200 et 250 minutes d'usure, et la plupart des outils qui atteignent cette zone ne cassent pas : les capteurs ne permettent pas de savoir *lequel* va casser. La bonne réponse est **préventive** : changer systématiquement l'outil avant 200 minutes d'usure. L'application signale donc la zone d'usure à risque, même quand le risque calculé reste sous le seuil d'alerte.

### Type de panne

Pour les pannes de type connu, le modèle « type de panne » désigne le bon type dans **{pct(precision_type)}** des cas. C'est ce type qui détermine l'action de maintenance recommandée par l'application.

## 4. Importance des variables

![Importance des variables](figures/09_importance_variables.png)

L'importance est mesurée par permutation : on brouille une variable et on regarde de combien la performance baisse.

Les trois variables les plus utiles sont **{top3}**. C'est cohérent avec la physique des pannes : la vitesse intervient dans la dissipation de chaleur et dans la puissance, l'écart de température dans la dissipation de chaleur, et la contrainte dans la surcharge. Les températures prises isolément n'apportent presque rien : seul leur **écart** compte.

## 5. Limites

- **Données synthétiques** : les pannes de chaleur, de puissance et de surcharge suivent des règles exactes (étape 2). Les performances sont donc bien meilleures que ce qu'on obtiendrait sur une vraie usine.
- Les **pannes aléatoires** et les pannes **sans type** ne peuvent pas être anticipées par les capteurs.
- Les **pannes d'usure** surviennent à un moment tiré au hasard entre environ 200 et 250 minutes. Le modèle repère la zone de risque, pas l'instant exact.
- Sur une vraie usine, il faudrait réentraîner le modèle sur ses propres données et surveiller ses performances dans le temps.

## 6. Environnement

Python {meta['versions']['python']}, scikit-learn {meta['versions']['scikit-learn']}, pandas {meta['versions']['pandas']}, NumPy {meta['versions']['numpy']}.
""", encoding="utf-8")
    print("Modèle sauvegardé :", DOSSIER_MODELES / "predimaint.joblib")
    print("Rapport :", RAPPORT)


if __name__ == "__main__":
    main()
