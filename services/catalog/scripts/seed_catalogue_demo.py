"""Catalogue de démonstration réaliste pour le moteur IA (idempotent).

Les 8 activités de `seed_catalog.py` ne suffisent pas pour évaluer la recherche,
la recommandation et le solveur d'itinéraire (décision du 11/10/2026, étape 0).
Ce script ajoute 107 activités sur 5 zones : Djerba (36), Tunis / Sidi Bou Saïd (20),
Sousse / Monastir (20), Hammamet (15) et Tozeur (16).
- 86 activités du 11/10/2026 (Culture, Mer, Désert, Aventure, Gastronomie) ;
- 21 activités du 19/10/2026 dans 3 nouvelles catégories : Bien-être (thalasso,
  hammam, yoga), Famille & loisirs (parcs, zoos, musées pour enfants) et Golf.

Règles du jeu de données :
- lieux et types d'activités réels ; aucun nom d'entreprise inventé ;
- `latitude` / `longitude` = point de rendez-vous. Pour une excursion avec
  transport inclus, c'est le point de départ (la destination est dans le texte) ;
- coordonnées issues d'OpenStreetMap (Nominatim, 11/10/2026), arrondies à 4 décimales ;
- prix en DT : ordres de grandeur du marché, pas des tarifs officiels ;
- `localisation` = « Ville, lieu », pour rester trouvable par la recherche texte ;
- les 5 catégories d'origine (Culture, Mer, Désert, Aventure, Gastronomie) doivent
  exister (le script s'arrête sinon) ; les 3 nouvelles sont créées si besoin, avec
  leurs traductions.

Idempotence : une activité est identifiée par son titre français. Si elle existe
déjà, rien n'est écrasé : seules les traductions vides sont complétées et les
créneaux manquants ajoutés. Les autres activités de la base ne sont jamais touchées.
Les créneaux couvrent les 28 jours qui suivent la date d'exécution : relancer le
script plus tard prolonge l'horizon sans créer de doublon (date + heure).

Usage (depuis services/catalog) :
    python scripts/seed_catalogue_demo.py              # écrit en base
    python scripts/seed_catalogue_demo.py --verifier   # contrôle les données, sans base
"""

import argparse
import math
import os
import sys
from collections import Counter
from datetime import date, time, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Catégories créées par seed_catalog.py (obligatoires).
CATEGORIES_ORIGINE = ("Culture", "Mer", "Désert", "Aventure", "Gastronomie")
# Catégories ajoutées le 19/10/2026, créées par ce script : nom -> (nom_en, nom_ar).
NOUVELLES_CATEGORIES = {
    "Bien-être": ("Wellness", "العافية والاسترخاء"),
    "Famille & loisirs": ("Family & leisure", "العائلة والترفيه"),
    "Golf": ("Golf", "الغولف"),
}
CATEGORIES = CATEGORIES_ORIGINE + tuple(NOUVELLES_CATEGORIES)

# Ville (préfixe de `localisation`) -> zone de démonstration.
ZONES = {
    "Djerba": "Djerba",
    "Tunis": "Tunis / Sidi Bou Saïd",
    "Sousse": "Sousse / Monastir",
    "Monastir": "Sousse / Monastir",
    "Hammamet": "Hammamet",
    "Tozeur": "Tozeur",
}

# Centre de chaque zone : sert au contrôle de cohérence des coordonnées.
CENTRES = {
    "Djerba": (33.81, 10.88),
    "Tunis / Sidi Bou Saïd": (36.82, 10.25),
    "Sousse / Monastir": (35.80, 10.70),
    "Hammamet": (36.40, 10.60),
    "Tozeur": (33.92, 8.13),
}
RAYON_MAX_KM = 70

HORIZON_JOURS = 28
TOUS_LES_JOURS = (0, 1, 2, 3, 4, 5, 6)  # 0 = lundi
SAUF_LUNDI = (1, 2, 3, 4, 5, 6)


def act(ville, lieu, lat, lon, categorie, prix, duree, heures, places, fr, en, ar, jours=TOUS_LES_JOURS):
    """Une activité du seed. `fr`, `en`, `ar` = (titre, description) ; `duree` en minutes."""
    return {
        "ville": ville,
        "localisation": f"{ville}, {lieu}" if lieu else ville,
        "latitude": lat,
        "longitude": lon,
        "categorie": categorie,
        "prix": prix,
        "duree": duree,
        "heures": heures,
        "places": places,
        "jours": jours,
        "fr": fr,
        "en": en,
        "ar": ar,
    }


