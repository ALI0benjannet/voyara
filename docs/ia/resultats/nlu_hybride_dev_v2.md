# Évaluation NLU — méthode `hybride`, jeu `dev` — v2 exploratoire (transport aussi par le LLM)

## Provenance

| Élément | Valeur |
|---|---|
| Commit Git | `dcfea44` |
| Modifications non commitées | oui (32 fichiers modifiés ou non suivis) |
| Variante | v2 |
| LLM | Ollama `qwen2.5:3b` (digest `357c53fb659c`), serveur Ollama 0.40.6 · temperature 0.0 |
| Demandes évaluées | 77 |
| Date | 2026-11-09 23:44 |
| Replis sur les règles | 0 |
| Appels LLM réels (hors cache) | 75 |
| Note | Ablation v2, dÃ©cidÃ©e aprÃ¨s avoir vu le total du test v1 (0,831). Garde-fou : F1 transport du dev >= 0,99. |

## Conditions API

Simulation depuis le cache (aucun nouvel appel) : chaque demande dont l'appel Ollama a dépassé `NLU_DELAI_LLM_S` = 25 s reçoit la sortie des règles seules, comme la route. Le résultat officiel reste le F1 sans limite de temps ci-dessous ; celui-ci est une donnée pour l'étape 9.

| Conditions API | Valeur |
|---|---|
| Demandes au-delà de 25 s (repli sur les règles) | 25 / 77 (32.5%) |
| F1 macro en conditions API | 0.961 |
| F1 transport macro en conditions API | 0.968 |

> Généré le 2026-11-09 par `services/ai/scripts/evaluer_nlu.py`. 77 demandes relues (`valide` ou `corrige`). LLM : Ollama `qwen2.5:3b` (local). Coût : **0 DT** (aucun appel payant).

## Scores

| Score | Valeur |
|---|---|
| **F1 macro** (champs de support ≥ 5, critère « fini » ≥ 0,85) | **0.952** |
| F1 micro global (28 champs) | 0.968 |
| **F1 transport macro** (8 champs, support ≥ 5) | **0.945** |
| F1 transport micro | 0.941 |
| IC 95 % du F1 macro (bootstrap, 1000 tirages, graine 20261109) | [0.930 ; 0.968] |
| IC 95 % du F1 transport macro (idem) | [0.908 ; 0.974] |
| Latence moyenne | 27.0 s |
| Méthode effective | hybride 75, regles 2 |
| Replis sur les règles (LLM en panne, trop lent ou JSON invalide) | 0 |
| Coût | 0 DT |

Champs hors moyenne macro (support < 5) : `budget_illimite` (0), `mobilite_reduite` (3), `boite_auto` (4), `priorite` (2), `hors_sujet` (2).

## Par champ

| Champ | Support | Précision | Rappel | F1 | Exactitude | Macro |
|---|---|---|---|---|---|---|
| `destination` | 74 | 1.000 | 1.000 | 1.000 | 1.000 | oui |
| `autres_villes` | 11 | 1.000 | 1.000 | 1.000 | 1.000 | oui |
| `date_debut` | 7 | 1.000 | 1.000 | 1.000 | 1.000 | oui |
| `duree_jours` | 71 | 1.000 | 1.000 | 1.000 | 1.000 | oui |
| `nb_nuits` | 66 | 1.000 | 1.000 | 1.000 | 1.000 | oui |
| `budget_montant` | 68 | 1.000 | 1.000 | 1.000 | 1.000 | oui |
| `budget_devise` | 68 | 1.000 | 1.000 | 1.000 | 1.000 | oui |
| `budget_base` | 68 | 1.000 | 1.000 | 1.000 | 1.000 | oui |
| `budget_illimite` | 0 | — | — | — | 1.000 | non |
| `nb_voyageurs` | 69 | 0.944 | 0.986 | 0.965 | 0.935 | oui |
| `nb_adultes` | 60 | 0.937 | 0.983 | 0.959 | 0.935 | oui |
| `nb_enfants` | 10 | 0.909 | 1.000 | 0.952 | 0.987 | oui |
| `type_voyage` | 63 | 0.861 | 0.984 | 0.919 | 0.870 | oui |
| `preferences` | 52 | 0.963 | 1.000 | 0.981 | 0.974 | oui |
| `activites_souhaitees` | 63 | 0.896 | 0.952 | 0.923 | 0.883 | oui |
| `niveau_marche_max` | 5 | 0.556 | 1.000 | 0.714 | 0.948 | oui |
| `mobilite_reduite` | 3 | 1.000 | 1.000 | 1.000 | 1.000 | non |
| `langue` | 77 | 1.000 | 1.000 | 1.000 | 1.000 | oui |
| `ville_depart` (transport) | 22 | 0.917 | 1.000 | 0.957 | 0.974 | oui |
| `vol` (transport) | 26 | 0.839 | 1.000 | 0.912 | 0.935 | oui |
| `voiture` (transport) | 20 | 0.769 | 1.000 | 0.870 | 0.922 | oui |
| `transfert` (transport) | 12 | 0.923 | 1.000 | 0.960 | 0.987 | oui |
| `vol_direct` (transport) | 5 | 1.000 | 1.000 | 1.000 | 1.000 | oui |
| `boite_auto` (transport) | 4 | 1.000 | 1.000 | 1.000 | 1.000 | non |
| `priorite` (transport) | 2 | 1.000 | 1.000 | 1.000 | 1.000 | non |
| `budget_inclut_transport` (transport) | 36 | 0.947 | 1.000 | 0.973 | 0.974 | oui |
| `hors_sujet` | 2 | 1.000 | 1.000 | 1.000 | 1.000 | non |
| `champs_manquants` | 31 | 0.771 | 0.871 | 0.818 | 0.883 | oui |

## Par langue et par source

| Groupe | n | F1 macro | F1 micro | F1 transport macro |
|---|---|---|---|---|
| langue = ar | 16 | 0.960 | 0.974 | 0.900 |
| langue = darija | 14 | 0.824 | 0.949 | 0.902 |
| langue = en | 7 | 0.983 | 0.985 | 0.960 |
| langue = fr | 40 | 0.956 | 0.968 | 0.948 |
| source = genere | 25 | 0.961 | 0.970 | 0.990 |
| source = humain | 52 | 0.943 | 0.967 | 0.930 |

(F1 macro d'un groupe : mêmes champs que la moyenne globale.)

## Matrices d'erreurs

**`type_voyage`** (lignes : attendu, colonnes : prédit)

| attendu \ prédit | amis | couple | famille | groupe | solo | None |
|---|---|---|---|---|---|---|
| amis | 13 | · | · | · | · | · |
| couple | · | 19 | · | · | · | · |
| famille | · | · | 22 | · | · | · |
| groupe | · | · | · | 3 | · | · |
| solo | · | · | · | 1 | 5 | · |
| None | 4 | 3 | 1 | 1 | · | 5 |

**`besoins_transport.vol`** (lignes : attendu, colonnes : prédit)

| attendu \ prédit | indifferent | non | oui |
|---|---|---|---|
| indifferent | 46 | 1 | 4 |
| non | · | 9 | · |
| oui | · | · | 17 |

**`besoins_transport.voiture`** (lignes : attendu, colonnes : prédit)

| attendu \ prédit | indifferent | non | oui |
|---|---|---|---|
| indifferent | 51 | 4 | 2 |
| non | · | 9 | · |
| oui | · | · | 11 |

**`besoins_transport.transfert`** (lignes : attendu, colonnes : prédit)

| attendu \ prédit | indifferent | oui |
|---|---|---|
| indifferent | 64 | 1 |
| oui | · | 12 |

