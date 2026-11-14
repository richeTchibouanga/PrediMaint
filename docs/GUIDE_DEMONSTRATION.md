# PrédiMaint — Guide de démonstration et de test, de A à Z

*Pour présenter le projet en entretien ou à un client, refaire chaque test et répondre aux questions. Tous les résultats annoncés ici ont été vérifiés avec l'application et le modèle réels.*

---

## Sommaire

1. Le projet en 30 secondes
2. Lancer l'application
3. Comprendre ce que l'on voit
4. Tests du diagnostic : 10 machines à essayer
5. Simulations : 6 expériences
6. Tests de l'analyse de lot : 5 fichiers fournis
7. Scénarios économiques
8. Script de démonstration en 10 minutes
9. Questions d'entretien et réponses
10. Limites et pistes d'amélioration
11. Glossaire
12. Fiche de test à cocher

---

## 1. Le projet en 30 secondes

> « Dans un atelier d'usinage, une panne imprévue arrête la production, abîme la pièce en cours et oblige à réparer en urgence. J'ai conçu **PrédiMaint**, un outil qui lit les mesures des capteurs d'une machine (températures, vitesse, couple, usure de l'outil) et estime le **risque de panne**. Il indique le **type de panne probable**, **explique** sa décision et **recommande une action** de maintenance. Sur des données qu'il n'avait jamais vues, il détecte **85 % des pannes**, et 3 alertes sur 4 sont justifiées. Avec des hypothèses de coût prudentes, il réduit le coût de la maintenance d'environ **73 %**. Mon expérience en maintenance industrielle m'a servi à créer les variables qui font la différence : la puissance, l'écart de température et la contrainte de l'outil. »

**Les chiffres clés à retenir**

| Indicateur | Valeur |
|---|---|
| Données | 10 000 relevés de machines-outils, dont 339 pannes (3,4 %) — AI4I 2020 |
| Pannes détectées (rappel) | 85,3 % (58 sur 68, sur des données jamais vues) |
| Alertes justifiées (précision) | 76,3 % |
| Bon type de panne identifié | 93,9 % |
| Seuil d'alerte | 26 % de risque |
| Gain annuel (hypothèses par défaut) | 510 000 €, soit −73 % |
| Modèle | Forêt aléatoire, comparée à 2 autres algorithmes |

---

## 2. Lancer l'application

**Prérequis** : le dossier du projet avec son environnement Python (`.venv`) déjà installé.

1. Ouvrir un terminal dans le dossier `maintenance-predictive`.
2. Taper la commande :

   ```
   .venv\Scripts\streamlit run app/app.py
   ```

3. L'application s'ouvre dans le navigateur, à l'adresse `http://localhost:8501`.
4. Le premier affichage prend quelques secondes, le temps de charger le modèle. Ensuite, chaque calcul est instantané.

**Sans installation** : l'application est aussi en ligne, à l'adresse **https://predimaint.streamlit.app**, accessible depuis n'importe quel ordinateur ou téléphone. C'est la solution la plus simple pour une démonstration en entretien.

**Le menu de gauche** donne accès aux 5 pages : Diagnostic d'une machine, Analyse d'un lot, Simulation, Économie, À propos.

---

## 3. Comprendre ce que l'on voit

### 3.1 Les niveaux d'alerte

| Risque | Niveau | Couleur | Que faire |
|---|---|---|---|
| Moins de 26 % | Pas d'alerte | Vert | Poursuivre la surveillance |
| De 26 % à 60 % | Alerte : intervention à planifier | Orange | Prévoir une intervention dans les prochains jours |
| 60 % et plus | Alerte critique : intervenir rapidement | Rouge | Intervenir avant la prochaine production |

**Pourquoi 26 % et pas 50 % ?** Une panne manquée coûte beaucoup plus cher qu'une fausse alerte. Le seuil a donc été abaissé pour détecter au moins 85 % des pannes. L'étude économique a confirmé ce choix.

### 3.2 La règle préventive des 200 minutes

Dès que l'usure de l'outil atteint **200 minutes**, l'application recommande de **changer l'outil par précaution**, même sans alerte. Dans les données, les outils cassent au hasard entre 200 et 250 minutes, et seuls 5 % des outils qui entrent dans cette zone cassent. Aucun capteur ne permet de savoir lequel. La seule bonne réponse est donc préventive.

