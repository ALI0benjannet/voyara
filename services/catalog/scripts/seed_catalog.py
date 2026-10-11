"""Seed du catalogue Voyara (idempotent) — données issues de la maquette design.

Usage (depuis services/catalog) : python scripts/seed_catalog.py
Crée 5 catégories, 8 activités tunisiennes et des disponibilités sur 3 semaines.
"""

import os
import sys
from datetime import date, time, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.models import Activity, Availability, Category  # noqa: E402

CATEGORIES = ["Culture", "Mer", "Désert", "Aventure", "Gastronomie"]

ACTIVITIES = [
    {
        "titre": "Sidi Bou Saïd & Carthage",
        "description": "Ruelles bleues et blanches, café des Délices, puis les thermes d'Antonin — "
        "une matinée entre mer et histoire, menée par un guide passionné de Carthage. "
        "Guide local francophone, billets d'entrée inclus, petit groupe de 8 maximum.",
        "prix": 45, "duree": 240, "localisation": "Tunis",
        "latitude": 36.8687, "longitude": 10.3417, "categorie": "Culture",
    },
    {
        "titre": "Plongée aux récifs de Tabarka",
        "description": "Le plus beau corail de Méditerranée, encadré par des moniteurs certifiés CMAS. "
        "Baptême ou exploration, matériel complet fourni, 2 plongées incluses.",
        "prix": 120, "duree": 300, "localisation": "Tabarka",
        "latitude": 36.9544, "longitude": 8.7580, "categorie": "Mer",
    },
    {
        "titre": "Bivouac dans le désert de Douz",
        "description": "Dromadaires au couchant, dîner berbère sous les étoiles et nuit en campement "
        "équipé aux portes du Grand Erg Oriental. Repas traditionnels inclus, départ de Douz centre.",
        "prix": 260, "duree": 2880, "localisation": "Douz",
        "latitude": 33.4662, "longitude": 9.0203, "categorie": "Désert",
    },
    {
        "titre": "Food tour de la médina de Tunis",
        "description": "Lablabi, brik à l'œuf, makroudh du souk — six haltes gourmandes dans les souks "
        "classés de la médina, avec un guide gastronomique local. Groupe de 10 maximum.",
        "prix": 60, "duree": 180, "localisation": "Tunis",
        "latitude": 36.7992, "longitude": 10.1706, "categorie": "Gastronomie",
    },
    {
        "titre": "Kayak sur le lac de Bizerte",
        "description": "Pagayez entre le vieux port et la lagune au lever du jour, quand l'eau est un "
        "miroir. Kayak et gilet fournis, encadrement diplômé, photos offertes. Accessible dès 10 ans.",
        "prix": 55, "duree": 120, "localisation": "Bizerte",
        "latitude": 37.2744, "longitude": 9.8739, "categorie": "Aventure",
    },
    {
        "titre": "Montgolfière sur les oasis de Tozeur",
        "description": "Survolez palmeraies et dunes au lever du soleil (vol de 45 minutes, pilote "
        "certifié), puis toast aux dattes et thé à la menthe à l'atterrissage.",
        "prix": 210, "duree": 180, "localisation": "Tozeur",
        "latitude": 33.9197, "longitude": 8.1335, "categorie": "Désert",
    },
    {
        "titre": "Croisière au couchant à Djerba",
        "description": "Voilier traditionnel, baignade dans une crique et thé à la menthe pendant que "
        "le soleil tombe sur la lagune. Masque et tuba fournis, départ de Houmt Souk.",
        "prix": 85, "duree": 180, "localisation": "Djerba",
        "latitude": 33.8756, "longitude": 10.8574, "categorie": "Mer",
    },
    {
        "titre": "Randonnée au Cap Bon",
        "description": "Sentier côtier entre falaises et sources chaudes de Korbous, avec pique-nique "
        "face à la baie de Tunis. Niveau intermédiaire, transport depuis Tunis inclus.",
        "prix": 40, "duree": 300, "localisation": "Korbous",
        "latitude": 36.8236, "longitude": 10.5717, "categorie": "Aventure",
    },
]


def run() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Catégories
        cats: dict[str, Category] = {}
        for nom in CATEGORIES:
            cat = db.query(Category).filter(Category.nom == nom).first()
            if not cat:
                cat = Category(nom=nom)
                db.add(cat)
                db.flush()
                print(f"  + catégorie {nom}")
            cats[nom] = cat

        # Activités
        created = 0
        for data in ACTIVITIES:
            if db.query(Activity).filter(Activity.titre == data["titre"]).first():
                continue
            activity = Activity(
                titre=data["titre"],
                description=data["description"],
                prix=data["prix"],
                duree=data["duree"],
                localisation=data["localisation"],
                latitude=data["latitude"],
                longitude=data["longitude"],
                category_id=cats[data["categorie"]].id,
            )
            db.add(activity)
            db.flush()
            created += 1

            # Disponibilités : tous les 2 jours sur 3 semaines, 9h, 8 places
            start = date.today() + timedelta(days=2)
            for offset in range(0, 21, 2):
                db.add(
                    Availability(
                        activity_id=activity.id,
                        date=start + timedelta(days=offset),
                        heure=time(9, 0),
                        places_disponibles=8,
                    )
                )
            print(f"  + activité {data['titre']} (+11 créneaux)")

        db.commit()
        total = db.query(Activity).count()
        print(f"Terminé : {created} activité(s) créée(s), {total} au total.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
