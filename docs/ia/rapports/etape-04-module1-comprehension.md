# Étape 04 — Module 1 : comprendre le voyageur (NLU)

> Date : 2026-11-10 · Branche : ia/etape-04 · Module(s) : 1 (NLU) · LLM : Ollama `qwen2.5:3b` local uniquement, coût 0 DT

## 1. Objectif

Transformer un message libre (français, anglais, arabe, darija) en `DemandeVoyage` structurée, avec
le bloc transport (`ville_depart`, `besoins_transport`, `preferences_transport`,
`budget_inclut_transport`). Exposer le résultat par `POST /api/ai/comprendre`, avec une question de
clarification quand un champ utile manque. Quand un vol est demandé, la question porte d'abord sur la
ville de départ, puis sur la date.

**Critère de « fini » du guide v2** : F1 par champ ≥ 0,85, champs transport compris. Il se traduit
ici par deux conditions sur le jeu test, avec la méthode hybride figée avant l'évaluation :
**F1 macro ≥ 0,85 et F1 transport macro ≥ 0,85**.

Contraintes de budget : aucune clé Claude, aucun appel payant. Le seul LLM appelé est Ollama
(`LLM_PROVIDER=ollama` dans `services/ai/.env`). Le code reste compatible avec Claude via
`ClientLLM`, mais Claude n'a jamais été appelé.

**Résultat : étape livrée avec réserve.** Le résultat officiel (hybride v1 sur les 115 demandes du
test) donne un F1 macro de 0,841 [0,810 ; 0,867] et un F1 transport de 0,831 [0,753 ; 0,890]. Le
seuil de 0,85 n'est pas atteint en valeur ponctuelle mais il est compris dans l'IC 95 %. L'étudiant
a décidé de cocher l'étape avec cette réserve (§ 5).

## 2. Réalisé

| Fichier | Créé / modifié | Rôle (une ligne) |
|---|---|---|
| `services/ai/app/nlu/__init__.py` | créé | Paquet du module 1 |
| `services/ai/app/nlu/schemas.py` | créé | `DemandeVoyage` (validateurs), requête et réponse de la route, schémas JSON envoyés au LLM (réduit, réduit + transport, complet) |
| `services/ai/app/nlu/normalisation.py` | créé | Normalisation : alias des 29 villes (fr / ar / darija), montants, durées, dates relatives, budget total, cohérence des voyageurs |
| `services/ai/app/nlu/regles.py` | créé | Extraction par règles : langue, hors sujet, villes, durée, date, budget, voyageurs, thèmes, activités, contraintes, transport ; liste des champs « sûrs » |
| `services/ai/app/nlu/prompt.py` | créé | Consigne courte en français + 5 exemples few-shot tirés **du dev uniquement** |
| `services/ai/app/nlu/clarification.py` | créé | Questions de clarification en fr / en / ar / darija ; priorité ville de départ puis date si vol |
| `services/ai/app/nlu/extraction.py` | créé | `comprendre()` : règles, LLM, fusion, validation tolérante, replis ; méthodes `regles` / `hybride` / `llm`, option `transport_llm` (v2, ablation) ; garde-fou anti-invention des voyageurs (`garde_voyageurs`, actif par défaut) |
| `services/ai/app/nlu/routes.py` | créé | `POST /api/ai/comprendre` (20/min, auth facultative, délai LLM `NLU_DELAI_LLM_S`) |
| `services/ai/app/main.py`, `app/config.py` | modifiés | Routeur NLU inclus (version 0.4.0) ; `NLU_DELAI_LLM_S = 25` |
| `libs/common/voyara_common/auth.py` | modifié | `get_optional_identity` : sans jeton → anonyme ; jeton invalide → 401 |
| `services/ai/scripts/evaluer_nlu.py` | créé | Évaluation : F1 par champ, macro et micro, transport, bootstrap, conditions API, provenance, cache Ollama |
| `services/ai/scripts/jeu_nlu.py` | modifié | Répartition dev / test (`repartir_dev_test`, graine 20261109) et `demandes_du_jeu` |
| `services/ai/data/eval/*.jsonl`, `README.md` | modifiés | Relectures appliquées (184 valide, 8 corrige) ; règle « destination hors catalogue » précisée |
| `docs/ia/relecture/relecture_*.xlsx` | modifiés | 14 écarts de relecture tranchés, G-137 et G-138 ajoutées, validations étendues à 29 villes |
| `docs/ia/resultats/nlu_*.md` / `.csv` | créés | 10 évaluations, avec provenance et IC 95 % |
| `docs/ia/resultats/accord_annotateurs.*` | modifiés | κ moyen 0,919 après application des relectures |
| `services/ai/tests/test_nlu_*.py` (4 fichiers) | créés | 123 tests du module 1 (LLM simulé, aucun réseau) |
| `services/ai/tests/test_main.py`, `test_relecture_jeu_nlu.py` | modifiés | Route `/api/ai/comprendre` attendue ; assertion figée sur `a_relire` remplacée |
| `.gitignore` | modifié | Cache des sorties Ollama (`services/ai/data/eval/cache/`) et fichiers de verrouillage Office (`~$*`) non versionnés |

