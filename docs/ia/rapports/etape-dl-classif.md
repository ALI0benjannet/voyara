# Validation DL — Classification des demandes : Transfer Learning vs Fine-Tuning

> Branche `ia/dl-classif` · Boutheina Rjab · séance de validation Deep Learning (module Projet IA & Cognition, 5DS)

## 1. Objectif

Répondre aux 5 points demandés par le professeur pour la validation Deep Learning, sur une tâche de VOYARA : à partir du texte libre d'une demande de voyage (fr / en / ar / darija), prédire `type_voyage` (famille, couple, amis, solo, non précisé) et les besoins de transport `vol` et `voiture` (oui / non / indifférent). Comparer un modèle pré-entraîné gelé (Transfer Learning) et le même modèle réentraîné (Fine-Tuning), avec une baseline ML.

## 2. Réalisé

- `notebooks/05_dl_classif_demandes.ipynb` : notebook exécutable sur Colab (GPU T4), de la préparation des données à l'analyse des erreurs.
- `services/ai/data/dl/classif_train.jsonl` : 308 exemples d'entraînement = les 77 demandes du jeu dev + 231 paraphrases (3 par demande, dans d'autres langues), générées puis relues (22 corrigées). Chaque paraphrase garde les labels de sa demande d'origine (champ `origine`).
- `docs/ia/resultats/dl_classif.csv` / `.md` : tableau final ; `dl_classif_historique.csv` : toutes les tentatives.
- Modèles fine-tunés sauvegardés sur Google Drive (`voyara_dl/modeles/`), hors Git (≈ 1,1 Go chacun).
- Présentation de 7 slides pour la séance.

## 3. Choix techniques

- **Modèle pré-entraîné : `xlm-roberta-base`** (278 M paramètres, 100 langues dont l'arabe). Écartés : CamemBERT (français seul), AraBERT (arabe seul), mBERT (en général moins bon que XLM-R en classification).
- **Baseline ML** : TF-IDF sur n-grammes de caractères (2–5) + régression logistique (`class_weight="balanced"`).
- **Transfer Learning** : encodeur gelé, vecteur de 768 valeurs par demande (mean pooling de la dernière couche), régression logistique entraînée dessus.
- **Fine-Tuning, dégel progressif** : phase 1 = embeddings + 8 premières couches gelées, seules les 4 dernières et la tête sont entraînées (lr 3e-5) ; phase 2 = tout le modèle (lr 2e-5).
- **Perte pondérée** par l'inverse de la fréquence des classes, ajoutée après la tentative 1 (voir §6).
- **Validation** : 15 % des demandes d'origine, leurs paraphrases restant du même côté (pas de fuite) ; early stopping sur le F1 de validation (patience 5), meilleur modèle gardé en mémoire ; fp16 ; batch 16 ; 15 époques max.
- « groupe » (3 exemples en dev) fusionné avec « amis ».

## 4. Vérification

- Jeu de test : les 115 demandes `test` de `nlu_demandes.jsonl`, jamais utilisées pour entraîner ni pour choisir un réglage. Les corrections (poids de classes, patience) ont été décidées sur les courbes de **validation**.
- Aucune paraphrase ne reprend une demande du test (vérifié automatiquement).
- Fine-Tuning phase 1 relancé avec **3 graines** (42, 7, 2026) : moyenne ± écart-type.

## 5. Métriques

F1 macro sur le test :

| Approche | type_voyage | vol | voiture |
| :--- | ---: | ---: | ---: |
| ML : TF-IDF + régression logistique | 0,460 | 0,513 | 0,604 |
| DL Transfer Learning : XLM-R gelé | 0,366 | 0,595 | 0,538 |
| **DL Fine-Tuning phase 1 (3 graines)** | **0,547 ± 0,015** | **0,602 ± 0,006** | **0,808 ± 0,029** |
| DL Fine-Tuning phase 2 (1 graine) | 0,486 | — | — |

- Le Fine-Tuning gagne sur type_voyage (+0,09 face au ML) et voiture (+0,20). Sur vol, égalité avec le Transfer Learning (écart < variance).
- type_voyage, modèle de démonstration (F1 0,51) : famille 0,74 · couple 0,65 · amis 0,50 · solo 0,33 · non précisé 0,30.
- Temps d'entraînement d'un run phase 1 : ≈ 17 s sur T4 (hors chargement).

## 6. Limites, dette technique, risques

- **Tentative 1 : effondrement sur la classe majoritaire** (F1 validation bloqué à 0,28, prédiction toujours « indifférent » pour vol et voiture) → corrigé par la perte pondérée et une patience plus longue.
- **Variance** : un même réglage a donné 0,600 puis 0,51 sur type_voyage → résultats rapportés en moyenne de 3 graines.
- **Darija en lettres latines** faible (F1 0,25 à 0,43) : peu présente dans le pré-entraînement de XLM-R.
- **Classes rares ou floues** : solo (24 exemples d'entraînement) et non précisé (définie par l'absence d'indice).
- Paraphrases générées : moins variées que de vraies demandes ; test de 115 demandes (13 en anglais seulement).
- Les F1 de l'étape 4 (règles, LLM) utilisent une autre métrique (F1 sur champs remplis) : pas directement comparables.
- Dette : les premières sauvegardes par époque (≈ 1 min chacune) ralentissaient tout ; remplacées par une sauvegarde unique en fin de run.

## 7. À vérifier par moi

- Le notebook s'exécute de bout en bout sur Colab (GPU) et le modèle se recharge depuis Drive pour la démo.
- Les slides reprennent les chiffres de ce rapport.

## 8. Étape suivante recommandée

Ajouter des exemples pour solo et la darija, puis évaluer ce classifieur rapide (quelques ms, hors ligne) comme filtre avant le LLM de l'agent (niveau 5). Relecture de la branche par Ali avant fusion dans `main`.