C'est un point fort à présenter : le projet **combine** la maintenance prédictive (le modèle) et la maintenance préventive (la règle des 200 minutes).

### 3.3 Les trois indicateurs physiques

Ces indicateurs sont calculés à partir des mesures. Ils correspondent aux trois grandes causes de panne.

| Indicateur | Calcul | Limite de panne | Panne correspondante |
|---|---|---|---|
| Écart de température | température du procédé − température de l'air | moins de 8,6 K **et** vitesse inférieure à 1 380 tr/min | Dissipation de chaleur |
| Puissance | couple × vitesse × 2π / 60 | moins de 3 500 W ou plus de 9 000 W | Puissance |
| Contrainte | usure de l'outil × couple | plus de 11 000 (gamme L), 12 000 (M) ou 13 000 (H) | Surcharge |

### 3.4 « Pourquoi ce risque ? » : l'explication

Pour chaque mesure, l'application la remplace par sa **valeur habituelle sur une machine saine**, puis recalcule le risque :
- une barre **rouge** signifie que cette mesure **fait monter** le risque, de la longueur de la barre ;
- une barre **verte** signifie qu'elle le **fait baisser**.

**Attention** : les barres ne s'additionnent pas. Quand une panne dépend de deux mesures à la fois, comme l'usure et le couple pour la surcharge, ramener **l'une ou l'autre** à la normale suffit à faire disparaître le risque. Les deux barres sont alors toutes les deux grandes.

---

## 4. Tests du diagnostic : 10 machines à essayer

**Mode opératoire** : page **Diagnostic d'une machine**, saisir les 6 valeurs puis lire le résultat. Les scénarios D2, D3 et D4 se chargent aussi d'un clic dans l'encadré « Charger un exemple ».

| N° | Situation | Gamme | T. air (K) | T. procédé (K) | Vitesse (tr/min) | Couple (N·m) | Usure (min) |
|---|---|---|---|---|---|---|---|
| D1 | Machine normale | L | 300,0 | 310,0 | 1 500 | 40,0 | 100 |
| D2 | Outil usé et effort élevé | L | 300,0 | 309,0 | 1 300 | 62,0 | 205 |
| D3 | Refroidissement insuffisant | M | 302,5 | 310,5 | 1 330 | 45,0 | 60 |
| D4 | Vitesse très élevée, couple faible | H | 299,0 | 309,5 | 2 700 | 11,0 | 30 |
| D5 | Couple très élevé | L | 300,0 | 310,0 | 1 250 | 70,0 | 50 |
| D6 | Outil en zone d'usure, rien d'autre | L | 300,0 | 310,0 | 1 500 | 40,0 | 215 |
| D7 | Même machine, gamme L | L | 300,0 | 310,0 | 1 400 | 60,0 | 195 |
| D8 | Même machine, gamme H | H | 300,0 | 310,0 | 1 400 | 60,0 | 195 |
| D9 | Chaleur : conditions de panne tout juste réunies | M | 302,0 | 310,4 | 1 370 | 45,0 | 60 |
| D10 | Chaleur : tout juste en dehors des conditions | M | 302,0 | 310,8 | 1 390 | 45,0 | 60 |

**Résultats attendus**

| N° | Risque | Niveau | Panne probable | Causes principales | Ce que montre le test |
|---|---|---|---|---|---|
| D1 | 0 % | Pas d'alerte | — | aucune | Une machine saine ne déclenche rien ; tous les indicateurs sont dans les limites |
| D2 | 96 % | Critique | Surcharge | usure de l'outil, couple | Contrainte 12 710 > 11 000 (limite L) ; zone d'usure signalée en plus |
| D3 | 92 % | Critique | Dissipation de chaleur | température de l'air, vitesse | Écart de 8,0 K < 8,6 K et vitesse < 1 380 tr/min |
| D4 | 95 % | Critique | Puissance | couple, vitesse | Puissance de 3 110 W, sous les 3 500 W |
| D5 | 94 % | Critique | Puissance | couple | Puissance de 9 163 W, au-dessus des 9 000 W |
| D6 | 12 % | Pas d'alerte | — | usure de l'outil | **Aucune alerte, mais la règle des 200 min demande de changer l'outil** |
| D7 | 85 % | Critique | Surcharge | couple, usure | Contrainte 11 700 > 11 000 (limite L) |
| D8 | 53 % | Alerte | Puissance | couple, usure | Même contrainte, mais limite H à 13 000 : le risque baisse nettement (voir ci-dessous) |
| D9 | 90 % | Critique | Dissipation de chaleur | température de l'air, vitesse | Écart de 8,4 K et vitesse de 1 370 : les deux conditions sont réunies |
| D10 | 0,3 % | Pas d'alerte | — | aucune | Écart de 8,8 K et vitesse de 1 390 : il suffit de 0,4 K et 20 tr/min pour sortir de la zone |

