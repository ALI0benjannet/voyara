"""Photos des 107 activités du catalogue de démonstration (idempotent).

Complète `seed_catalogue_demo.py`, dont les activités sont créées sans photo.
Les images (Wikimedia Commons, licences libres) sont **versionnées** dans
`static/activities/demo/` : un collègue les reçoit par `git pull` et n'a besoin
ni d'Internet ni du quota de Commons pour les relier à sa base.

Le nom de fichier dérive du titre français (`<slug>.jpg`) et non de l'`id` de
l'activité, qui diffère d'un poste à l'autre.

Usage (depuis services/catalog) :
    python scripts/seed_photos_demo.py                # relie les photos en base (sans réseau)
    python scripts/seed_photos_demo.py --verifier     # contrôle fichiers et crédits, sans base
    python scripts/seed_photos_demo.py --telecharger  # (re)télécharge depuis Commons — mainteneur

Le mode par défaut ne remplace jamais une photo existante (upload admin compris).
"""

import argparse
import json
import os
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from seed_catalogue_demo import ACTIVITES  # noqa: E402
from seed_photos import CREDITS_FILE, PHOTO_DIR, USER_AGENT, download, with_retry  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DEMO_DIR = PHOTO_DIR / "demo"
URL_PREFIXE = "/static/activities/demo/"

# Vignette demandée à Commons, puis plus petite si le fichier reste trop lourd
# (pas de Pillow dans le projet : on laisse Commons redimensionner).
LARGEURS = (1024, 800, 640)
TAILLE_MAX = 400 * 1024

# Seules ces licences autorisent la réutilisation avec simple attribution.
LICENCES_LIBRES = re.compile(r"^(CC0|Public domain|CC BY(-SA)? \d(\.\d)?)", re.IGNORECASE)