## 3. Choix techniques

**Méthode hybride (règles + LLM) plutôt que LLM seul.**
- *Retenu* : les règles extraient les faits explicites (villes, montants, devise, durée, dates,
  langue, transport). Le LLM ne remplit, sur un schéma réduit à 9 champs (≈ 80 tokens de sortie), que
  ce qui demande de comprendre le texte : voyageurs, type de voyage, thèmes, activités, contraintes,
  hors sujet. Une valeur « sûre » des règles l'emporte sur le LLM, qui l'emporte sur une valeur non
  sûre.
- *Écartés* :
  - LLM seul : F1 macro 0,715 contre 0,879 sur les mêmes 30 demandes, et 78 s par demande sur ce
    poste ;
  - règles seules : elles sont sur-ajustées au dev et ne comprennent pas les tournures non prévues.
- Principe directeur respecté : le LLM comprend, les faits (montants, villes) ne viennent jamais de
  lui. Une activité proposée par le LLM n'est gardée que si au moins la moitié de ses mots figure dans
  le message.

**Définition du F1, figée avant toute évaluation.**
- **Valeurs vides** : une valeur nulle ou par défaut (`null`, liste vide, `indifferent`, `false`)
  compte comme « rien d'extrait ».
- **Précision et rappel** : précision = valeurs prédites justes / valeurs prédites ; rappel = valeurs
  prédites justes / valeurs attendues. Les listes sont comptées par élément.
- **Champs notés** : 28, dont `champs_manquants`. `horaires` n'est pas noté ; `budget_total_dt` est
  exclu car dérivé.
- **Seuil de support** : un champ de support < 5 est publié mais sort de la moyenne macro.
- **Scores publiés** :
  - F1 macro, qui est le critère ;
  - F1 micro global ;
  - même règle pour le bloc transport (8 champs) ;
  - par champ : support, précision, rappel, F1 et exactitude.

**Répartition dev / test.**
- Graine 20261109, stratifiée par langue, 40 % des demandes humaines au dev : dev = 77, test = 115.
- Les règles et le prompt ont été mis au point **sur le dev seulement**, en regardant ses erreurs.
- Sur le test, seuls des scores agrégés ont été lus (totaux, F1 par champ, par langue). **Aucune
  erreur individuelle du test n'a été regardée.** L'option `--erreurs` du script refuse le jeu test.

**Délai LLM de 25 s, puis repli sur les règles.**
- Le gateway coupe à 30 s. Au-delà de 25 s, la route répond donc avec les règles seules et
  l'avertissement « compréhension simplifiée », sans jamais renvoyer d'erreur 500.
- **À résoudre à l'étape 9** (démo) :
  - soit du streaming ;
  - soit un délai propre à `/api/ai` dans le gateway ;
  - dans tous les cas, `keep_alive` d'Ollama et un appel de préchauffage (§ 6).

**Refus de sécurité.** `LLMRefus` → la demande est traitée comme hors sujet, jamais contournée.

**Ablation « hybride v2 » (transport proposé par le LLM).** Elle a été **décidée après avoir vu le
total du test (0,831)**, donc ce n'est pas une décision a priori.
- *Principe* : là où les règles ne sont pas sûres d'un champ transport, la valeur d'Ollama est prise.
- *Garde-fou fixé à l'avance* : garder la v2 seulement si le F1 transport du dev reste ≥ 0,99.
- *Résultat* : 0,945 sur le dev, donc **v2 abandonnée et jamais évaluée sur le test**.
- Le code reste derrière l'option `transport_llm`, désactivée par défaut et non utilisée par la route.

