"""Offres de voyage de démonstration : séjours, vols, voitures, transferts (idempotent).

Les quatre tables existent depuis la phase « offres de voyage » mais étaient vides.
Ce script les remplit sur les 5 zones du catalogue de démonstration (Djerba,
Tunis / Sidi Bou Saïd, Sousse / Monastir, Hammamet, Tozeur), pour que le futur
moteur IA puisse chiffrer un séjour complet (hébergement + activités + déplacements).

Règles du jeu de données (décisions du 19/10/2026) :
- séjours et agences de location : **noms fictifs**, posés sur de vraies zones
  (coordonnées OpenStreetMap). Attribuer des prix ou des équipements inventés à un
  vrai hôtel serait une fausse information sur une entreprise réelle ;
- vols : **vraies compagnies, vrais aéroports, lignes plausibles** ; numéros,
  horaires, prix et remplissage sont inventés (données de démonstration) ;
- chaque zone propose des séjours pour les trois profils de voyageurs :
  solo, couple, famille (contrôlé par --verifier) ;
- prix en DT, ordres de grandeur relevés le 19/10/2026 (sources dans
  docs/ia/rapports/etape-01-offres-voyage.md), pas des tarifs officiels ;
- chaque ligne est validée par les schémas d'entrée de l'API admin
  (`StayIn`, `FlightIn`, `CarRentalIn`, `TransferIn`) : tout ce que le script écrit
  reste modifiable depuis l'espace admin.

Idempotence (clé naturelle → jamais de doublon, jamais d'écrasement) :
- séjour : `nom` (seules les traductions et la photo vides sont complétées) ;
- vol : (`numero_vol`, `depart_le`, `classe`) ; les vols couvrent les 28 jours
  qui suivent l'exécution, relancer plus tard prolonge l'horizon ;
- voiture : (`agence`, `marque`, `modele`) ; transfert : (`depart`, `arrivee`, `type_vehicule`).

Photos (Wikimedia Commons, licences libres, versionnées dans `static/offres/demo/`,
crédits sur la page /credits du site) : une par séjour, une par modèle de voiture.

Usage (depuis services/catalog) :
    python scripts/seed_offres_voyage_demo.py                # écrit en base + relie les photos
    python scripts/seed_offres_voyage_demo.py --verifier     # contrôle les données, sans base
    python scripts/seed_offres_voyage_demo.py --telecharger  # (re)télécharge les photos — mainteneur
"""

import argparse
import json
import os
import sys
import time
import zlib
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from seed_catalogue_demo import CENTRES, HORIZON_JOURS, RAYON_MAX_KM, distance_km  # noqa: E402
from seed_photos import CREDITS_FILE, download, with_retry  # noqa: E402
from seed_photos_demo import LARGEURS, LICENCES_LIBRES, TAILLE_MAX, infos_commons, lire_credits, slug  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OFFRES_DIR = Path(__file__).resolve().parents[1] / "static" / "offres" / "demo"
URL_PREFIXE = "/static/offres/demo/"
PROFILS = ("solo", "couple", "famille")


# ----------------------------------------------------------------------
# Séjours (27) — noms fictifs, vraies zones
# ----------------------------------------------------------------------


def sejour(zone, nom, type_, etoiles, localisation, lat, lon, prix_nuit, capacite, equipements,
           profils, photo, fr, en, ar):
    """`fr` = description ; `en`, `ar` = (nom, description) ; `photo` = fichier Commons."""
    return {
        "zone": zone, "nom": nom, "type": type_, "etoiles": etoiles,
        "localisation": localisation, "latitude": lat, "longitude": lon,
        "prix_nuit": prix_nuit, "capacite": capacite, "equipements": equipements,
        "profils": profils, "photo": photo,
        "description": fr, "nom_en": en[0], "description_en": en[1],
        "nom_ar": ar[0], "description_ar": ar[1],
    }