ACTIVITES = [
    # ------------------------------------------------------------------
    # Djerba (32)
    # ------------------------------------------------------------------
    act("Djerba", "Erriadh", 33.8139, 10.8594, "Culture", 35, 150, ["09:00", "14:30"], 12,
        ("Synagogue de la Ghriba et village d'Erriadh",
         "Visite guidée de la Ghriba, l'une des plus anciennes synagogues d'Afrique, puis balade dans "
         "les ruelles d'Erriadh (ancienne Hara Sghira). Tenue couvrant les épaules et les genoux."),
        ("El Ghriba Synagogue and Erriadh village",
         "Guided visit of El Ghriba, one of the oldest synagogues in Africa, followed by a stroll "
         "through the lanes of Erriadh (formerly Hara Sghira). Shoulders and knees must be covered."),
        ("كنيس الغريبة وقرية الرياض",
         "زيارة مصحوبة بمرشد لكنيس الغريبة، أحد أقدم الكنائس اليهودية في إفريقيا، ثم جولة في أزقة الرياض "
         "(الحارة الصغيرة سابقًا). يُرجى ارتداء لباس يغطي الكتفين والركبتين."),
        jours=(0, 1, 2, 3, 6)),
    act("Djerba", "Erriadh", 33.8191, 10.8543, "Culture", 25, 120, ["10:00", "16:00"], 12,
        ("Parcours street art Djerbahood à Erriadh",
         "Plus de 200 fresques peintes depuis 2014 par des artistes du monde entier sur les murs "
         "d'Erriadh. Parcours commenté à pied, rythme tranquille, adapté aux familles."),
        ("Djerbahood street-art trail in Erriadh",
         "More than 200 murals painted since 2014 by artists from around the world on the walls "
         "of Erriadh. Guided walking tour at an easy pace, family friendly."),
        ("مسار فنّ الشارع «جربة هود» في الرياض",
         "أكثر من 200 جدارية رسمها فنانون من أنحاء العالم على جدران الرياض منذ 2014. "
         "جولة مشي مع شرح وبوتيرة هادئة، مناسبة للعائلات.")),
    act("Djerba", "Guellala", 33.7287, 10.8558, "Culture", 40, 150, ["09:30", "14:30"], 8,
        ("Atelier de poterie à Guellala",
         "Guellala est le village potier de Djerba depuis l'Antiquité. Découverte des fours "
         "traditionnels puis initiation au tour avec un artisan ; votre pièce est à emporter."),
        ("Pottery workshop in Guellala",
         "Guellala has been Djerba's pottery village since Antiquity. Discover the traditional "
         "kilns, then try the wheel with a craftsman; take your piece home."),
        ("ورشة فخّار في قلالة",
         "قلالة قرية الفخّار في جربة منذ العصور القديمة. اكتشاف الأفران التقليدية ثم تجربة "
         "الدولاب مع حِرفي، وتأخذ قطعتك معك.")),
    act("Djerba", "Guellala", 33.7326, 10.8656, "Culture", 20, 90, ["10:00", "15:00"], 20,
        ("Musée du patrimoine de Guellala",
         "Sur la colline de Guellala, un musée de reconstitutions grandeur nature : mariage "
         "djerbien, métiers et costumes. Vue panoramique sur la mer et le continent."),
        ("Guellala Heritage Museum",
         "On the hill of Guellala, a museum of life-size scenes: a Djerbian wedding, crafts and "
         "costumes. Panoramic view over the sea and the mainland."),
        ("متحف التراث بقلالة",
         "على ربوة قلالة، متحف بمشاهد بالحجم الطبيعي: العرس الجربي والحِرف والأزياء. "
         "إطلالة بانورامية على البحر واليابسة.")),
    act("Djerba", "Houmt Souk", 33.8760, 10.8572, "Culture", 30, 180, ["09:00"], 15,
        ("Visite guidée de Houmt Souk : souks, fondouks et Borj El Kebir",
         "Les souks couverts, les anciens caravansérails (fondouks) puis le Borj El Kebir, "
         "forteresse du XVe siècle face à la mer. Entrée du fort incluse."),
        ("Guided tour of Houmt Souk: souks, fondouks and Borj El Kebir",
         "Covered souks, the old caravanserais (fondouks), then Borj El Kebir, a 15th-century "
         "fortress facing the sea. Fort entry included."),
        ("زيارة مصحوبة لحومة السوق: الأسواق والفنادق القديمة والبرج الكبير",
         "الأسواق المسقوفة والفنادق القديمة (الخانات) ثم البرج الكبير، حصن من القرن الخامس عشر "
         "مطلّ على البحر. تذكرة دخول البرج مشمولة.")),
    act("Djerba", "Houmt Souk", 33.8799, 10.8624, "Culture", 15, 75, ["10:00", "14:00"], 20,
        ("Musée du patrimoine traditionnel de Djerba",
         "Installé dans une ancienne zaouïa de Houmt Souk : bijoux, costumes de mariée, poteries "
         "et objets du quotidien djerbien. Visite libre avec livret explicatif."),
        ("Museum of Traditional Heritage of Djerba",
         "Housed in a former zaouia in Houmt Souk: jewellery, bridal costumes, pottery and "
         "everyday Djerbian objects. Self-guided visit with an explanatory booklet."),
        ("متحف التراث التقليدي بجربة",
         "في زاوية قديمة بحومة السوق: حُليّ وأزياء العروس وفخّار وأدوات الحياة اليومية الجربية. "
         "زيارة حرّة مع كتيّب توضيحي."),
        jours=SAUF_LUNDI),
    act("Djerba", "Fadhloun", 33.8248, 10.9593, "Culture", 45, 180, ["09:00"], 10,
        ("Circuit des mosquées ibadites : Fadhloun et El May",
         "L'architecture blanche et fortifiée des mosquées ibadites, inscrite au patrimoine "
         "mondial avec l'île en 2023. Visite de la mosquée Fadhloun puis route vers El May."),
        ("Ibadi mosques trail: Fadhloun and El May",
         "The white, fortified architecture of the Ibadi mosques, World Heritage listed with the "
         "island in 2023. Visit of Fadhloun Mosque, then on to El May."),
        ("مسار المساجد الإباضية: فضلون والماي",
         "العمارة البيضاء المحصّنة للمساجد الإباضية، المدرجة في التراث العالمي مع الجزيرة سنة 2023. "
         "زيارة جامع فضلون ثم الطريق نحو الماي."),
        jours=(1, 3, 5)),
    act("Djerba", "Djerba Explore", 33.8197, 11.0455, "Culture", 35, 180, ["10:00", "14:00"], 25,
        ("Musée Lalla Hadria et parc Djerba Explore",
         "Le musée Lalla Hadria retrace douze siècles d'arts de l'Islam ; le parc ajoute un "
         "village djerbien reconstitué et une ferme aux crocodiles. Idéal avec des enfants."),
        ("Lalla Hadria Museum and Djerba Explore park",
         "Lalla Hadria Museum covers twelve centuries of Islamic art; the park adds a rebuilt "
         "Djerbian village and a crocodile farm. Ideal with children."),
        ("متحف للا حضرية وفضاء جربة إكسبلور",
         "يروي متحف للا حضرية اثني عشر قرنًا من الفنون الإسلامية، ويضيف الفضاء قرية جربية "
         "معاد بناؤها ومزرعة تماسيح. مثالي مع الأطفال.")),
    act("Djerba", "Midoun", 33.8246, 11.0069, "Culture", 20, 120, ["09:00"], 15,
        ("Marché hebdomadaire de Midoun",
         "Chaque vendredi, Midoun s'anime : épices, poissons, vannerie, poteries et bétail. "
         "Un guide vous aide à décoder les étals et à négocier comme un local."),
        ("Midoun weekly market",
         "Every Friday, Midoun comes alive: spices, fish, basketry, pottery and livestock. "
         "A guide helps you read the stalls and haggle like a local."),
        ("السوق الأسبوعية بميدون",
         "كل يوم جمعة تنبض ميدون بالحياة: توابل وأسماك وسلال وفخّار ومواشٍ. "
         "يساعدك المرشد على فهم المعروضات والمساومة كأهل البلد."),
        jours=(4,)),
    act("Djerba", "Ajim", 33.7248, 10.7485, "Culture", 50, 180, ["09:30", "14:30"], 10,
        ("Sur les traces de Star Wars à Ajim",
         "Ajim et ses environs ont servi de décor à « Star Wars : Un nouvel espoir » (1977). "
         "Circuit commenté jusqu'à la maison d'Obi-Wan Kenobi et aux lieux de tournage."),
        ("On the trail of Star Wars in Ajim",
         "Ajim and its surroundings were a set for \"Star Wars: A New Hope\" (1977). "
         "Guided tour to Obi-Wan Kenobi's house and the filming locations."),
        ("على خُطى «حرب النجوم» في أجيم",
         "كانت أجيم وضواحيها ديكورًا لفيلم «حرب النجوم: أمل جديد» (1977). "
         "جولة مع شرح إلى بيت أوبي وان كينوبي وأماكن التصوير.")),
    act("Djerba", "El Kantara", 33.6853, 10.9215, "Culture", 40, 150, ["09:00"], 12,
        ("Site antique de Meninx et chaussée d'El Kantara",
         "Les vestiges de Meninx, principale ville romaine de l'île, célèbre pour sa pourpre, "
         "puis la chaussée d'origine romaine qui relie Djerba au continent."),
        ("Ancient Meninx and the El Kantara causeway",
         "The remains of Meninx, the island's main Roman town, famous for its purple dye, then "
         "the causeway of Roman origin linking Djerba to the mainland."),
        ("موقع مِنِنكس الأثري وطريق القنطرة",
         "آثار مِنِنكس، أهم مدينة رومانية في الجزيرة والمشهورة بصباغ الأرجوان، ثم الطريق "
         "الروماني الأصل الذي يربط جربة باليابسة."),
        jours=(1, 3, 5)),
    act("Djerba", "Midoun", 33.8246, 11.0069, "Aventure", 55, 240, ["08:30"], 10,
        ("Tour de Djerba à vélo : menzels et huileries souterraines",
         "Une boucle de 25 km sur petites routes plates entre menzels (fermes fortifiées), "
         "puits et huileries creusées sous terre. Vélo et casque fournis."),
        ("Djerba by bike: menzels and underground oil mills",
         "A 25 km loop on flat back roads past menzels (fortified farmsteads), wells and "
         "underground olive-oil mills. Bike and helmet provided."),
        ("جربة على الدرّاجة: المنازل والمعاصر الجوفية",
         "حلقة بطول 25 كم على طرق ريفية مستوية بين المنازل (الحوش المحصّنة) والآبار ومعاصر "
         "الزيت المحفورة تحت الأرض. الدرّاجة والخوذة متوفّرتان.")),
    act("Djerba", "Mahboubine", 33.7970, 10.9635, "Aventure", 30, 150, ["08:30", "16:00"], 12,
        ("Randonnée douce à Mahboubine et El May",
         "Marche de 8 km dans l'intérieur rural de l'île : oliviers, palmiers, menzels et la "
         "mosquée El Kateb de Mahboubine. Niveau facile, pause thé incluse."),
        ("Easy hike around Mahboubine and El May",
         "An 8 km walk through the island's rural interior: olive trees, palms, menzels and "
         "Mahboubine's El Kateb mosque. Easy level, tea break included."),
        ("مشي خفيف في محبوبين والماي",
         "مسيرة 8 كم في ريف الجزيرة: زياتين ونخيل ومنازل وجامع الكاتب بمحبوبين. "
         "مستوى سهل، واستراحة شاي مشمولة.")),
    act("Djerba", "port de Houmt Souk", 33.8879, 10.8573, "Mer", 60, 360, ["09:30"], 40,
        ("Bateau pirate vers l'île aux Flamants (Ras Rmel)",
         "Traversée en bateau décoré façon pirate jusqu'à la presqu'île de Ras Rmel, où les "
         "flamants roses hivernent. Baignade, déjeuner de poisson grillé et animation à bord."),
        ("Pirate boat to Flamingo Island (Ras Rmel)",
         "Sail on a pirate-style boat to the Ras Rmel peninsula, where pink flamingos winter. "
         "Swimming, grilled-fish lunch and entertainment on board."),
        ("مركب القراصنة إلى جزيرة الفلامنغو (رأس الرمل)",
         "رحلة على مركب بطابع القراصنة إلى شبه جزيرة رأس الرمل حيث يقضي النحام الوردي الشتاء. "
         "سباحة وغداء سمك مشوي وتنشيط على متن المركب.")),
    act("Djerba", "lagune de Bin El Ouedian", 33.7153, 10.9734, "Mer", 180, 120, ["10:00", "14:00"], 4,
        ("Initiation au kitesurf sur la lagune de Bin El Ouedian",
         "Eau peu profonde et vent régulier : la lagune est un spot reconnu pour débuter. "
         "Cours avec moniteur diplômé, matériel et liaison radio fournis."),
        ("Kitesurf lesson on the Bin El Ouedian lagoon",
         "Shallow water and steady wind make the lagoon a well-known spot for beginners. "
         "Lesson with a qualified instructor, gear and radio link provided."),
        ("تعلّم ركوب الأمواج بالطائرة الورقية في بحيرة بين الوديان",
         "مياه ضحلة ورياح منتظمة تجعل البحيرة مكانًا معروفًا للمبتدئين. "
         "درس مع مدرّب مؤهّل، والمعدّات والاتصال اللاسلكي متوفّرة.")),
    act("Djerba", "Sidi Mahrez", 33.8435, 10.9995, "Mer", 140, 180, ["09:00", "14:00"], 6,
        ("Baptême de plongée au large de la zone touristique",
         "Première plongée encadrée par un moniteur certifié, à 6 m maximum sur fond de "
         "posidonies. Briefing, combinaison et bouteille fournis. Dès 10 ans."),
        ("Discover scuba diving off the tourist zone",
         "A first dive with a certified instructor, 6 m maximum over seagrass meadows. "
         "Briefing, wetsuit and tank provided. From age 10."),
        ("غطسة تجريبية قبالة المنطقة السياحية",
         "أول غطسة بإشراف مدرّب معتمد، على عمق 6 أمتار كحدّ أقصى فوق أعشاب البوسيدونيا. "
         "شرح مسبق وبدلة وقارورة متوفّرة. ابتداءً من 10 سنوات.")),
    act("Djerba", "plage de Sidi Mahrez", 33.8435, 10.9995, "Mer", 80, 30, ["10:00", "11:00", "15:00", "16:00"], 4,
        ("Jet-ski à la plage de Sidi Mahrez",
         "Trente minutes de jet-ski en zone balisée le long de la plus longue plage de l'île. "
         "Gilet fourni, consignes de sécurité avant le départ. Permis non requis."),
        ("Jet ski at Sidi Mahrez beach",
         "Thirty minutes of jet ski in a marked zone along the island's longest beach. "
         "Life jacket provided, safety briefing before departure. No licence required."),
        ("جت سكي في شاطئ سيدي محرز",
         "ثلاثون دقيقة من الجت سكي في منطقة محدّدة على طول أطول شاطئ في الجزيرة. "
         "سترة النجاة متوفّرة، وتعليمات السلامة قبل الانطلاق. لا تُشترط رخصة.")),
    act("Djerba", "plage de Sidi Mahrez", 33.8435, 10.9995, "Mer", 70, 20, ["10:30", "12:00", "15:30"], 2,
        ("Parachute ascensionnel à la plage de Sidi Mahrez",
         "Un vol tracté par bateau à environ 50 m au-dessus de la mer, seul ou à deux. "
         "Décollage et atterrissage depuis le bateau, sans se mouiller."),
        ("Parasailing at Sidi Mahrez beach",
         "A boat-towed flight about 50 m above the sea, solo or tandem. "
         "Take-off and landing from the boat, without getting wet."),
        ("المظلّة البحرية في شاطئ سيدي محرز",
         "تحليق مقطور بالمركب على ارتفاع 50 مترًا تقريبًا فوق البحر، فرديًا أو ثنائيًا. "
         "الإقلاع والهبوط من المركب دون أن تبتلّ.")),
    act("Djerba", "port d'Ajim", 33.7172, 10.7421, "Mer", 65, 240, ["07:00"], 6,
        ("Pêche traditionnelle à la charfia avec les pêcheurs d'Ajim",
         "La charfia, piège fixe en palmes, est une technique de pêche djerbienne inscrite au "
         "patrimoine immatériel de l'UNESCO. Sortie en barque et relève des nasses."),
        ("Traditional charfia fishing with Ajim fishermen",
         "The charfia, a fixed trap made of palm fronds, is a Djerbian fishing technique on "
         "UNESCO's intangible heritage list. Boat trip and lifting of the traps."),
        ("صيد تقليدي بالشرفية مع بحّارة أجيم",
         "الشرفية مصيدة ثابتة من جريد النخيل، وهي تقنية صيد جربية مدرجة في التراث اللامادي "
         "لليونسكو. خرجة بالقارب ورفع الدرّينة.")),
    act("Djerba", "Aghir", 33.7655, 11.0232, "Mer", 50, 150, ["09:00", "15:30"], 8,
        ("Kayak de mer le long de la côte d'Aghir",
         "Pagayez sur une mer souvent calme le long des plages d'Aghir, avec arrêt baignade et "
         "snorkeling. Kayak biplace, gilet et masque fournis. Dès 8 ans accompagné."),
        ("Sea kayaking along the Aghir coast",
         "Paddle on a usually calm sea along the Aghir beaches, with a swim and snorkelling stop. "
         "Tandem kayak, life jacket and mask provided. From age 8 with an adult."),
        ("التجديف بالكاياك على ساحل أغير",
         "جدّف في بحر هادئ غالبًا على طول شواطئ أغير، مع توقّف للسباحة والغطس السطحي. "
         "كاياك لشخصين وسترة وقناع متوفّرة. من 8 سنوات برفقة بالغ.")),
    act("Djerba", "plage de la Seguia", 33.7865, 11.0580, "Mer", 40, 90, ["09:30", "16:30"], 8,
        ("Stand-up paddle à la plage de la Seguia",
         "Initiation au paddle sur l'eau turquoise et peu profonde de la Seguia, l'une des "
         "plages les plus préservées de l'île. Planche, pagaie et moniteur inclus."),
        ("Stand-up paddle at Seguia beach",
         "Learn paddleboarding on the shallow turquoise water of Seguia, one of the island's "
         "most unspoilt beaches. Board, paddle and instructor included."),
        ("التجديف وقوفًا في شاطئ السقية",
         "تعلّم التجديف وقوفًا في مياه السقية الفيروزية الضحلة، أحد أكثر شواطئ الجزيرة حفاظًا "
         "على طبيعته. اللوح والمجداف والمدرّب مشمولون.")),
    act("Djerba", "plage de Sidi Mahrez", 33.8435, 10.9995, "Aventure", 40, 60, ["17:00"], 10,
        ("Balade à dromadaire sur la plage de Sidi Mahrez",
         "Une heure à dos de dromadaire le long de la plage quand la lumière devient dorée. "
         "Accompagnateur à pied, adapté aux enfants dès 6 ans."),
        ("Camel ride on Sidi Mahrez beach",
         "One hour on a dromedary along the beach as the light turns golden. "
         "Guide on foot, suitable for children from age 6."),
        ("جولة على ظهر الجمل في شاطئ سيدي محرز",
         "ساعة على ظهر الجمل على طول الشاطئ حين يصير الضوء ذهبيًا. "
         "مرافق يمشي معك، ومناسبة للأطفال من 6 سنوات.")),
    act("Djerba", "Aghir", 33.7655, 11.0232, "Aventure", 55, 90, ["09:00", "16:00"], 6,
        ("Balade à cheval sur la plage d'Aghir",
         "Promenade équestre au pas et au trot entre dunes basses et bord de mer. "
         "Chevaux adaptés aux débutants, bombe fournie."),
        ("Horse ride on Aghir beach",
         "A horse ride at walk and trot between low dunes and the shoreline. "
         "Horses suited to beginners, riding helmet provided."),
        ("جولة على الخيل في شاطئ أغير",
         "نزهة على الخيل بين الكثبان المنخفضة وحافة البحر. "
         "خيول مناسبة للمبتدئين، والخوذة متوفّرة.")),
    act("Djerba", "Midoun", 33.8246, 11.0069, "Aventure", 90, 120, ["09:00", "14:00"], 8,
        ("Quad dans l'arrière-pays de Midoun",
         "Pistes de terre, palmeraies et oliveraies au guidon d'un quad, avec pause thé dans un "
         "menzel. Briefing et casque fournis ; conducteur dès 16 ans."),
        ("Quad biking in the Midoun countryside",
         "Dirt tracks, palm groves and olive groves on a quad bike, with a tea stop at a menzel. "
         "Briefing and helmet provided; drivers from age 16."),
        ("جولة بالكواد في ريف ميدون",
         "مسالك ترابية وغابات نخيل وزياتين على متن الكواد، مع استراحة شاي في منزل تقليدي. "
         "شرح مسبق وخوذة متوفّرة؛ السائق من 16 سنة.")),
    act("Djerba", "lagune de Bin El Ouedian", 33.7153, 10.9734, "Aventure", 35, 150, ["07:30"], 10,
        ("Observation des oiseaux à la lagune de Bin El Ouedian",
         "Flamants roses, hérons et limicoles fréquentent cette zone humide du sud-est de l'île. "
         "Sortie au lever du jour avec un guide naturaliste ; jumelles fournies."),
        ("Birdwatching at the Bin El Ouedian lagoon",
         "Pink flamingos, herons and waders frequent this wetland in the south-east of the "
         "island. Early-morning outing with a naturalist guide; binoculars provided."),
        ("مراقبة الطيور في بحيرة بين الوديان",
         "النحام الوردي ومالك الحزين والطيور الخوّاضة ترتاد هذه المنطقة الرطبة جنوب شرق الجزيرة. "
         "خرجة عند الفجر مع مرشد مختصّ في الطبيعة؛ المناظير متوفّرة."),
        jours=(2, 5, 6)),
    act("Djerba", "départ de Houmt Souk", 33.8760, 10.8572, "Désert", 320, 2880, ["07:00"], 16,
        ("Excursion de 2 jours à Ksar Ghilane",
         "Départ de Djerba en 4x4 vers l'oasis de Ksar Ghilane, aux portes du Grand Erg Oriental : "
         "source chaude, dunes et nuit en campement. Repas et transport inclus."),
        ("2-day trip to Ksar Ghilane",
         "Leave Djerba by 4x4 for the Ksar Ghilane oasis, at the edge of the Grand Erg Oriental: "
         "hot spring, dunes and a night in a desert camp. Meals and transport included."),
        ("رحلة يومين إلى قصر غيلان",
         "انطلاق من جربة بسيارة رباعية الدفع نحو واحة قصر غيلان على أبواب العرق الشرقي الكبير: "
         "عين ماء ساخنة وكثبان وليلة في مخيّم. الوجبات والنقل مشمولة."),
        jours=(0, 3)),
    act("Djerba", "départ de Midoun", 33.8246, 11.0069, "Désert", 150, 720, ["07:00"], 20,
        ("Journée à Matmata et aux ksour de Tataouine",
         "Les maisons troglodytes de Matmata, dont l'hôtel-décor de Star Wars, puis les greniers "
         "fortifiés (ksour) de la région de Tataouine. Déjeuner et transport inclus."),
        ("Day trip to Matmata and the Tataouine ksour",
         "The troglodyte houses of Matmata, including the Star Wars set hotel, then the fortified "
         "granaries (ksour) of the Tataouine region. Lunch and transport included."),
        ("يوم في مطماطة وقصور تطاوين",
         "البيوت الحفرية في مطماطة، ومنها النزل الذي صُوّر فيه «حرب النجوم»، ثم المخازن المحصّنة "
         "(القصور) في جهة تطاوين. الغداء والنقل مشمولان."),
        jours=(1, 4, 6)),
    act("Djerba", "Midoun", 33.8246, 11.0069, "Gastronomie", 90, 180, ["10:00"], 8,
        ("Cours de cuisine djerbienne chez l'habitant",
         "Préparez le riz djerbien à la vapeur, la salade méchouia et la brik avec une cuisinière "
         "de l'île, puis déjeunez ensemble dans son houch. Option végétarienne."),
        ("Djerbian cooking class in a local home",
         "Cook steamed Djerbian rice, mechouia salad and brik with a local cook, then share "
         "lunch in her houch. Vegetarian option."),
        ("درس طبخ جربي عند عائلة محلية",
         "حضّر الرزّ الجربي على البخار وسلطة مشوية والبريك مع طبّاخة من الجزيرة، ثم تناولوا "
         "الغداء معًا في حوشها. خيار نباتي متوفّر.")),
    act("Djerba", "Houmt Souk", 33.8760, 10.8572, "Gastronomie", 35, 90, ["10:00", "15:00"], 12,
        ("Dégustation d'huile d'olive et huilerie souterraine",
         "Visite d'une huilerie traditionnelle creusée sous terre, où les olives étaient pressées "
         "à l'abri de la chaleur, puis dégustation d'huiles et de pain tabouna."),
        ("Olive-oil tasting and underground oil mill",
         "Visit a traditional oil mill dug underground, where olives were pressed away from the "
         "heat, then taste olive oils with tabouna bread."),
        ("تذوّق زيت الزيتون ومعصرة جوفية",
         "زيارة معصرة تقليدية محفورة تحت الأرض كان الزيتون يُعصر فيها بعيدًا عن الحرّ، "
         "ثم تذوّق الزيوت مع خبز الطابونة.")),
    act("Djerba", "port de Houmt Souk", 33.8879, 10.8573, "Gastronomie", 45, 150, ["08:00"], 10,
        ("Criée aux poissons et dégustation au port de Houmt Souk",
         "Assistez à la vente à la criée, où un crieur juché sur une chaise met le poisson aux "
         "enchères, puis dégustez la pêche du jour grillée sur le port."),
        ("Fish auction and tasting at Houmt Souk port",
         "Watch the fish auction, where an auctioneer perched on a chair sells the catch, then "
         "taste the day's fish grilled at the port."),
        ("الدلالة على السمك وتذوّق في ميناء حومة السوق",
         "تابع بيع السمك بالدلالة، حيث يعتلي الدلاّل كرسيًا ويزايد على الصيد، "
         "ثم تذوّق سمك اليوم مشويًا في الميناء."),
        jours=(0, 1, 2, 3, 4, 5)),
    act("Djerba", "Mahboubine", 33.7970, 10.9635, "Gastronomie", 50, 120, ["10:00", "16:00"], 8,
        ("Atelier pain tabouna et brik dans un menzel",
         "Pétrissez la pâte, cuisez le pain dans le four en terre (tabouna) et pliez vos briks "
         "à l'œuf, à déguster sur place avec un thé à la menthe."),
        ("Tabouna bread and brik workshop in a menzel",
         "Knead the dough, bake bread in the clay oven (tabouna) and fold your egg briks, "
         "eaten on the spot with mint tea."),
        ("ورشة خبز الطابونة والبريك في منزل تقليدي",
         "اعجن العجين واخبزه في فرن الطين (الطابونة) ولُفّ البريك بالبيض، "
         "لتتذوّقه في المكان مع شاي بالنعناع.")),
    act("Djerba", "Midoun", 33.8246, 11.0069, "Gastronomie", 70, 150, ["19:00"], 20,
        ("Dîner traditionnel djerbien dans un menzel",
         "Couscous au poisson, salade tunisienne et pâtisseries aux dattes servis dans la cour "
         "d'un menzel, suivis d'un thé à la menthe aux amandes."),
        ("Traditional Djerbian dinner in a menzel",
         "Fish couscous, Tunisian salad and date pastries served in a menzel courtyard, "
         "followed by mint tea with almonds."),
        ("عشاء جربي تقليدي في منزل",
         "كسكسي بالسمك وسلطة تونسية وحلويات بالتمر تُقدَّم في فناء منزل تقليدي، "
         "يليها شاي بالنعناع واللوز.")),
    # ------------------------------------------------------------------
    # Tunis / Sidi Bou Saïd (16)
    # ------------------------------------------------------------------
    act("Tunis", "Le Bardo", 36.8093, 10.1343, "Culture", 45, 150, ["09:30", "14:00"], 15,
        ("Musée national du Bardo : mosaïques romaines",
         "L'une des plus grandes collections de mosaïques romaines au monde, dont le Virgile "
         "entouré des Muses, dans un ancien palais beylical. Billet d'entrée inclus."),
        ("Bardo National Museum: Roman mosaics",
         "One of the world's largest collections of Roman mosaics, including Virgil with the "
         "Muses, in a former beylical palace. Entry ticket included."),
        ("المتحف الوطني بباردو: الفسيفساء الرومانية",
         "من أكبر مجموعات الفسيفساء الرومانية في العالم، ومنها لوحة فرجيل بين ربّات الفنون، "
         "في قصر بايات قديم. تذكرة الدخول مشمولة."),
        jours=SAUF_LUNDI),
    act("Tunis", "Médina", 36.7974, 10.1715, "Culture", 35, 180, ["09:00", "14:30"], 15,
        ("Médina de Tunis : Zitouna et Dar Ben Abdallah",
         "La médina inscrite à l'UNESCO, des abords de la mosquée Zitouna aux souks des "
         "parfumeurs, jusqu'au palais Dar Ben Abdallah et son musée des arts et traditions."),
        ("Tunis medina: Zitouna and Dar Ben Abdallah",
         "The UNESCO-listed medina, from the surroundings of the Zitouna Mosque to the perfume "
         "souks, up to the Dar Ben Abdallah palace and its folk-arts museum."),
        ("مدينة تونس العتيقة: الزيتونة ودار بن عبد الله",
         "المدينة المدرجة في قائمة اليونسكو، من محيط جامع الزيتونة إلى سوق العطّارين، "
         "وصولًا إلى قصر دار بن عبد الله ومتحف الفنون والتقاليد الشعبية.")),
    act("Tunis", "Carthage", 36.8414, 10.3230, "Culture", 40, 150, ["09:00", "14:00"], 15,
        ("Carthage punique : tophet de Salammbô et ports puniques",
         "Sur les traces de la Carthage d'Hannibal : le sanctuaire du tophet puis les deux "
         "bassins des ports puniques, militaire circulaire et marchand rectangulaire."),
        ("Punic Carthage: Salammbo tophet and Punic ports",
         "In the footsteps of Hannibal's Carthage: the tophet sanctuary, then the two basins of "
         "the Punic ports, the circular naval one and the rectangular merchant one."),
        ("قرطاج البونية: توفاة صلامبو والموانئ البونية",
         "على خطى قرطاج حنبعل: معبد التوفاة ثم حوضا الموانئ البونية، "
         "الحربي الدائري والتجاري المستطيل.")),
    act("Tunis", "Carthage", 36.8575, 10.3314, "Culture", 40, 150, ["09:30", "14:30"], 15,
        ("Amphithéâtre et villas romaines de Carthage",
         "La Carthage romaine : le parc des villas romaines et sa vue sur le golfe, puis "
         "l'amphithéâtre et les citernes de La Malga. Entrées du site incluses."),
        ("Amphitheatre and Roman villas of Carthage",
         "Roman Carthage: the Roman villas park and its view of the gulf, then the "
         "amphitheatre and the La Malga cisterns. Site entries included."),
        ("المسرح المدرّج والفيلات الرومانية بقرطاج",
         "قرطاج الرومانية: منتزه الفيلات الرومانية وإطلالته على الخليج، "
         "ثم المسرح المدرّج وصهاريج المعلقة. تذاكر الموقع مشمولة.")),
    act("Tunis", "Carthage", 36.8527, 10.3237, "Culture", 35, 120, ["10:00", "15:00"], 15,
        ("Colline de Byrsa et musée national de Carthage",
         "Le cœur de la cité antique : le quartier punique de Byrsa, le musée et ses stèles, "
         "et le panorama sur les ports et le golfe de Tunis."),
        ("Byrsa Hill and the National Museum of Carthage",
         "The heart of the ancient city: the Punic quarter of Byrsa, the museum and its stelae, "
         "and the panorama over the ports and the Gulf of Tunis."),
        ("ربوة بيرصا والمتحف الوطني بقرطاج",
         "قلب المدينة القديمة: الحيّ البوني في بيرصا والمتحف ونصبه، "
         "وإطلالة بانورامية على الموانئ وخليج تونس."),
        jours=SAUF_LUNDI),
    act("Tunis", "Sidi Bou Saïd", 36.8692, 10.3482, "Culture", 25, 90, ["10:00", "14:00"], 15,
        ("Dar Ennejma Ezzahra, palais du baron d'Erlanger",
         "Palais arabo-andalou construit dans les années 1920 par le baron Rodolphe d'Erlanger, "
         "aujourd'hui Centre des musiques arabes et méditerranéennes."),
        ("Ennejma Ezzahra, Baron d'Erlanger's palace",
         "An Arab-Andalusian palace built in the 1920s by Baron Rodolphe d'Erlanger, "
         "now the Centre for Arab and Mediterranean Music."),
        ("النجمة الزهراء، قصر البارون ديرلانجي",
         "قصر عربي أندلسي شيّده البارون رودولف ديرلانجي في عشرينيات القرن الماضي، "
         "وهو اليوم مركز الموسيقى العربية والمتوسطية."),
        jours=SAUF_LUNDI),
    act("Tunis", "Médina", 36.7987, 10.1717, "Culture", 60, 120, ["10:00", "15:00"], 8,
        ("Atelier de calligraphie arabe dans la médina",
         "Initiation au calame et à l'encre avec un calligraphe : écriture coufique et maghrébine, "
         "puis composition de votre prénom en arabe, à emporter."),
        ("Arabic calligraphy workshop in the medina",
         "Learn to use the qalam and ink with a calligrapher: Kufic and Maghrebi scripts, "
         "then compose your first name in Arabic to take home."),
        ("ورشة الخطّ العربي في المدينة العتيقة",
         "تعلّم استعمال القلم والحبر مع خطّاط: الخطّ الكوفي والمغربي، "
         "ثم اكتب اسمك بالعربية وخذه معك.")),
    act("Tunis", "Médina", 36.7985, 10.1695, "Culture", 25, 90, ["10:00"], 10,
        ("Souk des Chaouachia : la chéchia tunisienne",
         "Dans le souk des Chaouachia, les derniers artisans fabriquent la chéchia rouge : "
         "tricot, foulage, teinture et cardage au chardon. Démonstration commentée."),
        ("Souk Ech Chaouachia: the Tunisian chechia",
         "In the Chaouachia souk, the last craftsmen make the red chechia: knitting, felting, "
         "dyeing and carding with teasels. Guided demonstration."),
        ("سوق الشواشية: الشاشية التونسية",
         "في سوق الشواشية يصنع آخر الحِرفيين الشاشية الحمراء: الحياكة والتلبيد والصباغة "
         "والتمشيط بالكَرْداش. عرض مع شرح."),
        jours=(0, 1, 2, 3, 4, 5)),
    act("Tunis", "port de Sidi Bou Saïd", 36.8668, 10.3518, "Mer", 110, 180, ["10:00", "15:00"], 8,
        ("Sortie en voilier dans le golfe de Tunis",
         "Trois heures à la voile au départ du port de plaisance de Sidi Bou Saïd, avec vue sur "
         "le village bleu et blanc et arrêt baignade selon la météo."),
        ("Sailing trip in the Gulf of Tunis",
         "Three hours under sail from the Sidi Bou Saïd marina, with views of the blue-and-white "
         "village and a swimming stop depending on the weather."),
        ("رحلة بالمركب الشراعي في خليج تونس",
         "ثلاث ساعات من الإبحار انطلاقًا من ميناء سيدي بو سعيد الترفيهي، مع إطلالة على القرية "
         "الزرقاء والبيضاء وتوقّف للسباحة حسب الطقس.")),
    act("Tunis", "La Marsa", 36.9103, 10.3155, "Mer", 45, 90, ["09:00", "16:00"], 8,
        ("Stand-up paddle à la plage de La Marsa",
         "Initiation au paddle sur la plage de La Marsa, au nord de Tunis, avec un moniteur. "
         "Planche, pagaie et gilet fournis ; sortie annulée si la mer est agitée."),
        ("Stand-up paddle at La Marsa beach",
         "Paddleboarding lesson on La Marsa beach, north of Tunis, with an instructor. "
         "Board, paddle and life jacket provided; cancelled in rough seas."),
        ("التجديف وقوفًا في شاطئ المرسى",
         "درس تجديف وقوفًا في شاطئ المرسى شمال تونس مع مدرّب. "
         "اللوح والمجداف والسترة متوفّرة؛ تُلغى الخرجة إذا كان البحر هائجًا.")),
    act("Tunis", "Carthage", 36.8545, 10.3338, "Aventure", 55, 210, ["09:00"], 10,
        ("Carthage à vélo, des thermes d'Antonin à Sidi Bou Saïd",
         "Les sites de Carthage à vélo à assistance électrique : thermes d'Antonin, villas "
         "romaines, ports puniques, puis montée jusqu'à Sidi Bou Saïd. Casque fourni."),
        ("Carthage by bike, from the Antonine Baths to Sidi Bou Saïd",
         "Carthage's sites by e-bike: the Antonine Baths, Roman villas, Punic ports, then the "
         "ride up to Sidi Bou Saïd. Helmet provided."),
        ("قرطاج على الدرّاجة، من حمّامات أنطونيوس إلى سيدي بو سعيد",
         "مواقع قرطاج على درّاجة بمساعدة كهربائية: حمّامات أنطونيوس والفيلات الرومانية والموانئ "
         "البونية، ثم الصعود إلى سيدي بو سعيد. الخوذة متوفّرة.")),
    act("Tunis", "Boukornine", 36.6712, 10.3757, "Aventure", 40, 240, ["08:30"], 15,
        ("Randonnée au parc national de Boukornine",
         "Montée vers les deux cornes du djebel Boukornine (576 m) entre pins d'Alep et "
         "oliviers sauvages, avec vue sur tout le golfe de Tunis. Niveau moyen."),
        ("Hike in Boukornine National Park",
         "Climb towards the twin peaks of Jebel Boukornine (576 m) through Aleppo pines and "
         "wild olive trees, with views over the whole Gulf of Tunis. Moderate level."),
        ("مشي في الحديقة الوطنية ببوقرنين",
         "صعود نحو قرنَي جبل بوقرنين (576 م) بين الصنوبر الحلبي والزيتون البرّي، "
         "مع إطلالة على كامل خليج تونس. مستوى متوسط."),
        jours=(5, 6)),
    act("Tunis", "Médina", 36.7987, 10.1717, "Gastronomie", 95, 180, ["10:00"], 8,
        ("Cours de cuisine tunisienne : couscous et brik",
         "Marché dans les souks, puis préparation d'un couscous à l'agneau, d'une brik et d'une "
         "salade méchouia dans une maison de la médina. Repas partagé."),
        ("Tunisian cooking class: couscous and brik",
         "Shop in the souks, then cook lamb couscous, brik and mechouia salad in a medina "
         "house. Shared meal."),
        ("درس الطبخ التونسي: الكسكسي والبريك",
         "تسوّق في الأسواق، ثم تحضير كسكسي بلحم العلّوش وبريك وسلطة مشوية في دار بالمدينة "
         "العتيقة. وجبة مشتركة.")),
    act("Tunis", "Sidi Bou Saïd", 36.8711, 10.3491, "Gastronomie", 20, 60, ["10:00", "16:00"], 12,
        ("Bambalouni et thé aux pignons à Sidi Bou Saïd",
         "Le beignet sucré bambalouni, frit à la minute dans la rue principale, puis un thé aux "
         "pignons en terrasse face à la mer. Courte balade commentée dans le village."),
        ("Bambalouni and pine-nut tea in Sidi Bou Saïd",
         "The sweet bambalouni doughnut, fried to order on the main street, then pine-nut tea "
         "on a terrace facing the sea. Short guided stroll through the village."),
        ("بمبالوني وشاي بالبندق في سيدي بو سعيد",
         "حلوى البمبالوني المقلية في الحين في الشارع الرئيسي، ثم شاي بالبندق في شرفة مطلّة "
         "على البحر. جولة قصيرة مع شرح في القرية.")),
    act("Tunis", "Marché central", 36.7974, 10.1773, "Gastronomie", 45, 120, ["08:30"], 10,
        ("Visite gourmande du marché central de Tunis",
         "Halles aux poissons, épices, olives et harissa du marché central, avec dégustations "
         "de produits de saison et explications sur la cuisine tunisienne du quotidien."),
        ("Food tour of the Tunis central market",
         "Fish halls, spices, olives and harissa at the central market, with tastings of "
         "seasonal produce and insights into everyday Tunisian cooking."),
        ("جولة تذوّق في السوق المركزية بتونس",
         "أجنحة السمك والتوابل والزيتون والهريسة في السوق المركزية، مع تذوّق منتجات الموسم "
         "وشرح عن المطبخ التونسي اليومي."),
        jours=SAUF_LUNDI),
    act("Tunis", "départ du centre-ville", 36.7999, 10.1868, "Culture", 170, 600, ["07:30"], 16,
        ("Excursion d'une journée à Dougga",
         "Dougga, cité romaine inscrite à l'UNESCO et l'une des mieux conservées d'Afrique du "
         "Nord : capitole, théâtre et mausolée libyco-punique. Transport et déjeuner inclus."),
        ("Day trip to Dougga",
         "Dougga, a UNESCO-listed Roman town and one of the best preserved in North Africa: "
         "capitol, theatre and Libyco-Punic mausoleum. Transport and lunch included."),
        ("رحلة يوم إلى دقّة",
         "دقّة مدينة رومانية مدرجة في قائمة اليونسكو ومن أفضل المدن المحفوظة في شمال إفريقيا: "
         "الكابيتول والمسرح والضريح الليبي البوني. النقل والغداء مشمولان."),
        jours=(2, 5)),
    # ------------------------------------------------------------------
    # Sousse / Monastir (14)
    # ------------------------------------------------------------------
    act("Sousse", "Médina", 35.8275, 10.6390, "Culture", 30, 150, ["09:00", "14:30"], 15,
        ("Médina de Sousse : Grande Mosquée et Ribat",
         "La médina inscrite à l'UNESCO : la Grande Mosquée du IXe siècle, puis le Ribat, "
         "forteresse-monastère dont la tour offre une vue sur la ville et le port."),
        ("Sousse medina: Great Mosque and Ribat",
         "The UNESCO-listed medina: the 9th-century Great Mosque, then the Ribat, a fortified "
         "monastery whose tower overlooks the city and the port."),
        ("مدينة سوسة العتيقة: الجامع الكبير والرباط",
         "المدينة المدرجة في قائمة اليونسكو: الجامع الكبير من القرن التاسع، ثم الرباط، "
         "الحصن الذي يطلّ برجه على المدينة والميناء.")),
    act("Sousse", "Kasbah", 35.8231, 10.6356, "Culture", 25, 90, ["10:00", "14:00"], 20,
        ("Musée archéologique de Sousse",
         "Dans la Kasbah, la deuxième collection de mosaïques du pays après le Bardo : "
         "scènes marines, Méduse et triomphe de Bacchus."),
        ("Sousse Archaeological Museum",
         "Inside the Kasbah, the country's second-largest mosaic collection after the Bardo: "
         "sea scenes, Medusa and the triumph of Bacchus."),
        ("المتحف الأثري بسوسة",
         "داخل القصبة، ثاني أكبر مجموعة فسيفساء في البلاد بعد باردو: "
         "مشاهد بحرية وميدوزا وانتصار باخوس."),
        jours=SAUF_LUNDI),
    act("Sousse", "Catacombes", 35.8181, 10.6264, "Culture", 20, 60, ["10:00", "15:00"], 15,
        ("Catacombes de Sousse",
         "Galeries funéraires paléochrétiennes creusées entre le IIe et le IVe siècle, dont la "
         "catacombe du Bon Pasteur, ouverte aux visiteurs."),
        ("Catacombs of Sousse",
         "Early Christian burial galleries dug between the 2nd and 4th centuries, including the "
         "Catacomb of the Good Shepherd, open to visitors."),
        ("سراديب سوسة",
         "أروقة دفن مسيحية مبكّرة حُفرت بين القرنين الثاني والرابع، ومنها سرداب "
         "الراعي الصالح المفتوح للزوّار."),
        jours=SAUF_LUNDI),
    act("Sousse", "départ de la médina", 35.8249, 10.6375, "Culture", 110, 360, ["08:00"], 20,
        ("Excursion à l'amphithéâtre d'El Jem",
         "L'amphithéâtre romain d'El Jem, inscrit à l'UNESCO, pouvait accueillir 35 000 "
         "spectateurs. Visite guidée de l'arène et des souterrains, transport inclus."),
        ("Trip to the El Jem amphitheatre",
         "The UNESCO-listed Roman amphitheatre of El Jem could seat 35,000 spectators. "
         "Guided tour of the arena and the underground passages, transport included."),
        ("رحلة إلى قصر الجمّ",
         "المسرح الروماني بالجمّ، المدرج في قائمة اليونسكو، كان يتّسع لـ35 ألف متفرّج. "
         "زيارة مصحوبة للحلبة والأقبية، والنقل مشمول."),
        jours=(0, 2, 4, 6)),
    act("Monastir", "Ribat", 35.7762, 10.8329, "Culture", 25, 120, ["09:30", "14:30"], 15,
        ("Ribat de Monastir et médina",
         "Le ribat de Harthema, fondé en 796, décor de nombreux films, puis les ruelles de la "
         "médina de Monastir jusqu'à la Grande Mosquée."),
        ("Ribat of Monastir and the medina",
         "The Ribat of Harthema, founded in 796 and a backdrop for many films, then the lanes of "
         "Monastir's medina up to the Great Mosque."),
        ("رباط المنستير والمدينة العتيقة",
         "رباط هرثمة الذي تأسّس سنة 796 وصُوّرت فيه أفلام عديدة، ثم أزقة المدينة العتيقة "
         "بالمنستير حتى الجامع الكبير.")),
    act("Monastir", "Mausolée Bourguiba", 35.7777, 10.8284, "Culture", 15, 60, ["10:00", "15:00"], 20,
        ("Mausolée Habib Bourguiba",
         "Le mausolée du premier président de la Tunisie, avec ses coupoles dorées et ses "
         "minarets jumeaux, et une salle consacrée à son parcours."),
        ("Habib Bourguiba Mausoleum",
         "The mausoleum of Tunisia's first president, with its golden domes and twin minarets, "
         "and a room devoted to his life."),
        ("ضريح الحبيب بورقيبة",
         "ضريح أول رئيس للجمهورية التونسية بقببه الذهبية ومئذنتيه التوأمين، "
         "وقاعة مخصّصة لمسيرته.")),
    act("Sousse", "Port El Kantaoui", 35.8939, 10.5984, "Mer", 55, 240, ["10:00"], 40,
        ("Bateau pirate au départ de Port El Kantaoui",
         "Croisière côtière en galion décoré, avec baignade en pleine mer, déjeuner à bord et "
         "animation pour les enfants. Retour au port en milieu d'après-midi."),
        ("Pirate boat from Port El Kantaoui",
         "Coastal cruise on a decorated galleon, with a swim in open water, lunch on board and "
         "entertainment for children. Back at the port mid-afternoon."),
        ("مركب القراصنة من ميناء القنطاوي",
         "رحلة ساحلية على سفينة مزيّنة، مع سباحة في عرض البحر وغداء على متنها وتنشيط "
         "للأطفال. العودة إلى الميناء في منتصف الظهيرة.")),
    act("Sousse", "Port El Kantaoui", 35.8939, 10.5984, "Mer", 140, 180, ["09:00", "14:00"], 6,
        ("Baptême de plongée à Port El Kantaoui",
         "Première plongée encadrée au large d'El Kantaoui : poissons de roche, posidonies et "
         "parfois des mérous. Équipement complet fourni, dès 10 ans."),
        ("Discover scuba diving in Port El Kantaoui",
         "A supervised first dive off El Kantaoui: rock fish, seagrass and sometimes groupers. "
         "Full equipment provided, from age 10."),
        ("غطسة تجريبية في ميناء القنطاوي",
         "أول غطسة مؤطّرة قبالة القنطاوي: أسماك الصخور وأعشاب البوسيدونيا وأحيانًا الميرو. "
         "المعدّات كاملة متوفّرة، ابتداءً من 10 سنوات.")),
    act("Sousse", "Port El Kantaoui", 35.8939, 10.5984, "Mer", 80, 30, ["10:00", "11:00", "15:00", "16:00"], 4,
        ("Jet-ski à Port El Kantaoui",
         "Trente minutes de jet-ski en zone balisée au large de la marina, après un briefing de "
         "sécurité. Gilet fourni, passager possible."),
        ("Jet ski in Port El Kantaoui",
         "Thirty minutes of jet ski in a marked zone off the marina, after a safety briefing. "
         "Life jacket provided, passenger allowed."),
        ("جت سكي في ميناء القنطاوي",
         "ثلاثون دقيقة من الجت سكي في منطقة محدّدة قبالة المرسى بعد شرح للسلامة. "
         "السترة متوفّرة ويمكن اصطحاب راكب.")),
    act("Monastir", "port de Monastir", 35.7802, 10.8316, "Mer", 90, 420, ["08:30"], 30,
        ("Sortie en mer aux îles Kuriat",
         "Traversée vers les îles Kuriat, réserve naturelle où pondent les tortues caouannes : "
         "eau turquoise, baignade et déjeuner de poisson. Débarquement encadré."),
        ("Boat trip to the Kuriat Islands",
         "Crossing to the Kuriat Islands, a nature reserve where loggerhead turtles nest: "
         "turquoise water, swimming and a fish lunch. Supervised landing."),
        ("رحلة بحرية إلى جزر قوريا",
         "عبور نحو جزر قوريا، المحمية الطبيعية التي تبيض فيها السلاحف البحرية ضخمة الرأس: "
         "مياه فيروزية وسباحة وغداء سمك. نزول مؤطّر.")),
    act("Sousse", "Chott Meriem", 35.9270, 10.5669, "Aventure", 55, 90, ["09:00", "16:00"], 6,
        ("Balade à cheval à Chott Meriem",
         "Promenade équestre entre plage et oliveraies au nord de Sousse, au pas et au trot. "
         "Chevaux calmes adaptés aux débutants, bombe fournie."),
        ("Horse ride in Chott Meriem",
         "A horse ride between the beach and olive groves north of Sousse, at walk and trot. "
         "Calm horses suited to beginners, riding helmet provided."),
        ("جولة على الخيل في شط مريم",
         "نزهة على الخيل بين الشاطئ وغابات الزيتون شمال سوسة. "
         "خيول هادئة مناسبة للمبتدئين، والخوذة متوفّرة.")),
    act("Monastir", "Skanes", 35.7660, 10.7774, "Aventure", 40, 150, ["09:00", "16:00"], 10,
        ("De Skanes à la médina de Monastir à vélo",
         "Itinéraire plat le long de la corniche, de la zone de Skanes jusqu'au ribat et à la "
         "marina de Monastir. Vélo, casque et pause boisson inclus."),
        ("From Skanes to the Monastir medina by bike",
         "A flat route along the corniche from Skanes to the ribat and marina of Monastir. "
         "Bike, helmet and drinks stop included."),
        ("من صقانص إلى مدينة المنستير على الدرّاجة",
         "مسار مستوٍ على طول الكورنيش من صقانص إلى الرباط ومرسى المنستير. "
         "الدرّاجة والخوذة واستراحة مشروب مشمولة.")),
    act("Sousse", "Médina", 35.8249, 10.6375, "Gastronomie", 85, 180, ["10:00"], 8,
        ("Cours de cuisine du Sahel tunisien",
         "Couscous au poisson, slata méchouia et makroudh : les recettes du Sahel préparées avec "
         "une cuisinière de Sousse, puis partagées autour de la table."),
        ("Sahel cooking class",
         "Fish couscous, slata mechouia and makroudh: Sahel recipes cooked with a cook from "
         "Sousse, then shared around the table."),
        ("درس طبخ ساحلي",
         "كسكسي بالسمك وسلطة مشوية ومقروض: وصفات الساحل تُحضَّر مع طبّاخة من سوسة "
         "ثم تُتقاسم حول المائدة.")),
    act("Monastir", "centre-ville", 35.7708, 10.8281, "Gastronomie", 35, 90, ["15:00"], 12,
        ("Dégustation d'huile d'olive du Sahel",
         "Le Sahel est la grande région oléicole du pays : dégustation commentée de plusieurs "
         "huiles vierges extra, avec pain, olives et harissa."),
        ("Sahel olive-oil tasting",
         "The Sahel is the country's great olive-growing region: guided tasting of several "
         "extra-virgin oils, with bread, olives and harissa."),
        ("تذوّق زيت زيتون الساحل",
         "الساحل هو أكبر منطقة لزراعة الزيتون في البلاد: تذوّق مع شرح لعدّة زيوت بكر ممتازة، "
         "مع الخبز والزيتون والهريسة.")),
    # ------------------------------------------------------------------
    # Hammamet (12)
    # ------------------------------------------------------------------
    act("Hammamet", "Médina", 36.3990, 10.6130, "Culture", 25, 120, ["09:30", "16:00"], 15,
        ("Médina et Kasbah de Hammamet",
         "Les remparts de la médina au bord de l'eau, la Kasbah et son chemin de ronde, puis les "
         "ruelles blanches jusqu'au cimetière marin."),
        ("Hammamet medina and Kasbah",
         "The medina walls by the sea, the Kasbah and its rampart walk, then the white lanes "
         "down to the seaside cemetery."),
        ("مدينة الحمامات العتيقة والقصبة",
         "أسوار المدينة على حافة الماء، والقصبة وممشاها فوق الأسوار، ثم الأزقة البيضاء "
         "حتى المقبرة البحرية.")),
    act("Hammamet", "Centre culturel international", 36.4043, 10.5898, "Culture", 20, 90, ["10:00", "15:00"], 20,
        ("Dar Sebastian et le Centre culturel international",
         "La villa construite dans les années 1920 par George Sebastian, son jardin et son "
         "théâtre en plein air, aujourd'hui Centre culturel international de Hammamet."),
        ("Dar Sebastian and the International Cultural Centre",
         "The villa built in the 1920s by George Sebastian, its garden and open-air theatre, "
         "now the International Cultural Centre of Hammamet."),
        ("دار سيباستيان والمركز الثقافي الدولي",
         "الفيلا التي شيّدها جورج سيباستيان في عشرينيات القرن الماضي وحديقتها ومسرحها "
         "الصيفي، وهي اليوم المركز الثقافي الدولي بالحمامات.")),
    act("Hammamet", "Pupput", 36.3932, 10.5619, "Culture", 15, 75, ["09:00", "15:00"], 15,
        ("Site archéologique de Pupput",
         "Les vestiges de Pupput, ville romaine devenue colonie au IIe siècle : maisons à "
         "mosaïques, thermes et nécropole, à deux pas des hôtels."),
        ("Pupput archaeological site",
         "The remains of Pupput, a Roman town made a colony in the 2nd century: houses with "
         "mosaics, baths and a necropolis, close to the hotels."),
        ("موقع بوبوت الأثري",
         "آثار بوبوت، المدينة الرومانية التي صارت مستعمرة في القرن الثاني: بيوت بالفسيفساء "
         "وحمّامات ومقبرة، على بعد خطوات من النزل.")),
    act("Hammamet", "départ de la médina", 36.3990, 10.6130, "Culture", 40, 240, ["08:30"], 16,
        ("Marché du vendredi et poterie de Nabeul",
         "Nabeul, à 15 minutes, capitale de la poterie et de la céramique : marché du vendredi, "
         "ateliers de potiers et boutiques de céramique peinte. Transport inclus."),
        ("Nabeul Friday market and pottery",
         "Nabeul, 15 minutes away, capital of pottery and ceramics: Friday market, potters' "
         "workshops and painted-ceramic shops. Transport included."),
        ("سوق الجمعة وفخّار نابل",
         "نابل، على بعد 15 دقيقة، عاصمة الفخّار والخزف: سوق الجمعة وورشات الفخّارين "
         "ومحلات الخزف المرسوم. النقل مشمول."),
        jours=(4,)),
    act("Hammamet", "départ de la médina", 36.3990, 10.6130, "Culture", 120, 540, ["08:00"], 16,
        ("Excursion à Kerkouane et au fort de Kélibia",
         "Kerkouane, seule cité punique conservée telle qu'abandonnée, inscrite à l'UNESCO, "
         "puis le fort de Kélibia dominant la mer. Transport et déjeuner inclus."),
        ("Trip to Kerkouane and Kelibia fort",
         "Kerkouane, the only Punic city preserved as it was abandoned, UNESCO-listed, then "
         "Kelibia fort overlooking the sea. Transport and lunch included."),
        ("رحلة إلى كركوان وحصن قليبية",
         "كركوان، المدينة البونية الوحيدة المحفوظة كما هُجرت والمدرجة في قائمة اليونسكو، "
         "ثم حصن قليبية المطلّ على البحر. النقل والغداء مشمولان."),
        jours=(1, 5)),
    act("Hammamet", "Yasmine Hammamet", 36.3747, 10.5411, "Mer", 55, 240, ["10:00"], 40,
        ("Bateau pirate à Yasmine Hammamet",
         "Croisière en galion au départ de la marina de Yasmine, baignade au large, déjeuner "
         "grillé à bord et animation. Retour en milieu d'après-midi."),
        ("Pirate boat in Yasmine Hammamet",
         "Galleon cruise from the Yasmine marina, swimming offshore, grilled lunch on board and "
         "entertainment. Back mid-afternoon."),
        ("مركب القراصنة في ياسمين الحمامات",
         "رحلة على سفينة من مرسى ياسمين، وسباحة في عرض البحر وغداء مشوي على متنها وتنشيط. "
         "العودة في منتصف الظهيرة.")),
    act("Hammamet", "plage de Yasmine", 36.3699, 10.5392, "Mer", 70, 20, ["10:30", "12:00", "15:30"], 2,
        ("Parachute ascensionnel à Yasmine Hammamet",
         "Vol tracté par bateau au-dessus de la baie de Hammamet, seul ou à deux, décollage "
         "depuis le bateau. Gilet et harnais fournis."),
        ("Parasailing in Yasmine Hammamet",
         "A boat-towed flight over the Bay of Hammamet, solo or tandem, take-off from the boat. "
         "Life jacket and harness provided."),
        ("المظلّة البحرية في ياسمين الحمامات",
         "تحليق مقطور بالمركب فوق خليج الحمامات، فرديًا أو ثنائيًا، والإقلاع من المركب. "
         "السترة والحزام متوفّران.")),
    act("Hammamet", "Yasmine Hammamet", 36.3747, 10.5411, "Mer", 140, 180, ["09:00"], 6,
        ("Baptême de plongée à Hammamet",
         "Première plongée dans le golfe de Hammamet avec un moniteur certifié, à faible "
         "profondeur. Équipement complet fourni, dès 10 ans."),
        ("Discover scuba diving in Hammamet",
         "A first dive in the Gulf of Hammamet with a certified instructor, at shallow depth. "
         "Full equipment provided, from age 10."),
        ("غطسة تجريبية في الحمامات",
         "أول غطسة في خليج الحمامات مع مدرّب معتمد، على عمق قليل. "
         "المعدّات كاملة متوفّرة، ابتداءً من 10 سنوات.")),
    act("Hammamet", "Carthage Land", 36.3695, 10.5348, "Aventure", 45, 300, ["10:00"], 50,
        ("Journée au parc Carthage Land",
         "Parc d'attractions sur le thème de Carthage à Yasmine Hammamet : manèges, montagnes "
         "russes et attractions aquatiques pour tous les âges. Entrée incluse."),
        ("Day at Carthage Land park",
         "A Carthage-themed amusement park in Yasmine Hammamet: rides, roller coasters and water "
         "attractions for all ages. Entry included."),
        ("يوم في مدينة الألعاب قرطاج لاند",
         "مدينة ألعاب بطابع قرطاجي في ياسمين الحمامات: ألعاب دوّارة وقطار الأفعوانية وألعاب "
         "مائية لكل الأعمار. الدخول مشمول."),
        jours=(5, 6)),
    act("Hammamet", "plage de Jinene", 36.3928, 10.5660, "Aventure", 55, 90, ["09:00", "16:00"], 6,
        ("Balade à cheval entre plage et orangeraies",
         "Promenade équestre de la plage de Hammamet vers les vergers d'agrumes de l'arrière-pays. "
         "Chevaux adaptés aux débutants, bombe fournie."),
        ("Horse ride between beach and orange groves",
         "A horse ride from Hammamet beach towards the citrus orchards inland. "
         "Horses suited to beginners, riding helmet provided."),
        ("جولة على الخيل بين الشاطئ وبساتين البرتقال",
         "نزهة على الخيل من شاطئ الحمامات نحو بساتين القوارص في الداخل. "
         "خيول مناسبة للمبتدئين، والخوذة متوفّرة.")),
    act("Hammamet", "Médina", 36.3990, 10.6130, "Gastronomie", 90, 180, ["10:00"], 8,
        ("Cours de cuisine du Cap Bon : couscous au poisson et harissa",
         "Préparez une harissa maison au piment du Cap Bon et un couscous au poisson avec une "
         "cuisinière de Hammamet, puis passez à table."),
        ("Cap Bon cooking class: fish couscous and harissa",
         "Make homemade harissa with Cap Bon chillies and a fish couscous with a cook from "
         "Hammamet, then sit down to eat."),
        ("درس طبخ الوطن القبلي: كسكسي بالسمك وهريسة",
         "حضّر هريسة منزلية بفلفل الوطن القبلي وكسكسي بالسمك مع طبّاخة من الحمامات، "
         "ثم اجلس إلى المائدة.")),
    act("Hammamet", "Nabeul", 36.4513, 10.7356, "Gastronomie", 35, 120, ["10:00", "15:00"], 12,
        ("Dégustation de harissa et produits du Cap Bon à Nabeul",
         "Harissa, piments séchés, eau de fleur d'oranger et épices : la région de Nabeul en "
         "dégustation commentée, avec conseils pour cuisiner au retour."),
        ("Harissa and Cap Bon produce tasting in Nabeul",
         "Harissa, dried chillies, orange-blossom water and spices: the Nabeul region in a guided "
         "tasting, with tips for cooking back home."),
        ("تذوّق الهريسة ومنتجات الوطن القبلي في نابل",
         "هريسة وفلفل مجفّف وماء الزهر وتوابل: جهة نابل في جلسة تذوّق مع شرح، "
         "ونصائح للطبخ عند العودة.")),
    # ------------------------------------------------------------------
    # Tozeur (12)
    # ------------------------------------------------------------------
    act("Tozeur", "Ouled El Hadef", 33.9180, 8.1300, "Culture", 25, 120, ["09:00", "16:00"], 15,
        ("Quartier Ouled El Hadef et ses façades de briques",
         "La vieille ville de Tozeur et ses façades en briques d'argile crue dessinant des "
         "motifs géométriques, héritage du XIVe siècle. Balade guidée à pied."),
        ("Ouled El Hadef quarter and its brick façades",
         "Tozeur's old town and its façades of sun-dried clay bricks forming geometric patterns, "
         "a 14th-century heritage. Guided walking tour."),
        ("حيّ أولاد الهادف وواجهاته الآجرّية",
         "مدينة توزر القديمة وواجهاتها من الآجرّ الطيني المجفّف التي ترسم أشكالًا هندسية، "
         "إرث من القرن الرابع عشر. جولة مشي مصحوبة.")),
    act("Tozeur", "Dar Cherait", 33.9132, 8.1206, "Culture", 20, 90, ["10:00", "15:00"], 20,
        ("Musée Dar Cherait",
         "Un musée d'arts et traditions installé dans une demeure de style traditionnel : "
         "costumes, bijoux et scènes de la vie tunisienne d'autrefois."),
        ("Dar Cherait Museum",
         "A folk-arts museum in a traditional-style mansion: costumes, jewellery and scenes "
         "of Tunisian life in the past."),
        ("متحف دار شريّط",
         "متحف للفنون والتقاليد في دار على الطراز التقليدي: أزياء وحُليّ "
         "ومشاهد من الحياة التونسية قديمًا.")),
    act("Tozeur", "Nefta", 33.8780, 7.8745, "Culture", 45, 180, ["09:00"], 12,
        ("Nefta : la Corbeille et les zaouïas",
         "Nefta, haut lieu du soufisme, et sa Corbeille, cuvette de palmiers entourée de "
         "coupoles de zaouïas. Visite guidée de la ville et belvédère."),
        ("Nefta: the Corbeille and the zaouias",
         "Nefta, a centre of Sufism, and its Corbeille, a palm-filled hollow ringed by zaouia "
         "domes. Guided tour of the town and viewpoint."),
        ("نفطة: السلّة والزوايا",
         "نفطة، معقل من معاقل التصوّف، و«سلّتها» المنخفض المليء بالنخيل والمحاط بقباب "
         "الزوايا. زيارة مصحوبة للمدينة ونقطة مشاهدة.")),
    act("Tozeur", "palmeraie", 33.9116, 8.1374, "Désert", 30, 60, ["09:00", "10:30", "15:00", "16:30"], 4,
        ("Calèche dans la palmeraie de Tozeur",
         "Une heure en calèche sous les palmiers dattiers, entre canaux d'irrigation et jardins "
         "étagés (palmiers, arbres fruitiers, cultures)."),
        ("Horse-carriage ride in the Tozeur palm grove",
         "One hour by carriage under the date palms, past irrigation channels and layered "
         "gardens (palms, fruit trees, crops)."),
        ("جولة بالكرّيطة في واحة توزر",
         "ساعة في عربة تجرّها الخيول تحت نخيل التمر، بين سواقي الري والبساتين المتدرّجة "
         "(نخيل وأشجار مثمرة ومزروعات).")),
    act("Tozeur", "départ du centre-ville", 33.9239, 8.1371, "Désert", 120, 360, ["08:00"], 6,
        ("Oasis de montagne en 4x4 : Chebika, Tamerza et Mides",
         "Les trois oasis de montagne près de la frontière algérienne : source et cascade de "
         "Chebika, vieux village de Tamerza et canyon de Mides. 4x4 avec chauffeur."),
        ("Mountain oases by 4x4: Chebika, Tamerza and Mides",
         "The three mountain oases near the Algerian border: Chebika's spring and waterfall, "
         "old Tamerza village and the Mides canyon. 4x4 with driver."),
        ("الواحات الجبلية بسيارة رباعية الدفع: الشبيكة وتمغزة وميداس",
         "الواحات الجبلية الثلاث قرب الحدود الجزائرية: عين الشبيكة وشلالها، وقرية تمغزة "
         "القديمة، وأخدود ميداس. سيارة رباعية الدفع مع سائق.")),
    act("Tozeur", "départ du centre-ville", 33.9239, 8.1371, "Désert", 70, 180, ["05:45"], 6,
        ("Lever du soleil sur le Chott el-Jérid",
         "Traversée du plus grand lac salé du Maghreb au petit matin, quand les cristaux de sel "
         "rosissent et que les mirages apparaissent. Thé chaud sur place."),
        ("Sunrise over the Chott el-Jerid",
         "Cross the largest salt lake in the Maghreb at dawn, when the salt crystals turn pink "
         "and mirages appear. Hot tea on site."),
        ("شروق الشمس على شطّ الجريد",
         "عبور أكبر بحيرة ملحية في المغرب العربي في الصباح الباكر، حين تتلوّن بلّورات الملح "
         "بالوردي وتظهر السراب. شاي ساخن في المكان.")),
    act("Tozeur", "Ong Jemel", 34.0161, 7.9123, "Désert", 80, 240, ["14:00"], 6,
        ("Décors de Star Wars et rocher d'Ong Jemel",
         "Le rocher en « cou de chameau » d'Ong Jemel et le village de Mos Espa construit pour "
         "Star Wars, au milieu des dunes. Coucher de soleil sur place."),
        ("Star Wars sets and the Ong Jemel rock",
         "The \"camel's neck\" rock of Ong Jemel and the Mos Espa village built for Star Wars, "
         "among the dunes. Sunset on site."),
        ("ديكورات «حرب النجوم» وصخرة عنق الجمل",
         "صخرة «عنق الجمل» وقرية موس إسبا التي بُنيت لفيلم «حرب النجوم» وسط الكثبان. "
         "مشاهدة الغروب في المكان.")),
    act("Tozeur", "Belvédère", 33.9088, 8.1107, "Désert", 45, 90, ["16:30"], 10,
        ("Balade à dromadaire au coucher du soleil à Tozeur",
         "Au pied des rochers du Belvédère, une balade à dromadaire en lisière de désert, "
         "face à la palmeraie qui s'embrase au soleil couchant."),
        ("Sunset camel ride in Tozeur",
         "At the foot of the Belvédère rocks, a camel ride on the edge of the desert, "
         "facing the palm grove glowing in the setting sun."),
        ("جولة على ظهر الجمل عند الغروب في توزر",
         "عند سفح صخور البلفدير، جولة على ظهر الجمل على تخوم الصحراء، "
         "قبالة الواحة المتوهّجة عند غروب الشمس.")),
    act("Tozeur", "départ du centre-ville", 33.9239, 8.1371, "Aventure", 100, 120, ["09:00", "15:00"], 6,
        ("Quad dans les dunes autour de Tozeur",
         "Pistes sablonneuses et petites dunes au guidon d'un quad, avec pause thé dans le "
         "désert. Briefing, casque et chèche fournis ; conducteur dès 16 ans."),
        ("Quad biking in the dunes around Tozeur",
         "Sandy tracks and small dunes on a quad bike, with a tea break in the desert. "
         "Briefing, helmet and chech scarf provided; drivers from age 16."),
        ("الكواد في الكثبان حول توزر",
         "مسالك رملية وكثبان صغيرة على متن الكواد، مع استراحة شاي في الصحراء. "
         "شرح مسبق وخوذة وشاش متوفّرة؛ السائق من 16 سنة.")),
    act("Tozeur", "Mides", 34.4117, 7.9275, "Aventure", 60, 180, ["09:00"], 10,
        ("Randonnée dans les gorges de Mides",
         "Marche au fond et sur les rebords du canyon de Mides, avec vue sur le village "
         "abandonné perché au-dessus des gorges. Niveau moyen, chaussures fermées."),
        ("Hike in the Mides gorges",
         "Walk along the bottom and the rims of the Mides canyon, with views of the abandoned "
         "village perched above the gorges. Moderate level, closed shoes."),
        ("مشي في أخدود ميداس",
         "مسيرة في قاع أخدود ميداس وعلى حوافّه، مع إطلالة على القرية المهجورة المعلّقة "
         "فوق الأخدود. مستوى متوسط، أحذية مغلقة."),
        jours=(1, 3, 5, 6)),
    act("Tozeur", "palmeraie", 33.9116, 8.1374, "Gastronomie", 30, 90, ["10:00", "15:00"], 12,
        ("Dégustation de dattes Deglet Nour dans une palmeraie",
         "En pleine saison de récolte, découvrez la pollinisation et la cueillette des dattes, "
         "puis dégustez Deglet Nour et autres variétés avec du lait fermenté (leben)."),
        ("Deglet Nour date tasting in a palm grove",
         "In the harvest season, learn about date pollination and picking, then taste Deglet "
         "Nour and other varieties with fermented milk (leben)."),
        ("تذوّق دقلة النور في واحة",
         "في موسم الجني، اكتشف تلقيح النخيل وجني التمور، ثم تذوّق دقلة النور وأصنافًا أخرى "
         "مع اللبن.")),
    act("Tozeur", "palmeraie", 33.9116, 8.1374, "Gastronomie", 45, 120, ["17:00"], 10,
        ("Atelier khobz mella, le pain cuit dans le sable",
         "Le pain des nomades du Sud : pâte pétrie à la main puis enfouie sous le sable et les "
         "braises. Dégusté chaud avec huile d'olive et thé."),
        ("Khobz mella workshop: bread baked in the sand",
         "The bread of southern nomads: hand-kneaded dough buried under sand and embers. "
         "Eaten hot with olive oil and tea."),
        ("ورشة خبز المِلّة المطهوّ في الرمل",
         "خبز رُحّل الجنوب: عجين يُعجن باليد ثم يُدفن تحت الرمل والجمر. "
         "يؤكل ساخنًا مع زيت الزيتون والشاي.")),

    # ------------------------------------------------------------------
    # Ajout du 19/10/2026 — Bien-être (9). La Tunisie est l'une des grandes
    # destinations de thalassothérapie : les centres sont dans les hôtels des
    # zones touristiques, d'où un point de rendez-vous « zone » et aucun nom d'hôtel.
    # ------------------------------------------------------------------
    act("Djerba", "zone touristique de Midoun", 33.8293, 11.0403, "Bien-être", 150, 240, ["09:30", "14:00"], 8,
        ("Demi-journée thalasso à Djerba : parcours marin, hammam et enveloppement",
         "Parcours en bassin d'eau de mer chauffée, jets et hydromassage, puis hammam, gommage au "
         "savon noir et enveloppement aux algues. Peignoir et serviettes fournis. Idéal en solo "
         "ou en couple."),
        ("Half-day thalasso in Djerba: sea-water circuit, hammam and body wrap",
         "Heated sea-water pool circuit with jets and hydromassage, followed by hammam, black-soap "
         "scrub and seaweed wrap. Bathrobe and towels provided. Ideal solo or as a couple."),
        ("نصف يوم علاج بمياه البحر في جربة: مسار بحري وحمّام ولفّ بالطحالب",
         "مسار في حوض مياه بحر دافئة مع نفاثات وتدليك مائي، ثم حمّام وتقشير بالصابون الأسود "
         "ولفّ بالطحالب. يوفَّر رداء الحمّام والمناشف. مثالي للفرد أو للأزواج.")),
    act("Djerba", "Houmt Souk", 33.8760, 10.8572, "Bien-être", 40, 90, ["10:00", "15:00", "17:00"], 6,
        ("Hammam traditionnel et gommage au kassa à Houmt Souk",
         "Le rituel du hammam tunisien comme le pratiquent les Djerbiens : bain de vapeur, gommage "
         "au gant kassa et savon noir, thé à la menthe pour finir. Séances séparées femmes et hommes."),
        ("Traditional hammam and kessa scrub in Houmt Souk",
         "The Tunisian hammam ritual as Djerbans practise it: steam bath, kessa-glove scrub with "
         "black soap, and mint tea to finish. Separate sessions for women and men."),
        ("حمّام تقليدي وتكييس في حومة السوق",
         "طقوس الحمّام التونسي كما يمارسها أهل جربة: حمّام بخار، وتكييس بالكاسة والصابون "
         "الأسود، وكأس شاي بالنعناع في الختام. حصص منفصلة للنساء والرجال.")),
    act("Djerba", "Aghir", 33.7621, 11.0183, "Bien-être", 120, 60, ["17:00", "18:15"], 4,
        ("Massage en duo à l'huile d'argan à Aghir",
         "Une heure de massage relaxant côte à côte, à l'huile d'argan et à la fleur d'oranger, "
         "dans un spa face à la mer. Pensé pour les couples ; prix par personne."),
        ("Couples massage with argan oil in Aghir",
         "One hour of side-by-side relaxing massage with argan oil and orange blossom, in a spa "
         "facing the sea. Designed for couples; price per person."),
        ("تدليك ثنائي بزيت الأرغان في أغير",
         "ساعة من التدليك المريح جنبًا إلى جنب بزيت الأرغان وماء الزهر، في منتجع صحي مطلّ على "
         "البحر. مصمَّم للأزواج؛ السعر للشخص الواحد.")),
    act("Tunis", "Médina", 36.7976, 10.1712, "Bien-être", 55, 120, ["10:00", "16:00"], 6,
        ("Hammam et rituel de soins dans la médina de Tunis",
         "Dans un hammam de quartier de la médina : bain de vapeur, gommage, masque au tfal "
         "(argile) et massage court, puis thé dans une ancienne demeure. Accompagnement par une guide."),
        ("Hammam and beauty ritual in the Tunis medina",
         "In a neighbourhood hammam of the medina: steam bath, scrub, tfal clay mask and a short "
         "massage, then tea in an old house. Accompanied by a guide."),
        ("حمّام وطقوس عناية في مدينة تونس العتيقة",
         "في حمّام حيّ داخل المدينة العتيقة: حمّام بخار وتكييس وقناع بالطفل وتدليك قصير، ثم "
         "شاي في دار قديمة. برفقة مرشدة.")),
    act("Tunis", "Sidi Bou Saïd", 36.8711, 10.3491, "Bien-être", 35, 75, ["07:00"], 12,
        ("Yoga au lever du soleil face au golfe de Tunis",
         "Séance de yoga doux tous niveaux sur une terrasse de Sidi Bou Saïd qui domine le golfe, "
         "suivie d'un thé aux pignons. Tapis fournis ; parfait pour les voyageurs en solo."),
        ("Sunrise yoga overlooking the Gulf of Tunis",
         "Gentle all-levels yoga on a Sidi Bou Saïd terrace above the gulf, followed by pine-nut "
         "tea. Mats provided; perfect for solo travellers."),
        ("يوغا عند شروق الشمس مطلّة على خليج تونس",
         "حصة يوغا لطيفة لكل المستويات على سطح في سيدي بوسعيد يطلّ على الخليج، يليها شاي "
         "بالبندق. الحُصُر متوفّرة؛ مثالية للمسافرين بمفردهم."),
        jours=SAUF_LUNDI),
    act("Sousse", "Port El Kantaoui", 35.8939, 10.5984, "Bien-être", 140, 180, ["09:30", "14:30"], 8,
        ("Thalasso à Port El Kantaoui : bassin d'eau de mer et soins",
         "Bassin d'eau de mer chauffée, douche à jet, bain bouillonnant aux huiles essentielles et "
         "massage de 25 minutes, dans un centre de thalassothérapie de la station."),
        ("Thalasso in Port El Kantaoui: sea-water pool and treatments",
         "Heated sea-water pool, jet shower, essential-oil bubble bath and a 25-minute massage, in "
         "one of the resort's thalassotherapy centres."),
        ("علاج بمياه البحر في مرسى القنطاوي: حوض وعلاجات",
         "حوض مياه بحر دافئة ورشّ نفاث وحمّام فقاعات بالزيوت العطرية وتدليك لمدة 25 دقيقة، في "
         "أحد مراكز العلاج بمياه البحر في المنتجع.")),
    act("Monastir", "Skanes", 35.7637, 10.7295, "Bien-être", 130, 180, ["09:30", "14:30"], 8,
        ("Demi-journée de thalassothérapie à Skanes",
         "Affusion marine, bain hydromassant, enveloppement d'algues et accès libre au bassin "
         "d'eau de mer, dans un centre de la zone touristique de Skanes."),
        ("Half-day thalassotherapy in Skanes",
         "Sea-water affusion, hydromassage bath, seaweed wrap and free access to the sea-water "
         "pool, in a centre of the Skanes tourist zone."),
        ("نصف يوم علاج بمياه البحر في صقانص",
         "رشّ بمياه البحر وحمّام تدليك مائي ولفّ بالطحالب ودخول حرّ إلى حوض مياه البحر، في "
         "مركز بالمنطقة السياحية بصقانص.")),
    act("Hammamet", "Yasmine Hammamet", 36.3699, 10.5392, "Bien-être", 145, 180, ["09:30", "14:30"], 8,
        ("Thalasso et hammam à Yasmine Hammamet",
         "Parcours marin, hammam à l'eucalyptus, gommage et massage à l'huile d'olive du Cap Bon, "
         "dans un centre de thalasso de la station de Yasmine."),
        ("Thalasso and hammam in Yasmine Hammamet",
         "Sea-water circuit, eucalyptus hammam, scrub and massage with Cap Bon olive oil, in a "
         "thalasso centre of the Yasmine resort."),
        ("علاج بمياه البحر وحمّام في ياسمين الحمامات",
         "مسار بحري وحمّام بالكالبتوس وتكييس وتدليك بزيت زيتون الوطن القبلي، في مركز علاج "
         "بمياه البحر بمنتجع ياسمين.")),
    act("Tozeur", "palmeraie", 33.9116, 8.1374, "Bien-être", 90, 120, ["10:00", "16:00"], 6,
        ("Soins aux dattes et hammam dans un spa de l'oasis",
         "Gommage au noyau de datte, masque au miel et à la sève de palmier (legmi), hammam et "
         "repos au calme de la palmeraie. Une pause douceur entre deux excursions dans le désert."),
        ("Date treatments and hammam in an oasis spa",
         "Date-stone scrub, honey and palm-sap (legmi) mask, hammam and rest in the calm of the "
         "palm grove. A gentle break between two desert excursions."),
        ("علاجات بالتمر وحمّام في منتجع صحي بالواحة",
         "تقشير بنوى التمر وقناع بالعسل واللاقمي، وحمّام واسترخاء في هدوء الواحة. استراحة "
         "لطيفة بين رحلتين في الصحراء.")),

    # ------------------------------------------------------------------
    # Ajout du 19/10/2026 — Famille & loisirs (7). Lieux vérifiés dans OSM
    # (Nominatim, 19/10/2026). Parcs aquatiques écartés : fermés hors saison.
    # ------------------------------------------------------------------
    act("Sousse", "Port El Kantaoui", 35.8915, 10.5949, "Famille & loisirs", 30, 180, ["10:00", "15:00"], 30,
        ("Sortie au Hannibal Park de Port El Kantaoui",
         "Le parc d'attractions de la station : manèges pour petits et grands, autos tamponneuses, "
         "grande roue et jeux. Une sortie facile pour les familles avec enfants."),
        ("Outing to Hannibal Park in Port El Kantaoui",
         "The resort's amusement park: rides for young and old, bumper cars, Ferris wheel and "
         "games. An easy outing for families with children."),
        ("نزهة في حديقة حنبعل بمرسى القنطاوي",
         "مدينة ألعاب المنتجع: ألعاب للصغار والكبار وسيارات متصادمة وعجلة دوّارة. نزهة سهلة "
         "للعائلات مع الأطفال.")),
    act("Tunis", "Belvédère", 36.8187, 10.1702, "Famille & loisirs", 15, 180, ["09:30", "14:00"], 25,
        ("Parc du Belvédère et zoo de Tunis en famille",
         "Le grand parc boisé de Tunis et son zoo : lions, girafes, flamants, aires de jeux et "
         "pique-nique sous les pins. Une sortie idéale avec des enfants."),
        ("Belvédère Park and Tunis Zoo with the family",
         "Tunis's large wooded park and its zoo: lions, giraffes, flamingos, playgrounds and "
         "picnics under the pines. An ideal outing with children."),
        ("منتزه البلفيدير وحديقة حيوانات تونس مع العائلة",
         "منتزه تونس الكبير المشجَّر وحديقة حيواناته: أسود وزرافات ونحام ومساحات لعب ونزهة "
         "تحت الصنوبر. نزهة مثالية مع الأطفال."),
        jours=SAUF_LUNDI),
    act("Tunis", "Cité des sciences", 36.8470, 10.1924, "Famille & loisirs", 20, 150, ["10:00", "14:30"], 25,
        ("Cité des sciences de Tunis et séance au planétarium",
         "Expositions interactives sur l'espace, le corps humain et la Terre, puis une séance sous "
         "la coupole du planétarium. Pour les familles et les curieux de tout âge."),
        ("Tunis Science City and a planetarium show",
         "Interactive exhibitions on space, the human body and the Earth, followed by a show under "
         "the planetarium dome. For families and the curious of all ages."),
        ("مدينة العلوم بتونس وعرض في القبة السماوية",
         "معارض تفاعلية حول الفضاء وجسم الإنسان والأرض، يليها عرض تحت القبة السماوية. للعائلات "
         "ولكل الفضوليين من جميع الأعمار."),
        jours=SAUF_LUNDI),
    act("Hammamet", "Bouficha", 36.2047, 10.4232, "Famille & loisirs", 45, 240, ["09:30"], 30,
        ("Friguia Park : animaux d'Afrique en famille",
         "Parc animalier entre Hammamet et Sousse : éléphants, girafes, fauves, oiseaux et animaux "
         "de la ferme, avec des spectacles pour les enfants selon la saison. Transport non inclus."),
        ("Friguia Park: African animals for the whole family",
         "Wildlife park between Hammamet and Sousse: elephants, giraffes, big cats, birds and farm "
         "animals, with shows for children depending on the season. Transport not included."),
        ("فريقيا بارك: حيوانات إفريقيا مع العائلة",
         "حديقة حيوانات بين الحمامات وسوسة: فيلة وزرافات وسباع وطيور وحيوانات المزرعة، مع عروض "
         "للأطفال حسب الموسم. النقل غير مشمول.")),
    act("Tozeur", "Chak Wak", 33.9111, 8.1465, "Famille & loisirs", 25, 120, ["09:30", "15:00"], 20,
        ("Chak Wak, le parc de la préhistoire et des civilisations",
         "Un parcours en plein air dans la palmeraie, des dinosaures aux grandes civilisations, "
         "avec des reconstitutions grandeur nature. Plaît beaucoup aux enfants."),
        ("Chak Wak, the park of prehistory and civilisations",
         "An open-air trail in the palm grove, from dinosaurs to great civilisations, with "
         "life-size reconstructions. Very popular with children."),
        ("شاك واك، حديقة ما قبل التاريخ والحضارات",
         "مسار في الهواء الطلق داخل الواحة، من الديناصورات إلى الحضارات الكبرى، مع مجسّمات "
         "بالحجم الطبيعي. يحبّه الأطفال كثيرًا.")),
    act("Tozeur", "Eden Palm", 33.9171, 8.1471, "Famille & loisirs", 20, 90, ["10:00", "15:30"], 20,
        ("Eden Palm : le palmier dattier raconté en famille",
         "Musée-jardin consacré au palmier dattier : variétés de dattes, outils des grimpeurs, "
         "fabrication de confitures et de pâtes de dattes, et dégustation. Visite courte adaptée "
         "aux enfants."),
        ("Eden Palm: the date palm explained for families",
         "Garden-museum devoted to the date palm: date varieties, climbers' tools, making jams and "
         "date pastes, and a tasting. Short visit suited to children."),
        ("إيدن بالم: نخلة التمر تُروى للعائلة",
         "متحف-حديقة مخصّص لنخلة التمر: أصناف التمور وأدوات المتسلّقين وصنع المربّى وعجين "
         "التمر، مع تذوّق. زيارة قصيرة مناسبة للأطفال.")),
    act("Tozeur", "Belvédère", 33.8961, 8.1361, "Famille & loisirs", 12, 60, ["09:00", "15:00", "16:30"], 25,
        ("Zoo du Paradis, le zoo du désert de Tozeur",
         "Petit zoo consacré à la faune saharienne : fennecs, hyènes rayées, dromadaires, gazelles "
         "et oiseaux du désert. Une heure de visite près du Belvédère."),
        ("Zoo du Paradis, Tozeur's desert zoo",
         "Small zoo devoted to Saharan wildlife: fennecs, striped hyenas, dromedaries, gazelles and "
         "desert birds. A one-hour visit near the Belvédère."),
        ("حديقة حيوانات الصحراء بتوزر",
         "حديقة حيوانات صغيرة مخصّصة لحيوانات الصحراء: فنك وضباع مخطّطة وإبل وغزلان وطيور "
         "صحراوية. زيارة لمدة ساعة قرب البلفيدير.")),

    # ------------------------------------------------------------------
    # Ajout du 19/10/2026 — Golf (5). Parcours vérifiés dans OSM ; prix = green-fee
    # indicatif par joueur.
    # ------------------------------------------------------------------
    act("Djerba", "Djerba Golf Club", 33.8283, 11.0070, "Golf", 210, 270, ["08:00", "13:00"], 8,
        ("Parcours de golf au Djerba Golf Club",
         "Green-fee 18 trous sur un parcours en bord de mer, entre palmiers, oliviers et lacs. "
         "Location de clubs et de voiturette en supplément sur place ; pour joueurs confirmés, "
         "practice ouvert aux débutants."),
        ("Round of golf at Djerba Golf Club",
         "18-hole green fee on a seaside course among palms, olive trees and lakes. Club and buggy "
         "hire extra on site; for experienced players, driving range open to beginners."),
        ("جولة غولف في نادي جربة للغولف",
         "رسم دخول لـ18 حفرة في ملعب على شاطئ البحر بين النخيل والزيتون والبحيرات. كراء المضارب "
         "والعربة بمقابل إضافي؛ للاعبين المتمرّسين، وميدان التمرين مفتوح للمبتدئين.")),
    act("Hammamet", "Golf Citrus", 36.4259, 10.5456, "Golf", 200, 270, ["08:00", "13:00"], 8,
        ("Green-fee au golf Citrus de Hammamet",
         "Deux parcours dessinés entre forêt d'eucalyptus et orangeraies, à quelques minutes de la "
         "plage. Pour golfeurs confirmés ; location de matériel sur place."),
        ("Green fee at Citrus golf, Hammamet",
         "Two courses laid out between eucalyptus forest and orange groves, a few minutes from the "
         "beach. For experienced golfers; equipment hire on site."),
        ("رسم دخول لملعب سيتروس للغولف بالحمامات",
         "ملعبان بين غابة الكالبتوس وبساتين البرتقال، على بعد دقائق من الشاطئ. للاعبي الغولف "
         "المتمرّسين؛ كراء المعدّات في المكان.")),
    act("Monastir", "Flamingo Golf", 35.7468, 10.7982, "Golf", 190, 270, ["08:00", "13:00"], 8,
        ("Parcours au Flamingo Golf de Monastir",
         "18 trous au milieu des oliviers et des lacs, tout près de l'aéroport de Monastir. "
         "Pratique pour une dernière partie avant le vol retour."),
        ("Round at Flamingo Golf, Monastir",
         "18 holes among olive trees and lakes, close to Monastir airport. Handy for a last round "
         "before the flight home."),
        ("جولة في ملعب فلامنغو للغولف بالمنستير",
         "18 حفرة وسط الزيتون والبحيرات، قرب مطار المنستير. مناسب لجولة أخيرة قبل رحلة العودة.")),
    act("Sousse", "El Kantaoui", 35.8949, 10.5870, "Golf", 200, 270, ["08:00", "13:00"], 8,
        ("Green-fee au golf d'El Kantaoui",
         "Deux parcours, dont l'un longe la mer, au cœur de la station de Port El Kantaoui. "
         "Location de matériel et de voiturette sur place."),
        ("Green fee at El Kantaoui golf",
         "Two courses, one of them running along the sea, in the heart of the Port El Kantaoui "
         "resort. Equipment and buggy hire on site."),
        ("رسم دخول لملعب القنطاوي للغولف",
         "ملعبان، أحدهما على طول البحر، في قلب منتجع مرسى القنطاوي. كراء المعدّات والعربة في المكان.")),
    act("Sousse", "El Kantaoui", 35.8949, 10.5870, "Golf", 80, 90, ["10:00", "16:00"], 6,
        ("Initiation au golf à El Kantaoui",
         "Première approche du golf avec un moniteur : prise de club, swing au practice et petit "
         "jeu sur le green. Matériel fourni ; dès 8 ans, en famille ou en solo."),
        ("Introduction to golf in El Kantaoui",
         "A first taste of golf with an instructor: grip, swing at the driving range and short "
         "game on the green. Equipment provided; from age 8, with family or solo."),
        ("تعلّم أساسيات الغولف في القنطاوي",
         "أول تجربة للغولف مع مدرّب: مسك المضرب والتأرجح في ميدان التمرين واللعب القصير على "
         "العشب. المعدّات متوفّرة؛ من 8 سنوات، مع العائلة أو بمفردك.")),
]


