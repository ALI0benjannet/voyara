"""Modèles du domaine Catalogue : catégories, activités, disponibilités,
et offres de voyage (séjours, vols, voitures de location, transferts).

NOTE microservices : plus de relations vers bookings/reviews — ces données
appartiennent à d'autres services et référencent activity_id par simple entier.
"""

from datetime import date, datetime, time

from sqlalchemy import (
    DDL,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
    event,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.lieux import AEROPORTS_REFERENCE
from app.tags_ia import MOMENTS, PUBLICS, THEMES


def _liste_sql(valeurs: tuple[str, ...]) -> str:
    return ", ".join(f"'{v}'" for v in valeurs)


def _tableau_json(valeurs: tuple[str, ...]) -> str:
    return "'[" + ", ".join(f'"{v}"' for v in valeurs) + "]'::jsonb"


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

    # --- Attributs IA (étape 2) — vocabulaire dans app/tags_ia.py ---------
    # Listes en JSONB plutôt qu'en table d'association : catalog ne filtre
    # jamais dessus (c'est le service ai qui indexe), l'export reste une
    # requête sans jointure. Les CHECK ci-dessous gardent les valeurs propres.
    themes: Mapped[list[str]] = mapped_column(
        JSONB, default=list, server_default="[]", nullable=False
    )
    public: Mapped[list[str]] = mapped_column(
        JSONB, default=list, server_default="[]", nullable=False
    )
    niveau_marche: Mapped[int | None] = mapped_column(Integer, nullable=True)
    interieur: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    moment_ideal: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # Faux tant qu'un humain n'a pas relu les tags dans l'admin.
    tags_valides: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False, index=True
    )
    # Copie figée de la proposition automatique (source, date, valeurs,
    # raisons) : permet de mesurer ce que l'humain a corrigé.
    tags_proposes: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # Mise à jour par le trigger `trg_activities_modifie_le` (même en SQL
    # brut) : sert à la synchronisation incrémentale du service ai.
    modifie_le: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    __table_args__ = (
        CheckConstraint(
            "niveau_marche IS NULL OR niveau_marche BETWEEN 1 AND 3",
            name="ck_activities_niveau_marche",
        ),
        CheckConstraint(
            f"moment_ideal IS NULL OR moment_ideal IN ({_liste_sql(MOMENTS)})",
            name="ck_activities_moment_ideal",
        ),
        CheckConstraint(
            f"jsonb_typeof(themes) = 'array' AND themes <@ {_tableau_json(THEMES)}",
            name="ck_activities_themes",
        ),
        CheckConstraint(
            f"jsonb_typeof(public) = 'array' AND public <@ {_tableau_json(PUBLICS)}",
            name="ck_activities_public",
        ),
        # Des tags validés sont forcément complets.
        CheckConstraint(
            "NOT tags_valides OR (jsonb_array_length(themes) > 0"
            " AND jsonb_array_length(public) > 0 AND niveau_marche IS NOT NULL"
            " AND interieur IS NOT NULL AND moment_ideal IS NOT NULL)",
            name="ck_activities_tags_complets",
        ),
    )

    category = relationship("Category", back_populates="activities")
    availabilities = relationship("Availability", back_populates="activity")


# Trigger `modifie_le` : partagé entre `create_all` (base neuve) et les scripts
# de migration (base existante) : add_tags_ia_columns.py (activités, étape 2) et
# add_transport_ia.py (séjours, étape 2-bis). Même fonction pour les deux tables.
_DDL_FONCTION_MODIFIE_LE = """
    CREATE OR REPLACE FUNCTION catalog_maj_modifie_le() RETURNS trigger AS $$
    BEGIN
        NEW.modifie_le := now();
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql
    """


def ddl_trigger_modifie_le(table: str) -> tuple[str, ...]:
    return (
        _DDL_FONCTION_MODIFIE_LE,
        f"DROP TRIGGER IF EXISTS trg_{table}_modifie_le ON {table}",
        f"""
    CREATE TRIGGER trg_{table}_modifie_le
    BEFORE UPDATE ON {table}
    FOR EACH ROW EXECUTE FUNCTION catalog_maj_modifie_le()
    """,
    )