# Titre français -> fichier Wikimedia Commons, choisi à la main pour montrer le
# lieu réel. Les entrées marquées « illustration » montrent le même type
# d'activité ailleurs, faute d'image libre du lieu exact.
PHOTOS_DEMO: dict[str, str] = {
    # --- Djerba ---
    "Synagogue de la Ghriba et village d'Erriadh": "El Ghriba Synagogue, Djerba.jpg",
    "Parcours street art Djerbahood à Erriadh": "Djerba Er Riadh Street Art 05.JPG",
    "Atelier de poterie à Guellala": "Poterie de guellala djerba.JPG",
    "Musée du patrimoine de Guellala": "Guellala djerba.jpg",
    "Visite guidée de Houmt Souk : souks, fondouks et Borj El Kebir": "Borj El Ghazi Mustapha - Houmt El Souk, Djerba 01.jpg",
    "Musée du patrimoine traditionnel de Djerba": "Djerba Traditional Heritage Museum.jpg",
    "Circuit des mosquées ibadites : Fadhloun et El May": "Tunisie Jemaâ Fadhloun 1.jpg",
    "Musée Lalla Hadria et parc Djerba Explore": "Djerba Explore Nile crocodile 12.JPG",
    "Marché hebdomadaire de Midoun": "Midoun markt.JPG",
    "Sur les traces de Star Wars à Ajim": "Ajim-Mos Eisley Cantina-rapidtravelchai.jpg",
    "Site antique de Meninx et chaussée d'El Kantara": "Basilica, Meninx (Djerba, 2025).jpg",
    "Tour de Djerba à vélo : menzels et huileries souterraines": "Huilerie El Fsili--Midoun 47.jpg",
    "Randonnée douce à Mahboubine et El May": "Sidi Ben Arous Mahboubine Mosque 01.jpg",
    "Bateau pirate vers l'île aux Flamants (Ras Rmel)": "Djerba Ras Rmel 01.jpg",
    "Initiation au kitesurf sur la lagune de Bin El Ouedian": "Kitesurf Djerba.jpg",
    "Baptême de plongée au large de la zone touristique": "P6054238 (Archetto, Tavolara) (MP).jpg",  # illustration
    "Jet-ski à la plage de Sidi Mahrez": "Jet Skiing - Mahe - Seychelles - 2025.jpg",  # illustration
    "Parachute ascensionnel à la plage de Sidi Mahrez": "Vue Parachute à la zone touristique 1 Paillote Djerba.jpg",
    "Pêche traditionnelle à la charfia avec les pêcheurs d'Ajim": "Port Ajim Djerba 40.jpg",
    "Kayak de mer le long de la côte d'Aghir": "Plage aghir djerba 1.jpg",
    "Stand-up paddle à la plage de la Seguia": "Jerba Seguia 2.jpg",
    "Balade à dromadaire sur la plage de Sidi Mahrez": "Djerba-camel on the beach-sky walker.jpg",
    "Balade à cheval sur la plage d'Aghir": "Horses on the Beach (8596770349).jpg",  # illustration
    "Quad dans l'arrière-pays de Midoun": "Djerba architecture house.jpg",
    "Observation des oiseaux à la lagune de Bin El Ouedian": "Un groupe de flamants roses à Guellala - Djerba.jpg",
    "Excursion de 2 jours à Ksar Ghilane": "Ksar Ghilane, Tunisia (Unsplash).jpg",
    "Journée à Matmata et aux ksour de Tataouine": "Ksar Ouled Soltane 26.jpg",
    "Cours de cuisine djerbienne chez l'habitant": "Tunisian couscous with fish.JPG",
    "Dégustation d'huile d'olive et huilerie souterraine": "Underground Olive Oil Mill near Berdaoui Underground Mosque, Djerba.jpg",
    "Criée aux poissons et dégustation au port de Houmt Souk": "Port de Houmt Souk-01-phileole.jpg",
    "Atelier pain tabouna et brik dans un menzel": "Tabouna oven.JPG",
    "Dîner traditionnel djerbien dans un menzel": "Djerba-somewhere near Midoun-1-sky walker.jpg",
    # --- Tunis / Sidi Bou Saïd ---
    "Musée national du Bardo : mosaïques romaines": "BAR - Marine-life Roman mosaic in the Bardo National Museum, Tunis, 2018.jpg",
    "Médina de Tunis : Zitouna et Dar Ben Abdallah": "Dome and Minaret of Jamaa Zitouna.jpg",
    "Carthage punique : tophet de Salammbô et ports puniques": "Tophet de Carthage.jpg",
    "Amphithéâtre et villas romaines de Carthage": "Amphithéâtre romain de Carthage 24.jpg",
    "Colline de Byrsa et musée national de Carthage": "Carthage Byrsa 2.jpg",
    "Dar Ennejma Ezzahra, palais du baron d'Erlanger": "Le Palais Ennejma Ezzahra 14.jpg",
    "Atelier de calligraphie arabe dans la médina": "Arabic calligraphy on wood.jpg",  # illustration
    "Souk des Chaouachia : la chéchia tunisienne": "Chechia Maker in his shop.jpg",
    "Sortie en voilier dans le golfe de Tunis": "Golfe de Tunis et port de Sidi Bou Saïd.jpg",
    "Stand-up paddle à la plage de La Marsa": "La Marsa Plage.JPG",
    "Carthage à vélo, des thermes d'Antonin à Sidi Bou Saïd": "Antonine Baths at Carthage.jpg",
    "Randonnée au parc national de Boukornine": "Parc National de Boukornine.jpg",
    "Cours de cuisine tunisienne : couscous et brik": "Tunisian Briks.JPG",
    "Bambalouni et thé aux pignons à Sidi Bou Saïd": "Bambalouni - بمبلوني.jpg",
    "Visite gourmande du marché central de Tunis": "Tunis central market 1.jpg",
    "Excursion d'une journée à Dougga": "Dougga Capitol.jpg",
    # --- Sousse / Monastir ---
    "Médina de Sousse : Grande Mosquée et Ribat": "Great Mosque of Sousse 1.jpg",
    "Musée archéologique de Sousse": "Sousse mosaic Ganymede 03.JPG",
    "Catacombes de Sousse": "Catacombes chrétiennes, Sousse, 23 septembre 2013, (25).jpg",
    "Excursion à l'amphithéâtre d'El Jem": "Anfiteatro, El Jem, Túnez, 2016-09-04, DD 38-40 HDR.jpg",
    "Ribat de Monastir et médina": "Ribat de Monastir 111.jpg",
    "Mausolée Habib Bourguiba": "Habib Bourguiba Mausoleum.jpg",
    "Bateau pirate au départ de Port El Kantaoui": "Bateau pirate touristique à Sousse.jpg",
    "Baptême de plongée à Port El Kantaoui": "Discover Scuba Diving course at Sand Dollar Sports.jpg",  # illustration
    "Jet-ski à Port El Kantaoui": "Group of Jet Ski Riders in Key West, Florida.jpg",  # illustration
    "Sortie en mer aux îles Kuriat": "Îles Kuriats, Août 2021, 20210812 150700.jpg",
    "Balade à cheval à Chott Meriem": "Monastir beach 2.jpg",
    "De Skanes à la médina de Monastir à vélo": "Ribat of Monastir, April 3, 2025 (03).jpg",
    "Cours de cuisine du Sahel tunisien": "Tunisian couscous with Chicken.JPG",
    "Dégustation d'huile d'olive du Sahel": "Pot en terre cuite pour huile d'olive, Lamta Tunisie mai 2013.jpg",
    # --- Hammamet ---
    "Médina et Kasbah de Hammamet": "Kasbah de hammamet 1.jpg",
    "Dar Sebastian et le Centre culturel international": "Hammamet Centre Culturel R01.jpg",
    "Site archéologique de Pupput": "Site de Pupput, 19 septembre 2013, 01.jpg",
    "Marché du vendredi et poterie de Nabeul": "Potteries in Nabeul.jpg",
    "Excursion à Kerkouane et au fort de Kélibia": "Kerkouane, Tunesien Januar 2015 03.JPG",
    "Bateau pirate à Yasmine Hammamet": "Bateau pirate, Yasmina Tunisie, juin 2013.jpg",
    "Parachute ascensionnel à Yasmine Hammamet": "Parachute ascensionnel مظلة.jpg",
    "Baptême de plongée à Hammamet": "Ship wreck Carnatic 2017-04-22 Egypt-7947.jpg",  # illustration
    "Journée au parc Carthage Land": "AICCSA 2017 - Gates of Carthage Land.jpg",
    "Balade à cheval entre plage et orangeraies": "La marsa chevales.JPG",  # illustration
    "Cours de cuisine du Cap Bon : couscous au poisson et harissa": "Tunisian couscous with fish and vegetables.JPG",
    "Dégustation de harissa et produits du Cap Bon à Nabeul": "Harissa in pots.jpg",
    # --- Tozeur ---
    "Quartier Ouled El Hadef et ses façades de briques": "Ouled El Hadef Brick facade.jpg",
    "Musée Dar Cherait": "Musée Dar Cheraït 2019 - 72.jpg",
    "Nefta : la Corbeille et les zaouïas": "Corbeille de Nefta, Tunisie, DSC 2125.jpg",
    "Calèche dans la palmeraie de Tozeur": "Calèche Tozeur matin.jpg",
    "Oasis de montagne en 4x4 : Chebika, Tamerza et Mides": "Chebika, Tozeur, Tunisia.jpg",
    "Lever du soleil sur le Chott el-Jérid": "Chott el jerid.jpg",
    "Décors de Star Wars et rocher d'Ong Jemel": "Mos Espa, site du tournage de Starwars, Tunisie, 20220324 123053.jpg",
    "Balade à dromadaire au coucher du soleil à Tozeur": "The desert ship Tozeur Tunisia.jpg",
    "Quad dans les dunes autour de Tozeur": "Quad Bikes in Swakopmund dessert in Namibia.jpg",  # illustration
    "Randonnée dans les gorges de Mides": "Mides Canyon.jpg",
    "Dégustation de dattes Deglet Nour dans une palmeraie": "Une grappe de datte avant la récolte , palmeraie de tozeur - tunisie.jpg",
    "Atelier khobz mella, le pain cuit dans le sable": "Flatbread baked in sand.jpg",
    # --- Ajout du 19/10/2026 : Bien-être, Famille & loisirs, Golf (vérifiées à l'œil) ---
    "Demi-journée thalasso à Djerba : parcours marin, hammam et enveloppement": "Indoor swimming pool at Hotel Mercure Krynica Zdroj Resort & Spa, Poland, 2023, 02.jpg",  # illustration
    "Hammam traditionnel et gommage au kassa à Houmt Souk": "Hammam Tunisia.jpg",
    "Massage en duo à l'huile d'argan à Aghir": "Massage-hand-1.jpg",  # illustration
    "Hammam et rituel de soins dans la médina de Tunis": "Dome of Hammam el Sultan.jpg",  # illustration
    "Yoga au lever du soleil face au golfe de Tunis": "Morning Yoga (134921595).jpeg",  # illustration
    "Thalasso à Port El Kantaoui : bassin d'eau de mer et soins": "Les Thermes Marins de Cannes - Thalassothérapie - panoramio.jpg",  # illustration
    "Demi-journée de thalassothérapie à Skanes": "Dinard-Thalasso-byMmeRundvald.jpg",  # illustration
    "Thalasso et hammam à Yasmine Hammamet": "Centre de Thalasotherapie Ainturk - Oran.jpg",  # illustration
    "Soins aux dattes et hammam dans un spa de l'oasis": "Inside Tozeur Oasis 03.jpg",
    "Sortie au Hannibal Park de Port El Kantaoui": "Luna Park Port El Kantaoui - panoramio.jpg",
    "Parc du Belvédère et zoo de Tunis en famille": "Zoo Belvédère Tunis.jpg",
    "Cité des sciences de Tunis et séance au planétarium": "Cité des sciences Tunis.jpg",
    "Friguia Park : animaux d'Afrique en famille": "Watusi cattle in Friguia park, Tunisia, december 2018, DSC 0664.jpg",
    "Chak Wak, le parc de la préhistoire et des civilisations": "Modèle de la Grande Mosquée de Kairouan au parc Chak Wak, Tozeur.jpg",
    "Eden Palm : le palmier dattier raconté en famille": "Tozeur Oasis at sunset.jpg",  # illustration
    "Zoo du Paradis, le zoo du désert de Tozeur": "Zoo du paradis, tozeur, Tunisie, mars 2022 DSC 2153.jpg",
    "Parcours de golf au Djerba Golf Club": "2008-11-25-Monastir-Flamingo-53.JPG",  # illustration
    "Green-fee au golf Citrus de Hammamet": "2007-11-21-Hammamet-Golf-Citrus-1.JPG",
    "Parcours au Flamingo Golf de Monastir": "2008-11-25-Monastir-Flamingo-74.JPG",
    "Green-fee au golf d'El Kantaoui": "Sousse - Kantaoui Golf Course.jpg",
    "Initiation au golf à El Kantaoui": "2008-11-25-El-Kantaoui-93.JPG",
}


