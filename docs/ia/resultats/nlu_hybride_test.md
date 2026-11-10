# Évaluation NLU — méthode `hybride`, jeu `test`

## Provenance

| Élément | Valeur |
|---|---|
| Commit Git | `dcfea44` |
| Modifications non commitées | oui (32 fichiers modifiés ou non suivis) |
| Variante | v1 |
| LLM | Ollama `qwen2.5:3b` (digest `357c53fb659c`), serveur Ollama 0.40.6 · temperature 0.0 |
| Demandes évaluées | 115 |
| Date | 2026-11-09 23:10 |
| Replis sur les règles | 0 |
| Appels LLM réels (hors cache) | 0 |
| Note | Sorties Ollama produites par un processus dont le code a été chargé avant l'ajout de la v2 (107 appels réels, durée 2 266 s) ; fichier régénéré ensuite depuis le cache v1, scores identiques au run d'origine vérifiés. |

## Conditions API

Simulation depuis le cache (aucun nouvel appel) : chaque demande dont l'appel Ollama a dépassé `NLU_DELAI_LLM_S` = 25 s reçoit la sortie des règles seules, comme la route. Le résultat officiel reste le F1 sans limite de temps ci-dessous ; celui-ci est une donnée pour l'étape 9.

| Conditions API | Valeur |
|---|---|
| Demandes au-delà de 25 s (repli sur les règles) | 20 / 115 (17.4%) |
| F1 macro en conditions API | 0.841 |
| F1 transport macro en conditions API | 0.831 |

> Généré le 2026-11-09 par `services/ai/scripts/evaluer_nlu.py`. 115 demandes relues (`valide` ou `corrige`). LLM : Ollama `qwen2.5:3b` (local). Coût : **0 DT** (aucun appel payant).

## Scores

| Score | Valeur |
|---|---|
| **F1 macro** (champs de support ≥ 5, critère « fini » ≥ 0,85) | **0.841** |
| F1 micro global (28 champs) | 0.892 |
| **F1 transport macro** (8 champs, support ≥ 5) | **0.831** |
| F1 transport micro | 0.850 |
| IC 95 % du F1 macro (bootstrap, 1000 tirages, graine 20261109) | [0.810 ; 0.867] |
| IC 95 % du F1 transport macro (idem) | [0.753 ; 0.890] |
| Latence moyenne | 20.8 s |
| Méthode effective | hybride 112, regles 3 |
| Replis sur les règles (LLM en panne, trop lent ou JSON invalide) | 0 |
| Coût | 0 DT |

Champs hors moyenne macro (support < 5) : `budget_illimite` (3), `mobilite_reduite` (1), `vol_direct` (3), `boite_auto` (3), `priorite` (3), `hors_sujet` (2).

## Par champ