**Garde-fou anti-invention des voyageurs.** Il a été **ajouté après le résultat officiel** : il
découle d'un principe du README (« les faits viennent du texte ») et n'a pas été ajusté sur le test.
**Son effet sur le test n'est pas mesuré** : le test n'a pas été relancé.
- *Principe* : en hybride, `nb_adultes` et `nb_enfants` venus du LLM ne sont gardés que si le nombre
  figure dans le message.
- *Ce qui compte comme nombre dit* :
  - chiffres, y compris arabes et collés à un préfixe (« ل٣ ») ;
  - mots-nombres en français, anglais, darija et arabe (deux, zouz, ثلاثة…) ;
  - effectifs implicites : « à deux » et « couple » valent 2, « seul » vaut 1.
- *Tolérance pour `nb_voyageurs`* (règle du README, « ena w s7abi 5 » = 6) : il est aussi gardé s'il
  se déduit directement du texte, soit locuteur + N, soit la somme de deux nombres dits.
- *Ce qui ne compte pas* : les nombres suivis d'une durée, de nuits, d'une monnaie, d'un âge
  (« 5 et 8 ans »), d'une heure ou d'un mois.
- Sinon, le champ reste vide, comme avec les règles, et la question de clarification est posée.
- *Reproduction* : l'option `--sans-garde` d'`evaluer_nlu.py` reproduit le code du résultat officiel.

**Provenance et reproductibilité.**
- *En-tête de chaque fichier `nlu_*.md`* :
  - commit Git et présence de modifications non commitées ;
  - variante ;
  - modèle Ollama, son digest et la version du serveur ;
  - temperature ;
  - nombre de demandes, date, replis et appels réels.
- *Cache des sorties brutes d'Ollama* : clé `id:sha12:schéma`, avec un fichier séparé pour la v2.
  Les fichiers de résultats sont régénérés depuis ce cache sans nouvel appel.

## 4. Vérification

Tests du service `ai`, avec `postgres-ai` démarré :

```text
PS> cd services\ai; ..\..\.venv\Scripts\python -m pytest -q
277 passed, 3 warnings in 8.54s
```

La référence avant l'étape était de 139 passed (+ 15 en échec faute de `postgres-ai`). Les 123
nouveaux tests du module 1 couvrent : normalisation, règles, fusion, replis, refus, prompt (few-shot
du dev uniquement), clarification en 4 langues, route (anonyme, jeton valide, jeton invalide → 401,
corps invalide → 422), métriques, bootstrap, conditions API, v2 et garde-fou des voyageurs
(« en famille » → vide et question posée ; « moi et trois potes » → 4 ; 2 adultes + 3 enfants → 5 ;
âges, durées et montants ignorés). Deux tests écrits avant le garde-fou acceptaient un nombre de
voyageurs inventé par le LLM simulé (« avec ma tribu » → 4, exemple 1 → 4) ; ils ont été adaptés. Le Dockerfile copie tout
`services/ai` (dont `scripts/`, importé par `app.nlu`) ; `test_nlu_normalisation.py` vérifie que
`app.nlu` s'importe.

Évaluation officielle :

```text
PS> ..\..\.venv\Scripts\python scripts\evaluer_nlu.py --methode hybride --jeu test
F1 macro 0.841 · F1 micro 0.892 · F1 transport macro 0.831 · micro 0.850
Replis : 0 · appels LLM réels : 107 · durée 2266 s · latence moyenne 20.9 s
```

Le fichier a ensuite été régénéré depuis le cache, avec la provenance, l'IC et les conditions API. Le
processus d'origine avait chargé le code avant l'ajout de la v2. Les scores régénérés ont été
comparés au fichier d'origine : identiques.

```text
IC 95 % bootstrap : F1 macro [0.810 ; 0.867] · F1 transport macro [0.753 ; 0.890]
Conditions API (> 25 s → règles) : 20/115 demandes (17.4%) · F1 macro 0.841 · F1 transport macro 0.831
```

Ablation v2 sur le dev :

```text
PS> ..\..\.venv\Scripts\python scripts\evaluer_nlu.py --methode hybride --variante v2 --jeu dev
F1 macro 0.952 · F1 micro 0.968 · F1 transport macro 0.945 · micro 0.941
F1 transport dev v2 = 0.945  → v2 abandonnée (< 0,99) : pas d'évaluation v2 sur le test
```

Appels réels à `POST /api/ai/comprendre`, service sur :8008 puis via le gateway :8000.

