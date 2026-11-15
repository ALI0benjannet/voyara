# Validation DL — Recherche d'activités : Transfer Learning vs Fine-Tuning d'embeddings

> Date : 2026-11-15 · Branche : `ons_work` · Ons · séance de validation Deep Learning (module Projet IA & Cognition, 5DS) · Module 2 (recherche sémantique, prépare l'étape 5)

## 1. Objectif

Répondre aux 5 points du professeur sur une tâche de VOYARA : à partir d'une requête libre (« plage calme en famille à Djerba », « nheb nchouf sahra f Tozeur »), retrouver les bonnes activités du catalogue. Comparer un modèle d'embeddings pré-entraîné **gelé** (Transfer Learning) et le **même modèle réentraîné** sur nos activités (Fine-Tuning), avec TF-IDF comme référence. Critère de « fini » (guide d'Ons, §10) : notebook exécutable de bout en bout, tableau global et par langue, 3 exemples d'erreurs, rapport.

## 2. Réalisé

| Fichier | Créé / modifié | Rôle (une ligne) |
|---|---|---|
| `services/ai/scripts/dl_recherche_catalogue.py` | créé | Export des activités (seed hors ligne ou `/internal/activities/export`) → `activites.json` + `activites_meta.json` |
| `services/ai/scripts/dl_recherche_jeu_test.py` | créé | Jeu de test de 70 requêtes rédigé à la main, titres vérifiés contre le catalogue |
| `services/ai/scripts/dl_recherche_paires.py` | créé | 291 paires d'entraînement + contrôle automatique de fuite du test |
| `services/ai/data/dl/activites.json`, `activites_meta.json` | créés | 115 activités (texte indexé ; ville, catégorie, thèmes, titres en/ar) |
| `services/ai/data/eval/recherche_requetes.jsonl` | créé | Jeu de test : 70 requêtes (35 fr · 14 en · 11 ar · 10 darija) |
| `services/ai/data/dl/paires_train.jsonl` | créé | 291 paires requête ↔ activité |
| `notebooks/05_dl_recherche.ipynb` | créé | Les 5 points : TF-IDF, choix du modèle, e5 gelé, fine-tuning (3 graines + variante), résultats, analyse |
| `docs/ia/resultats/dl_recherche*.csv`, `dl_recherche.md` | créés | Tableau final, historique, pertes par époque, choix du modèle, rangs par requête |
| `scripts/telecharger_modeles_dl.ps1` | créé | Téléchargement d'e5-base avec reprise (curl) pour une exécution locale |
| `requirements-dev.txt`, `services/ai/requirements.txt` | modifiés | sentence-transformers, transformers, torch, peft, scikit-learn (+ tabulate en dev) |
| `.gitignore` | modifié | `modeles/` (≈ 1,1 Go par modèle) jamais versionné |

## 3. Choix techniques

- **Catalogue hors ligne depuis le seed** (115 activités = 8 de `seed_catalog.py` + 107 de `seed_catalogue_demo.py`), thèmes calculés par `proposer_regles` de l'étape 2. Alternative : la route interne de catalog (prévue par le guide, gardée en `--source api`) ; écartée pour l'exécution car Docker n'était pas installé sur le poste.
- **Clé d'une activité = titre français** et non l'id SQL : unique (clé d'idempotence des seeds), identique hors ligne et en base, et lisible pour la relecture du jeu de test. L'id dépend de l'ordre d'insertion.
- **Point 1 — modèle : `intfloat/multilingual-e5-base`** (278 M). Mini-comparaison gelée sur le jeu de test : e5-base, e5-small (118 M, même famille), LaBSE (472 M, entraîné pour aligner des traductions), bge-m3 (568 M). bge-m3 est le meilleur gelé (nDCG@10 0,827 contre 0,796) mais 2 fois plus lourd et 2 fois plus lent par requête (22,8 ms contre 14 ms sur GPU) ; e5-base est retenu pour tourner sur CPU dans la démo. LaBSE, non entraîné pour la recherche, est nettement derrière (0,683).
- **Point 2 — Transfer Learning** : poids gelés, `passage: …` pour les activités et `query: …` pour les requêtes, embeddings normalisés, cosinus.
- **Point 3 — Fine-Tuning contrastif** : MultipleNegativesRankingLoss (négatifs = autres activités du batch, échelle 20). Boucle PyTorch écrite à la main pour : masquer les faux négatifs (même activité deux fois dans un batch), maîtriser les graines, et ne sauvegarder qu'une fois en fin de run (conseil de Boutheina). Hyperparamètres : 3 époques, lr 2e-5, warmup 10 %, batch 16, AdamW. Variante : embeddings + 6 premières couches gelées.
- **Paires d'entraînement** : titre anglais et titre arabe de chaque activité (208 paires, alignement entre langues) + 83 requêtes manuelles (60 fr, 18 darija, 5 en) pour les 8 activités sans traduction et la darija. Alternative : générer avec Ollama (guide) ; écartée faute de LLM disponible sur le poste au moment du travail.
- **Contrôle de fuite** : une paire est écartée si sa requête ressemble à une requête du test (cosinus des trigrammes ≥ 0,6) ou la contient → 7 écartées (ex. « Sunset camel ride in Tozeur » ~ R-036). Recontrôlé dans le notebook (0 requête du test dans l'entraînement).
- **Exécution de référence sur Kaggle (GPU)** : le notebook détecte Kaggle / Colab, clone la branche `ons_work` et ajoute bge-m3 à la comparaison. En local (CPU, 6 Go de RAM), un fine-tuning d'e5-base prend ≈ 1 h.

## 4. Vérification

- Données (local, PowerShell depuis la racine) :
  ```
  python services/ai/scripts/dl_recherche_catalogue.py
  115 activités (source : seed) → …\services\ai\data\dl
  Par ville : Djerba 37, Tunis 22, Tozeur 17, Hammamet 15, Sousse 13, Monastir 7, Tabarka 1, Douz 1, Bizerte 1, Korbous 1

  python services/ai/scripts/dl_recherche_jeu_test.py
  70 requêtes → …\services\ai\data\eval\recherche_requetes.jsonl
  Langues : {'fr': 35, 'en': 14, 'ar': 11, 'darija': 10}
  Pertinentes par requête (moyenne) : 2.03
  Activités pertinentes au moins une fois : 84 / 115

  python services/ai/scripts/dl_recherche_paires.py
  291 paires → …\services\ai\data\dl\paires_train.jsonl
  Par source : {'titre_ar': 104, 'manuelle': 83, 'titre_en': 104}
  Activités couvertes : 115 / 115
  Écartées (fuite du test, seuil 0.6) : 7
  ```
- Notebook : essai complet en local sur CPU avec e5-small (1 époque) → s'exécute de bout en bout sans erreur (un bug corrigé : `tokenize` de sentence-transformers 6 renvoie aussi du texte). Exécution de référence : Kaggle, GPU, branche `ons_work` (commit `afec0ed`), « Run All » ; archive `resultats_dl_recherche.zip` rapatriée dans `docs/ia/resultats/`. Le notebook versionné est sans sorties.
- Sortie du contrôle de fuite dans le notebook : `Requêtes du test présentes dans l'entraînement : 0`.

## 5. Métriques

Jeu de test : `recherche_requetes.jsonl`, 70 requêtes rédigées par l'équipe, 1 à 5 activités pertinentes (2,03 en moyenne), sur 115 activités. Fine-tuning : moyenne de 3 graines (42, 7, 2026), écart-type ≤ 0,010.

| Approche | Recall@5 | Recall@10 | nDCG@10 | MRR | Entraînement | Latence / requête |
|---|---:|---:|---:|---:|---:|---:|
| Baseline TF-IDF (caractères 3-5) | 0,651 | 0,737 | 0,626 | 0,630 | — | 1,3 ms |
| **DL Transfer Learning (e5 gelé)** | **0,830** | **0,907** | **0,796** | **0,787** | — | 11,7 ms |
| DL Fine-Tuning complet (3 graines) | 0,793 ± 0,010 | 0,867 ± 0,006 | 0,758 ± 0,001 | 0,741 ± 0,002 | 24 s (GPU) | 11,7 ms |
| DL Fine-Tuning, 6 couches gelées (3 graines) | 0,794 ± 0,005 | 0,868 ± 0,004 | 0,772 ± 0,004 | 0,773 ± 0,005 | 14 s (GPU) | 11,5 ms |

nDCG@10 par langue :

| Approche | fr (35) | en (14) | ar (11) | darija (10) |
|---|---:|---:|---:|---:|
| TF-IDF | 0,844 | 0,567 | 0,085 | 0,539 |
| e5 gelé | **0,876** | 0,811 | 0,658 | **0,645** |
| Fine-Tuning complet (3 graines) | 0,810 | 0,837 | **0,715** | 0,508 |
| Fine-Tuning 6 couches gelées | 0,841 | **0,838** | 0,704 | 0,517 |

Choix du modèle (gelés, même jeu de test, GPU) :

| Modèle | Paramètres | nDCG@10 | Recall@5 | MRR | Latence |
|---|---:|---:|---:|---:|---:|
| multilingual-e5-base (retenu) | 278 M | 0,796 | 0,830 | 0,787 | 14,0 ms |
| multilingual-e5-small | 118 M | 0,777 | 0,791 | 0,774 | 11,0 ms |
| LaBSE | 472 M | 0,683 | 0,721 | 0,658 | 11,4 ms |
| bge-m3 | 568 M | 0,827 | 0,841 | 0,829 | 22,8 ms |

- Le Deep Learning bat nettement la baseline : +0,17 de nDCG@10 pour e5 gelé, et l'arabe passe de 0,085 (TF-IDF ne relie pas l'arabe au texte français) à 0,658.
- **Le fine-tuning ne bat pas le modèle gelé** sur l'ensemble (0,758 contre 0,796) : il gagne en anglais (+0,03) et en arabe (+0,06), mais perd en français (−0,07) et en darija (−0,14). Geler les 6 premières couches limite la perte (0,772).
- Requêtes sans aucune bonne activité dans le top 5 : TF-IDF 18, e5 gelé 8, fine-tuné (graine 42) 10. Par rapport au gelé, le fine-tuning améliore le rang de 13 requêtes, en dégrade 15, en laisse 42 identiques.
- Perte d'entraînement (moyenne par époque) : 0,885 → 0,189 → 0,093 (graine 42) — le modèle apprend très vite ses 291 paires.

## 6. Limites, dette technique, risques

- **Analyse critique — pourquoi le fine-tuning déçoit** : 72 % des paires (208 / 291) sont des **titres traduits** en anglais ou en arabe. Le modèle apprend surtout « titre en/ar → texte français », d'où le gain en anglais et en arabe, mais il n'a vu que 60 requêtes françaises et 18 en darija, formulées autrement que le test : il s'écarte de ce que le pré-entraînement savait déjà faire en français. La perte qui tombe à 0,09 dès la 3e époque montre un sur-apprentissage sur un petit jeu. Avec 115 activités, e5 gelé est déjà fort (0,83 de Recall@5) : la marge de gain est faible.
- **3 exemples d'erreurs** (rangs de la 1re activité pertinente, TF-IDF / gelé / fine-tuné) :
  1. R-067 darija « nhebou na3mlou dawra bel babour » (faire un tour en bateau) : 15 / **4** / 69 — le fine-tuning a « oublié » *babour* ; top 1 : « Marché du vendredi et poterie de Nabeul ».
  2. R-011 fr « sensations fortes sur l'eau à Sousse » : 27 / **2** / 16 — « eau » attire la thalasso (« bassin d'eau de mer ») au lieu du jet-ski : confusion de sens sur un mot partagé.
  3. R-059 ar « جولة في الواحات بسيارة رباعية الدفع » (circuit des oasis en 4x4) : 87 / 42 / 23 — amélioré par le fine-tuning mais toujours raté : son titre arabe d'entraînement, trop proche du test, a été écarté par le contrôle de fuite, et le nom des oasis n'apparaît pas dans la requête.
  Inversement, R-036 « camel ride in the desert at sunset » (6 → **1**) et R-055 « جولة بالدراجة الهوائية » (9 → **1**) profitent de l'entraînement en anglais et en arabe (pour R-036, le titre anglais le plus proche avait pourtant été écarté par le contrôle de fuite).
- **Le gain justifie-t-il le coût ?** Non en l'état : le fine-tuning coûte peu (24 s sur GPU, ≈ 1 h sur CPU) mais oblige à héberger un modèle de 1,1 Go spécifique, pour un résultat global inférieur. Recommandation : e5 gelé (ou bge-m3 si le serveur le permet) dans une recherche **hybride** avec BM25 (étape 5).
- Jeu de test petit (70 requêtes) et écrit par l'équipe ; **pas encore relu par Boutheina** (prévu par le guide avant le fine-tuning) ; catalogue de démonstration, pas de vraies requêtes d'utilisateurs ; 8 activités sans traduction ni thèmes validés.
- Thèmes calculés par les règles de l'étape 2 (propositions non validées : 0/117 validées en base).
- bge-m3 mesuré seulement gelé ; la variante de négatifs difficiles (bonus du guide) n'est pas faite.
- Le modèle fine-tuné n'est sauvegardé que dans la session Kaggle (pas copié sur Drive).

## 7. À vérifier par moi

1. Faire relire `services/ai/data/eval/recherche_requetes.jsonl` par Boutheina (activités pertinentes correctes pour chaque requête). Si elle corrige : `python services/ai/scripts/dl_recherche_jeu_test.py`, puis `python services/ai/scripts/dl_recherche_paires.py`, puis relancer le notebook.
2. Relire `services/ai/data/dl/paires_train.jsonl` (surtout les 18 requêtes darija).
3. Sur Kaggle : ouvrir le notebook importé depuis `ons_work`, Settings → GPU T4 + Internet on → Run All (≈ 15 min) ; vérifier que les chiffres correspondent à `docs/ia/resultats/dl_recherche.md`. Télécharger le notebook exécuté (File → Download Notebook) pour la démo.
4. Préparer les 5 slides du guide (§7) à partir des tableaux du §5 et des exemples du §6, puis répéter avec Boutheina.

## 8. Étape suivante recommandée

Rééquilibrer les paires (plus de requêtes françaises et darija, négatifs difficiles de la même ville) et relancer le fine-tuning pour vérifier si l'écart avec le modèle gelé se referme. Puis l'**étape 5** du guide : index pgvector avec e5 gelé + BM25 + RRF (la baseline BM25 de Boutheina sur ce même jeu servira de point de comparaison), `POST /api/ai/rechercher`.