def slug(titre: str) -> str:
    """« Musée Dar Cherait » -> « musee-dar-cherait » : nom de fichier stable et ASCII."""
    ascii_ = unicodedata.normalize("NFKD", titre).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_.lower()).strip("-")


def chemin_local(titre: str) -> Path:
    return DEMO_DIR / f"{slug(titre)}.jpg"


def lire_credits() -> list[dict[str, str]]:
    if CREDITS_FILE.exists():
        return json.loads(CREDITS_FILE.read_text(encoding="utf-8"))
    return []


def verifier() -> list[str]:
    """Contrôles sans base : couverture, fichiers présents et légers, crédits."""
    erreurs = []
    titres = [a["fr"][0] for a in ACTIVITES]
    for titre in titres:
        if titre not in PHOTOS_DEMO:
            erreurs.append(f"pas de photo prévue : {titre}")
    for titre in PHOTOS_DEMO:
        if titre not in titres:
            erreurs.append(f"titre inconnu du seed : {titre}")
    slugs = [slug(t) for t in PHOTOS_DEMO]
    if len(set(slugs)) != len(slugs):
        erreurs.append("deux titres donnent le même nom de fichier")

    credites = {c["fichier"] for c in lire_credits()}
    for titre, fichier in PHOTOS_DEMO.items():
        chemin = chemin_local(titre)
        if not chemin.exists():
            erreurs.append(f"fichier absent : {chemin.name}")
        elif chemin.stat().st_size > TAILLE_MAX:
            erreurs.append(f"fichier trop lourd ({chemin.stat().st_size // 1024} Ko) : {chemin.name}")
        if fichier not in credites:
            erreurs.append(f"crédit manquant : {fichier}")
    return erreurs


