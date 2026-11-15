"""Paires d'entraînement de la validation DL « recherche » (guide d'Ons, étape C).

Écrit services/ai/data/dl/paires_train.jsonl : {"requete", "activite", "source", "langue"}
où `activite` = titre français (clé de activites.json).

Deux sources :
- `titre_en` / `titre_ar` : le titre anglais et arabe de chaque activité du seed, utilisé
  comme requête vers le texte français (apprend l'alignement entre langues) ;
- `manuelle` : requêtes écrites à la main (fr, en, darija), vagues ou avec contrainte,
  pour les cas que les titres ne couvrent pas (8 activités sans traduction, darija).

Règle d'or (contrôle de fuite) : une paire est écartée si sa requête ressemble à une
requête du jeu de test (similarité cosinus des trigrammes de caractères ≥ SEUIL_FUITE)
ou la contient mot pour mot. Les paires écartées sont listées.

Usage (depuis la racine) : python services/ai/scripts/dl_recherche_paires.py
"""

import json
import math
import random
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RACINE = Path(__file__).resolve().parents[3]
DL = RACINE / "services" / "ai" / "data" / "dl"
TEST = RACINE / "services" / "ai" / "data" / "eval" / "recherche_requetes.jsonl"
SORTIE = DL / "paires_train.jsonl"
SEUIL_FUITE = 0.6