# ----------------------------------------------------------------------
# Contrôles et statistiques (sans base de données)
# ----------------------------------------------------------------------


def distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance orthodromique (haversine)."""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def contient_arabe(texte: str) -> bool:
    return any("؀" <= c <= "ۿ" for c in texte)


def verifier() -> list[str]:
    """Contrôles de cohérence des données ; renvoie la liste des erreurs."""
    erreurs = []
    titres = Counter(a["fr"][0] for a in ACTIVITES)
    for titre, n in titres.items():
        if n > 1:
            erreurs.append(f"titre en double : {titre}")
    for a in ACTIVITES:
        t = a["fr"][0]
        zone = ZONES.get(a["ville"])
        if zone is None:
            erreurs.append(f"{t} : ville inconnue {a['ville']}")
            continue
        if a["categorie"] not in CATEGORIES:
            erreurs.append(f"{t} : catégorie inconnue {a['categorie']}")
        d = distance_km(a["latitude"], a["longitude"], *CENTRES[zone])
        if d > RAYON_MAX_KM:
            erreurs.append(f"{t} : à {d:.0f} km du centre de {zone}")
        if not (a["prix"] > 0 and a["duree"] > 0 and a["places"] > 0 and a["heures"]):
            erreurs.append(f"{t} : prix, durée, places ou heures invalides")
        for langue in ("fr", "en", "ar"):
            titre, description = a[langue]
            if not titre.strip() or not description.strip():
                erreurs.append(f"{t} : traduction {langue} vide")
            if len(titre) > 200:
                erreurs.append(f"{t} : titre {langue} > 200 caractères")
        if not contient_arabe(a["ar"][0] + a["ar"][1]):
            erreurs.append(f"{t} : texte arabe sans caractère arabe")
        for h in a["heures"]:
            time.fromisoformat(h)
    return erreurs


def creneaux_prevus(a: dict, debut: date) -> list[tuple[date, time]]:
    """Créneaux (date, heure) de l'activité sur l'horizon, selon ses jours d'ouverture."""
    res = []
    for i in range(HORIZON_JOURS):
        jour = debut + timedelta(days=i)
        if jour.weekday() in a["jours"]:
            res.extend((jour, time.fromisoformat(h)) for h in a["heures"])
    return res


