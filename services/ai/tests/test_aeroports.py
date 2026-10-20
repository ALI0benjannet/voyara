"""POI « aeroport » (étape 2-bis) : requête nationale, rattachement à une ville, upsert.

Réseau simulé (httpx.MockTransport) ; la base `voyara_ai` est annulée après chaque test.
"""

import importlib.util
from datetime import UTC, datetime
from pathlib import Path

import httpx
from sqlalchemy import func

from app.collecte import (
    collecter_aeroports,
    construire_requete_aeroports,
    distance_km,
    enregistrer,
    selectionner_aeroports,
    ville_la_plus_proche,
)
from app.models import TYPES_POI, Poi

URL = "https://overpass.test/api/interpreter"
MAINTENANT = datetime(2026, 10, 20, 12, 0, tzinfo=UTC)


def aerodrome(type_osm, identifiant, iata, nom, lat, lon):
    element = {"type": type_osm, "id": identifiant,
               "tags": {"aeroway": "aerodrome", "iata": iata, "name": nom}}
    if type_osm == "node":
        element |= {"lat": lat, "lon": lon}
    else:
        element["center"] = {"lat": lat, "lon": lon}
    return element


# Coordonnées approximatives des aéroports réels (OSM)
ELEMENTS = [
    aerodrome("way", 9001, "TUN", "Aéroport international de Tunis-Carthage", 36.851, 10.227),
    aerodrome("node", 9002, "TUN", "Tunis-Carthage (nœud)", 36.850, 10.230),  # doublon
    aerodrome("way", 9003, "DJE", "Aéroport international de Djerba-Zarzis", 33.875, 10.775),
    aerodrome("way", 9004, "NBE", "Aéroport international d'Enfidha-Hammamet", 36.076, 10.439),
    aerodrome("way", 9005, "SFA", "Aéroport international de Sfax-Thyna", 34.718, 10.691),
]


def test_type_aeroport_declare():
    assert "aeroport" in TYPES_POI


def test_requete_nationale_par_code_iata():
    requete = construire_requete_aeroports()
    assert '"ISO3166-1"="TN"' in requete
    assert '["aeroway"="aerodrome"]["iata"]' in requete
    assert "out center tags;" in requete


def test_distance_et_ville_la_plus_proche():
    assert round(distance_km(36.8, 10.17, 36.8, 10.17)) == 0
    assert 110 < distance_km(36.8065, 10.1815, 35.8256, 10.6411) < 125  # Tunis-Sousse à vol d'oiseau
    assert ville_la_plus_proche(36.851, 10.227).nom == "Tunis"
    assert ville_la_plus_proche(33.875, 10.775).nom == "Djerba"
    assert ville_la_plus_proche(34.718, 10.691) is None  # Sfax : aucune ville couverte à 60 km


def test_selection_un_poi_par_iata_avec_ville():
    pois = selectionner_aeroports(ELEMENTS, MAINTENANT)
    assert [(p["tags"]["iata"], p["ville"]) for p in pois] == [
        ("DJE", "Djerba"), ("NBE", "Sousse"), ("TUN", "Tunis"),
    ]
    tunis = next(p for p in pois if p["tags"]["iata"] == "TUN")
    assert tunis["source_id"] == "way/9001"  # le contour est préféré au nœud
    assert all(p["type"] == "aeroport" and p["source"] == "osm" for p in pois)


def test_collecte_et_upsert_sans_doublon(db):
    def gerer(requete: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"elements": ELEMENTS})

    client = httpx.Client(transport=httpx.MockTransport(gerer))
    ids = ("way/9001", "way/9003", "way/9004")
    pois = collecter_aeroports(client, URL, dormir=lambda s: None)
    assert enregistrer(db, pois) == (3, 0)
    assert enregistrer(db, collecter_aeroports(client, URL, dormir=lambda s: None)) == (0, 3)
    assert db.query(func.count(Poi.id)).filter(Poi.source_id.in_(ids)).scalar() == 3


def test_option_aeroports_du_script(monkeypatch, capsys):
    chemin = Path(__file__).resolve().parents[1] / "scripts" / "collecter_pois.py"
    spec = importlib.util.spec_from_file_location("collecter_pois", chemin)
    script = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(script)
    villes_appelees = []
    monkeypatch.setattr(script, "collecter_aeroports",
                        lambda client, url: selectionner_aeroports(ELEMENTS, MAINTENANT))
    monkeypatch.setattr(script, "collecter_ville", lambda *a: villes_appelees.append(a) or [])
    assert script.main(["--aeroports", "--dry-run"]) == 0
    sortie = capsys.readouterr().out
    assert villes_appelees == []  # pas de collecte par ville
    assert "TUN" in sortie and "3 POI (dry-run" in sortie