**Les deux tests les plus intéressants à commenter**

- **D9 et D10, la précision du modèle.** Deux machines presque identiques donnent 90 % et 0,3 % de risque. Le modèle a appris la frontière physique de la panne de chaleur à quelques dixièmes de degré près.
- **D7 et D8, l'effet de la gamme, avec une erreur du modèle.** La même machine passe de 85 % de risque en gamme L à 53 % en gamme H, car les produits H tolèrent plus de contrainte. Pourtant, d'après les règles physiques, la machine D8 ne devrait **pas** tomber en panne : sa contrainte (11 700) reste sous la limite H (13 000), et sa puissance (8 796 W) sous les 9 000 W.

  C'est donc une **fausse alerte**, et l'étiquette « Puissance » n'est pas la bonne. Ce cas est utile en entretien : il montre que le modèle n'est pas une formule exacte, qu'il peut se tromper près des frontières, et qu'on l'a vérifié soi-même. C'est pour cela que l'outil **aide** le technicien sans le remplacer.

---

## 5. Simulations : 6 expériences

**Mode opératoire** : page **Simulation**. On saisit la machine de départ, on choisit la mesure à faire varier, puis on lit la courbe et le message sous le graphique.

| N° | Machine de départ | Mesure qui varie | Résultat affiché | Ce qu'il faut en dire |
|---|---|---|---|---|
| S1 | D1 (machine normale) | Couple | Alerte jusqu'à **21,8 N·m** et à partir de **57,4 N·m** | À 1 500 tr/min, ce sont exactement les limites de puissance de 3 500 W et 9 000 W : le modèle a retrouvé la physique |
| S2 | D1 | Usure de l'outil | Aucune alerte (risque maximal de 12 %), mais bande orange au-delà de 200 min | L'usure seule ne permet pas de prédire la casse : d'où la règle préventive |
| S3 | D1, avec un couple de **55 N·m** | Usure de l'outil | Alerte à partir d'environ **199 min** | 11 000 ÷ 55 = 200 min : la limite de surcharge de la gamme L est retrouvée |
| S4 | D3 (refroidissement), à 1 330 tr/min | Température de l'air | Alerte à partir de **301,9 K** | Avec un procédé à 310,5 K, l'écart passe sous 8,6 K à 301,9 K |
| S5 | D3, avec une température de l'air de 302,5 K | Vitesse de rotation | Alerte jusqu'à **1 372 tr/min** | La limite de 1 380 tr/min est retrouvée : accélérer la machine fait disparaître le risque |
| S6 | D1 | Vitesse de rotation | Alerte entre 2 189 et 2 280 tr/min, puis à partir de 2 477 tr/min, avec un risque maximal de **28 %** seulement | Le modèle hésite : ces vitesses avec un couple de 40 N·m sont très rares dans les données. Bon exemple de **limite** à présenter |

**Message clé** : la simulation sert à répondre à la question du responsable de production, « jusqu'où puis-je pousser la machine avant d'entrer en zone de risque ? ».

---

## 6. Tests de l'analyse de lot : 5 fichiers fournis

Les fichiers sont dans le dossier `data/exemples/` du projet.

**Mode opératoire** : page **Analyse d'un lot**. Désactiver l'échantillon de démonstration, puis importer le fichier avec le bouton « Upload ».

| Fichier | Contenu | Résultat attendu |
|---|---|---|
| `lot_atelier_10_machines.csv` | Les 10 machines du § 4, numérotées M01 à M10 | 10 machines, **7 alertes**. M02 en tête (96 %), M06 sans alerte mais avec « Zone d'usure : changer l'outil par précaution » |
| `lot_format_origine_ai4i.csv` | 20 vrais relevés du jeu de test, au format d'origine, avec la vraie colonne de panne | 20 machines, **6 alertes**, qui correspondent aux **6 vraies pannes**. Les 6 types prédits sont corrects (3 chaleur, 2 puissance, 1 surcharge) et il n'y a aucune fausse alerte |
| `erreur_colonne_manquante.csv` | La colonne `couple` a été retirée | Message « Colonnes manquantes : couple » |
| `erreur_gamme_inconnue.csv` | Une gamme vaut « X » | Message « La colonne « gamme » ne doit contenir que L, M ou H. » |
| `erreur_valeur_non_numerique.csv` | Un couple vaut « abc » | Message « Certaines mesures sont vides ou ne sont pas des nombres. » |

