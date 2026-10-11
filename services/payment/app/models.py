"""Modèle du domaine Paiement.

NOTE microservices : booking_id est un simple entier (référence vers le
booking-service), pas de ForeignKey inter-services.
"""

import enum
from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, func
from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PaymentType(str, enum.Enum):
    full = "full"
    deposit = "deposit"


class PaymentStatus(str, enum.Enum):
    pending = "pending"
    succeeded = "succeeded"
    failed = "failed"


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    booking_id: Mapped[int] = mapped_column(Integer, index=True)  # ref booking-service
    montant: Mapped[float] = mapped_column(Float)
    type: Mapped[PaymentType] = mapped_column(
        SQLAlchemyEnum(PaymentType, name="paymenttype"), default=PaymentType.full
    )
    methode: Mapped[str] = mapped_column(String(50), default="stripe")
    statut: Mapped[PaymentStatus] = mapped_column(
        SQLAlchemyEnum(PaymentStatus, name="paymentstatus"),
        default=PaymentStatus.pending,
    )
    stripe_intent_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    date_paiement: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ProcessedEvent(Base):
    """Idempotence du webhook Stripe : un événement n'est traité qu'une fois."""

    __tablename__ = "processed_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    processed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