SEJOURS = [
    # --- Djerba (6) ---
    sejour("Djerba", "Hôtel Les Dunes de Midoun", "hotel", 4,
           "Djerba, zone touristique de Midoun (Sidi Mahrez)", 33.8452, 10.9958, 320, 4,
           "piscine,plage privée,club enfants,chambres familiales,demi-pension,wifi", ("famille",),
           "Djerba-Blick vom Pool-avatar1.jpg",
           "Grand hôtel de plage à Sidi Mahrez : piscine, club enfants de 4 à 12 ans et chambres "
           "familiales jusqu'à 4 personnes. Formule demi-pension.",
           ("Les Dunes de Midoun Hotel",
            "Large beach hotel in Sidi Mahrez: pool, kids' club for ages 4 to 12 and family rooms "
            "for up to 4 people. Half board."),
           ("فندق كثبان ميدون",
            "فندق شاطئي كبير في سيدي محرز: مسبح ونادٍ للأطفال من 4 إلى 12 سنة وغرف عائلية "
            "حتى 4 أشخاص. نصف إقامة.")),
    sejour("Djerba", "Hôtel Lagune d'Aghir", "hotel", 5,
           "Djerba, zone touristique d'Aghir", 33.7640, 11.0200, 520, 2,
           "spa,thalasso,piscine,plage privée,adultes uniquement,wifi", ("couple",),
           "Plage Hassi Jerbi.jpg",
           "Hôtel réservé aux adultes face à la mer turquoise d'Aghir, avec centre de thalasso. "
           "Pensé pour les couples en quête de calme.",
           ("Lagune d'Aghir Hotel",
            "Adults-only hotel facing the turquoise sea of Aghir, with a thalasso centre. "
            "Designed for couples seeking peace and quiet."),
           ("فندق بحيرة أغير",
            "فندق مخصّص للكبار مطلّ على بحر أغير الفيروزي، مع مركز للعلاج بمياه البحر. "
            "مصمَّم للأزواج الباحثين عن الهدوء.")),
    sejour("Djerba", "Houch Yasmina", "maison_hotes", None,
           "Djerba, Erriadh", 33.8165, 10.8570, 180, 2,
           "patio,terrasse,petit-déjeuner,vélos,wifi", ("couple", "solo"),
           "Houch à Djerba.jpg",
           "Houch djerbien restauré autour de son patio blanchi à la chaux, à deux pas des fresques "
           "d'Erriadh. Petit-déjeuner maison et vélos prêtés.",
           ("Houch Yasmina",
            "Restored Djerban houch around its whitewashed patio, a short walk from the Erriadh "
            "murals. Home-made breakfast and bikes on loan."),
           ("حوش ياسمينة",
            "حوش جربي مرمَّم حول فنائه المطليّ بالجير، على بعد خطوات من جداريات الرياض. "
            "فطور منزلي ودرّاجات على ذمّة الضيوف.")),
    sejour("Djerba", "Dar El Menzel", "maison_hotes", None,
           "Djerba, menzel près de Midoun", 33.8180, 10.9900, 240, 5,
           "patio,piscine,jardin,cuisine équipée,petit-déjeuner", ("famille",),
           "Cour intérieure houch djerbien.jpg",
           "Menzel traditionnel loué en entier, avec piscine et jardin d'oliviers : de la place pour "
           "une famille jusqu'à 5 personnes, à 10 minutes des plages.",
           ("Dar El Menzel",
            "Traditional menzel rented as a whole, with a pool and olive garden: room for a family "
            "of up to 5, 10 minutes from the beaches."),
           ("دار المنزل",
            "منزل تقليدي يُكرى كاملًا، مع مسبح وحديقة زيتون: يتّسع لعائلة حتى 5 أشخاص، على بعد "
            "10 دقائق من الشواطئ.")),
    sejour("Djerba", "Studio du Souk", "appartement", None,
           "Djerba, Houmt Souk", 33.8755, 10.8580, 95, 2,
           "climatisation,kitchenette,wifi", ("solo",),
           "Houmt Souk-street arcades-Al@in76.jpg",
           "Petit studio au cœur de Houmt Souk, entre souks et port : la base économique idéale "
           "pour un voyageur en solo.",
           ("Souk Studio",
            "Small studio in the heart of Houmt Souk, between the souks and the harbour: the ideal "
            "budget base for a solo traveller."),
           ("استوديو السوق",
            "استوديو صغير في قلب حومة السوق، بين الأسواق والميناء: قاعدة اقتصادية مثالية "
            "للمسافر بمفرده.")),
    sejour("Djerba", "Dar Fresques d'Erriadh", "maison_hotes", None,
           "Djerba, Erriadh", 33.8130, 10.8600, 150, 2,
           "terrasse,petit-déjeuner,wifi", ("solo", "couple"),
           "Djerba hood.jpg",
           "Maison d'hôtes dans les ruelles peintes d'Erriadh, avec terrasse sur les toits. "
           "Accueil chaleureux, chambres simples et lumineuses.",
           ("Dar Fresques d'Erriadh",
            "Guesthouse in the painted alleys of Erriadh, with a rooftop terrace. Warm welcome, "
            "simple and bright rooms."),
           ("دار جداريات الرياض",
            "دار ضيافة في أزقّة الرياض المرسومة، مع سطح للجلوس. استقبال دافئ وغرف بسيطة ومضيئة.")),
    # --- Tunis / Sidi Bou Saïd (7) ---
    sejour("Tunis / Sidi Bou Saïd", "Dar Bleu de Sidi Bou Saïd", "maison_hotes", None,
           "Tunis, Sidi Bou Saïd", 36.8700, 10.3470, 380, 2,
           "terrasse vue mer,patio,petit-déjeuner,wifi", ("couple",),
           "Sidi Bou Said, Tunisia, 19 March 2018 DSC 8005.jpg",
           "Maison blanche et bleue sur les hauteurs du village, terrasse avec vue sur le golfe. "
           "Une adresse romantique pour un couple.",
           ("Dar Bleu de Sidi Bou Saïd",
            "White-and-blue house on the heights of the village, with a terrace overlooking the "
            "gulf. A romantic address for a couple."),
           ("الدار الزرقاء بسيدي بوسعيد",
            "دار بيضاء وزرقاء في أعالي القرية، بسطح يطلّ على الخليج. عنوان رومانسي للأزواج.")),
    sejour("Tunis / Sidi Bou Saïd", "Hôtel Les Falaises", "hotel", 4,
           "Tunis, Sidi Bou Saïd", 36.8730, 10.3510, 420, 3,
           "vue mer,piscine,spa,restaurant,wifi", ("couple",),
           "Sidi Bou Said Cliff.jpg",
           "Hôtel accroché à la falaise de Sidi Bou Saïd, piscine à débordement et spa. "
           "Le café des Délices est à quelques minutes à pied.",
           ("Les Falaises Hotel",
            "Hotel clinging to the Sidi Bou Saïd cliff, with an infinity pool and spa. The Café "
            "des Délices is a few minutes' walk away."),
           ("فندق المنحدرات",
            "فندق على منحدر سيدي بوسعيد، بمسبح لا متناهٍ ومنتجع صحي. مقهى العالية على بعد "
            "دقائق سيرًا.")),
    sejour("Tunis / Sidi Bou Saïd", "Dar Nour El Medina", "maison_hotes", None,
           "Tunis, Médina", 36.7985, 10.1705, 230, 2,
           "patio,terrasse,petit-déjeuner,wifi", ("solo", "couple"),
           "Dar ya.jpg",
           "Demeure de la médina restaurée, chambres autour d'un patio carrelé, terrasse sur les "
           "minarets. Idéale pour découvrir Tunis à pied.",
           ("Dar Nour El Medina",
            "Restored medina residence, rooms around a tiled patio and a terrace facing the "
            "minarets. Ideal for exploring Tunis on foot."),
           ("دار نور المدينة",
            "دار مرمَّمة في المدينة العتيقة، غرف حول فناء مبلَّط وسطح يطلّ على المآذن. مثالية "
            "لاكتشاف تونس سيرًا على الأقدام.")),
    sejour("Tunis / Sidi Bou Saïd", "Maison du Patio", "maison_hotes", None,
           "Tunis, Sidi Bou Saïd", 36.8695, 10.3480, 300, 4,
           "patio,chambre familiale,petit-déjeuner,wifi", ("famille",),
           "PatioArabicHouse.JPG",
           "Maison d'hôtes familiale avec grand patio fleuri et chambre pour 4. Les enfants "
           "adorent le puits et la fontaine.",
           ("Maison du Patio",
            "Family guesthouse with a large flowered patio and a room for 4. Children love the "
            "well and the fountain."),
           ("دار الفناء",
            "دار ضيافة عائلية بفناء كبير مزهر وغرفة لأربعة أشخاص. يحبّ الأطفال البئر والنافورة.")),
    sejour("Tunis / Sidi Bou Saïd", "Appartement Plage de La Marsa", "appartement", None,
           "Tunis, La Marsa", 36.8790, 10.3270, 210, 5,
           "cuisine équipée,balcon,climatisation,wifi,plage à 200 m", ("famille",),
           "Marsa-plage.jpg",
           "Appartement de trois pièces à 200 m de la plage de La Marsa, cuisine équipée et "
           "balcon. Pratique pour une famille qui veut cuisiner.",
           ("La Marsa Beach Apartment",
            "Three-room apartment 200 m from La Marsa beach, with a fitted kitchen and balcony. "
            "Handy for a family that wants to cook."),
           ("شقّة شاطئ المرسى",
            "شقّة من ثلاث غرف على بعد 200 متر من شاطئ المرسى، بمطبخ مجهّز وشرفة. عملية لعائلة "
            "تريد الطبخ.")),
    sejour("Tunis / Sidi Bou Saïd", "Hôtel Gammarth Horizon", "hotel", 5,
           "Tunis, Gammarth", 36.9150, 10.2900, 560, 2,
           "spa,piscine,plage privée,restaurant gastronomique,wifi", ("couple",),
           "View of the Gammarth beach.jpg",
           "Palace balnéaire de Gammarth : plage privée, spa et restaurant gastronomique. "
           "Pour une escapade de luxe à deux.",
           ("Gammarth Horizon Hotel",
            "Seaside palace in Gammarth: private beach, spa and fine-dining restaurant. For a "
            "luxury getaway for two."),
           ("فندق أفق قمرت",
            "قصر شاطئي في قمرت: شاطئ خاص ومنتجع صحي ومطعم راقٍ. لعطلة فاخرة لشخصين.")),
    sejour("Tunis / Sidi Bou Saïd", "Studio des Artistes", "appartement", None,
           "Tunis, Sidi Bou Saïd", 36.8705, 10.3485, 140, 1,
           "kitchenette,terrasse commune,wifi", ("solo",),
           "Sidi Bou Said 08.jpg",
           "Studio pour une personne au-dessus des boutiques d'artisans du village. "
           "Terrasse partagée avec vue sur le golfe.",
           ("Artists' Studio",
            "Single-occupancy studio above the village's craft shops. Shared terrace with a view "
            "of the gulf."),
           ("استوديو الفنّانين",
            "استوديو لشخص واحد فوق دكاكين الحرفيين في القرية. سطح مشترك بإطلالة على الخليج.")),
    # --- Sousse / Monastir (6) ---
    sejour("Sousse / Monastir", "Hôtel Marina Kantaoui", "hotel", 4,
           "Sousse, Port El Kantaoui", 35.8925, 10.5995, 290, 4,
           "piscine,club enfants,plage,chambres familiales,demi-pension,wifi", ("famille",),
           "Port El Kantaoui Beach (348954999).jpg",
           "Hôtel familial les pieds dans l'eau, à côté du port de plaisance : piscines, "
           "toboggans, club enfants et animation en soirée.",
           ("Marina Kantaoui Hotel",
            "Family hotel right on the beach, next to the marina: pools, slides, kids' club and "
            "evening entertainment."),
           ("فندق مرسى القنطاوي",
            "فندق عائلي على الشاطئ مباشرة بجانب الميناء الترفيهي: مسابح وزلّاقات ونادٍ للأطفال "
            "وتنشيط مسائي.")),
    sejour("Sousse / Monastir", "Appartement Vue Marina", "appartement", None,
           "Sousse, Port El Kantaoui", 35.8945, 10.5975, 170, 4,
           "cuisine équipée,balcon vue port,piscine de résidence,climatisation", ("famille",),
           "Early Morning At Port El Kantaoui.jpg",
           "Appartement de deux chambres avec balcon sur le port de plaisance et piscine de "
           "résidence. Restaurants et Hannibal Park à pied.",
           ("Marina View Apartment",
            "Two-bedroom apartment with a balcony over the marina and a residence pool. "
            "Restaurants and Hannibal Park within walking distance."),
           ("شقّة بإطلالة على الميناء",
            "شقّة بغرفتين وشرفة على الميناء الترفيهي ومسبح الإقامة. المطاعم وحديقة حنبعل "
            "على بعد خطوات.")),
    sejour("Sousse / Monastir", "Dar Médina Sousse", "maison_hotes", None,
           "Sousse, Médina", 35.8260, 10.6380, 160, 2,
           "patio,terrasse,petit-déjeuner,wifi", ("solo", "couple"),
           "Old House in the Medina of Sousse-001.jpg",
           "Vieille maison de la médina classée UNESCO, porte cloutée et patio. Le ribat et la "
           "Grande Mosquée sont à cinq minutes.",
           ("Dar Médina Sousse",
            "Old house in the UNESCO-listed medina, with a studded door and patio. The ribat and "
            "Great Mosque are five minutes away."),
           ("دار مدينة سوسة",
            "دار قديمة في المدينة العتيقة المصنّفة لدى اليونسكو، بباب مسمَّر وفناء. الرباط "
            "والجامع الكبير على بعد خمس دقائق.")),
    sejour("Sousse / Monastir", "Hôtel Corniche Boujaafar", "hotel", 3,
           "Sousse, Boujaafar", 35.8380, 10.6310, 160, 2,
           "plage en face,petit-déjeuner,wifi", ("solo",),
           "Sousse beach - panoramio.jpg",
           "Hôtel simple sur la corniche de Boujaafar, plage en face et médina à 15 minutes à "
           "pied. Bon rapport qualité-prix pour un voyageur seul.",
           ("Corniche Boujaafar Hotel",
            "Simple hotel on the Boujaafar seafront, beach opposite and the medina a 15-minute "
            "walk away. Good value for a solo traveller."),
           ("فندق كورنيش بوجعفر",
            "فندق بسيط على كورنيش بوجعفر، الشاطئ قبالته والمدينة العتيقة على بعد 15 دقيقة "
            "سيرًا. جودة جيّدة مقابل السعر للمسافر بمفرده.")),
    sejour("Sousse / Monastir", "Hôtel Skanes Azur", "hotel", 4,
           "Monastir, Skanes", 35.7650, 10.7280, 260, 3,
           "thalasso,spa,piscine,plage privée,wifi", ("couple",),
           "Monastir- Al Qurayyah beach.jpg",
           "Hôtel de thalasso sur la plage de Skanes, à 10 minutes de l'aéroport de Monastir. "
           "Parfait pour un séjour bien-être à deux.",
           ("Skanes Azur Hotel",
            "Thalasso hotel on Skanes beach, 10 minutes from Monastir airport. Perfect for a "
            "wellness stay for two."),
           ("فندق صقانص الأزرق",
            "فندق علاج بمياه البحر على شاطئ صقانص، على بعد 10 دقائق من مطار المنستير. مثالي "
            "لإقامة استرخاء لشخصين.")),
    sejour("Sousse / Monastir", "Résidence Marina Monastir", "appartement", None,
           "Monastir, marina", 35.7795, 10.8300, 150, 4,
           "cuisine équipée,balcon,climatisation,wifi", ("famille", "solo"),
           "Marina 4 Monastir.jpg",
           "Appartement sur la marina de Monastir, à pied du ribat et de la médina. Deux chambres, "
           "cuisine équipée.",
           ("Monastir Marina Residence",
            "Apartment on the Monastir marina, walking distance from the ribat and the medina. "
            "Two bedrooms, fitted kitchen."),
           ("إقامة ميناء المنستير",
            "شقّة على الميناء الترفيهي بالمنستير، قريبة من الرباط والمدينة العتيقة. غرفتان "
            "ومطبخ مجهّز.")),
    # --- Hammamet (4) ---
    sejour("Hammamet", "Hôtel Jardins de Yasmine", "hotel", 4,
           "Hammamet, Yasmine Hammamet", 36.3730, 10.5430, 280, 4,
           "piscine,club enfants,thalasso,plage,chambres familiales,wifi", ("famille",),
           "Hammamet Yasmine R01.jpg",
           "Hôtel-club de Yasmine avec jardins, piscines et club enfants ; Carthage Land et la "
           "médina de Yasmine sont à pied.",
           ("Jardins de Yasmine Hotel",
            "Yasmine club hotel with gardens, pools and a kids' club; Carthage Land and the "
            "Yasmine medina are within walking distance."),
           ("فندق حدائق ياسمين",
            "فندق نادٍ في ياسمين بحدائق ومسابح ونادٍ للأطفال؛ قرطاج لاند ومدينة ياسمين على بعد "
            "خطوات.")),
    sejour("Hammamet", "Résidence Port Yasmine", "appartement", None,
           "Hammamet, marina de Yasmine", 36.3700, 10.5450, 190, 4,
           "cuisine équipée,balcon vue marina,parking,climatisation", ("famille",),
           "Jachthafen von Yasmine Hammamet, Januar 2015.jpg",
           "Appartement avec balcon sur la marina de Yasmine, parking et plage à 300 m. "
           "Autonomie totale pour une famille.",
           ("Port Yasmine Residence",
            "Apartment with a balcony over the Yasmine marina, parking and a beach 300 m away. "
            "Complete independence for a family."),
           ("إقامة ميناء ياسمين",
            "شقّة بشرفة على ميناء ياسمين، مع موقف سيارات وشاطئ على بعد 300 متر. استقلالية "
            "تامّة للعائلة.")),
    sejour("Hammamet", "Dar Kasbah", "maison_hotes", None,
           "Hammamet, Médina", 36.3995, 10.6125, 220, 2,
           "terrasse vue mer,patio,petit-déjeuner", ("couple",),
           "Tunisie Hammamet Medina 07.JPG",
           "Maison d'hôtes dans les remparts de la médina, terrasse sur la mer et la kasbah. "
           "Une adresse intime pour deux.",
           ("Dar Kasbah",
            "Guesthouse within the medina walls, with a terrace over the sea and the kasbah. An "
            "intimate address for two."),
           ("دار القصبة",
            "دار ضيافة داخل أسوار المدينة العتيقة، بسطح يطلّ على البحر والقصبة. عنوان حميم "
            "لشخصين.")),
    sejour("Hammamet", "Hôtel Plage Sud", "hotel", 3,
           "Hammamet, Hammamet Sud", 36.3880, 10.5750, 150, 2,
           "plage,piscine,demi-pension,wifi", ("solo", "couple"),
           "Hammamet-Sud beach R01.jpg",
           "Hôtel simple et bien tenu sur la plage de Hammamet Sud, demi-pension. "
           "Le meilleur prix de la zone pour un séjour balnéaire.",
           ("Plage Sud Hotel",
            "Simple, well-kept hotel on Hammamet South beach, half board. The best price in the "
            "area for a beach stay."),
           ("فندق الشاطئ الجنوبي",
            "فندق بسيط ومعتنى به على شاطئ الحمامات الجنوبية، نصف إقامة. أفضل سعر في المنطقة "
            "لإقامة شاطئية.")),
    # --- Tozeur (4) ---
    sejour("Tozeur", "Hôtel Oasis des Dunes", "hotel", 4,
           "Tozeur, zone touristique", 33.9140, 8.1200, 360, 4,
           "piscine,palmeraie,hammam,restaurant,chambres familiales,wifi", ("famille",),
           "Inside Tozeur Oasis 02.jpg",
           "Hôtel en briques de terre au bord de la palmeraie, grande piscine et hammam. "
           "Point de départ des excursions vers le Chott el-Jérid et les oasis de montagne.",
           ("Oasis des Dunes Hotel",
            "Mud-brick hotel on the edge of the palm grove, with a large pool and hammam. "
            "Starting point for trips to Chott el-Jerid and the mountain oases."),
           ("فندق واحة الكثبان",
            "فندق من الآجرّ على حافّة الواحة، بمسبح كبير وحمّام. نقطة انطلاق الرحلات إلى شطّ "
            "الجريد وواحات الجبل.")),
    sejour("Tozeur", "Dar Briques d'Ouled El Hadef", "maison_hotes", None,
           "Tozeur, Ouled El Hadef", 33.9185, 8.1310, 190, 2,
           "patio,terrasse,petit-déjeuner,wifi", ("couple",),
           "Ouled El Hadef Brick facade.jpg",
           "Maison d'hôtes dans le vieux quartier aux façades de briques sculptées, "
           "terrasse sur la palmeraie au coucher du soleil.",
           ("Dar Briques d'Ouled El Hadef",
            "Guesthouse in the old quarter of carved brick façades, with a terrace over the palm "
            "grove at sunset."),
           ("دار آجرّ أولاد الهادف",
            "دار ضيافة في الحيّ العتيق ذي الواجهات الآجرّية المنقوشة، بسطح يطلّ على الواحة "
            "عند الغروب.")),
    sejour("Tozeur", "Gîte de la Palmeraie", "maison_hotes", None,
           "Tozeur, palmeraie", 33.9100, 8.1390, 140, 3,
           "jardin,petit-déjeuner,vélos", ("solo", "couple"),
           "Inside Tozeur Oasis 04.jpg",
           "Gîte simple au milieu des jardins de la palmeraie, vélos prêtés pour explorer "
           "l'oasis. Calme absolu.",
           ("Gîte de la Palmeraie",
            "Simple lodge among the palm-grove gardens, with bikes on loan to explore the oasis. "
            "Absolute calm."),
           ("نُزل الواحة",
            "نُزل بسيط وسط بساتين الواحة، مع درّاجات على ذمّة الضيوف لاكتشافها. هدوء تامّ.")),
    sejour("Tozeur", "Campement de la Corbeille", "maison_hotes", None,
           "Tozeur, Nefta", 33.8740, 7.8800, 170, 4,
           "jardin,piscine,petit-déjeuner,dîner", ("famille",),
           "Oasis Nefta 2.JPG",
           "Maison d'hôtes au-dessus de la Corbeille de Nefta, chambres familiales, dîner du "
           "terroir servi au jardin.",
           ("Campement de la Corbeille",
            "Guesthouse above the Nefta Corbeille, family rooms, local dinner served in the "
            "garden."),
           ("مخيّم السلّة",
            "دار ضيافة فوق سلّة نفطة، غرف عائلية وعشاء محلي يُقدَّم في الحديقة.")),
]