**Échantillon de démonstration** (interrupteur activé, sans fichier) : 200 machines analysées, **7 alertes** et **11 outils à changer par précaution**.

**À montrer en entretien** :
- le fichier au format d'origine, où l'on compare directement la colonne `panne` (la réalité) à la prédiction ;
- un fichier erroné, pour montrer que l'outil **contrôle les données** avant de calculer, au lieu de produire un résultat faux.

---

## 7. Scénarios économiques

**Mode opératoire** : page **Économie**. Les hypothèses se modifient dans le menu de gauche, et le seuil avec le curseur.

| N° | Ce qu'on change | Coût sans le modèle | Coût avec le modèle | Gain annuel | Réduction |
|---|---|---|---|---|---|
| E1 | Rien (hypothèses par défaut) | 697 000 € | 187 000 € | **510 000 €** | 73 % |
| E2 | Panne peu coûteuse : arrêt 0 h, réparation 500 €, pièce 0 € | 170 000 € | 109 500 € | **60 500 €** | 36 % |
| E3 | Arrêt de 8 h et production à 800 €/h | 2 397 000 € | 437 000 € | **1 960 000 €** | 82 % |
| E4 | Coût de la solution à 50 000 €/an | 697 000 € | 234 000 € | **463 000 €** | 66 % |
| E5 | Petit atelier : 2 000 opérations par an | 139 400 € | 39 800 € | **99 600 €** | 71 % |
| E6 | Seuil très bas (0,05) | 697 000 € | 200 000 € | **497 000 €** | 71 % |
| E7 | Seuil élevé (0,60) | 697 000 € | 233 000 € | **464 000 €** | 67 % |

**Pannes évitées et fausses alertes selon le seuil** (pour une année de 10 000 opérations)

| Seuil | Pannes évitées (sur 340) | Fausses alertes |
|---|---|---|
| 0,05 | 315 | 670 |
| **0,26 (retenu)** | **290** | **90** |
| 0,60 | 260 | 10 |

**Ce qu'il faut en dire**

1. **La conclusion résiste aux hypothèses.** Même avec une panne qui ne coûte que 500 € (E2), le gain reste de 60 500 €/an. La solution devient rentable dès qu'une panne coûte plus d'environ 300 €.
2. **Le seuil est un compromis.** À 0,05, on évite 25 pannes de plus, mais on déclenche 670 fausses alertes au lieu de 90. Les techniciens finiraient par ne plus y croire. À 0,60, on manque 30 pannes de plus. Le seuil de 0,26 donne le meilleur équilibre.
3. **Le principal poste de coût restant est celui des pannes manquées.** C'est là que se trouve la marge de progrès du modèle.

---

## 8. Script de démonstration en 10 minutes

| Temps | Page | Ce qu'on fait | Ce qu'on dit |
|---|---|---|---|
| 0:00 – 1:00 | — | Présenter le problème | Le pitch du § 1 : pannes imprévues, coûts, capteurs déjà présents |
| 1:00 – 3:00 | Diagnostic | Charger l'exemple **surcharge** (D2) | « 96 % de risque, panne de surcharge. Le modèle explique : c'est l'usure **et** le couple. La contrainte dépasse la limite de la gamme L. L'action est concrète : réduire la charge et changer l'outil. » |
| 3:00 – 4:00 | Diagnostic | Saisir **D6** (usure à 215 min) | « Pas d'alerte, mais l'outil est en zone d'usure. Le modèle ne peut pas prédire la casse d'un outil : je l'ai mesuré, et j'ai ajouté une règle préventive. Prédictif et préventif sont combinés. » |
| 4:00 – 5:30 | Simulation | **S1** : faire varier le couple | « Le modèle a retrouvé seul les limites physiques de puissance, à 22 N·m et 57 N·m pour 1 500 tr/min. Cela montre qu'il a appris la mécanique, pas du bruit. » |
| 5:30 – 7:00 | Analyse d'un lot | Importer `lot_format_origine_ai4i.csv` | « 20 vrais relevés : 6 pannes réelles, 6 détectées avec le bon type, aucune fausse alerte. Le responsable voit d'abord les machines à traiter. » |
| 7:00 – 9:00 | Économie | E1, puis E2 | « 510 000 € de gain par an. Même si une panne ne coûtait que 500 €, on gagnerait encore 60 000 €. Et le seuil a été choisi pour éviter de noyer les techniciens sous les fausses alertes. » |
| 9:00 – 10:00 | À propos | Montrer les limites | « Données synthétiques, donc performances optimistes. Sur une vraie usine, je réentraînerais le modèle sur ses données. J'ai aussi trouvé une fausse alerte en testant la gamme H : l'outil aide le technicien, il ne le remplace pas. » |