| Champ | Support | Précision | Rappel | F1 | Exactitude | Macro |
|---|---|---|---|---|---|---|
| `destination` | 111 | 0.991 | 0.973 | 0.982 | 0.974 | oui |
| `autres_villes` | 29 | 0.933 | 0.966 | 0.949 | 0.974 | oui |
| `date_debut` | 10 | 1.000 | 1.000 | 1.000 | 1.000 | oui |
| `duree_jours` | 109 | 1.000 | 0.927 | 0.962 | 0.930 | oui |
| `nb_nuits` | 100 | 0.990 | 0.960 | 0.975 | 0.957 | oui |
| `budget_montant` | 98 | 0.939 | 0.939 | 0.939 | 0.948 | oui |
| `budget_devise` | 98 | 1.000 | 1.000 | 1.000 | 1.000 | oui |
| `budget_base` | 98 | 0.939 | 0.939 | 0.939 | 0.948 | oui |
| `budget_illimite` | 3 | 1.000 | 0.333 | 0.500 | 0.983 | non |
| `nb_voyageurs` | 103 | 0.843 | 0.883 | 0.863 | 0.843 | oui |
| `nb_adultes` | 93 | 0.844 | 0.871 | 0.857 | 0.809 | oui |
| `nb_enfants` | 16 | 0.692 | 0.562 | 0.621 | 0.913 | oui |
| `type_voyage` | 96 | 0.794 | 0.885 | 0.837 | 0.800 | oui |
| `preferences` | 52 | 0.915 | 0.827 | 0.869 | 0.904 | oui |
| `activites_souhaitees` | 61 | 0.630 | 0.754 | 0.687 | 0.722 | oui |
| `niveau_marche_max` | 6 | 0.105 | 0.333 | 0.160 | 0.843 | oui |
| `mobilite_reduite` | 1 | 0.091 | 1.000 | 0.167 | 0.913 | non |
| `langue` | 115 | 1.000 | 1.000 | 1.000 | 1.000 | oui |
| `ville_depart` (transport) | 27 | 0.926 | 0.926 | 0.926 | 0.965 | oui |
| `vol` (transport) | 28 | 0.893 | 0.893 | 0.893 | 0.957 | oui |
| `voiture` (transport) | 33 | 0.958 | 0.697 | 0.807 | 0.913 | oui |
| `transfert` (transport) | 21 | 1.000 | 0.476 | 0.645 | 0.904 | oui |
| `vol_direct` (transport) | 3 | 1.000 | 1.000 | 1.000 | 1.000 | non |
| `boite_auto` (transport) | 3 | 1.000 | 0.333 | 0.500 | 0.983 | non |
| `priorite` (transport) | 3 | 1.000 | 0.667 | 0.800 | 0.991 | non |
| `budget_inclut_transport` (transport) | 52 | 1.000 | 0.788 | 0.882 | 0.904 | oui |
| `hors_sujet` | 2 | 0.667 | 1.000 | 0.800 | 0.991 | non |
| `champs_manquants` | 44 | 0.667 | 0.773 | 0.716 | 0.809 | oui |

## Par langue et par source

| Groupe | n | F1 macro | F1 micro | F1 transport macro |
|---|---|---|---|---|
| langue = ar | 23 | 0.776 | 0.867 | 0.742 |
| langue = darija | 23 | 0.761 | 0.825 | 0.760 |
| langue = en | 13 | 0.823 | 0.890 | 0.748 |
| langue = fr | 56 | 0.886 | 0.925 | 0.890 |
| source = genere | 37 | 0.819 | 0.903 | 0.702 |
| source = humain | 78 | 0.836 | 0.888 | 0.850 |

(F1 macro d'un groupe : mêmes champs que la moyenne globale.)

## Matrices d'erreurs

**`type_voyage`** (lignes : attendu, colonnes : prédit)

| attendu \ prédit | amis | couple | famille | groupe | solo | None |
|---|---|---|---|---|---|---|
| amis | 20 | · | 1 | · | · | · |
| couple | 3 | 19 | 1 | · | · | · |
| famille | 2 | 2 | 24 | · | · | 1 |
| groupe | · | · | · | 4 | · | · |
| solo | 1 | · | · | · | 18 | · |
| None | 7 | · | 1 | 4 | · | 7 |

**`besoins_transport.vol`** (lignes : attendu, colonnes : prédit)

| attendu \ prédit | indifferent | non | oui |
|---|---|---|---|
| indifferent | 85 | 2 | · |
| non | 2 | 4 | 1 |
| oui | · | · | 21 |

**`besoins_transport.voiture`** (lignes : attendu, colonnes : prédit)

| attendu \ prédit | indifferent | non | oui |
|---|---|---|---|
| indifferent | 82 | · | · |
| non | 2 | 12 | 1 |
| oui | 7 | · | 11 |

**`besoins_transport.transfert`** (lignes : attendu, colonnes : prédit)

| attendu \ prédit | indifferent | oui |
|---|---|---|
| indifferent | 94 | · |
| oui | 11 | 10 |