# ----------------------------------------------------------------------
# Vols — vraies compagnies et lignes, horaires et prix inventés
# ----------------------------------------------------------------------

AEROPORTS = {
    "TUN": "Tunis", "DJE": "Djerba", "MIR": "Monastir", "NBE": "Enfidha", "TOE": "Tozeur",
    "ORY": "Paris", "CDG": "Paris", "LYS": "Lyon", "MRS": "Marseille", "NCE": "Nice",
    "FCO": "Rome", "FRA": "Francfort", "BRU": "Bruxelles", "GVA": "Genève",
}
TUNISIE = {"TUN", "DJE", "MIR", "NBE", "TOE"}
LUN, MAR, MER, JEU, VEN, SAM, DIM = range(7)
CHAQUE_JOUR = tuple(range(7))

# (compagnie, n° aller, n° retour, A, B, jours, heure A->B, heure B->A, durée min,
#  places éco, places business (0 = pas de business), prix de base éco en DT, aller simple)
# L'aller part de A. Durées : ordres de grandeur des vols directs réels.
LIGNES = [
    ("Tunisair Express", "UG101", "UG102", "TUN", "DJE", CHAQUE_JOUR, "07:00", "08:45", 60, 70, 0, 190),
    ("Tunisair Express", "UG103", "UG104", "TUN", "DJE", CHAQUE_JOUR, "12:30", "14:15", 60, 70, 0, 190),
    ("Tunisair Express", "UG105", "UG106", "TUN", "DJE", CHAQUE_JOUR, "18:45", "20:30", 60, 70, 0, 190),
    ("Tunisair Express", "UG141", "UG142", "TUN", "TOE", (LUN, MER, VEN), "09:30", "11:30", 70, 70, 0, 210),
    ("Tunisair", "TU711", "TU712", "ORY", "TUN", CHAQUE_JOUR, "10:15", "06:50", 145, 150, 12, 520),
    ("Tunisair", "TU821", "TU822", "CDG", "DJE", (MAR, JEU, SAM, DIM), "11:00", "06:45", 175, 150, 12, 600),
    ("Transavia", "TO3960", "TO3961", "ORY", "DJE", (LUN, MER, VEN, DIM), "13:40", "17:35", 175, 186, 0, 470),
    ("Nouvelair", "BJ541", "BJ542", "ORY", "MIR", (MER, SAM), "09:20", "12:50", 150, 180, 0, 460),
    ("Nouvelair", "BJ551", "BJ552", "ORY", "NBE", (JEU, DIM), "08:00", "11:30", 145, 180, 0, 450),
    ("Tunisair", "TU631", "TU632", "LYS", "TUN", (LUN, JEU, SAM), "14:20", "11:10", 125, 150, 12, 480),
    ("Tunisair", "TU561", "TU562", "MRS", "TUN", (LUN, MER, VEN, DIM), "15:10", "12:30", 95, 150, 0, 380),
    ("Nouvelair", "BJ371", "BJ372", "NCE", "TUN", (MAR, VEN), "16:00", "13:00", 100, 180, 0, 400),
    ("Tunisair", "TU751", "TU752", "FCO", "TUN", (LUN, MER, VEN), "13:15", "10:30", 75, 150, 0, 360),
    ("Nouvelair", "BJ101", "BJ102", "FRA", "DJE", (SAM,), "10:00", "14:40", 190, 180, 0, 640),
    ("Nouvelair", "BJ111", "BJ112", "FRA", "NBE", (DIM,), "09:00", "13:30", 170, 180, 0, 560),
    ("Tunisair", "TU851", "TU852", "BRU", "TUN", (MAR, VEN, DIM), "12:00", "07:45", 150, 150, 12, 550),
    ("Tunisair", "TU891", "TU892", "GVA", "DJE", (SAM,), "12:30", "08:30", 160, 150, 0, 620),
    ("Tunisair", "TU921", "TU922", "ORY", "TOE", (SAM,), "09:00", "13:00", 160, 150, 0, 560),
]
COEF_BUSINESS = 2.6


