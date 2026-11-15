"""Jeu de test de la validation DL « recherche » (guide d'Ons, étape B).

Écrit services/ai/data/eval/recherche_requetes.jsonl : 70 requêtes
(35 fr · 14 en · 11 ar · 10 darija), formes précises, vagues et avec contrainte,
sur toutes les villes du catalogue. `pertinentes` = titres français des activités
(clé de services/ai/data/dl/activites.json, voir dl_recherche_catalogue.py).

Rédigé à la main d'après le catalogue ; à relire par Boutheina avant le
fine-tuning (le script vérifie seulement que chaque titre existe).

Usage (depuis la racine) : python services/ai/scripts/dl_recherche_jeu_test.py
"""

import json
import sys
from collections import Counter
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RACINE = Path(__file__).resolve().parents[3]
CATALOGUE = RACINE / "services" / "ai" / "data" / "dl" / "activites.json"
SORTIE = RACINE / "services" / "ai" / "data" / "eval" / "recherche_requetes.jsonl"

# Raccourcis → titres exacts du catalogue (évite les fautes de frappe).
T = {
    "pirate_djerba": "Bateau pirate vers l'île aux Flamants (Ras Rmel)",
    "kayak_aghir": "Kayak de mer le long de la côte d'Aghir",
    "sup_seguia": "Stand-up paddle à la plage de la Seguia",
    "drom_plage": "Balade à dromadaire sur la plage de Sidi Mahrez",
    "plongee_tab": "Plongée aux récifs de Tabarka",
    "carthageland": "Journée au parc Carthage Land",
    "friguia": "Friguia Park : animaux d'Afrique en famille",
    "pirate_ham": "Bateau pirate à Yasmine Hammamet",
    "amphi_carth": "Amphithéâtre et villas romaines de Carthage",
    "dougga": "Excursion d'une journée à Dougga",
    "velo_carth": "Carthage à vélo, des thermes d'Antonin à Sidi Bou Saïd",
    "bardo": "Musée national du Bardo : mosaïques romaines",
    "douz": "Bivouac dans le désert de Douz",
    "ghilane": "Excursion de 2 jours à Ksar Ghilane",
    "cuis_tunis": "Cours de cuisine tunisienne : couscous et brik",
    "cuis_capbon": "Cours de cuisine du Cap Bon : couscous au poisson et harissa",
    "cuis_djerba": "Cours de cuisine djerbienne chez l'habitant",
    "cuis_sahel": "Cours de cuisine du Sahel tunisien",
    "massage_duo": "Massage en duo à l'huile d'argan à Aghir",
    "golf_mon": "Parcours au Flamingo Golf de Monastir",
    "chott": "Lever du soleil sur le Chott el-Jérid",
    "montgolf": "Montgolfière sur les oasis de Tozeur",
    "sw_tozeur": "Décors de Star Wars et rocher d'Ong Jemel",
    "sw_ajim": "Sur les traces de Star Wars à Ajim",
    "jetski_kant": "Jet-ski à Port El Kantaoui",
    "plongee_kant": "Baptême de plongée à Port El Kantaoui",
    "musee_sousse": "Musée archéologique de Sousse",
    "cheval_aghir": "Balade à cheval sur la plage d'Aghir",
    "cheval_meriem": "Balade à cheval à Chott Meriem",
    "cheval_ham": "Balade à cheval entre plage et orangeraies",
    "thalasso_kant": "Thalasso à Port El Kantaoui : bassin d'eau de mer et soins",
    "poterie_guel": "Atelier de poterie à Guellala",
    "nabeul": "Marché du vendredi et poterie de Nabeul",
    "bourguiba": "Mausolée Habib Bourguiba",
    "ribat_mon": "Ribat de Monastir et médina",
    "4x4": "Oasis de montagne en 4x4 : Chebika, Tamerza et Mides",
    "oiseaux": "Observation des oiseaux à la lagune de Bin El Ouedian",
    "foodtour": "Food tour de la médina de Tunis",
    "marche_central": "Visite gourmande du marché central de Tunis",
    "bambalouni": "Bambalouni et thé aux pignons à Sidi Bou Saïd",
    "quad_tozeur": "Quad dans les dunes autour de Tozeur",
    "quad_midoun": "Quad dans l'arrière-pays de Midoun",
    "kuriat": "Sortie en mer aux îles Kuriat",
    "hammam_tunis": "Hammam et rituel de soins dans la médina de Tunis",
    "hammam_djerba": "Hammam traditionnel et gommage au kassa à Houmt Souk",
    "thalasso_ham": "Thalasso et hammam à Yasmine Hammamet",
    "spa_dattes": "Soins aux dattes et hammam dans un spa de l'oasis",
    "zoo_tunis": "Parc du Belvédère et zoo de Tunis en famille",
    "zoo_tozeur": "Zoo du Paradis, le zoo du désert de Tozeur",
    "eljem": "Excursion à l'amphithéâtre d'El Jem",
    "ibadites": "Circuit des mosquées ibadites : Fadhloun et El May",
    "velo_djerba": "Tour de Djerba à vélo : menzels et huileries souterraines",
    "velo_mon": "De Skanes à la médina de Monastir à vélo",
    "midoun": "Marché hebdomadaire de Midoun",
    "boukornine": "Randonnée au parc national de Boukornine",
    "dattes": "Dégustation de dattes Deglet Nour dans une palmeraie",
    "edenpalm": "Eden Palm : le palmier dattier raconté en famille",
    "parachute_ham": "Parachute ascensionnel à Yasmine Hammamet",
    "plongee_ham": "Baptême de plongée à Hammamet",
    "punique": "Carthage punique : tophet de Salammbô et ports puniques",
    "byrsa": "Colline de Byrsa et musée national de Carthage",
    "croisiere": "Croisière au couchant à Djerba",
    "drom_tozeur": "Balade à dromadaire au coucher du soleil à Tozeur",
    "hannibal": "Sortie au Hannibal Park de Port El Kantaoui",
    "streetart": "Parcours street art Djerbahood à Erriadh",
    "huile_djerba": "Dégustation d'huile d'olive et huilerie souterraine",
    "huile_sahel": "Dégustation d'huile d'olive du Sahel",
    "plongee_djerba": "Baptême de plongée au large de la zone touristique",
    "pirate_kant": "Bateau pirate au départ de Port El Kantaoui",
    "kite": "Initiation au kitesurf sur la lagune de Bin El Ouedian",
    "pupput": "Site archéologique de Pupput",
    "thalasso_djerba": "Demi-journée thalasso à Djerba : parcours marin, hammam et enveloppement",
    "thalasso_skanes": "Demi-journée de thalassothérapie à Skanes",
    "medina_ham": "Médina et Kasbah de Hammamet",
    "voilier": "Sortie en voilier dans le golfe de Tunis",
    "cite_sciences": "Cité des sciences de Tunis et séance au planétarium",
    "charfia": "Pêche traditionnelle à la charfia avec les pêcheurs d'Ajim",
    "yoga": "Yoga au lever du soleil face au golfe de Tunis",
    "matmata": "Journée à Matmata et aux ksour de Tataouine",
    "medina_sousse": "Médina de Sousse : Grande Mosquée et Ribat",
    "golf_ham": "Green-fee au golf Citrus de Hammamet",
    "caleche": "Calèche dans la palmeraie de Tozeur",
    "sbs": "Sidi Bou Saïd & Carthage",
    "houmtsouk": "Visite guidée de Houmt Souk : souks, fondouks et Borj El Kebir",
}

