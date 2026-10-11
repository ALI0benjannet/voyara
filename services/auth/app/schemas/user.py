from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_serializer, model_validator

from app.models.enums import UserRole


class UserBase(BaseModel):
    email: EmailStr
    nom: str = Field(min_length=2, max_length=100)
    prenom: str = Field(min_length=2, max_length=100)


class UserCreate(BaseModel):
    email: EmailStr
    nom: str | None = None
    prenom: str | None = None
    full_name: str | None = None
    password: str = Field(min_length=8, max_length=128)

    @model_validator(mode="before")
    @classmethod
    def parse_full_name(cls, values):
        if not isinstance(values, dict):
            return values

        nom = values.get("nom")
        prenom = values.get("prenom")
        full_name = values.get("full_name")

        if full_name and not (nom and prenom):
            parts = full_name.strip().split()
            if len(parts) < 2:
                raise ValueError("full_name must include at least a first name and a last name")
            values["prenom"] = parts[0]
            values["nom"] = " ".join(parts[1:])

        if not values.get("nom") or not values.get("prenom"):
            raise ValueError("Either nom/prenom or full_name must be provided")

        return values


class UserUpdate(BaseModel):
    nom: str | None = None
    prenom: str | None = None
    preferences: str | None = None


class UserRead(UserBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    role: UserRole
    is_active: bool
    is_verified: bool
    created_at: datetime
    avatar_url: str | None = None

    @field_serializer("role")
    def serialize_role(self, role: UserRole) -> str:
        return role.name