*Série 1* : juste après le calcul « Ollama seul », Ollama avait en cache un prompt différent.

```text
http://127.0.0.1:8008 | 200 | 25.4 s | methode=regles   (exemple 1, repli : LLM trop lent)
http://127.0.0.1:8008 | 200 | 25.3 s | methode=regles   (exemple 2)
http://127.0.0.1:8000 | 200 | 25.5 s | methode=regles   (exemple 1)
http://127.0.0.1:8000 | 200 | 25.3 s | methode=regles   (exemple 2)
```

Dans le journal d'Ollama, ces 4 appels apparaissent en HTTP 500 vers 25 s : la route a coupé la
requête. Un appel interrompu ne remplit pas le cache de prompt d'Ollama, donc tous les appels
suivants échouaient de la même façon.

*Série 2* : après un seul appel de préchauffage sans délai (97,7 s), avec le texte neutre
« préchauffage : séjour à Sousse ».

```text
http://127.0.0.1:8008 | 200 | 16.9 s | methode=hybride provider=ollama  (exemple 1)
http://127.0.0.1:8008 | 200 | 14.5 s | methode=hybride provider=ollama  (exemple 2)
http://127.0.0.1:8000 | 200 | 16.4 s | methode=hybride provider=ollama  (exemple 1)
http://127.0.0.1:8000 | 200 | 15.0 s | methode=hybride provider=ollama  (exemple 2)
```

Les 2 exemples du guide selon la méthode (série 2 pour l'hybride ; règles et Ollama seul par script,
sans délai) :

| Exemple | Champ | Règles | Ollama seul | Hybride |
|---|---|---|---|---|
| 1. « Je vais à Djerba 3 jours, 300 DT, en famille, culture et plage » | destination · durée · budget | Djerba · 3 · 300 TND | Djerba · 3 · 300 TND | Djerba · 3 · 300 TND |
| | voyageurs · type | **null** · famille | 4 (inventé) · famille | 3 (inventé) · famille |
| | thèmes | plage, culture | culture, plage | plage, culture |
| | champs manquants → question | voyageurs → « Combien de personnes voyagent… ? » | aucun | aucun |
| | temps | 0,1 s | 45,4 s | 16,9 s |
| 2. « On part de Tunis en avion, 4 jours à Djerba, 1200 DT à deux, avec une voiture » | destination · départ · durée · budget | Djerba · Tunis · 4 · 1200 TND | Djerba · Tunis · 4 · 1200 TND | Djerba · Tunis · 4 · 1200 TND |
| | voyageurs · type | 2 · **null** | 2 · amis (inventé) | 2 · amis (inventé) |
| | vol · voiture · transfert | oui · oui · indifférent | oui · **non** · indifférent | oui · oui · indifférent |
| | champs manquants → question | date_debut → « À quelle date… ? » | date_debut | date_debut → même question |
| | temps | 0,0 s | 38,9 s | 14,5 s |

Sur ces deux exemples, les règles sont les plus justes. Le LLM invente un nombre de voyageurs
(« en famille » sans nombre) et un type « amis » (« à deux », que la consigne demande de laisser à
null). C'est le même défaut que celui mesuré sur `type_voyage` au § 5.

*Série 3, avec le garde-fou des voyageurs* : préchauffage de 38,8 s, puis les mêmes appels.

```text
http://127.0.0.1:8008 | 200 | 15.9 s | methode=hybride  voyageurs=None type=famille  manquants=['voyageurs']
   question='Combien de personnes voyagent, et y a-t-il des enfants ?'
http://127.0.0.1:8008 | 200 | 15.3 s | methode=hybride  voyageurs=2 type=amis  manquants=['date_debut']
http://127.0.0.1:8000 | 200 | 18.0 s | methode=hybride  voyageurs=None type=famille  manquants=['voyageurs']
http://127.0.0.1:8000 | 200 | 16.8 s | methode=hybride  voyageurs=2 type=amis  manquants=['date_debut']
```

Le nombre de voyageurs n'est plus inventé : l'exemple 1 pose désormais la question, comme les
règles. `type_voyage = amis` reste inventé pour « à deux » : ce champ n'est pas couvert par le
garde-fou (piste du § 8).

## 5. Métriques