def dernier_dimanche(annee: int, mois: int) -> date:
    d = date(annee, mois + 1, 1) - timedelta(days=1) if mois < 12 else date(annee, 12, 31)
    return d - timedelta(days=(d.weekday() - DIM) % 7)


def decalage_utc(iata: str, jour: date) -> int:
    """Heure locale - UTC. Tunisie : +1 toute l'année ; Europe : +2 en heure d'été."""
    if iata in TUNISIE:
        return 1
    ete = dernier_dimanche(jour.year, 3) <= jour < dernier_dimanche(jour.year, 10)
    return 2 if ete else 1


def bruit(cle: str, amplitude: int) -> int:
    """Entier déterministe dans [-amplitude, amplitude] (prix, remplissage reproductibles)."""
    return zlib.crc32(cle.encode()) % (2 * amplitude + 1) - amplitude


def vols_prevus(debut: date) -> list[dict]:
    vols = []
    for (compagnie, num_a, num_r, a, b, jours, h_a, h_r, duree, eco, business, prix) in LIGNES:
        for i in range(HORIZON_JOURS):
            jour = debut + timedelta(days=i)
            if jour.weekday() not in jours:
                continue
            for numero, dep, arr, heure, minutes in (
                (num_a, a, b, h_a, duree),
                (num_r, b, a, h_r, duree + 5),  # retour un peu plus long (vents dominants)
            ):
                depart = datetime.combine(jour, datetime.strptime(heure, "%H:%M").time())
                decalage = decalage_utc(arr, jour) - decalage_utc(dep, jour)
                arrivee = depart + timedelta(minutes=minutes, hours=decalage)
                week_end = 1.15 if jour.weekday() in (VEN, SAM, DIM) else 1.0
                base = prix * week_end * (1 + bruit(f"{numero}{jour}", 6) / 100)
                for classe, places, coef in (("economy", eco, 1.0), ("business", business, COEF_BUSINESS)):
                    if not places:
                        continue
                    vendus = (45 + bruit(f"{numero}{jour}{classe}", 25)) / 100  # 20 % à 70 % vendus
                    vols.append({
                        "compagnie": compagnie, "numero_vol": numero,
                        "aeroport_depart": dep, "aeroport_arrivee": arr,
                        "ville_depart": AEROPORTS[dep], "ville_arrivee": AEROPORTS[arr],
                        "depart_le": depart, "arrivee_le": arrivee, "classe": classe,
                        "prix": float(round(base * coef)),
                        "places_totales": places,
                        "places_disponibles": places - round(places * vendus),
                    })
    return vols


