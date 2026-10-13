"""Modèles du moteur IA (base `voyara_ai`).

Étape 1 : points d'intérêt OpenStreetMap et cache météo Open-Meteo.
Aucune référence SQL vers les autres services (database-per-service) : une
activité du catalogue n'est jamais jointe à un POI, le rapprochement se fait
par coordonnées GPS côté moteur.
"""

from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, Float, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

TYPES_POI = ("restaurant", "plage", "musee", "monument", "souk", "parc", "cafe")


class Poi(Base):
    __tablename__ = "pois"
    __table_args__ = (Index("ix_pois_ville_type", "ville", "type"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[str] = mapped_column(String(20))
    nom: Mapped[str] = mapped_column(String(255))
    # Traductions issues de `name:en` / `name:ar` d'OSM ; `nom` sert de repli.
    nom_en: Mapped[str | None] = mapped_column(String(255), nullable=True)
    nom_ar: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ville: Mapped[str] = mapped_column(String(100))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    # Valeur OSM `opening_hours` telle quelle, et sa version structurée
    # ({"lundi": [["09:00", "18:00"]], ...}) quand elle est analysable.
    horaires_ouverture: Mapped[str | None] = mapped_column(Text, nullable=True)
    # none_as_null : None devient un NULL SQL (et non le JSON `null`), mesurable par IS NULL
    horaires_normalises: Mapped[dict | None] = mapped_column(JSON(none_as_null=True), nullable=True)
    prix_moyen: Mapped[float | None] = mapped_column(Float, nullable=True)  # en DT
    tags: Mapped[dict] = mapped_column(JSON, default=dict)
    source: Mapped[str] = mapped_column(String(20), default="osm")
    # Identifiant chez la source (`node/123`, `way/456`) : clé de l'upsert idempotent.
    source_id: Mapped[str] = mapped_column(String(50), unique=True)
    maj_le: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class MeteoCache(Base):
    __tablename__ = "meteo_cache"
    __table_args__ = (UniqueConstraint("ville", "date", name="uq_meteo_ville_date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    ville: Mapped[str] = mapped_column(String(100))
    date: Mapped[date] = mapped_column(Date)
    temp_min: Mapped[float | None] = mapped_column(Float, nullable=True)  # °C
    temp_max: Mapped[float | None] = mapped_column(Float, nullable=True)  # °C
    precipitations: Mapped[float | None] = mapped_column(Float, nullable=True)  # mm
    code_meteo: Mapped[int | None] = mapped_column(Integer, nullable=True)  # code WMO
    maj_le: Mapped[datetime] = mapped_column(DateTime(timezone=True))