**Jeu** : `services/ai/data/eval/nlu_demandes.jsonl`.
- **Taille** : 192 demandes relues (184 `valide`, 8 `corrige`) ; 130 humaines, 62 générées.
- **Langues** : fr 96, ar 39, darija 37, en 20.
- **Transport** : 115 demandes avec un champ transport.
- **Accord inter-annotateurs** : κ moyen 0,919.
- **Répartition** : dev 77 (52 humaines + 25 générées) ; test 115 (78 + 37 ; fr 56, ar 23, darija
  23, en 13).
- **Échantillon de 30** : stratifié par langue, graine 20261109 (fr 15, ar 6, darija 6, en 3).

**IC 95 %** : bootstrap des demandes, 1 000 tirages, graine 20261109. Les tirages sont appariés : à
demandes égales, toutes les méthodes sont mesurées sur les mêmes tirages.

| Méthode | Jeu | n | F1 macro [IC 95 %] | F1 transport macro [IC 95 %] | Latence moy. |
|---|---|---|---|---|---|
| Règles seules | dev (mise au point) | 77 | 0,997 [0,993 ; 1,000] | 1,000 [1,000 ; 1,000] | < 0,1 s |
| Règles seules | test | 115 | 0,841 [0,798 ; 0,872] | 0,831 [0,753 ; 0,890] | < 0,1 s |
| **Hybride v1 — résultat officiel** | **test** | **115** | **0,841 [0,810 ; 0,867]** | **0,831 [0,753 ; 0,890]** | 20,8 s |
| Hybride v1 en conditions API (> 25 s → règles) | test | 115 | 0,841 | 0,831 | — |
| Règles seules | échantillon test | 30 | 0,843 [0,781 ; 0,894] | 0,786 [0,617 ; 0,927] | < 0,1 s |
| Ollama seul (schéma complet) | échantillon test | 30 | 0,715 [0,612 ; 0,780] | 0,617 [0,437 ; 0,749] | 77,8 s |
| Hybride v1 | échantillon test | 30 | 0,879 [0,818 ; 0,928] | 0,786 [0,617 ; 0,927] | 20,5 s |
| Hybride v2 (exploratoire, décidée après le total du test) | dev | 77 | 0,952 [0,930 ; 0,968] | 0,945 [0,908 ; 0,974] | 27,0 s |
| Hybride v2 | test | — | non évaluée (garde-fou du dev non atteint) | — | — |

Le F1 micro de l'hybride v1 sur le test est 0,892, contre 0,889 pour les règles. Le F1 transport micro
vaut 0,850 dans les deux cas.

**Critère** : v1 sur le test donne un F1 macro de 0,841 et un F1 transport de 0,831, tous deux
< 0,85. La borne haute des IC (0,867 et 0,890) dépasse 0,85 : avec 115 demandes, l'écart au seuil
n'est pas significatif dans un sens ni dans l'autre.

> **Étape 4 livrée avec réserve : F1 macro 0,841 [0,810 ; 0,867] et transport 0,831 [0,753 ; 0,890]
> sur le test, critère 0,85 non atteint en valeur ponctuelle mais compris dans l'IC 95 % ;
> amélioration prévue via un jeu de validation (pistes NLU).**

**Garde-fou des voyageurs, mesuré sur le dev seulement.** Les deux lignes utilisent le même cache
de sorties Ollama : 75 appels réels, puis une relecture du cache sans le garde-fou. Le garde-fou est
postérieur au résultat officiel, et **son effet sur le test n'est pas mesuré**.

| Hybride, dev (77) | F1 macro [IC 95 %] | `nb_voyageurs` P / R / F1 | `nb_adultes` P / R / F1 | `nb_enfants` P / R / F1 |
|---|---|---|---|---|
| sans garde-fou (code du résultat officiel) | 0,956 [0,939 ; 0,969] | 0,944 / 0,986 / 0,965 | 0,937 / 0,983 / 0,959 | 0,833 / 1,000 / 0,909 |
| **avec garde-fou** | **0,966 [0,952 ; 0,976]** | **1,000 / 0,986 / 0,993** | **1,000 / 0,983 / 0,992** | **1,000 / 1,000 / 1,000** |

Le rappel ne bouge pas sur les trois champs (0,986 ; 0,983 ; 1,000) : aucun total juste n'est perdu.
La précision passe à 1,000 : le garde-fou ne retire que des nombres inventés. Le F1 transport du dev
reste à 1,000.