def afficher_repartition() -> None:
    zones = list(CENTRES)
    print("\nRépartition du seed (zone x catégorie) :")
    entete = f"{'Zone':<24}" + "".join(f"{c:>19}" for c in CATEGORIES) + f"{'Total':>8}"
    print(entete)
    compte = Counter((ZONES[a["ville"]], a["categorie"]) for a in ACTIVITES)
    for z in zones:
        ligne = [compte[(z, c)] for c in CATEGORIES]
        print(f"{z:<24}" + "".join(f"{n:>19}" for n in ligne) + f"{sum(ligne):>8}")
    totaux = [sum(compte[(z, c)] for z in zones) for c in CATEGORIES]
    print(f"{'Total':<24}" + "".join(f"{n:>19}" for n in totaux) + f"{sum(totaux):>8}")

    prix = sorted(a["prix"] for a in ACTIVITES)
    durees = sorted(a["duree"] for a in ACTIVITES)
    print(f"Prix (DT) : min {prix[0]:g} · médiane {prix[len(prix) // 2]:g} · max {prix[-1]:g}")
    print(f"Durée (min) : min {durees[0]} · médiane {durees[len(durees) // 2]} · max {durees[-1]}")


# ----------------------------------------------------------------------
# Écriture en base
# ----------------------------------------------------------------------