# ----------------------------------------------------------------------
# Voitures de location — agences fictives « Voyara Location », modèles courants
# ----------------------------------------------------------------------

# clé -> (marque, modèle, catégorie, transmission, carburant, places, prix/jour DT, photo Commons)
MODELES = {
    "picanto": ("Kia", "Picanto", "economique", "manuelle", "essence", 4, 85,
                "2021 KIA Picanto 1 DPi - 998cc 1.0 (66PS) Petrol - Blue Breeze - 03-2024, Front.jpg"),
    "i10": ("Hyundai", "i10", "economique", "manuelle", "essence", 4, 90,
            "2020 Hyundai i10 Premium 1.0.jpg"),
    "clio": ("Renault", "Clio", "compacte", "manuelle", "essence", 5, 120,
             "Renault Clio V 1X7A0392.jpg"),
    "208": ("Peugeot", "208", "compacte", "automatique", "essence", 5, 150,
            "2020 Peugeot 208 Allure.jpg"),
    "ibiza": ("Seat", "Ibiza", "compacte", "manuelle", "essence", 5, 125,
              "2018 SEAT Ibiza FR.jpg"),
    "yaris": ("Toyota", "Yaris Hybrid", "compacte", "automatique", "hybride", 5, 165,
              "Toyota Yaris Hybrid (2021) (52925177607).jpg"),
    "mg4": ("MG", "MG4 Electric", "compacte", "automatique", "electrique", 5, 240,
            "MG4 EV Automesse Ludwigsburg 2022 1X7A5920.jpg"),
    "duster": ("Dacia", "Duster", "suv", "manuelle", "diesel", 5, 180,
               "2018 Dacia Duster Comfort 1.6.jpg"),
    "tucson": ("Hyundai", "Tucson", "suv", "automatique", "diesel", 5, 260,
               "2021 Hyundai Tucson Elite N-Line front.jpg"),
    "sportage": ("Kia", "Sportage", "suv", "automatique", "diesel", 5, 270,
                 "Kia Sportage (NQ5) 1X7A0319.jpg"),
    "prado": ("Toyota", "Land Cruiser Prado", "suv", "automatique", "diesel", 7, 380,
              "Toyota Land Cruiser Prado, Baku (P1090223).jpg"),
    "jogger": ("Dacia", "Jogger", "van", "manuelle", "essence", 7, 210,
               "2023 Dacia Jogger 1X7A6203.jpg"),
    "h1": ("Hyundai", "H-1", "van", "manuelle", "diesel", 9, 340,
           "Hyundai H-1 (Starex) (48504376301).jpg"),
}
SUPPLEMENT_AEROPORT = 10  # DT/jour : frais de prise en charge à l'aéroport