Limite de cette mesure : sur le dev, les règles trouvent déjà ces effectifs (F1 0,993 / 0,992 /
1,000, identiques à l'hybride avec garde-fou), car elles y ont été mises au point. Le dev montre donc
que le garde-fou retire des inventions sans casser de totaux. Il ne montre pas ce qu'il apporterait
sur des tournures nouvelles.

**Où Ollama aide et où il nuit** (F1 par champ, test, 115 demandes) :

| Champ | Support | Règles | Hybride v1 | Effet |
|---|---|---|---|---|
| `activites_souhaitees` | 61 | 0,552 | 0,687 | aide |
| `champs_manquants` | 44 | 0,619 | 0,716 | aide |
| `nb_voyageurs` | 103 | 0,813 | 0,863 | aide |
| `nb_adultes` | 93 | 0,812 | 0,857 | aide |
| `preferences` | 52 | 0,842 | 0,869 | aide |
| `type_voyage` | 96 | 0,869 | 0,837 | **nuit** |
| `niveau_marche_max` | **6** | 0,500 | 0,160 | **nuit** |

Ollama aide sur la compréhension (activités, champs manquants, voyageurs) mais nuit sur
`type_voyage` et `niveau_marche_max`. Les deux effets s'annulent dans la moyenne macro, qui reste à
0,841 comme celle des règles. **Un champ de support 6** (`niveau_marche_max`) **pèse autant dans la
moyenne macro qu'un champ de support 103** : sa chute de 0,50 à 0,16 coûte à elle seule ≈ 0,015 de F1
macro. Le transport ne bouge pas en v1 : il vient uniquement des règles. Les champs les plus faibles
sont `transfert` (F1 0,645, rappel 0,476) et `voiture` (0,807, rappel 0,697).

**Par langue** (hybride v1, test) :

| Langue | n | F1 macro | F1 transport macro |
|---|---|---|---|
| fr | 56 | 0,886 | 0,890 |
| en | 13 | 0,823 | 0,748 |
| ar | 23 | 0,776 | 0,742 |
| darija | 23 | 0,761 | 0,760 |

Par source : 0,836 pour les demandes humaines et 0,819 pour les demandes générées.

**Ablation v2 sur le dev.** Le rappel transport reste à 1,000 ; seule la précision baisse : `voiture`
0,769, `vol` 0,839, `ville_depart` 0,917, `transfert` 0,923. Ollama n'ajoute que des fausses valeurs
là où les règles disaient « indifférent ».

**Latence et conditions API** : appels Ollama hybrides de 14 à 37 s une fois le modèle chargé (premier
appel : 71 s). 17,4 % des demandes du test dépassent 25 s, et 32,5 % avec le schéma v2 sur le dev.
Coût total : 0 DT. 308 appels Ollama locaux : 304 journalisés en succès dans `llm_appels`
(`usage = nlu`, `cout_estime` = 0), plus les 4 appels de la série 1 interrompus à 25 s. Aucun appel
Claude.

## 6. Limites, dette technique, risques

- **Critère non atteint en valeur ponctuelle** : 0,841 et 0,831 pour un seuil de 0,85, compris dans
  l'IC 95 %. L'étape est livrée avec cette réserve.
- **Garde-fou des voyageurs postérieur au résultat officiel** : il est mesuré sur le dev seulement,
  et son effet sur le test n'est pas connu. Le résultat officiel (0,841) a été obtenu sans lui.
- **Sur-apprentissage des règles sur le dev** : 0,997 sur le dev contre 0,841 sur le test. Les
  règles ont été mises au point en lisant les erreurs du dev, donc le score du dev est gonflé et ne
  mesure plus la généralisation. L'écart est le plus fort en arabe et en darija (0,776 et 0,761).
- **Pas de jeu de validation** : sans troisième jeu, toute nouvelle variante devrait être jugée sur le
  test, ce qui le contaminerait. C'est pour cela que la v2 a été jugée sur le dev et que plus aucune
  variante ne sera évaluée sur le test à l'étape 4.
- **v2 décidée après avoir vu le test** : le garde-fou du dev l'a écartée. Elle reste dans le code,
  désactivée, comme trace de l'ablation.
- **Effet du LLM sur `type_voyage` et `niveau_marche_max`** : `qwen2.5:3b` invente un type
  (« amis » pour « à deux »), malgré la consigne. Les exemples du guide le montrent aussi. Les
  nombres de voyageurs inventés (« en famille » → 3 ou 4) sont désormais écartés par le garde-fou.
- **Latence de démo** :
  - le modèle chargé, un appel prend 14 à 37 s, et 17 % des appels dépassent 25 s ;
  - après un autre prompt ou un déchargement, tous les appels échouent tant qu'un appel complet n'a
    pas reconstruit le cache de prompt d'Ollama : série 1 du § 4, 4 replis sur 4 ;
  - `keep_alive` par défaut d'Ollama : 5 min.
- **Changement de statut du jeu** : les JSONL étaient tous `a_relire`. L'application des relectures
  (`--appliquer`) est la première réelle : 184 `valide` et 8 `corrige`. L'assertion de
  `test_aller_retour_excel`, qui attendait `a_relire` en dur, a été corrigée pour comparer au statut
  du jeu.
- **Correction de mesure** : la latence d'un appel réel était comptée deux fois (mesure locale +
  latence en cache). C'est corrigé avant les runs officiels, et les fichiers concernés ont été
  régénérés.
