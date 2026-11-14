# Validation DL — classification des demandes : résultats finaux

F1 macro sur les 115 demandes de test (`nlu_demandes.jsonl`, jeu `test`), jamais utilisées pour entraîner ni pour régler.
Entraînement : `services/ai/data/dl/classif_train.jsonl` (77 demandes du dev + 231 paraphrases relues).

| Approche | type_voyage | vol | voiture |
| :--- | ---: | ---: | ---: |
| ML : TF-IDF + régression logistique | 0,460 | 0,513 | 0,604 |
| DL Transfer Learning : XLM-R gelé + régression logistique | 0,366 | 0,595 | 0,538 |
| **DL Fine-Tuning phase 1 (4 dernières couches), moyenne de 3 graines** | **0,547 ± 0,015** | **0,602 ± 0,006** | **0,808 ± 0,029** |
| DL Fine-Tuning phase 2 (tout dégelé), 1 graine | 0,486 | — | — |

## F1 par langue (1 graine)

| Approche | Champ | fr | en | ar | darija |
| :--- | :--- | ---: | ---: | ---: | ---: |
| ML TF-IDF | type_voyage | 0,470 | 0,314 | 0,407 | 0,462 |
| ML TF-IDF | vol | 0,507 | 0,375 | 0,574 | 0,642 |
| ML TF-IDF | voiture | 0,666 | 0,619 | 0,467 | 0,577 |
| XLM-R gelé | type_voyage | 0,410 | 0,157 | 0,299 | 0,372 |
| XLM-R gelé | vol | 0,685 | 0,571 | 0,435 | 0,743 |
| XLM-R gelé | voiture | 0,606 | 0,822 | 0,451 | 0,329 |
| FT phase 1 | type_voyage | 0,668 | 0,667 | 0,505 | 0,433 |
| FT phase 1 | vol | 0,736 | 0,578 | 0,580 | 0,302 |
| FT phase 1 | voiture | 0,845 | 1,000 | 0,881 | 0,252 |

Effectifs du test par langue : fr 56, en 13, ar 23, darija 23 (un score sur 13 demandes est peu fiable).
L'historique de toutes les tentatives (dont la tentative 1 sans poids de classes) est dans `dl_classif_historique.csv`.