DDL_TRIGGER_MODIFIE_LE = ddl_trigger_modifie_le("activities")

for _instruction in DDL_TRIGGER_MODIFIE_LE:
    event.listen(Activity.__table__, "after_create", DDL(_instruction))


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
# Lecture publique (offres_routes), CRUD admin (travel_routes), recherche
# interne pour le moteur IA (internal_offres_routes) ; pas encore de réservation.
# Créées au démarrage par `create_all` (AUTO_CREATE_TABLES) comme les autres ;
# base existante : scripts/add_transport_ia.py (étape 2-bis).
# ---------------------------------------------------------------------------


class Aeroport(Base):
    """Référentiel des aéroports (étape 2-bis) : relie vols, voitures et transferts.

    Pas de coordonnées ici : la position vient d'OpenStreetMap (POI « aeroport » du
    service ai). Pas de clé étrangère depuis `flights` : un code saisi par l'admin
    et absent du référentiel reste accepté (sa durée de vol est alors inconnue)."""

    __tablename__ = "aeroports"

    code_iata: Mapped[str] = mapped_column(String(3), primary_key=True)
    nom: Mapped[str] = mapped_column(String(100))
    ville: Mapped[str] = mapped_column(String(100), index=True)  # ville desservie
    pays: Mapped[str] = mapped_column(String(2))  # ISO 3166-1 alpha-2
    # Fuseau IANA : les horaires de `flights` sont en heure locale de l'aéroport ;
    # sans fuseau, la durée Paris -> Tunis serait fausse d'une heure en été.
    fuseau: Mapped[str] = mapped_column(String(50))


@event.listens_for(Aeroport.__table__, "after_create")
def _remplir_aeroports(table, connection, **_):
    connection.execute(table.insert(), list(AEROPORTS_REFERENCE))


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
    # Étape 2-bis : synchronisation incrémentale de l'index sémantique (service ai),
    # tenue par le trigger `trg_stays_modifie_le` comme pour les activités.
    modifie_le: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )


for _instruction in ddl_trigger_modifie_le("stays"):
    event.listen(Stay.__table__, "after_create", DDL(_instruction))


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
    # Étape 2-bis — déduits de `localisation` (app/lieux.py) s'ils ne sont pas saisis :
    # « Tunis, aéroport Tunis-Carthage » -> ville « Tunis », aeroport « TUN ».
    ville: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    aeroport: Mapped[str | None] = mapped_column(String(3), nullable=True)  # code IATA
    prix_jour: Mapped[float] = mapped_column(Float)
    photos: Mapped[str | None] = mapped_column(Text, nullable=True)
    disponible: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")


class Transfer(Base):
    """Trajet avec chauffeur, typiquement aéroport ↔ hôtel."""

    __tablename__ = "transfers"

    id: Mapped[int] = mapped_column(primary_key=True)
    depart: Mapped[str] = mapped_column(String(255))  # ex. « Aéroport Tunis-Carthage »
    arrivee: Mapped[str] = mapped_column(String(255))
    # Étape 2-bis — déduits de `depart` / `arrivee` (app/lieux.py) s'ils ne sont pas saisis.
    ville_depart: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    ville_arrivee: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    aeroport_depart: Mapped[str | None] = mapped_column(String(3), nullable=True)  # code IATA
    aeroport_arrivee: Mapped[str | None] = mapped_column(String(3), nullable=True)
    type_vehicule: Mapped[str] = mapped_column(String(50))  # taxi | grand_taxi | berline | van | minibus
    capacite: Mapped[int] = mapped_column(Integer)  # passagers max
    bagages: Mapped[int] = mapped_column(Integer, default=0)
    duree: Mapped[int] = mapped_column(Integer)  # minutes
    prix: Mapped[float] = mapped_column(Float)  # par véhicule, pas par passager
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    actif: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
