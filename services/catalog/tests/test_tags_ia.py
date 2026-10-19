"""Valeurs autorisées des tags IA : API admin (422) et base (contraintes CHECK)."""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.tags_ia import MOMENTS, PUBLICS, THEMES, TagsIA

TAGS_VALIDES = {
    "themes": ["nautique", "plage"],
    "public": ["couple", "solo"],
    "niveau_marche": 1,
    "interieur": False,
    "moment_ideal": "soir",
}


def url(activite) -> str:
    return f"/api/v1/etiquetage/activities/{activite.id}"


# --- Vocabulaire ---------------------------------------------------------------


def test_vocabulaire_du_guide():
    assert set(THEMES) == {
        "plage", "culture", "histoire", "nature", "gastronomie",
        "aventure", "detente", "shopping", "nautique", "desert",
    }
    assert set(PUBLICS) == {"famille", "couple", "solo", "groupe", "enfants"}
    assert set(MOMENTS) == {"matin", "apres_midi", "soir", "indifferent"}


def test_schema_dedoublonne():
    tags = TagsIA(**{**TAGS_VALIDES, "themes": ["plage", "plage", "nautique"]})
    assert tags.themes == ["plage", "nautique"]


# --- Route admin ----------------------------------------------------------------


def test_etiquetage_sans_jeton_401(client, activite):
    assert client.put(url(activite), json=TAGS_VALIDES).status_code == 401


def test_validation_ok(admin_client, activite):
    reponse = admin_client.put(url(activite), json=TAGS_VALIDES)
    assert reponse.status_code == 200, reponse.text
    corps = reponse.json()
    assert corps["tags_valides"] is True
    assert corps["themes"] == ["nautique", "plage"] and corps["moment_ideal"] == "soir"


def test_enregistrer_sans_valider(admin_client, activite):
    corps = admin_client.put(url(activite), json={**TAGS_VALIDES, "tags_valides": False}).json()
    assert corps["tags_valides"] is False and corps["niveau_marche"] == 1


@pytest.mark.parametrize(
    "modification",
    [
        {"themes": ["plage", "ski"]},           # thème hors vocabulaire
        {"themes": []},                         # au moins un thème
        {"public": ["adolescents"]},            # public hors vocabulaire
        {"public": []},
        {"niveau_marche": 0},
        {"niveau_marche": 4},                   # 1 à 3 seulement
        {"moment_ideal": "nuit"},               # moment hors vocabulaire
        {"interieur": "peut-être"},
        {"inconnu": 1},                         # champ en trop refusé
    ],
)
def test_valeurs_interdites_422(admin_client, activite, modification):
    reponse = admin_client.put(url(activite), json={**TAGS_VALIDES, **modification})
    assert reponse.status_code == 422, modification


@pytest.mark.parametrize("champ", list(TAGS_VALIDES))
def test_champ_obligatoire(admin_client, activite, champ):
    corps = {k: v for k, v in TAGS_VALIDES.items() if k != champ}
    assert admin_client.put(url(activite), json=corps).status_code == 422


def test_activite_introuvable_404(admin_client):
    assert admin_client.put("/api/v1/etiquetage/activities/999999", json=TAGS_VALIDES).status_code == 404


def test_liste_et_filtre(admin_client, activite):
    corps = admin_client.get(
        "/api/v1/etiquetage/activities", params={"search": "croisière de test", "tags_valides": "false"}
    ).json()
    assert [i["id"] for i in corps["items"]] == [activite.id]
    admin_client.put(url(activite), json=TAGS_VALIDES)
    corps = admin_client.get(
        "/api/v1/etiquetage/activities", params={"search": "croisière de test", "tags_valides": "false"}
    ).json()
    assert corps["total"] == 0


def test_stats_mesurent_les_corrections(admin_client, db, activite):
    activite.tags_proposes = {**TAGS_VALIDES, "source": "regles"}
    db.commit()
    avant = admin_client.get("/api/v1/etiquetage/stats").json()
    # L'humain corrige le niveau de marche et le moment, garde le reste.
    admin_client.put(url(activite), json={**TAGS_VALIDES, "niveau_marche": 2, "moment_ideal": "matin"})
    apres = admin_client.get("/api/v1/etiquetage/stats").json()
    assert apres["validees"] == avant["validees"] + 1
    assert apres["comparables"] == avant["comparables"] + 1
    if avant["comparables"] == 0:  # base sans validation humaine préalable
        assert apres["corrections"]["niveau_marche"] == 1.0
        assert apres["corrections"]["themes"] == 0.0


# --- Contraintes en base (même hors API) -------------------------------------


@pytest.mark.parametrize(
    "affectation",
    [
        "niveau_marche = 5",
        "moment_ideal = 'nuit'",
        "themes = '[\"ski\"]'::jsonb",
        "public = '\"famille\"'::jsonb",        # doit être un tableau
        "tags_valides = true",                  # tags incomplets : refusé
    ],
)
def test_contraintes_check(db, activite, affectation):
    point = db.begin_nested()
    with pytest.raises(IntegrityError):
        db.execute(text(f"UPDATE activities SET {affectation} WHERE id = :id"), {"id": activite.id})
    point.rollback()