**Conseil** : finir sur les limites montre de la maturité. Un recruteur se méfie d'un projet « parfait ».

---

## 9. Questions d'entretien et réponses

**1. Pourquoi ne pas mesurer la performance avec le taux de bonnes réponses ?**
Parce que 96,6 % des relevés sont sans panne. Un modèle qui répondrait toujours « pas de panne » aurait 96,6 % de bonnes réponses tout en étant inutile. J'ai donc mesuré le **rappel**, c'est-à-dire la part des pannes détectées, et la **précision**, c'est-à-dire la part des alertes justifiées.

**2. Pourquoi une forêt aléatoire ?**
J'ai comparé trois algorithmes en validation croisée : la régression logistique, la forêt aléatoire et le gradient boosting. Les pannes dépendent de seuils, parfois des deux côtés : la puissance peut être trop faible **ou** trop forte. Un modèle linéaire ne sait pas représenter cela (PR-AUC de 0,45). Les modèles à base d'arbres atteignent 0,89. La forêt aléatoire avait la meilleure PR-AUC.

**3. Qu'est-ce qui a le plus amélioré le modèle ?**
Les **variables issues du métier** : la puissance, l'écart de température et la contrainte. Elles font passer la PR-AUC de la forêt aléatoire de 0,76 à 0,89. C'est mon expérience de technicien de maintenance qui m'a donné ces idées.

**4. Comment avez-vous évité de « tricher » ?**
- Les colonnes qui décrivent la panne elle-même (TWF à RNF) ne sont **jamais** des entrées du modèle.
- 20 % des données ont été mises de côté **avant** tout réglage, et le test final n'a été fait **qu'une fois**.
- Le seuil d'alerte a été choisi sur les données d'entraînement, pas sur le test.

**5. Pourquoi le seuil est-il à 26 % ?**
C'est le seuil qui maximise le F1 tout en détectant au moins 85 % des pannes, en validation croisée. L'étude économique le confirme : le coût est presque le même entre 0,08 et 0,33, et 0,26 limite les fausses alertes (90 par an au lieu de 670 à 0,05).

**6. Pourquoi le modèle détecte-t-il mal les casses d'outil ?**
Elles se produisent au hasard entre 200 et 250 minutes d'usure, et seuls 5 % des outils de cette zone cassent. Aucune mesure ne permet de savoir lequel. J'ai préféré une réponse **préventive** : changer l'outil avant 200 minutes. Mieux vaut le reconnaître que forcer le modèle.

**7. Comment le modèle explique-t-il ses décisions ?**
Pour chaque mesure, je la remplace par sa valeur normale et je regarde de combien le risque baisse. C'est simple, compréhensible par un technicien, et cela marche avec n'importe quel modèle.

**8. Vos résultats sont-ils réalistes ?**
Non, ils sont optimistes, et je le dis clairement : les données sont **synthétiques**, et certaines pannes y suivent des règles exactes. Sur une vraie usine, il y aurait du bruit de mesure et des causes non mesurées. La **démarche**, en revanche, est la même : préparation des données, variables métier, choix des métriques, validation, seuil, étude économique, application.

**9. Comment l'adapteriez-vous à une vraie usine ?**
- Récupérer l'historique des capteurs et des pannes (souvent dans la GMAO).
- Réentraîner et revalider le modèle sur ces données.
- Remplacer les hypothèses de coût par les chiffres réels.
- Brancher l'outil sur les relevés en continu, avec des alertes automatiques.
- Surveiller ses performances dans le temps et le réentraîner régulièrement.