# (langue, requête, titre français)
MANUELLES = [
    # --- 8 activités sans traduction dans le seed
    ("fr", "balade entre maisons bleues et vestiges antiques", "Sidi Bou Saïd & Carthage"),
    ("darija", "nheb nemchi l Sidi Bou Said nechreb ahwa", "Sidi Bou Saïd & Carthage"),
    ("en", "coral reef dive in the north west", "Plongée aux récifs de Tabarka"),
    ("fr", "explorer les fonds marins coralliens", "Plongée aux récifs de Tabarka"),
    ("fr", "camper une nuit dans les dunes", "Bivouac dans le désert de Douz"),
    ("darija", "nbatou fel sahra f Douz", "Bivouac dans le désert de Douz"),
    ("fr", "découverte culinaire à pied dans la vieille ville", "Food tour de la médina de Tunis"),
    ("darija", "nhebou nda9ou lmakla fel medina", "Food tour de la médina de Tunis"),
    ("fr", "pagayer sur un lac au nord", "Kayak sur le lac de Bizerte"),
    ("en", "kayaking on a lagoon near Bizerte", "Kayak sur le lac de Bizerte"),
    ("fr", "survoler les palmeraies en ballon", "Montgolfière sur les oasis de Tozeur"),
    ("darija", "nheb ntir fel montgolfière", "Montgolfière sur les oasis de Tozeur"),
    ("fr", "navigation tranquille quand le soleil se couche sur l'île", "Croisière au couchant à Djerba"),
    ("en", "evening boat cruise on Djerba", "Croisière au couchant à Djerba"),
    ("fr", "marche sur les sentiers côtiers du Cap Bon", "Randonnée au Cap Bon"),
    ("darija", "randonnée fel jbal 9rib l Korbous", "Randonnée au Cap Bon"),
    # --- Djerba
    ("fr", "lieu de pèlerinage juif à Djerba", "Synagogue de la Ghriba et village d'Erriadh"),
    ("fr", "art urbain dans un village djerbien", "Parcours street art Djerbahood à Erriadh"),
    ("darija", "nheb nkhdem bidi fel fokhar", "Atelier de poterie à Guellala"),
    ("fr", "reconstitution d'un mariage traditionnel", "Musée du patrimoine de Guellala"),
    ("fr", "flâner dans les souks de la capitale de l'île", "Visite guidée de Houmt Souk : souks, fondouks et Borj El Kebir"),
    ("fr", "architecture religieuse ibadite", "Circuit des mosquées ibadites : Fadhloun et El May"),
    ("fr", "crocodiles et musée des arts", "Musée Lalla Hadria et parc Djerba Explore"),
    ("darija", "souk el jom3a f Midoun", "Marché hebdomadaire de Midoun"),
    ("fr", "cité antique romaine sur l'île", "Site antique de Meninx et chaussée d'El Kantara"),
    ("darija", "dawra bel bicyclette f jerba", "Tour de Djerba à vélo : menzels et huileries souterraines"),
    ("fr", "marche facile entre villages et oliviers", "Randonnée douce à Mahboubine et El May"),
    ("fr", "glisser sur l'eau tiré par une voile", "Initiation au kitesurf sur la lagune de Bin El Ouedian"),
    ("fr", "moto des mers à Djerba", "Jet-ski à la plage de Sidi Mahrez"),
    ("darija", "nheb ntir fel parachute fel b7ar", "Parachute ascensionnel à la plage de Sidi Mahrez"),
    ("fr", "pêcher comme les anciens avec des palmes", "Pêche traditionnelle à la charfia avec les pêcheurs d'Ajim"),
    ("fr", "pagaie debout sur une mer calme", "Stand-up paddle à la plage de la Seguia"),
    ("fr", "équitation sur le sable", "Balade à cheval sur la plage d'Aghir"),
    ("darija", "nsou9 quad f Midoun", "Quad dans l'arrière-pays de Midoun"),
    ("fr", "ornithologie dans une zone humide", "Observation des oiseaux à la lagune de Bin El Ouedian"),
    ("fr", "deux jours dans le désert avec source chaude", "Excursion de 2 jours à Ksar Ghilane"),
    ("fr", "maisons creusées dans la roche et greniers fortifiés", "Journée à Matmata et aux ksour de Tataouine"),
    ("darija", "nheb nta3allem ntayeb makla jerbia", "Cours de cuisine djerbienne chez l'habitant"),
    ("fr", "poisson frais vendu aux enchères", "Criée aux poissons et dégustation au port de Houmt Souk"),
    ("fr", "souper typique dans une maison djerbienne", "Dîner traditionnel djerbien dans un menzel"),
    ("fr", "soins à l'eau de mer à Djerba", "Demi-journée thalasso à Djerba : parcours marin, hammam et enveloppement"),
    ("fr", "parcours de 18 trous sur l'île", "Parcours de golf au Djerba Golf Club"),
    # --- Tunis
    ("fr", "plus grand musée de mosaïques du pays", "Musée national du Bardo : mosaïques romaines"),
    ("darija", "nheb nzour jemaa ezzitouna", "Médina de Tunis : Zitouna et Dar Ben Abdallah"),
    ("fr", "palais et jardins d'un musicien à Sidi Bou Saïd", "Dar Ennejma Ezzahra, palais du baron d'Erlanger"),
    ("fr", "écrire en arabe avec un calame", "Atelier de calligraphie arabe dans la médina"),
    ("fr", "fabrication du bonnet rouge traditionnel", "Souk des Chaouachia : la chéchia tunisienne"),
    ("fr", "naviguer à la voile au large de La Goulette", "Sortie en voilier dans le golfe de Tunis"),
    ("fr", "paddle sur la plage de la banlieue nord", "Stand-up paddle à la plage de La Marsa"),
    ("fr", "beignet sucré face à la mer", "Bambalouni et thé aux pignons à Sidi Bou Saïd"),
    ("fr", "étoiles et expériences scientifiques pour les enfants", "Cité des sciences de Tunis et séance au planétarium"),
    ("darija", "nheb nchouf l7ayawenet fel Belvédère", "Parc du Belvédère et zoo de Tunis en famille"),
    ("fr", "ville romaine classée au patrimoine mondial dans le nord-ouest", "Excursion d'une journée à Dougga"),
    # --- Sousse / Monastir
    ("fr", "forteresse et grande mosquée du Sahel", "Médina de Sousse : Grande Mosquée et Ribat"),
    ("fr", "galeries souterraines chrétiennes", "Catacombes de Sousse"),
    ("darija", "nheb nzour l'amphithéâtre mta3 El Jem", "Excursion à l'amphithéâtre d'El Jem"),
    ("fr", "plonger pour la première fois à Sousse", "Baptême de plongée à Port El Kantaoui"),
    ("fr", "attractions et toboggans à El Kantaoui", "Sortie au Hannibal Park de Port El Kantaoui"),
    ("fr", "apprendre à tenir un club de golf", "Initiation au golf à El Kantaoui"),
    ("fr", "tombeau du premier président", "Mausolée Habib Bourguiba"),
    ("fr", "îles sauvages et tortues marines", "Sortie en mer aux îles Kuriat"),
    ("darija", "zit zitoun mta3 sahel", "Dégustation d'huile d'olive du Sahel"),
    ("fr", "thalassothérapie à Monastir", "Demi-journée de thalassothérapie à Skanes"),
    ("fr", "manger comme au Sahel, cours pratique", "Cours de cuisine du Sahel tunisien"),
    # --- Hammamet / Nabeul
    ("fr", "remparts et vieille ville de Hammamet", "Médina et Kasbah de Hammamet"),
    ("fr", "villa d'artiste et théâtre en plein air", "Dar Sebastian et le Centre culturel international"),
    ("fr", "cité punique au bout du Cap Bon", "Excursion à Kerkouane et au fort de Kélibia"),
    ("darija", "nheb nemchi l Carthage Land m3a wledi", "Journée au parc Carthage Land"),
    ("fr", "safari et animaux sauvages près de Hammamet", "Friguia Park : animaux d'Afrique en famille"),
    ("fr", "piment et épices du Cap Bon", "Dégustation de harissa et produits du Cap Bon à Nabeul"),
    ("fr", "golf au milieu des orangers", "Green-fee au golf Citrus de Hammamet"),
    ("darija", "nheb nesbe7 fel b7ar w nchouf l7out", "Baptême de plongée à Hammamet"),
    # --- Tozeur
    ("fr", "architecture de briques ocre dans la vieille ville", "Quartier Ouled El Hadef et ses façades de briques"),
    ("fr", "musée sur la vie traditionnelle du Jérid", "Musée Dar Cherait"),
    ("fr", "ville sainte soufie près de Tozeur", "Nefta : la Corbeille et les zaouïas"),
    ("darija", "dawra bel karrossa fel ghaba", "Calèche dans la palmeraie de Tozeur"),
    ("fr", "cascades et canyons dans les montagnes", "Randonnée dans les gorges de Mides"),
    ("fr", "pain cuit sous le sable chaud", "Atelier khobz mella, le pain cuit dans le sable"),
    ("fr", "parc de dinosaures et préhistoire", "Chak Wak, le parc de la préhistoire et des civilisations"),
    ("darija", "nheb nchouf decor mta3 star wars f Tozeur", "Décors de Star Wars et rocher d'Ong Jemel"),
    ("fr", "lac salé immense dans le sud", "Lever du soleil sur le Chott el-Jérid"),
    ("fr", "fennecs et animaux du désert", "Zoo du Paradis, le zoo du désert de Tozeur"),
    ("en", "dune buggy ride in the Sahara", "Quad dans les dunes autour de Tozeur"),
    ("en", "date palm farm visit with tasting", "Dégustation de dattes Deglet Nour dans une palmeraie"),
]


