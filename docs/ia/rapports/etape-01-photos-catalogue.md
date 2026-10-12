# Étape 01 (sous-tâche) — Photos du catalogue de démonstration

> Date : 2026-10-12 · Branche : `ia/etape-01` · Module(s) : 2 (données) ·
> Suite de : [etape-01-seed-catalogue.md](etape-01-seed-catalogue.md) §6 (« Pas de photos »)

## 1. Objectif

Les 86 activités de `seed_catalogue_demo.py` avaient `photos = NULL` : le site client affichait un
placeholder beige « Photo — Tozeur, palmeraie ». L'objectif est de donner une vraie photo à chacune.

**Critère de « fini »** (plan validé le 12/10/2026) :
- une photo libre de droits par activité, montrant le lieu réel quand c'est possible ;
- images **versionnées dans Git** (décision de l'utilisateur), pour que les collègues les reçoivent par `git pull` ;
- script idempotent qui relie les photos en base **sans réseau** et sans écraser une photo existante ;
- attribution de chaque image sur la page `/credits`.

## 2. Réalisé

| Fichier | Créé / modifié | Rôle (une ligne) |
|---|---|---|
| `services/catalog/scripts/seed_photos_demo.py` | créé | Table titre → fichier Commons (86 entrées). Trois modes : par défaut (relie en base), `--verifier`, `--telecharger` (mainteneur). |
| `services/catalog/static/activities/demo/*.jpg` | créés | 86 images, nommées d'après le titre (`<slug>.jpg`), 21,2 Mo au total. |
| `frontend/apps/client/src/app/credits/photo-credits.json` | modifié | 86 attributions ajoutées (8 → 94 entrées). |
| `services/catalog/app/admin_routes.py` | modifié | `_delete_photo_file` ne supprime plus un fichier de `demo/` quand l'admin remplace une photo. |
| `RUN.md` §5.4 | modifié | Commande `seed_photos_demo.py` après `seed_catalogue_demo.py`. |
| `docs/architecture.md` §7 | modifié | Script ajouté à la liste des seeds. |
| `docs/plan.md`, `docs/ia/journal.md`, `docs/ia/README.md` | modifiés | Sous-tâche cochée, ligne de journal, index des rapports. |
| `docs/ia/rapports/etape-01-photos-catalogue.md` | créé | Ce rapport. |

Aucun modèle, aucune route publique, aucun composant front n'a changé : `ActivityImage` affichait déjà `photos`.

## 3. Choix techniques

| Décision | Option retenue | Alternatives envisagées | Pourquoi écartées |
|---|---|---|---|
| Stockage des images | **Versionnées dans Git** (`static/activities/demo/`) | Téléchargement sur chaque poste | Décision de l'utilisateur. Un téléchargement par poste dépend d'Internet et du quota Commons : HTTP 429 sur 8 images sur 86 au premier passage, voir §4. |
| Nom de fichier | **Slug du titre français** (`musee-dar-cherait.jpg`) | Convention admin `<id>-<hash>.jpg` | L'`id` d'une activité diffère d'un poste à l'autre. Un fichier versionné doit avoir le même nom partout. |
| Choix des images | **À la main**, après recherche dans l'API Commons, en privilégiant le lieu réel | Première image renvoyée par la recherche | La recherche renvoie souvent des images hors sujet (« Ghriba du Kef », « Grand Canyon mid-air collision » pour « Mides canyon »). |
| Licence | **Lue dans `extmetadata.LicenseShortName`** ; seules CC0, domaine public, CC BY et CC BY-SA sont acceptées, sinon refus | Licence recopiée à la main (comme `seed_photos.py`) | Une licence recopiée peut être fausse. Lue à la source, elle est vérifiable. |
| Poids | Vignette demandée en 1024 px, **800 px si le fichier dépasse 400 Ko** | Recompression avec Pillow | Pillow n'est pas une dépendance du projet. On laisse Commons redimensionner. |
| Réutilisation | `download`, `with_retry`, `PHOTO_DIR`, `CREDITS_FILE`, `USER_AGENT` **importés** de `seed_photos.py` | Copier ces fonctions | Pas de duplication. |
| Upload admin | **Garde-fou** : un fichier de `demo/` n'est jamais supprimé | Laisser tel quel | Sinon, remplacer la photo d'une activité de démo depuis l'admin supprimerait un fichier suivi par Git, qui apparaîtrait « supprimé » dans `git status`. |

## 4. Vérification

Commandes lancées depuis `services\catalog` (PowerShell / Git Bash), avec le backend démarré.

**1. Téléchargement** (premier passage, extrait) : 78 images téléchargées et 8 refus du quota, sans aucune licence refusée.

```text
PS> ..\..\.venv\Scripts\python scripts\seed_photos_demo.py --telecharger
  + synagogue-de-la-ghriba-et-village-d-erriadh.jpg <- El Ghriba Synagogue, Djerba.jpg (CC BY 4.0, 334 Ko)
  ...
  ! Site antique de Meninx et chaussée d'El Kantara : HTTP Error 429: Too Many Requests
  ...
Terminé : 78 téléchargée(s), 0 déjà présente(s), 0 licence(s) refusée(s), 8 échec(s).
```

Une relance a complété les 8 manquantes (`8 téléchargée(s), 78 déjà présente(s), 0 licence(s) refusée(s), 0 échec(s)`).

**2. Contrôle visuel** : j'ai ouvert 12 images pour les comparer à leur activité. J'en ai corrigé cinq, une fois retéléchargées :

| Activité | Avant | Après |
|---|---|---|
| Quad dans l'arrière-pays de Midoun | portail djerbien bleu | menzels et oliviers |
| Dîner traditionnel djerbien dans un menzel | menzels et oliviers | portail djerbien bleu |
| De Skanes à la médina de Monastir à vélo | cheval sur une plage | Ribat de Monastir |
| Balade à cheval à Chott Meriem | chevaux à La Marsa | cheval sur la plage de Monastir |
| Balade à cheval entre plage et orangeraies | bateau et jet-skis à Hammamet | chevaux sur la plage de La Marsa |

**3. Contrôle sans base**, puis contrôle d'un cas faux injecté :

```text
PS> ..\..\.venv\Scripts\python scripts\seed_photos_demo.py --verifier
Photos valides : 86 fichiers dans ...\services\catalog\static\activities\demo.

# titre inventé ajouté + « Musée Dar Cherait » retiré de la table
['pas de photo prévue : Musée Dar Cherait', 'titre inconnu du seed : Titre inventé',
 'fichier absent : titre-invente.jpg', 'crédit manquant : Inexistant.jpg']
```

**4. Liaison en base, puis idempotence**

```text
----- 1er passage -----
Photos valides : 86 fichiers dans ...\static\activities\demo.
Terminé : 86 photo(s) reliée(s), 0 activité(s) déjà illustrée(s), 0 absente(s) de la base.
----- 2e passage (idempotence) -----
Terminé : 0 photo(s) reliée(s), 86 activité(s) déjà illustrée(s), 0 absente(s) de la base.
```

**5. API publique et gateway (:8000)**

```text
total API : 96 · avec photo : 96 · dont demo/ : 86
sans photo : []
200 image/jpeg 288507 /static/activities/demo/atelier-khobz-mella-le-pain-cuit-dans-le-sable.jpg
200 image/jpeg 249092 /static/activities/demo/randonnee-dans-les-gorges-de-mides.jpg
```

**6. Site client (:5173)**
- Le HTML rendu de `/activities?search=tozeur` référence bien `activities/demo/caleche-dans-la-palmeraie-de-tozeur.jpg`, etc.
- `/credits` répond 200 et contient « Mides Canyon ».

**Non vérifié** :
- je n'ai pas regardé la page dans un navigateur (seulement le HTML rendu) ;
- 74 des 86 images n'ont été contrôlées que par leur nom de fichier et leur description Commons, pas visuellement.

## 5. Métriques

| Mesure | Valeur |
|---|---|
| Activités illustrées | 96 / 96 (86 démo + 8 d'origine + 2 de test) |
| Taille ajoutée au dépôt | 21,2 Mo (86 fichiers, 111 à 384 Ko, environ 250 Ko en moyenne) |
| Licences des 94 crédits | CC BY-SA 4.0 : 56 · CC BY-SA 3.0 : 10 · CC0 : 8 · CC BY 2.0 : 7 · CC BY-SA 2.0 : 6 · CC BY 4.0 : 5 · CC BY 3.0 : 1 · domaine public : 1 |
| Requêtes Commons | 140 recherches + 91 téléchargements réussis (78, puis 8 relancés après le quota, puis 5 remplacés) |
| Images « illustration » (même type d'activité, autre lieu) | 9 (voir §6) |

## 6. Limites, dette technique, risques

- **Écart avec le plan** : le plan annonçait environ 13 Mo. Commons renvoie des vignettes normalisées de 1280 px au lieu de 1024, d'où 21,2 Mo. Chaque fichier reste sous 400 Ko.
- **9 images d'illustration** : aucune image libre ne montre l'activité au lieu exact. Elles sont marquées `# illustration` dans le script :
  - plongée à Djerba (Sardaigne), à Port El Kantaoui (Floride) et à Hammamet (épave en Égypte) ;
  - jet-ski à Sidi Mahrez (Seychelles) et à Port El Kantaoui (Floride) ;
  - cheval à Aghir (plage non située) et à Hammamet (La Marsa) ;
  - quad à Tozeur (Namibie) ;
  - calligraphie (calligraphie sur bois, non située).

  À remplacer par de vraies photos de prestataires si le projet en obtient.
- **Images peu engageantes** : « Djerba Explore » montre un crocodile en train de manger. C'est fidèle au parc, mais pas très vendeur. « Charfia à Ajim » montre le port d'Ajim, pas une charfia : les images libres de charfia sont prises aux Kerkennah.
- **Poids du dépôt** : 21 Mo de binaires dans l'historique Git, définitivement. Acceptable pour un projet étudiant. Au-delà, il faudrait Git LFS.
- **Crédits** : la page `/credits` liste désormais 94 entrées en une seule liste. Elle reste lisible, mais un regroupement par ville serait plus clair.
- **Activités de test** (« touzer », « claude ») : toujours en base, comme signalé dans le rapport précédent.

## 7. À vérifier par moi

1. `git branch --show-current` → `ia/etape-01`.
2. Depuis `services\catalog` : `..\..\.venv\Scripts\python scripts\seed_photos_demo.py --verifier` → « Photos valides : 86 fichiers ».
3. Relance `..\..\.venv\Scripts\python scripts\seed_photos_demo.py` → « 0 photo(s) reliée(s), 86 activité(s) déjà illustrée(s) ».
4. Sur http://localhost:5173, parcours les activités de Djerba et de Tozeur : chaque carte a une photo. Signale celles qui ne te plaisent pas, en particulier les 9 illustrations du §6.
5. Ouvre http://localhost:5173/credits : les nouvelles attributions apparaissent.
6. Dans l'admin, remplace la photo d'une activité de démo, puis lance `git status` : aucun fichier de `demo/` ne doit apparaître supprimé.
7. Commit (message proposé dans le chat).

## 8. Étape suivante recommandée

Reprendre la suite de l'**étape 1** prévue dans [etape-01-seed-catalogue.md](etape-01-seed-catalogue.md) §8 :
base `voyara_ai`, table `pois`, collecte Overpass (≥ 300 POI), client Open-Meteo avec cache, notebook d'EDA.