**10. Le modèle se trompe-t-il ?**
Oui. Il manque environ 15 % des pannes, surtout des casses d'outil. Et en testant moi-même, j'ai trouvé une fausse alerte : une machine en gamme H à 53 % de risque, alors que les règles physiques ne prévoient pas de panne. C'est pour cela que l'application **explique** chaque décision et laisse le dernier mot au technicien.

**11. Combien de temps vous a pris ce projet, et avec quels outils ?**
Environ deux semaines à temps partiel, en suivant un cahier des charges que j'ai rédigé au départ. Outils : Python, pandas, scikit-learn, Matplotlib, Altair et Streamlit. Le code, la documentation et l'application sont publiés.

**12. Que feriez-vous ensuite ?**
Ajouter un assistant IA qui guide le technicien pas à pas selon la panne prédite. Travailler sur des séries temporelles pour estimer la durée de vie restante d'un outil. Ajouter des alertes automatiques.

---

## 10. Limites et pistes d'amélioration

| Limite | Conséquence | Piste d'amélioration |
|---|---|---|
| Données synthétiques | Performances optimistes | Réentraîner sur des données réelles d'usine |
| Casses d'outil imprévisibles | Seulement 2 sur 10 détectées | Règle préventive à 200 min ; suivi de l'outil dans le temps |
| Pannes aléatoires | Impossibles à anticiper | À traiter par la maintenance corrective |
| Peu d'exemples à très haute vitesse | Modèle hésitant (S6) | Collecter plus de données dans ces conditions |
| Erreurs près des frontières de panne | Fausse alerte (D8) | Plus de données, et l'explication pour garder l'esprit critique |
| Relevés ponctuels | Pas de surveillance continue | Connexion aux capteurs en temps réel et alertes automatiques |
| Coûts estimés | Gain chiffré indicatif | Utiliser les coûts réels de l'usine |

---

## 11. Glossaire

| Terme | Définition simple |
|---|---|
| Maintenance corrective | Réparer après la panne |
| Maintenance préventive | Intervenir à intervalles fixes, sans attendre la panne |
| Maintenance prédictive | Intervenir au bon moment, quand les mesures annoncent une panne |
| Rappel | Part des vraies pannes que le modèle détecte |
| Précision | Part des alertes du modèle qui correspondent à une vraie panne |
| F1 | Note qui combine le rappel et la précision |
| PR-AUC | Qualité globale du modèle sur des données déséquilibrées (1 = parfait) |
| Seuil d'alerte | Risque à partir duquel le modèle déclenche une alerte (ici 26 %) |
| Fausse alerte | Alerte alors qu'aucune panne ne survient |
| Validation croisée | Évaluer le modèle plusieurs fois sur des parties différentes des données d'entraînement |
| Jeu de test | Données mises de côté et jamais vues par le modèle, pour l'évaluation finale |
| Fuite d'information | Donner au modèle une information qu'il n'aurait pas en réalité ; elle fausse les résultats |
| Forêt aléatoire | Ensemble de nombreux arbres de décision qui votent |
| Variable dérivée | Variable calculée à partir des mesures (puissance, écart de température, contrainte) |

---

## 12. Fiche de test à cocher

À faire avant chaque démonstration, en moins de 15 minutes.

- [ ] L'application se lance et les 5 pages s'ouvrent sans erreur
- [ ] D1 : 0 %, pas d'alerte
- [ ] D2 : 96 %, critique, surcharge, zone d'usure signalée
- [ ] D3 : 92 %, dissipation de chaleur
- [ ] D4 : 95 %, puissance
- [ ] D6 : 12 %, pas d'alerte, mais changement d'outil recommandé
- [ ] D9 et D10 : 90 % puis 0,3 %
- [ ] S1 : alerte jusqu'à 21,8 N·m et à partir de 57,4 N·m
- [ ] S3 : alerte à partir d'environ 199 min
- [ ] Lot `lot_atelier_10_machines.csv` : 10 machines, 7 alertes
- [ ] Lot `lot_format_origine_ai4i.csv` : 6 alertes, qui correspondent aux 6 vraies pannes
- [ ] Les 3 fichiers d'erreur affichent leur message
- [ ] Économie E1 : 510 000 € de gain
- [ ] Économie E2 : 60 500 € de gain