- **Champs de faible support** : `budget_illimite`, `mobilite_reduite`, `vol_direct`, `boite_auto`,
  `priorite` et `hors_sujet` (support 1 à 3 sur le test) sont publiés mais hors moyenne macro.
- **Journal incomplet** : un appel coupé par le délai de la route (`asyncio.wait_for`) n'est pas
  écrit dans `llm_appels`. Les 4 replis de la série 1 n'y figurent pas, et le tableau de bord de
  l'étape 10 sous-estimerait ces replis. À corriger : journaliser l'annulation avec le statut
  `delai`.
- **Non testé** : Claude (aucune clé, aucun budget), `qwen2.5:7b` (RAM Docker insuffisante, étape 3).

## 7. À vérifier par moi

1. `docker compose up -d postgres` puis `docker compose --profile ollama up -d ollama` ; vérifier
   `docker exec voyara-ollama-1 ollama ps` (le modèle `qwen2.5:3b` doit être présent).
2. `cd services\ai; ..\..\.venv\Scripts\python -m pytest -q` → 277 passed attendus.
3. Relire les scores sans appel LLM :
   `..\..\.venv\Scripts\python scripts\evaluer_nlu.py --methode regles --jeu test` → 0,841 / 0,831.
4. Ouvrir `docs/ia/resultats/nlu_hybride_test.md` : provenance (commit `dcfea44` + modifications non
   commitées, `qwen2.5:3b` digest `357c53fb659c`, Ollama 0.40.6, temperature 0.0), conditions API,
   IC.
5. Démarrer le service (`.\scripts\dev.ps1`). Envoyer un premier message pour préchauffer, puis :
   `Invoke-RestMethod -Method Post http://127.0.0.1:8000/api/ai/comprendre -ContentType "application/json" -Body '{"texte":"On part de Tunis en avion, 4 jours à Djerba, 1200 DT à deux, avec une voiture"}'`
   → `methode = hybride`, `question_clarification` = date de départ. Avec l'exemple 1 (« … en
   famille, culture et plage »), `nb_voyageurs` doit rester vide et la question « Combien de
   personnes… ? » être posée.
6. Couper Ollama (`docker stop voyara-ollama-1`), renvoyer la même requête → réponse 200,
   `methode = regles`, avertissement « compréhension simplifiée ».

## 8. Étape suivante recommandée

**Étape 4 livrée avec réserve** (cochée par décision de l'étudiant). Pistes NLU gratuites, sans
toucher au jeu test actuel :

- écrire en équipe un **nouveau jeu de validation de 20 à 30 demandes**, pour choisir entre versions
  sans contaminer le test ;
- sur ce jeu, valider la **priorité des règles sur `type_voyage` et `niveau_marche_max`** (le LLM n'y
  écrirait que si les règles n'ont rien trouvé) ;
- mesurer sur ce même jeu l'effet du garde-fou des voyageurs ;
- n'évaluer sur le test qu'une seule fois, à la fin, la version choisie sur ce jeu de validation ;
- journaliser les appels coupés par le délai (`statut = delai`).

**Pour l'étape 9 (démo)** :
- `keep_alive` long pour Ollama (modèle gardé en mémoire) ;
- un appel de préchauffage au démarrage du service ;
- streaming, ou délai propre à `/api/ai` dans le gateway, au lieu de la coupure à 25 s.

Ensuite : **étape 5**, recherche sémantique, RAG et recherche transport. Elle consomme la
`DemandeVoyage` produite ici.
