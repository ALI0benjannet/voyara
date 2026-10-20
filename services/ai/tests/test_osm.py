"""Mapping OSM -> Poi : fonctions pures, sans base ni réseau."""

from datetime import UTC, datetime

import pytest

from app.osm import determiner_type, element_vers_poi, extraire_prix, normaliser_horaires

MAINTENANT = datetime(2026, 10, 13, 12, 0, tzinfo=UTC)


@pytest.mark.parametrize(
    ("tags", "attendu"),
    [
        ({"amenity": "restaurant"}, "restaurant"),
        ({"amenity": "cafe"}, "cafe"),
        ({"natural": "beach"}, "plage"),
        ({"leisure": "beach_resort"}, "plage"),
        ({"tourism": "museum"}, "musee"),
        ({"historic": "archaeological_site"}, "monument"),
        ({"historic": "fort"}, "monument"),
        ({"amenity": "marketplace"}, "souk"),
        ({"shop": "bazaar"}, "souk"),
        ({"leisure": "park"}, "parc"),
        ({"tourism": "zoo"}, "parc"),
        # priorité : un musée installé dans un fort reste un musée
        ({"tourism": "museum", "historic": "fort"}, "musee"),
        # aéroport (étape 2-bis) : seulement avec un code IATA
        ({"aeroway": "aerodrome", "iata": "DJE"}, "aeroport"),
        ({"aeroway": "aerodrome"}, None),
        ({"aeroway": "helipad", "iata": "XXX"}, None),
        # hors périmètre
        ({"amenity": "bank"}, None),
        ({"tourism": "attraction"}, None),
        ({"historic": "wayside_cross"}, None),
    ],
)
def test_determiner_type(tags, attendu):
    assert determiner_type(tags) == attendu


def test_noeud_complet():
    element = {
        "type": "node", "id": 42, "lat": 33.8751, "lon": 10.8571,
        "tags": {
            "amenity": "restaurant", "name": "Restaurant Haroun", "name:fr": "Chez Haroun",
            "name:en": "Haroun's", "name:ar": "مطعم هارون", "opening_hours": "Mo-Su 12:00-23:00",
        },
    }
    poi = element_vers_poi(element, "Djerba", MAINTENANT)
    assert poi["type"] == "restaurant"
    assert poi["nom"] == "Chez Haroun"  # name:fr prioritaire sur name
    assert (poi["nom_en"], poi["nom_ar"]) == ("Haroun's", "مطعم هارون")
    assert (poi["latitude"], poi["longitude"]) == (33.8751, 10.8571)
    assert poi["source_id"] == "node/42"
    assert poi["horaires_normalises"]["lundi"] == [["12:00", "23:00"]]
    assert poi["ville"] == "Djerba" and poi["source"] == "osm" and poi["maj_le"] == MAINTENANT


def test_voie_utilise_le_centre_et_repli_des_noms():
    element = {
        "type": "way", "id": 7, "center": {"lat": 36.87, "lon": 10.34},
        "tags": {"natural": "beach", "name": "Plage de Sidi Bou Saïd"},
    }
    poi = element_vers_poi(element, "Sidi Bou Saïd", MAINTENANT)
    assert poi["source_id"] == "way/7"
    assert (poi["latitude"], poi["longitude"]) == (36.87, 10.34)
    assert poi["nom"] == "Plage de Sidi Bou Saïd"
    assert poi["nom_en"] is None and poi["nom_ar"] is None
    assert poi["horaires_ouverture"] is None and poi["horaires_normalises"] is None


@pytest.mark.parametrize(
    "element",
    [
        {"type": "node", "id": 1, "lat": 1, "lon": 1, "tags": {"amenity": "cafe"}},  # sans nom
        {"type": "node", "id": 2, "lat": 1, "lon": 1, "tags": {"amenity": "bank", "name": "Banque"}},
        {"type": "way", "id": 3, "tags": {"amenity": "cafe", "name": "Café sans position"}},
    ],
)
def test_elements_ignores(element):
    assert element_vers_poi(element, "Tunis", MAINTENANT) is None


def test_horaires_plusieurs_regles():
    h = normaliser_horaires("Mo-Fr 09:00-12:00,14:00-18:00; Sa 09:00-13:00; Su off")
    assert h["lundi"] == h["vendredi"] == [["09:00", "12:00"], ["14:00", "18:00"]]
    assert h["samedi"] == [["09:00", "13:00"]]
    assert h["dimanche"] == []


def test_horaires_24_7_et_plage_seule():
    assert normaliser_horaires("24/7")["dimanche"] == [["00:00", "24:00"]]
    h = normaliser_horaires("08:00-23:00")
    assert all(h[j] == [["08:00", "23:00"]] for j in h)


def test_horaires_semaine_qui_passe_par_dimanche_et_regle_suivante_prioritaire():
    h = normaliser_horaires("Sa-Mo 10:00-20:00; Mo off")
    assert h["samedi"] == h["dimanche"] == [["10:00", "20:00"]]
    assert h["lundi"] == [] and h["mardi"] == []


@pytest.mark.parametrize("brut", ["sunrise-sunset", "Mo-Fr 9h-18h", "Jan-Mar 10:00-17:00", "", None])
def test_horaires_non_analysables(brut):
    assert normaliser_horaires(brut) is None


def test_horaires_bruts_conserves_si_non_analysables():
    element = {"type": "node", "id": 9, "lat": 1, "lon": 1,
               "tags": {"tourism": "museum", "name": "Musée", "opening_hours": "sunrise-sunset"}}
    poi = element_vers_poi(element, "Tunis", MAINTENANT)
    assert poi["horaires_ouverture"] == "sunrise-sunset"
    assert poi["horaires_normalises"] is None


@pytest.mark.parametrize(
    ("tags", "attendu"),
    [
        ({"charge": "12 TND"}, 12.0),
        ({"charge": "7,5 DT"}, 7.5),
        ({"charge": "10 dinars"}, 10.0),
        ({"fee": "no"}, 0.0),
        ({"charge": "5 EUR"}, None),
        ({"fee": "yes"}, None),
        ({}, None),
    ],
)
def test_extraire_prix(tags, attendu):
    assert extraire_prix(tags) == attendu