# (agence, localisation, aéroport ?, modèles)
AGENCES = [
    ("Voyara Location — Aéroport Tunis-Carthage", "Tunis, aéroport Tunis-Carthage", True,
     ("picanto", "clio", "208", "duster", "tucson", "h1")),
    ("Voyara Location — Les Berges du Lac", "Tunis, Les Berges du Lac", False,
     ("mg4", "yaris", "sportage")),
    ("Voyara Location — Aéroport Djerba-Zarzis", "Djerba, aéroport Djerba-Zarzis", True,
     ("picanto", "i10", "clio", "duster", "jogger", "h1")),
    ("Voyara Location — Midoun", "Djerba, zone touristique de Midoun", False,
     ("i10", "ibiza", "yaris")),
    ("Voyara Location — Aéroport Monastir", "Monastir, aéroport Habib-Bourguiba", True,
     ("picanto", "clio", "duster", "jogger")),
    ("Voyara Location — Port El Kantaoui", "Sousse, Port El Kantaoui", False,
     ("i10", "208", "sportage")),
    ("Voyara Location — Aéroport Enfidha-Hammamet", "Enfidha, aéroport Enfidha-Hammamet", True,
     ("picanto", "ibiza", "tucson", "h1")),
    ("Voyara Location — Yasmine Hammamet", "Hammamet, Yasmine Hammamet", False,
     ("i10", "clio", "yaris")),
    ("Voyara Location — Aéroport Tozeur-Nefta", "Tozeur, aéroport Tozeur-Nefta", True,
     ("i10", "duster", "prado")),
]


def voitures_prevues() -> list[dict]:
    res = []
    for agence, localisation, aeroport, cles in AGENCES:
        for cle in cles:
            marque, modele, categorie, transmission, carburant, places, prix, _ = MODELES[cle]
            res.append({
                "cle_modele": cle, "marque": marque, "modele": modele, "categorie": categorie,
                "transmission": transmission, "carburant": carburant, "nb_places": places,
                "agence": agence, "localisation": localisation,
                "prix_jour": float(prix + (SUPPLEMENT_AEROPORT if aeroport else 0)),
                "disponible": True,
            })
    return res


# ----------------------------------------------------------------------
# Transferts — prix par véhicule (pas par passager)
# ----------------------------------------------------------------------

VEHICULES = {  # type -> (capacité, bagages, description type)
    "taxi": (4, 3, "Taxi officiel, prix forfaitaire convenu à la réservation (pas de compteur à "
                   "négocier). Majoration de nuit d'environ 50 % entre 21 h et 5 h."),
    "berline": (3, 3, "Chauffeur privé en berline climatisée, accueil avec pancarte au nom du "
                      "voyageur, suivi du vol en cas de retard."),
    "van": (7, 7, "Van climatisé avec chauffeur, pour une famille ou un petit groupe ; sièges "
                  "enfants sur demande."),
    "minibus": (16, 16, "Minibus climatisé avec chauffeur pour les groupes ; soute à bagages."),
}

# (départ, arrivée, type, durée min, prix DT)
TRANSFERTS = [
    ("Aéroport Djerba-Zarzis", "Djerba, Houmt Souk", "taxi", 15, 30),
    ("Aéroport Djerba-Zarzis", "Djerba, zone touristique de Midoun", "taxi", 30, 60),
    ("Aéroport Djerba-Zarzis", "Djerba, zone touristique de Midoun", "berline", 30, 85),
    ("Aéroport Djerba-Zarzis", "Djerba, zone touristique de Midoun", "van", 30, 120),
    ("Aéroport Djerba-Zarzis", "Djerba, zone touristique de Midoun", "minibus", 35, 220),
    ("Aéroport Djerba-Zarzis", "Djerba, zone touristique d'Aghir", "taxi", 40, 70),
    ("Aéroport Djerba-Zarzis", "Djerba, Erriadh", "taxi", 20, 40),
    ("Aéroport Djerba-Zarzis", "Tozeur, zone touristique", "van", 285, 650),
    ("Aéroport Tunis-Carthage", "Tunis, Médina", "taxi", 20, 20),
    ("Aéroport Tunis-Carthage", "Tunis, Sidi Bou Saïd", "taxi", 25, 30),
    ("Aéroport Tunis-Carthage", "Tunis, Sidi Bou Saïd", "berline", 25, 70),
    ("Aéroport Tunis-Carthage", "Tunis, Gammarth / La Marsa", "berline", 30, 80),
    ("Aéroport Tunis-Carthage", "Tunis, Gammarth / La Marsa", "van", 30, 110),
    ("Aéroport Tunis-Carthage", "Hammamet, Yasmine Hammamet", "berline", 60, 180),
    ("Aéroport Tunis-Carthage", "Hammamet, Yasmine Hammamet", "van", 60, 240),
    ("Aéroport Tunis-Carthage", "Sousse, Port El Kantaoui", "berline", 110, 320),
    ("Aéroport Tunis-Carthage", "Sousse, Port El Kantaoui", "minibus", 120, 550),
    ("Aéroport Enfidha-Hammamet", "Hammamet, Yasmine Hammamet", "taxi", 40, 110),
    ("Aéroport Enfidha-Hammamet", "Hammamet, Yasmine Hammamet", "berline", 45, 140),
    ("Aéroport Enfidha-Hammamet", "Hammamet, Yasmine Hammamet", "van", 45, 170),
    ("Aéroport Enfidha-Hammamet", "Sousse, Port El Kantaoui", "taxi", 35, 100),
    ("Aéroport Enfidha-Hammamet", "Monastir, Skanes", "berline", 55, 150),
    ("Aéroport Monastir Habib-Bourguiba", "Sousse, Port El Kantaoui", "taxi", 25, 45),
    ("Aéroport Monastir Habib-Bourguiba", "Sousse, Port El Kantaoui", "van", 25, 90),
    ("Aéroport Monastir Habib-Bourguiba", "Monastir, Skanes", "taxi", 10, 20),
    ("Aéroport Monastir Habib-Bourguiba", "Monastir, centre-ville", "taxi", 10, 15),
    ("Aéroport Tozeur-Nefta", "Tozeur, zone touristique", "taxi", 10, 15),
    ("Aéroport Tozeur-Nefta", "Tozeur, Nefta", "taxi", 30, 45),
    ("Hammamet, Yasmine Hammamet", "Tunis, Sidi Bou Saïd", "berline", 70, 190),
    ("Hammamet, Yasmine Hammamet", "Aéroport Tunis-Carthage", "van", 60, 240),
    ("Sousse, Port El Kantaoui", "Aéroport Tunis-Carthage", "berline", 110, 320),
    ("Tozeur, zone touristique", "Aéroport Djerba-Zarzis", "van", 285, 650),
]
LONG_TRAJET_MIN = 180