def infos_commons(fichier: str, largeur: int) -> dict:
    """URL de vignette, auteur, licence et page de description d'un fichier Commons."""
    api = (
        "https://commons.wikimedia.org/w/api.php?action=query&format=json"
        f"&titles={urllib.parse.quote('File:' + fichier)}"
        f"&prop=imageinfo&iiprop=url|extmetadata&iiurlwidth={largeur}"
    )
    requete = urllib.request.Request(api, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(requete, timeout=30) as reponse:
        data = json.load(reponse)
    for page in (data.get("query", {}).get("pages", {}) or {}).values():
        info = (page.get("imageinfo") or [{}])[0]
        meta = info.get("extmetadata", {})
        auteur = re.sub(r"<[^>]+>", "", meta.get("Artist", {}).get("value", "")).strip()
        return {
            "url": info.get("thumburl") or info.get("url"),
            "auteur": auteur or "Auteur inconnu",
            "licence": meta.get("LicenseShortName", {}).get("value", ""),
            "source": info.get("descriptionurl", ""),
        }
    return {"url": None}


def telecharger() -> None:
    """Mainteneur : récupère les vignettes depuis Commons et complète les crédits."""
    DEMO_DIR.mkdir(parents=True, exist_ok=True)
    nouveaux, refuses, echecs, deja = [], 0, 0, 0
    for titre, fichier in PHOTOS_DEMO.items():
        chemin = chemin_local(titre)
        if chemin.exists():
            deja += 1
            continue
        try:
            for largeur in LARGEURS:
                info = with_retry(lambda: infos_commons(fichier, largeur))
                if not info["url"]:
                    raise RuntimeError("fichier introuvable sur Commons")
                if not LICENCES_LIBRES.match(info["licence"]):
                    raise PermissionError(f"licence refusée : {info['licence'] or 'inconnue'}")
                contenu = with_retry(lambda: download(info["url"]))
                time.sleep(1)  # reste sous le quota de Commons
                if len(contenu) <= TAILLE_MAX:
                    break
            else:
                raise RuntimeError(f"vignette trop lourde même en {LARGEURS[-1]} px")
        except PermissionError as exc:
            print(f"  ! {titre} : {exc}")
            refuses += 1
            continue
        except Exception as exc:  # réseau, fichier renommé, quota…
            print(f"  ! {titre} : {exc}")
            echecs += 1
            continue

        chemin.write_bytes(contenu)
        nouveaux.append({
            "activite": titre,
            "fichier": fichier,
            "auteur": info["auteur"],
            "licence": info["licence"],
            "source": info["source"],
        })
        print(f"  + {chemin.name} <- {fichier} ({info['licence']}, {len(contenu) // 1024} Ko)")

    if nouveaux:
        credits = lire_credits()
        connus = {c["fichier"] for c in credits}
        credits.extend(c for c in nouveaux if c["fichier"] not in connus)
        CREDITS_FILE.write_text(json.dumps(credits, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Crédits écrits dans {CREDITS_FILE}")
    print(
        f"Terminé : {len(nouveaux)} téléchargée(s), {deja} déjà présente(s), "
        f"{refuses} licence(s) refusée(s), {echecs} échec(s)."
    )


def relier() -> None:
    """Pour tout le monde : relie les fichiers versionnés aux activités en base."""
    from app.database import SessionLocal
    from app.models import Activity

    db = SessionLocal()
    reliees = deja = absentes = 0
    try:
        for titre in PHOTOS_DEMO:
            activite = db.query(Activity).filter(Activity.titre == titre).first()
            if activite is None:
                absentes += 1
                continue
            if activite.photos:
                deja += 1  # photo existante (seed ou upload admin) : jamais écrasée
                continue
            activite.photos = URL_PREFIXE + chemin_local(titre).name
            reliees += 1
        db.commit()
    finally:
        db.close()
    print(f"Terminé : {reliees} photo(s) reliée(s), {deja} activité(s) déjà illustrée(s), {absentes} absente(s) de la base.")
    if absentes:
        print("Activités absentes : lancer d'abord scripts/seed_catalogue_demo.py.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--verifier", action="store_true", help="contrôle fichiers et crédits, sans base")
    mode.add_argument("--telecharger", action="store_true", help="télécharge les images depuis Commons")
    args = parser.parse_args()

    if args.telecharger:
        telecharger()
        return

    erreurs = verifier()
    if erreurs:
        print("Photos invalides :")
        for erreur in erreurs:
            print(f"  - {erreur}")
        sys.exit(1)
    print(f"Photos valides : {len(PHOTOS_DEMO)} fichiers dans {DEMO_DIR}.")
    if not args.verifier:
        relier()


if __name__ == "__main__":
    main()
