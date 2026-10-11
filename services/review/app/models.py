"""Modèles du domaine Avis & Favoris.

NOTE microservices : user_id et activity_id sont de simples entiers
(références vers auth-service et catalog-service).
"""

from datetime import datetime

from sqlalchemy import DateTime, Integer, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)      # ref auth-service
    activity_id: Mapped[int] = mapped_column(Integer, index=True)  # ref catalog-service
    note: Mapped[int] = mapped_column(Integer)
    commentaire: Mapped[str | None] = mapped_column(Text, nullable=True)
    date: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Favorite(Base):
    __tablename__ = "favorites"
    __table_args__ = (UniqueConstraint("user_id", "activity_id", name="uq_user_activity_fav"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)      # ref auth-service
    activity_id: Mapped[int] = mapped_column(Integer, index=True)  # ref catalog-service