def ecrire() -> None:
    from app.database import Base, SessionLocal, engine
    from app.models import Activity, Availability, Category

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        cats = {c.nom: c for c in db.query(Category).filter(Category.nom.in_(CATEGORIES))}
        for nom, (nom_en, nom_ar) in NOUVELLES_CATEGORIES.items():
            if nom not in cats:
                cats[nom] = Category(nom=nom, nom_en=nom_en, nom_ar=nom_ar)
                db.add(cats[nom])
                print(f"Catégorie créée : {nom}")
        db.flush()
        manquantes = [c for c in CATEGORIES_ORIGINE if c not in cats]
        if manquantes:
            sys.exit(
                f"Catégories absentes : {', '.join(manquantes)}. "
                "Lancer d'abord scripts/seed_catalog.py puis scripts/seed_translations.py."
            )

        debut = date.today() + timedelta(days=1)
        crees = completees = creneaux = 0
        for a in ACTIVITES:
            titre_fr, description_fr = a["fr"]
            activite = db.query(Activity).filter(Activity.titre == titre_fr).first()
            if activite is None:
                activite = Activity(
                    titre=titre_fr,
                    description=description_fr,
                    titre_en=a["en"][0],
                    description_en=a["en"][1],
                    titre_ar=a["ar"][0],
                    description_ar=a["ar"][1],
                    prix=a["prix"],
                    duree=a["duree"],
                    localisation=a["localisation"],
                    latitude=a["latitude"],
                    longitude=a["longitude"],
                    category_id=cats[a["categorie"]].id,
                )
                db.add(activite)
                db.flush()
                crees += 1
            else:
                # Ne jamais écraser une saisie (admin ou exécution précédente).
                modifiee = False
                for champ, valeur in (
                    ("titre_en", a["en"][0]),
                    ("description_en", a["en"][1]),
                    ("titre_ar", a["ar"][0]),
                    ("description_ar", a["ar"][1]),
                ):
                    if not getattr(activite, champ):
                        setattr(activite, champ, valeur)
                        modifiee = True
                completees += modifiee

            existants = {
                (d, h)
                for d, h in db.query(Availability.date, Availability.heure).filter(
                    Availability.activity_id == activite.id, Availability.date >= debut
                )
            }
            for jour, heure in creneaux_prevus(a, debut):
                if (jour, heure) in existants:
                    continue
                db.add(
                    Availability(
                        activity_id=activite.id,
                        date=jour,
                        heure=heure,
                        places_disponibles=a["places"],
                        places_totales=a["places"],
                    )
                )
                creneaux += 1

        db.commit()
        fin = debut + timedelta(days=HORIZON_JOURS - 1)
        print(f"Horizon des créneaux : {debut} -> {fin}")
        print(
            f"Terminé : {crees} activité(s) créée(s), {completees} traduction(s) complétée(s), "
            f"{creneaux} créneau(x) ajouté(s)."
        )
        print(f"Catalogue complet : {db.query(Activity).count()} activité(s) en base.")
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--verifier", action="store_true", help="contrôle les données sans toucher à la base"
    )
    args = parser.parse_args()

    erreurs = verifier()
    if erreurs:
        print("Données invalides :")
        for e in erreurs:
            print(f"  - {e}")
        sys.exit(1)
    print(f"Données valides : {len(ACTIVITES)} activités.")
    afficher_repartition()
    if not args.verifier:
        print()
        ecrire()


if __name__ == "__main__":
    main()
