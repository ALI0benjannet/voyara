"""Collecte Overpass : nouvelles tentatives, plafond, upsert idempotent, option --ville.

Réseau simulé (httpx.MockTransport) ; la base `voyara_ai` est annulée après chaque test.
"""

import importlib.util
from pathlib import Path

import httpx
import pytest
from sqlalchemy import func

from app import collecte
from app.collecte import OverpassIndisponible, collecter_ville, enregistrer, interroger_overpass, selectionner
from app.models import Poi
from app.villes import trouver_ville

URL = "https://overpass.test/api/interpreter"
DJERBA = trouver_ville("Djerba")
# La base contient aussi les vrais POI collectés : on ne compte que ceux du test
IDS_TEST = ("node/101", "node/102")


def noeud(identifiant, nom, **tags):
    return {"type": "node", "id": identifiant, "lat": 33.8 + identifiant / 1e4, "lon": 10.85,
            "tags": {"name": nom, **tags}}


def client_simule(reponses: list):
    """Client qui renvoie, dans l'ordre, chaque réponse (ou lève chaque exception)."""
    appels = []

    def gerer(requete: httpx.Request) -> httpx.Response:
        appels.append(requete)
        reponse = reponses[min(len(appels), len(reponses)) - 1]
        if isinstance(reponse, Exception):
            raise reponse
        return reponse

    return httpx.Client(transport=httpx.MockTransport(gerer)), appels


def ok(elements):
    return httpx.Response(200, json={"elements": elements})


def test_reessaie_apres_429_puis_reussit():
    client, appels = client_simule([httpx.Response(429), ok([noeud(1, "Café", amenity="cafe")])])
    attentes = []
    elements = interroger_overpass(client, URL, "requete", dormir=attentes.append)
    assert len(elements) == 1 and len(appels) == 2
    assert attentes == [10]


def test_reessaie_sur_delai_depasse_et_remarque_serveur():
    client, appels = client_simule([
        httpx.ReadTimeout("trop long"),
        httpx.Response(200, json={"elements": [], "remark": "runtime error: Query timed out"}),
        ok([]),
    ])
    attentes = []
    assert interroger_overpass(client, URL, "requete", dormir=attentes.append) == []
    assert len(appels) == 3 and attentes == [10, 30]


def test_abandon_apres_tous_les_essais():
    client, appels = client_simule([httpx.Response(504)])
    attentes = []
    with pytest.raises(OverpassIndisponible, match="4 essais"):
        interroger_overpass(client, URL, "requete", dormir=attentes.append)
    assert len(appels) == 4 and attentes == [10, 30, 60]


def test_erreur_non_reessayable_immediate():
    client, appels = client_simule([httpx.Response(400)])
    with pytest.raises(OverpassIndisponible, match="400"):
        interroger_overpass(client, URL, "requete", dormir=lambda s: None)
    assert len(appels) == 1


def test_requete_envoyee_contient_le_rayon_et_les_familles():
    client, appels = client_simule([ok([])])
    collecter_ville(client, URL, DJERBA, max_par_type=10, dormir=lambda s: None)
    corps = appels[0].content.decode()
    assert "around%3A16000%2C33.81%2C10.88" in corps  # data= encodé en formulaire
    assert "museum" in corps and "beach" in corps


def test_plafond_par_type_deterministe_et_dedoublonnage():
    from datetime import UTC, datetime

    elements = [noeud(i, f"Resto {i}", amenity="restaurant") for i in (5, 3, 9, 1)]
    elements += [noeud(2, "Plage", natural="beach"), noeud(2, "Plage", natural="beach")]  # doublon
    retenus = selectionner(elements, DJERBA, max_par_type=2, maintenant=datetime.now(UTC))
    assert [p["source_id"] for p in retenus] == ["node/1", "node/2", "node/3"]


def test_upsert_idempotent(db):
    client, _ = client_simule([ok([noeud(101, "Café des Nattes", amenity="cafe"),
                                   noeud(102, "Plage Sidi Mahrez", natural="beach")])])
    pois = collecter_ville(client, URL, DJERBA, 60, dormir=lambda s: None)

    assert enregistrer(db, pois) == (2, 0)
    assert db.query(func.count(Poi.id)).filter(Poi.source_id.in_(IDS_TEST)).scalar() == 2
    maj_avant = db.query(Poi).filter_by(source_id="node/101").one().maj_le

    # Deuxième collecte : un nom a changé dans OSM, aucun doublon ne doit apparaître
    client, _ = client_simule([ok([noeud(101, "Café des Nattes — terrasse", amenity="cafe"),
                                   noeud(102, "Plage Sidi Mahrez", natural="beach")])])
    pois = collecter_ville(client, URL, DJERBA, 60, dormir=lambda s: None)
    assert enregistrer(db, pois) == (0, 2)
    assert db.query(func.count(Poi.id)).filter(Poi.source_id.in_(IDS_TEST)).scalar() == 2
    db.expire_all()
    cafe = db.query(Poi).filter_by(source_id="node/101").one()
    assert cafe.nom == "Café des Nattes — terrasse"
    assert cafe.maj_le >= maj_avant


def _charger_script():
    chemin = Path(__file__).resolve().parents[1] / "scripts" / "collecter_pois.py"
    spec = importlib.util.spec_from_file_location("collecter_pois", chemin)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_option_ville_ne_collecte_que_les_villes_demandees(monkeypatch, capsys):
    script = _charger_script()
    demandees = []

    def faux_collecter(client, url, ville, max_par_type):
        demandees.append((ville.nom, max_par_type))
        return []

    monkeypatch.setattr(script, "collecter_ville", faux_collecter)
    monkeypatch.setattr(script.time, "sleep", lambda s: None)
    code = script.main(["--ville", "djerba", "--ville", "Sidi-Bou-Said", "--max-par-type", "5", "--dry-run"])
    assert code == 0
    assert demandees == [("Djerba", 5), ("Sidi Bou Saïd", 5)]


def test_option_ville_inconnue(capsys):
    script = _charger_script()
    assert script.main(["--ville", "Paris", "--dry-run"]) == 2
    assert "Ville inconnue" in capsys.readouterr().out


def test_une_ville_en_echec_donne_le_code_1(monkeypatch):
    script = _charger_script()

    def faux_collecter(client, url, ville, max_par_type):
        if ville.nom == "Tozeur":
            raise collecte.OverpassIndisponible("HTTP 504")
        return []

    monkeypatch.setattr(script, "collecter_ville", faux_collecter)
    monkeypatch.setattr(script.time, "sleep", lambda s: None)
    assert script.main(["--ville", "Djerba", "--ville", "Tozeur", "--dry-run"]) == 1
