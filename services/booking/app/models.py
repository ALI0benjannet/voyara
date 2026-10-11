"""Modèles du domaine Réservation.

NOTE microservices : user_id, activity_id et availability_id sont de simples
entiers — pas de ForeignKey inter-services. La validation d'existence se fait
par appel API (catalog-service) au moment de la réservation.
"""

import enum
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
    text,
)
from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class BookingStatus(str, enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    cancelled = "cancelled"


class PromoCode(Base):
    __tablename__ = "promo_codes"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    reduction: Mapped[float] = mapped_column(Float)
    date_expiration: Mapped[date] = mapped_column(Date)
    actif: Mapped[bool] = mapped_column(Boolean, default=True)

    bookings = relationship("Booking", back_populates="promo_code")


class Booking(Base):
    __tablename__ = "bookings"

    # Anti-doublon : un même utilisateur ne peut pas avoir deux réservations
    # actives sur le même créneau. La contrainte est posée en base (et non
    # vérifiée en Python) car elle seule résiste à deux requêtes simultanées :
    # un double-clic, ou un client qui rejoue sa requête sur timeout.
    # `postgresql_where` la limite aux réservations non annulées, pour qu'un
    # utilisateur puisse re-réserver après une annulation.
    __table_args__ = (
        Index(
            "uq_booking_active_user_slot",
            "user_id",
            "availability_id",
            unique=True,
            postgresql_where=text("statut <> 'cancelled'"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)          # ref auth-service
    activity_id: Mapped[int] = mapped_column(Integer, index=True)      # ref catalog-service
    availability_id: Mapped[int] = mapped_column(Integer)              # ref catalog-service
    promo_code_id: Mapped[int | None] = mapped_column(
        ForeignKey("promo_codes.id"), nullable=True
    )
    date_reservation: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    statut: Mapped[BookingStatus] = mapped_column(
        SQLAlchemyEnum(BookingStatus, name="bookingstatus"),
        default=BookingStatus.pending,
    )
    qr_code: Mapped[str | None] = mapped_column(String(255), nullable=True)
    montant_total: Mapped[float] = mapped_column(Float, default=0.0)
    nb_places: Mapped[int] = mapped_column(Integer, default=1, server_default="1")

    promo_code = relationship("PromoCode", back_populates="bookings")
