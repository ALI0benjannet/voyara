# Accord entre annotateurs — jeu NLU (étape 4)

> Généré le 2026-11-09 par `services/ai/scripts/accord_annotateurs.py`. Annotateur A : équipe (`brut/demandes_equipe.json`) ; annotateur B : annotation du jeu (`demandes_humaines_a_annoter.jsonl`). 100 demandes humaines ; statuts : a_relire 100.

| Champ | n | Accords | Accord (%) | κ de Cohen | Interprétation |
|---|---|---|---|---|---|
| `destination` | 100 | 100 | 100.0 | 1.000 | presque parfait |
| `autres_villes` | 100 | 100 | 100.0 | — | — |
| `langue` | 100 | 100 | 100.0 | 1.000 | presque parfait |
| `type_voyage` | 100 | 82 | 82.0 | 0.776 | substantiel |
| `nb_voyageurs` | 100 | 96 | 96.0 | — | — |
| `duree_jours` | 100 | 100 | 100.0 | — | — |
| `budget_montant` | 100 | 88 | 88.0 | — | — |
| `budget_devise` | 100 | 100 | 100.0 | 1.000 | presque parfait |
| `budget_base` | 100 | 100 | 100.0 | 1.000 | presque parfait |
| `ville_depart` | 100 | 94 | 94.0 | 0.852 | presque parfait |
| `vol` | 100 | 92 | 92.0 | 0.792 | substantiel |
| `voiture` | 100 | 93 | 93.0 | 0.861 | presque parfait |
| `transfert` | 100 | 100 | 100.0 | 1.000 | presque parfait |
| `champs_manquants` | 100 | 77 | 77.0 | — | — |

κ moyen sur les 9 champs catégoriels : **0.920**.

Lecture : κ corrige l'accord du hasard (`null` compte comme une catégorie) ; échelle de Landis et Koch : > 0,8 presque parfait, > 0,6 substantiel, > 0,4 modéré. Les champs numériques ou listes (voyageurs, durée, montant, autres villes, champs manquants) n'ont qu'un pourcentage d'accord exact. Une partie des désaccords est **voulue** : les règles du README (budget par personne converti en total, date manquante pour un vol, type de voyage plus strict) ont été appliquées après coup à l'annotation B.