def transferts_prevus() -> list[dict]:
    res = []
    for depart, arrivee, type_, duree, prix in TRANSFERTS:
        capacite, bagages, texte = VEHICULES[type_]
        if duree >= LONG_TRAJET_MIN:
            texte += " Long trajet : une pause est prévue en route."
        res.append({
            "depart": depart, "arrivee": arrivee, "type_vehicule": type_, "capacite": capacite,
            "bagages": bagages, "duree": duree, "prix": float(prix), "description": texte,
            "actif": True,
        })
    return res


# ----------------------------------------------------------------------
# Photos
# ----------------------------------------------------------------------


def photos_prevues() -> dict[str, tuple[str, str]]:
    """Nom de fichier local -> (fichier Commons, libellé pour la page /credits)."""
    res = {f"{slug(s['nom'])}.jpg": (s["photo"], f"Séjour — {s['nom']}") for s in SEJOURS}
    for cle, (marque, modele, *_reste, fichier) in MODELES.items():
        res[f"voiture-{slug(cle)}.jpg"] = (fichier, f"Voiture — {marque} {modele}")
    return res


def photo_voiture(cle_modele: str) -> str:
    return f"voiture-{slug(cle_modele)}.jpg"


# ----------------------------------------------------------------------
# Contrôles (sans base)
# ----------------------------------------------------------------------


def verifier(fichiers: bool = True) -> list[str]:
    from app.travel_routes import CarRentalIn, FlightIn, StayIn, TransferIn

    erreurs = []
    debut = date.today() + timedelta(days=1)

    def valider(schema, donnees: dict, libelle: str) -> None:
        try:
            schema(**{k: v for k, v in donnees.items() if k in schema.model_fields})
        except Exception as exc:  # pydantic.ValidationError
            erreurs.append(f"{libelle} : {exc}")

    noms = Counter(s["nom"] for s in SEJOURS)
    erreurs += [f"séjour en double : {n}" for n, c in noms.items() if c > 1]
    for s in SEJOURS:
        valider(StayIn, s, f"séjour {s['nom']}")
        d = distance_km(s["latitude"], s["longitude"], *CENTRES[s["zone"]])
        if d > RAYON_MAX_KM:
            erreurs.append(f"séjour {s['nom']} : à {d:.0f} km du centre de {s['zone']}")
        if s["type"] == "hotel" and not s["etoiles"]:
            erreurs.append(f"séjour {s['nom']} : hôtel sans étoiles")
        if not set(s["profils"]) <= set(PROFILS):
            erreurs.append(f"séjour {s['nom']} : profil inconnu {s['profils']}")
    for zone in CENTRES:
        couverts = {p for s in SEJOURS if s["zone"] == zone for p in s["profils"]}
        for p in PROFILS:
            if p not in couverts:
                erreurs.append(f"zone {zone} : aucun séjour pour le profil « {p} »")

    vols = vols_prevus(debut)
    cles = Counter((v["numero_vol"], v["depart_le"], v["classe"]) for v in vols)
    erreurs += [f"vol en double : {c}" for c, n in cles.items() if n > 1]
    for v in vols:
        valider(FlightIn, v, f"vol {v['numero_vol']} {v['depart_le']:%d/%m %H:%M}")
        if not 0 <= v["places_disponibles"] <= v["places_totales"]:
            erreurs.append(f"vol {v['numero_vol']} : places incohérentes")

    voitures = voitures_prevues()
    cles = Counter((v["agence"], v["marque"], v["modele"]) for v in voitures)
    erreurs += [f"voiture en double : {c}" for c, n in cles.items() if n > 1]
    for v in voitures:
        valider(CarRentalIn, v, f"voiture {v['marque']} {v['modele']} ({v['agence']})")

    transferts = transferts_prevus()
    cles = Counter((t["depart"], t["arrivee"], t["type_vehicule"]) for t in transferts)
    erreurs += [f"transfert en double : {c}" for c, n in cles.items() if n > 1]
    for t in transferts:
        valider(TransferIn, t, f"transfert {t['depart']} -> {t['arrivee']} ({t['type_vehicule']})")

    if fichiers:
        credites = {c["fichier"] for c in lire_credits()}
        for local, (commons, _) in photos_prevues().items():
            chemin = OFFRES_DIR / local
            if not chemin.exists():
                erreurs.append(f"photo absente : {local} (lancer --telecharger)")
            elif chemin.stat().st_size > TAILLE_MAX:
                erreurs.append(f"photo trop lourde : {local}")
            if commons not in credites:
                erreurs.append(f"crédit manquant : {commons}")
    return erreurs