def normaliser(texte: str) -> str:
    texte = unicodedata.normalize("NFKD", texte.lower())
    texte = "".join(c for c in texte if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", texte)).strip()


def trigrammes(texte: str) -> Counter:
    t = f"  {normaliser(texte)}  "
    return Counter(t[i:i + 3] for i in range(len(t) - 2))


def cosinus(a: Counter, b: Counter) -> float:
    num = sum(v * b[k] for k, v in a.items())
    den = math.sqrt(sum(v * v for v in a.values())) * math.sqrt(sum(v * v for v in b.values()))
    return num / den if den else 0.0


def main() -> None:
    titres = set(json.loads((DL / "activites.json").read_text(encoding="utf-8")))
    meta = json.loads((DL / "activites_meta.json").read_text(encoding="utf-8"))
    test = [json.loads(ligne) for ligne in TEST.read_text(encoding="utf-8").splitlines() if ligne]

    paires = []
    for m in meta:
        if m["titre_en"]:
            paires.append({"requete": m["titre_en"], "activite": m["cle"], "source": "titre_en", "langue": "en"})
        if m["titre_ar"]:
            paires.append({"requete": m["titre_ar"], "activite": m["cle"], "source": "titre_ar", "langue": "ar"})
    for langue, requete, titre in MANUELLES:
        if titre not in titres:
            raise SystemExit(f"Titre absent du catalogue : {titre}")
        paires.append({"requete": requete, "activite": titre, "source": "manuelle", "langue": langue})

    # Contrôle de fuite : aucune requête d'entraînement proche d'une requête du test.
    tests = [(q["id"], q["requete"], trigrammes(q["requete"]), normaliser(q["requete"])) for q in test]
    gardees, ecartees = [], []
    for p in paires:
        tg, norm = trigrammes(p["requete"]), normaliser(p["requete"])
        pire = max(((cosinus(tg, t3), qid, q) for qid, q, t3, _ in tests), key=lambda x: x[0])
        contient = any(qn and (qn in norm or norm in qn) for _, _, _, qn in tests)
        if pire[0] >= SEUIL_FUITE or contient:
            ecartees.append((p, pire))
        else:
            gardees.append(p)

    random.Random(42).shuffle(gardees)
    with SORTIE.open("w", encoding="utf-8", newline="\n") as f:
        for p in gardees:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")

    print(f"{len(gardees)} paires → {SORTIE}")
    print("Par source :", dict(Counter(p["source"] for p in gardees)))
    print("Par langue :", dict(Counter(p["langue"] for p in gardees)))
    print("Activités couvertes :", len({p["activite"] for p in gardees}), "/", len(titres))
    print(f"Écartées (fuite du test, seuil {SEUIL_FUITE}) : {len(ecartees)}")
    for p, (score, qid, q) in ecartees:
        print(f"  - « {p['requete']} » ~ {qid} « {q} » ({score:.2f})")


if __name__ == "__main__":
    main()
