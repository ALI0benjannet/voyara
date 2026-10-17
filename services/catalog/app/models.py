"""Modèles du domaine Catalogue : catégories, activités, disponibilités,
et offres de voyage (séjours, vols, voitures de location, transferts).

NOTE microservices : plus de relations vers bookings/reviews — ces données
appartiennent à d'autres services et référencent activity_id par simple entier.
"""

from datetime import date, datetime, time

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    nom: Mapped[str] = mapped_column(String(100), unique=True)
    # Traductions optionnelles ; `nom` (français) sert de repli.
    nom_en: Mapped[str | None] = mapped_column(String(100), nullable=True)
    nom_ar: Mapped[str | None] = mapped_column(String(100), nullable=True)

    activities = relationship("Activity", back_populates="category")


class Activity(Base):
    __tablename__ = "activities"

    id: Mapped[int] = mapped_column(primary_key=True)
    titre: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    # Traductions optionnelles : le français (colonnes ci-dessus) sert de repli
    # quand une langue n'est pas renseignée.
    titre_en: Mapped[str | None] = mapped_column(String(200), nullable=True)
    titre_ar: Mapped[str | None] = mapped_column(String(200), nullable=True)
    description_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    description_ar: Mapped[str | None] = mapped_column(Text, nullable=True)
    prix: Mapped[float] = mapped_column(Float)
    duree: Mapped[int] = mapped_column(Integer)
    localisation: Mapped[str] = mapped_column(String(255))
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    photos: Mapped[str | None] = mapped_column(Text, nullable=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"))
    # Espace prestataire : une activité proposée par un prestataire reste
    # « en_attente » jusqu'à la modération admin (« publiee » ou « refusee »).
    # Les activités créées par l'admin sont publiées directement.
    statut: Mapped[str] = mapped_column(
        String(20), default="publiee", server_default="publiee", index=True
    )
    # user_id (auth-service) du prestataire — simple entier, pas de FK (ADR-002).
    prestataire_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    category = relationship("Category", back_populates="activities")
    availabilities = relationship("Availability", back_populates="activity")


class Availability(Base):
    __tablename__ = "availabilities"

    id: Mapped[int] = mapped_column(primary_key=True)
    activity_id: Mapped[int] = mapped_column(ForeignKey("activities.id"))
    date: Mapped[date] = mapped_column(Date)
    heure: Mapped[time] = mapped_column(Time)
    # Compteur décrémenté à chaque réservation (UPDATE conditionnel atomique).
    places_disponibles: Mapped[int] = mapped_column(Integer, default=0)
    # Capacité d'origine, figée à la création du créneau. Sans elle,
    # `places_disponibles` n'est qu'un nombre : impossible de vérifier qu'il
    # correspond aux réservations réellement enregistrées. Sert de référence au
    # script de réconciliation (voir architecture.md §12 n° 3).
    places_totales: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    activity = relationship("Activity", back_populates="availabilities")


# ---------------------------------------------------------------------------
# Offres de voyage (onglets Séjours, Vols, Voitures de location, Transferts).
# Tables posées en avance : pas encore d'API ni de réservation branchée.
# Créées au démarrage par `create_all` (AUTO_CREATE_TABLES) comme les autres.
# ---------------------------------------------------------------------------


class Stay(Base):
    """Hébergement : hôtel, riad, maison d'hôtes, appartement…"""

    __tablename__ = "stays"

    id: Mapped[int] = mapped_column(primary_key=True)
    nom: Mapped[str] = mapped_column(String(200))
    type: Mapped[str] = mapped_column(String(50))  # hotel | riad | maison_hotes | appartement
    description: Mapped[str] = mapped_column(Text)
    nom_en: Mapped[str | None] = mapped_column(String(200), nullable=True)
    nom_ar: Mapped[str | None] = mapped_column(String(200), nullable=True)
    description_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    description_ar: Mapped[str | None] = mapped_column(Text, nullable=True)
    localisation: Mapped[str] = mapped_column(String(255))
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    etoiles: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1 à 5
    prix_nuit: Mapped[float] = mapped_column(Float)
    capacite: Mapped[int] = mapped_column(Integer)  # voyageurs max
    equipements: Mapped[str | None] = mapped_column(Text, nullable=True)  # « wifi,piscine,… »
    photos: Mapped[str | None] = mapped_column(Text, nullable=True)
    actif: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")


class Flight(Base):
    """Vol régulier, une ligne par départ (date + heure)."""

    __tablename__ = "flights"

    id: Mapped[int] = mapped_column(primary_key=True)
    compagnie: Mapped[str] = mapped_column(String(100))
    numero_vol: Mapped[str] = mapped_column(String(20), index=True)
    aeroport_depart: Mapped[str] = mapped_column(String(3))  # code IATA, ex. TUN
    aeroport_arrivee: Mapped[str] = mapped_column(String(3))
    ville_depart: Mapped[str] = mapped_column(String(100))
    ville_arrivee: Mapped[str] = mapped_column(String(100))
    depart_le: Mapped[datetime] = mapped_column(DateTime)
    arrivee_le: Mapped[datetime] = mapped_column(DateTime)
    classe: Mapped[str] = mapped_column(String(20), default="economy")  # economy | business
    prix: Mapped[float] = mapped_column(Float)
    # Même logique que les créneaux d'activité : compteur + capacité d'origine.
    places_disponibles: Mapped[int] = mapped_column(Integer, default=0)
    places_totales: Mapped[int] = mapped_column(Integer, default=0, server_default="0")


class CarRental(Base):
    """Voiture proposée à la location par une agence."""

    __tablename__ = "car_rentals"

    id: Mapped[int] = mapped_column(primary_key=True)
    marque: Mapped[str] = mapped_column(String(100))
    modele: Mapped[str] = mapped_column(String(100))
    categorie: Mapped[str] = mapped_column(String(50))  # economique | compacte | suv | van
    transmission: Mapped[str] = mapped_column(String(20))  # manuelle | automatique
    carburant: Mapped[str] = mapped_column(String(20))  # essence | diesel | hybride | electrique
    nb_places: Mapped[int] = mapped_column(Integer)
    agence: Mapped[str] = mapped_column(String(150))
    localisation: Mapped[str] = mapped_column(String(255))  # lieu de prise en charge
    prix_jour: Mapped[float] = mapped_column(Float)
    photos: Mapped[str | None] = mapped_column(Text, nullable=True)
    disponible: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")


class Transfer(Base):
    """Trajet avec chauffeur, typiquement aéroport ↔ hôtel."""

    __tablename__ = "transfers"

    id: Mapped[int] = mapped_column(primary_key=True)
    depart: Mapped[str] = mapped_column(String(255))  # ex. « Aéroport Tunis-Carthage »
    arrivee: Mapped[str] = mapped_column(String(255))
    type_vehicule: Mapped[str] = mapped_column(String(50))  # taxi | grand_taxi | berline | van | minibus
    capacite: Mapped[int] = mapped_column(Integer)  # passagers max
    bagages: Mapped[int] = mapped_column(Integer, default=0)
    duree: Mapped[int] = mapped_column(Integer)  # minutes
    prix: Mapped[float] = mapped_column(Float)  # par véhicule, pas par passager
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    actif: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