def afficher_bilan() -> None:
    debut = date.today() + timedelta(days=1)
    vols = vols_prevus(debut)
    print(f"Séjours : {len(SEJOURS)} · " + ", ".join(
        f"{z} {sum(s['zone'] == z for s in SEJOURS)}" for z in CENTRES))
    types = Counter(s["type"] for s in SEJOURS)
    print("  types : " + ", ".join(f"{t} {n}" for t, n in types.most_common()))
    prix = sorted(s["prix_nuit"] for s in SEJOURS)
    print(f"  prix/nuit (DT) : min {prix[0]:g} · médiane {prix[len(prix) // 2]:g} · max {prix[-1]:g}")
    print(f"Vols : {len(vols)} sur {HORIZON_JOURS} jours ({len(LIGNES)} lignes, "
          f"{sum(v['classe'] == 'business' for v in vols)} en business)")
    print(f"Voitures : {len(voitures_prevues())} dans {len(AGENCES)} agences, {len(MODELES)} modèles")
    print(f"Transferts : {len(TRANSFERTS)}")
    print(f"Photos prévues : {len(photos_prevues())}")


# ----------------------------------------------------------------------
# Téléchargement des photos (mainteneur)
# ----------------------------------------------------------------------


def telecharger() -> None:
    OFFRES_DIR.mkdir(parents=True, exist_ok=True)
    nouveaux, refuses, echecs, deja = [], 0, 0, 0
    for local, (fichier, libelle) in photos_prevues().items():
        chemin = OFFRES_DIR / local
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
                time.sleep(2)  # reste sous le quota de Commons
                if len(contenu) <= TAILLE_MAX:
                    break
            else:
                raise RuntimeError(f"vignette trop lourde même en {LARGEURS[-1]} px")
        except PermissionError as exc:
            print(f"  ! {local} : {exc}")
            refuses += 1
            continue
        except Exception as exc:  # réseau, fichier renommé, quota…
            print(f"  ! {local} : {exc}")
            echecs += 1
            continue
        chemin.write_bytes(contenu)
        nouveaux.append({
            "activite": libelle, "fichier": fichier, "auteur": info["auteur"],
            "licence": info["licence"], "source": info["source"],
        })
        print(f"  + {local} <- {fichier} ({info['licence']}, {len(contenu) // 1024} Ko)")

    if nouveaux:
        credits = lire_credits()
        connus = {c["fichier"] for c in credits}
        credits.extend(c for c in nouveaux if c["fichier"] not in connus)
        CREDITS_FILE.write_text(json.dumps(credits, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Crédits écrits dans {CREDITS_FILE}")
    print(f"Terminé : {len(nouveaux)} téléchargée(s), {deja} déjà présente(s), "
          f"{refuses} licence(s) refusée(s), {echecs} échec(s).")


# ----------------------------------------------------------------------
# Écriture en base
# ----------------------------------------------------------------------


def ecrire() -> None:
    from app.database import Base, SessionLocal, engine
    from app.lieux import completer_lieux
    from app.models import Aeroport, CarRental, Flight, Stay, Transfer

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    debut = date.today() + timedelta(days=1)
    try:
        # Référentiel des aéroports (rempli à la création de la table) : sert à
        # déduire ville et code aéroport des voitures et transferts (étape 2-bis).
        aeroports = db.query(Aeroport).all()
        # Séjours : clé = nom ; ne complète que les champs vides.
        crees = completes = 0
        for s in SEJOURS:
            photo = URL_PREFIXE + f"{slug(s['nom'])}.jpg"
            stay = db.query(Stay).filter(Stay.nom == s["nom"]).first()
            if stay is None:
                db.add(Stay(
                    nom=s["nom"], type=s["type"], description=s["description"],
                    nom_en=s["nom_en"], nom_ar=s["nom_ar"],
                    description_en=s["description_en"], description_ar=s["description_ar"],
                    localisation=s["localisation"], latitude=s["latitude"], longitude=s["longitude"],
                    etoiles=s["etoiles"], prix_nuit=s["prix_nuit"], capacite=s["capacite"],
                    equipements=s["equipements"], photos=photo, actif=True,
                ))
                crees += 1
            else:
                modifie = False
                for champ in ("nom_en", "nom_ar", "description_en", "description_ar"):
                    if not getattr(stay, champ):
                        setattr(stay, champ, s[champ])
                        modifie = True
                if not stay.photos:
                    stay.photos = photo
                    modifie = True
                completes += modifie
        print(f"Séjours : {crees} créé(s), {completes} complété(s).")

        # Vols : clé = (numéro, départ, classe).
        existants = {
            (n, d, c) for n, d, c in db.query(Flight.numero_vol, Flight.depart_le, Flight.classe)
            .filter(Flight.depart_le >= datetime.combine(debut, datetime.min.time()))
        }
        ajoutes = 0
        for v in vols_prevus(debut):
            if (v["numero_vol"], v["depart_le"], v["classe"]) in existants:
                continue
            db.add(Flight(**v))
            ajoutes += 1
        print(f"Vols : {ajoutes} ajouté(s) ({debut} -> {debut + timedelta(days=HORIZON_JOURS - 1)}).")

        # Voitures : clé = (agence, marque, modèle).
        crees = 0
        for v in voitures_prevues():
            cle = v.pop("cle_modele")
            voiture = db.query(CarRental).filter(
                CarRental.agence == v["agence"], CarRental.marque == v["marque"],
                CarRental.modele == v["modele"],
            ).first()
            if voiture is None:
                voiture = CarRental(**v, photos=URL_PREFIXE + photo_voiture(cle))
                completer_lieux(voiture, aeroports)
                db.add(voiture)
                crees += 1
            elif not voiture.photos:
                voiture.photos = URL_PREFIXE + photo_voiture(cle)
        print(f"Voitures : {crees} créée(s).")

        # Transferts : clé = (départ, arrivée, type de véhicule).
        crees = 0
        for t in transferts_prevus():
            if db.query(Transfer).filter(
                Transfer.depart == t["depart"], Transfer.arrivee == t["arrivee"],
                Transfer.type_vehicule == t["type_vehicule"],
            ).first() is None:
                transfert = Transfer(**t)
                completer_lieux(transfert, aeroports)
                db.add(transfert)
                crees += 1
        print(f"Transferts : {crees} créé(s).")

        db.commit()
        print(
            f"En base : {db.query(Stay).count()} séjours, {db.query(Flight).count()} vols, "
            f"{db.query(CarRental).count()} voitures, {db.query(Transfer).count()} transferts."
        )
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--verifier", action="store_true", help="contrôle les données sans toucher à la base")
    mode.add_argument("--telecharger", action="store_true", help="télécharge les photos depuis Commons")
    args = parser.parse_args()

    if args.telecharger:
        erreurs = verifier(fichiers=False)
        if erreurs:
            sys.exit("Données invalides, téléchargement annulé :\n  - " + "\n  - ".join(erreurs))
        telecharger()
        return

    erreurs = verifier()
    if erreurs:
        print("Données invalides :")
        for e in erreurs[:40]:
            print(f"  - {e}")
        if len(erreurs) > 40:
            print(f"  … et {len(erreurs) - 40} autre(s)")
        sys.exit(1)
    print("Données valides.")
    afficher_bilan()
    if not args.verifier:
        print()
        ecrire()


if __name__ == "__main__":
    main()