REQUETES = [
    ("fr", "plage calme en famille à Djerba", ["pirate_djerba", "kayak_aghir", "sup_seguia", "drom_plage"]),
    ("fr", "plongée à Tabarka", ["plongee_tab"]),
    ("fr", "un truc sympa pour les enfants à Hammamet", ["carthageland", "friguia", "pirate_ham"]),
    ("fr", "visiter des ruines romaines près de Tunis", ["amphi_carth", "dougga", "velo_carth", "bardo"]),
    ("fr", "dormir sous les étoiles dans le Sahara", ["douz", "ghilane"]),
    ("fr", "apprendre à préparer un couscous", ["cuis_tunis", "cuis_capbon", "cuis_djerba", "cuis_sahel"]),
    ("fr", "se faire masser à deux en amoureux", ["massage_duo"]),
    ("fr", "jouer au golf à Monastir", ["golf_mon"]),
    ("fr", "activité très tôt le matin à Tozeur", ["chott", "montgolf"]),
    ("fr", "voir les lieux de tournage de Star Wars", ["sw_tozeur", "sw_ajim"]),
    ("fr", "sensations fortes sur l'eau à Sousse", ["jetski_kant", "plongee_kant"]),
    ("fr", "musée avec de belles mosaïques", ["bardo", "musee_sousse"]),
    ("fr", "monter à cheval au bord de la mer", ["cheval_aghir", "cheval_meriem", "cheval_ham"]),
    ("fr", "journée détente spa et soins vers Sousse", ["thalasso_kant"]),
    ("fr", "découvrir l'artisanat de la poterie", ["poterie_guel", "nabeul"]),
    ("fr", "visite culturelle à Monastir sans trop marcher", ["bourguiba", "ribat_mon"]),
    ("fr", "excursion en 4x4 dans les oasis de montagne", ["4x4"]),
    ("fr", "observer des flamants roses", ["pirate_djerba", "oiseaux"]),
    ("fr", "goûter aux spécialités locales à Tunis", ["foodtour", "marche_central", "bambalouni"]),
    ("fr", "faire du quad", ["quad_tozeur", "quad_midoun"]),
    ("fr", "sortie en bateau vers une île près de Monastir", ["kuriat"]),
    ("fr", "hammam traditionnel", ["hammam_tunis", "hammam_djerba", "thalasso_ham", "spa_dattes"]),
    ("fr", "zoo pour les petits", ["zoo_tunis", "zoo_tozeur", "friguia"]),
    ("fr", "voir le colisée d'El Jem", ["eljem"]),
    ("fr", "mosquées anciennes à Djerba", ["ibadites"]),
    ("fr", "balade à vélo avec visite", ["velo_carth", "velo_djerba", "velo_mon"]),
    ("fr", "marché local pour faire des achats", ["midoun", "nabeul"]),
    ("fr", "randonnée en pleine nature près de Tunis", ["boukornine"]),
    ("fr", "tout savoir sur les dattes", ["dattes", "edenpalm", "spa_dattes"]),
    ("fr", "activité nautique pour ados à Hammamet", ["parachute_ham", "plongee_ham"]),
    ("fr", "l'histoire punique de Carthage", ["punique", "byrsa"]),
    ("fr", "moment romantique au coucher du soleil", ["croisiere", "drom_tozeur"]),
    ("fr", "parc d'attractions avec manèges", ["carthageland", "hannibal"]),
    ("fr", "voir des fresques murales", ["streetart"]),
    ("fr", "dégustation d'huile d'olive", ["huile_djerba", "huile_sahel"]),
    ("en", "camel ride in the desert at sunset", ["drom_tozeur"]),
    ("en", "scuba diving for beginners", ["plongee_djerba", "plongee_kant", "plongee_ham"]),
    ("en", "family day out with kids near Sousse", ["hannibal", "pirate_kant"]),
    ("en", "learn kitesurfing", ["kite"]),
    ("en", "Roman history tour", ["amphi_carth", "eljem", "dougga", "pupput"]),
    ("en", "hot air balloon flight", ["montgolf"]),
    ("en", "street food tasting in the old town", ["foodtour"]),
    ("en", "relaxing thalasso day", ["thalasso_djerba", "thalasso_kant", "thalasso_skanes", "thalasso_ham"]),
    ("en", "walk through the old medina of Hammamet", ["medina_ham"]),
    ("en", "sailing trip", ["voilier"]),
    ("en", "indoor activity for children on a rainy day in Tunis", ["cite_sciences"]),
    ("en", "traditional fishing with local fishermen", ["charfia"]),
    ("en", "morning yoga session", ["yoga"]),
    ("en", "Berber troglodyte houses", ["matmata"]),
    ("ar", "غوص في طبرقة", ["plongee_tab"]),
    ("ar", "رحلة إلى الصحراء والمبيت في خيمة", ["douz", "ghilane"]),
    ("ar", "أنشطة للأطفال في تونس العاصمة", ["zoo_tunis", "cite_sciences"]),
    ("ar", "حمّام تقليدي في جربة", ["hammam_djerba"]),
    ("ar", "زيارة متحف باردو", ["bardo"]),
    ("ar", "جولة بالدراجة الهوائية", ["velo_carth", "velo_djerba", "velo_mon"]),
    ("ar", "تعلّم الطبخ التونسي", ["cuis_tunis", "cuis_capbon", "cuis_djerba", "cuis_sahel"]),
    ("ar", "ركوب الخيل على الشاطئ", ["cheval_aghir", "cheval_meriem", "cheval_ham"]),
    ("ar", "المدينة العتيقة في سوسة والرباط", ["medina_sousse"]),
    ("ar", "جولة في الواحات بسيارة رباعية الدفع", ["4x4"]),
    ("ar", "لعب الغولف في الحمامات", ["golf_ham"]),
    ("darija", "nheb nchouf sahra f Tozeur", ["quad_tozeur", "drom_tozeur", "caleche", "montgolf", "chott"]),
    ("darija", "n7eb nghtes f jerba", ["plongee_djerba"]),
    ("darija", "chniya na3mlou m3a sghar f Hammamet", ["carthageland", "friguia", "pirate_ham"]),
    ("darija", "nheb nekel makla tounsia f lmedina", ["foodtour"]),
    ("darija", "jet ski f sousse", ["jetski_kant"]),
    ("darija", "hammam w massage m3a mrti", ["massage_duo", "hammam_tunis", "hammam_djerba"]),
    ("darija", "nhebou na3mlou dawra bel babour",
     ["pirate_djerba", "croisiere", "pirate_kant", "pirate_ham", "kuriat"]),
    ("darija", "nzour Carthage w Sidi Bou Said", ["sbs", "velo_carth", "amphi_carth"]),
    ("darija", "dawra fel souk f Houmt Souk", ["houmtsouk"]),
    ("darija", "nheb nerkeb 3la jmal fel sahra", ["drom_tozeur", "douz"]),
]


def main() -> None:
    titres = set(json.loads(CATALOGUE.read_text(encoding="utf-8")))
    inconnus = [t for t in T.values() if t not in titres]
    if inconnus:
        raise SystemExit(f"Titres absents du catalogue : {inconnus}")
    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    with SORTIE.open("w", encoding="utf-8", newline="\n") as f:
        for i, (langue, requete, cles) in enumerate(REQUETES, 1):
            if len(cles) != len(set(cles)) or not 1 <= len(cles) <= 5:
                raise SystemExit(f"R-{i:03d} : 1 à 5 activités pertinentes distinctes attendues")
            ligne = {"id": f"R-{i:03d}", "langue": langue, "requete": requete,
                     "pertinentes": [T[c] for c in cles]}
            f.write(json.dumps(ligne, ensure_ascii=False) + "\n")
    print(f"{len(REQUETES)} requêtes → {SORTIE}")
    print("Langues :", dict(Counter(r[0] for r in REQUETES)))
    print("Pertinentes par requête (moyenne) :", round(sum(len(r[2]) for r in REQUETES) / len(REQUETES), 2))
    print("Activités pertinentes au moins une fois :", len({c for r in REQUETES for c in r[2]}), "/", len(titres))


if __name__ == "__main__":
    main()
