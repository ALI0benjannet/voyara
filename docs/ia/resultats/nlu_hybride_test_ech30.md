# Évaluation NLU — méthode `hybride`, jeu `test` (échantillon stratifié de 30)

## Provenance

| Élément | Valeur |
|---|---|
| Commit Git | `dcfea44` |
| Modifications non commitées | oui (36 fichiers modifiés ou non suivis) |
| Variante | v1 |
| LLM | Ollama `qwen2.5:3b` (digest `357c53fb659c`), serveur Ollama 0.40.6 · temperature 0.0 |
| Demandes évaluées | 30 |
| Date | 2026-11-10 00:24 |
| Replis sur les règles | 0 |
| Appels LLM réels (hors cache) | 0 |
| Note | Sorties tirÃ©es du cache v1 du run officiel (code chargÃ© avant l'ajout de la v2). |

## Conditions API

Simulation depuis le cache (aucun nouvel appel) : chaque demande dont l'appel Ollama a dépassé `NLU_DELAI_LLM_S` = 25 s reçoit la sortie des règles seules, comme la route. Le résultat officiel reste le F1 sans limite de temps ci-dessous ; celui-ci est une donnée pour l'étape 9.

| Conditions API | Valeur |
|---|---|
| Demandes au-delà de 25 s (repli sur les règles) | 7 / 30 (23.3%) |
| F1 macro en conditions API | 0.873 |
| F1 transport macro en conditions API | 0.786 |

> Généré le 2026-11-10 par `services/ai/scripts/evaluer_nlu.py`. 30 demandes relues (`valide` ou `corrige`). LLM : Ollama `qwen2.5:3b` (local). Coût : **0 DT** (aucun appel payant).

## Scores

| Score | Valeur |
|---|---|
| **F1 macro** (champs de support ≥ 5, critère « fini » ≥ 0,85) | **0.879** |
| F1 micro global (28 champs) | 0.911 |
| **F1 transport macro** (8 champs, support ≥ 5) | **0.786** |
| F1 transport micro | 0.795 |
| IC 95 % du F1 macro (bootstrap, 1000 tirages, graine 20261109) | [0.818 ; 0.928] |
| IC 95 % du F1 transport macro (idem) | [0.617 ; 0.927] |
| Latence moyenne | 20.5 s |
| Méthode effective | hybride 30 |
| Replis sur les règles (LLM en panne, trop lent ou JSON invalide) | 0 |
| Coût | 0 DT |

Champs hors moyenne macro (support < 5) : `date_debut` (4), `budget_illimite` (1), `nb_enfants` (4), `niveau_marche_max` (3), `mobilite_reduite` (1), `vol_direct` (1), `boite_auto` (2), `priorite` (1), `hors_sujet` (0).

## Par champ

| Champ | Support | Précision | Rappel | F1 | Exactitude | Macro |
|---|---|---|---|---|---|---|
| `destination` | 30 | 1.000 | 1.000 | 1.000 | 1.000 | oui |
| `autres_villes` | 7 | 1.000 | 1.000 | 1.000 | 1.000 | oui |
| `date_debut` | 4 | 1.000 | 1.000 | 1.000 | 1.000 | non |
| `duree_jours` | 29 | 1.000 | 0.897 | 0.945 | 0.900 | oui |
| `nb_nuits` | 26 | 1.000 | 0.923 | 0.960 | 0.933 | oui |
| `budget_montant` | 26 | 0.962 | 0.962 | 0.962 | 0.967 | oui |
| `budget_devise` | 26 | 1.000 | 1.000 | 1.000 | 1.000 | oui |
| `budget_base` | 26 | 0.962 | 0.962 | 0.962 | 0.967 | oui |
| `budget_illimite` | 1 | 1.000 | 1.000 | 1.000 | 1.000 | non |
| `nb_voyageurs` | 29 | 0.964 | 0.931 | 0.947 | 0.933 | oui |
| `nb_adultes` | 26 | 0.920 | 0.885 | 0.902 | 0.833 | oui |
| `nb_enfants` | 4 | 0.750 | 0.750 | 0.750 | 0.933 | non |
| `type_voyage` | 26 | 0.893 | 0.962 | 0.926 | 0.867 | oui |
| `preferences` | 12 | 1.000 | 0.917 | 0.957 | 0.967 | oui |
| `activites_souhaitees` | 9 | 0.417 | 0.556 | 0.476 | 0.767 | oui |
| `niveau_marche_max` | 3 | 0.250 | 0.333 | 0.286 | 0.867 | non |
| `mobilite_reduite` | 1 | 0.333 | 1.000 | 0.500 | 0.933 | non |
| `langue` | 30 | 1.000 | 1.000 | 1.000 | 1.000 | oui |
| `ville_depart` (transport) | 8 | 1.000 | 1.000 | 1.000 | 1.000 | oui |
| `vol` (transport) | 9 | 0.875 | 0.778 | 0.824 | 0.933 | oui |
| `voiture` (transport) | 11 | 0.875 | 0.636 | 0.737 | 0.867 | oui |
| `transfert` (transport) | 6 | 1.000 | 0.333 | 0.500 | 0.867 | oui |
| `vol_direct` (transport) | 1 | 1.000 | 1.000 | 1.000 | 1.000 | non |
| `boite_auto` (transport) | 2 | — | 0.000 | 0.000 | 0.933 | non |
| `priorite` (transport) | 1 | — | 0.000 | 0.000 | 0.967 | non |
| `budget_inclut_transport` (transport) | 13 | 1.000 | 0.769 | 0.870 | 0.900 | oui |
| `hors_sujet` | 0 | — | — | — | 1.000 | non |
| `champs_manquants` | 8 | 0.571 | 1.000 | 0.727 | 0.833 | oui |

## Par langue et par source

| Groupe | n | F1 macro | F1 micro | F1 transport macro |
|---|---|---|---|---|
| langue = ar | 6 | 0.775 | 0.867 | 0.733 |
| langue = darija | 6 | 0.824 | 0.878 | 0.792 |
| langue = en | 3 | 0.782 | 0.875 | 0.600 |
| langue = fr | 15 | 0.950 | 0.947 | 0.913 |
| source = genere | 9 | 0.782 | 0.889 | 0.633 |
| source = humain | 21 | 0.902 | 0.921 | 0.838 |

(F1 macro d'un groupe : mêmes champs que la moyenne globale.)

## Matrices d'erreurs

**`type_voyage`** (lignes : attendu, colonnes : prédit)

| attendu \ prédit | amis | couple | famille | groupe | solo | None |
|---|---|---|---|---|---|---|
| amis | 7 | · | · | · | · | · |
| couple | · | 5 | · | · | · | · |
| famille | · | · | 8 | · | · | 1 |
| groupe | · | · | · | 1 | · | · |
| solo | · | · | · | · | 4 | · |
| None | · | · | 1 | 2 | · | 1 |

**`besoins_transport.vol`** (lignes : attendu, colonnes : prédit)

| attendu \ prédit | indifferent | non | oui |
|---|---|---|---|
| indifferent | 21 | · | · |
| non | 1 | 3 | 1 |
| oui | · | · | 4 |

**`besoins_transport.voiture`** (lignes : attendu, colonnes : prédit)

| attendu \ prédit | indifferent | non | oui |
|---|---|---|---|
| indifferent | 19 | · | · |
| non | 1 | 3 | 1 |
| oui | 2 | · | 4 |

**`besoins_transport.transfert`** (lignes : attendu, colonnes : prédit)

| attendu \ prédit | indifferent | oui |
|---|---|---|
| indifferent | 24 | · |
| oui | 4 | 2 |

