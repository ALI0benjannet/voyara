"""Traductions EN / AR du catalogue de démonstration (idempotent).

Le français reste la langue de référence (colonnes `titre` / `description`) ;
ce script remplit les colonnes `*_en` et `*_ar` des activités et catégories
créées par `seed_catalog.py`. Une traduction déjà saisie n'est pas écrasée.

Prérequis : `python scripts/add_translation_columns.py`
Usage (depuis services/catalog) : python scripts/seed_translations.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from app.database import SessionLocal  # noqa: E402
from app.models import Activity, Category  # noqa: E402

CATEGORIES = {
    # nom français : (anglais, arabe)
    "Culture": ("Culture", "ثقافة"),
    "Mer": ("Sea", "بحر"),
    "Désert": ("Desert", "صحراء"),
    "Aventure": ("Adventure", "مغامرة"),
    "Gastronomie": ("Food", "مأكولات"),
}

ACTIVITIES = {
    "Sidi Bou Saïd & Carthage": {
        "en": (
            "Sidi Bou Saïd & Carthage",
            "Blue-and-white alleys, the Café des Délices, then the Baths of Antoninus — a morning "
            "between sea and history, led by a guide passionate about Carthage. French-speaking "
            "local guide, entry tickets included, small group of 8 maximum.",
        ),
        "ar": (
            "سيدي بو سعيد وقرطاج",
            "أزقة بالأزرق والأبيض، ومقهى العلّيق، ثم حمّامات أنطونينوس — صباح بين البحر والتاريخ "
            "بصحبة مرشد شغوف بقرطاج. مرشد محلي، تذاكر الدخول مشمولة، مجموعة صغيرة من 8 أشخاص كحد أقصى.",
        ),
    },
    "Plongée aux récifs de Tabarka": {
        "en": (
            "Diving at the Tabarka reefs",
            "The finest coral in the Mediterranean, supervised by CMAS-certified instructors. "
            "First dive or exploration dive, full equipment included.",
        ),
        "ar": (
            "الغوص في شعاب طبرقة",
            "أجمل مرجان في البحر الأبيض المتوسط، بإشراف مدربين معتمدين من CMAS. "
            "غطسة تجريبية أو استكشافية، مع كامل المعدات.",
        ),
    },
    "Bivouac dans le désert de Douz": {
        "en": (
            "Desert bivouac in Douz",
            "Camels at sunset, a Berber dinner under the stars and a night in a camp equipped for "
            "the desert. Full board and transfer from Douz included.",
        ),
        "ar": (
            "مبيت في صحراء دوز",
            "جِمال عند الغروب، وعشاء أمازيغي تحت النجوم، وليلة في مخيّم مجهّز في الصحراء. "
            "إقامة كاملة والنقل من دوز مشمولان.",
        ),
    },
    "Food tour de la médina de Tunis": {
        "en": (
            "Food tour of the Tunis medina",
            "Lablabi, egg brik, makroudh from the souk: six food stops in the UNESCO-listed souks. "
            "All tastings included, vegetarian option available.",
        ),
        "ar": (
            "جولة الأكل في مدينة تونس العتيقة",
            "لبلابي، وبريك بالبيض، ومقروض من السوق: ست محطات ذوق في الأسواق المصنّفة عالميًا. "
            "كل التذوّقات مشمولة، مع خيار نباتي.",
        ),
    },
    "Kayak sur le lac de Bizerte": {
        "en": (
            "Kayaking on Lake Bizerte",
            "Paddle between the old port and the lagoon at daybreak, when the water is a mirror. "
            "Kayak, life jacket and guide included — no experience needed.",
        ),
        "ar": (
            "التجديف في بحيرة بنزرت",
            "جدّف بين الميناء القديم والبحيرة عند الفجر، حين يصبح الماء كالمرآة. "
            "الزورق وسترة النجاة والمرشد مشمولون — لا حاجة إلى خبرة سابقة.",
        ),
    },
    "Montgolfière sur les oasis de Tozeur": {
        "en": (
            "Hot-air balloon over the Tozeur oases",
            "Fly over palm groves and dunes at sunrise (45-minute flight, certified pilot), then a "
            "toast with dates and mint tea on landing.",
        ),
        "ar": (
            "منطاد فوق واحات توزر",
            "حلّق فوق واحات النخيل والكثبان عند الشروق (رحلة 45 دقيقة، طيّار معتمد)، "
            "ثم نخب بالتمر والشاي بالنعناع عند الهبوط.",
        ),
    },
    "Croisière au couchant à Djerba": {
        "en": (
            "Sunset cruise in Djerba",
            "A traditional sailing boat, a swim in a cove and mint tea while the sun sets over the "
            "sea. Departure from Houmt Souk marina.",
        ),
        "ar": (
            "رحلة بحرية عند الغروب في جربة",
            "مركب شراعي تقليدي، وسباحة في خليج صغير، وشاي بالنعناع بينما تغرب الشمس في البحر. "
            "الانطلاق من مرسى حومة السوق.",
        ),
    },
    "Randonnée au Cap Bon": {
        "en": (
            "Hiking in Cap Bon",
            "A coastal trail between cliffs and the hot springs of Korbous, with a picnic facing "
            "the Bay of Tunis. Intermediate level, transport from Tunis included.",
        ),
        "ar": (
            "رحلة مشي في الوطن القبلي",
            "مسار ساحلي بين المنحدرات والينابيع الساخنة في قربص، مع نزهة أمام خليج تونس. "
            "مستوى متوسط، والنقل من تونس مشمول.",
        ),
    },
}


def main() -> None:
    db = SessionLocal()
    activities = categories = 0
    try:
        for nom, (en, ar) in CATEGORIES.items():
            category = db.query(Category).filter(Category.nom == nom).first()
            if category is None:
                continue
            if not category.nom_en:
                category.nom_en = en
            if not category.nom_ar:
                category.nom_ar = ar
            categories += 1
            print(f"  = catégorie {nom} -> {en} / {ar}")

        for titre, langs in ACTIVITIES.items():
            activity = db.query(Activity).filter(Activity.titre == titre).first()
            if activity is None:
                print(f"  ? activité absente : {titre}")
                continue
            if not activity.titre_en:
                activity.titre_en = langs["en"][0]
            if not activity.description_en:
                activity.description_en = langs["en"][1]
            if not activity.titre_ar:
                activity.titre_ar = langs["ar"][0]
            if not activity.description_ar:
                activity.description_ar = langs["ar"][1]
            activities += 1
            print(f"  + {titre}")

        db.commit()
        print(f"Terminé : {activities} activité(s), {categories} catégorie(s) traduites.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
