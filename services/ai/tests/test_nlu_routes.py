"""POST /api/ai/comprendre : TestClient sans démarrage (pas de base), LLM simulé, auth facultative."""

from fastapi.testclient import TestClient

from voyara_common.security import create_access_token, create_refresh_token

from app.llm.base import LLMIndisponible
from app.main import app
from tests.test_nlu_extraction import FauxLLM

# Sans `with` : le lifespan (base postgres-ai) n'est pas déclenché.
client = TestClient(app)
URL = "/api/ai/comprendre"
CORPS = {"texte": "Je vais à Djerba 3 jours, 300 DT, en famille, culture et plage", "date_reference": "2026-11-09"}


def setup_function():
    app.state.llm = FauxLLM(erreur=LLMIndisponible("Ollama arrêté", "ollama"))


def teardown_function():
    del app.state.llm


def test_anonyme_reponse_des_regles_si_llm_absent():
    r = client.post(URL, json=CORPS)
    assert r.status_code == 200
    corps = r.json()
    assert corps["methode"] == "regles" and corps["provider"] == "regles"
    assert corps["demande"]["destination"] == "Djerba" and corps["demande"]["budget_montant"] == 300
    assert corps["champs_manquants"] == ["voyageurs"]
    assert corps["question_clarification"].startswith("Combien de personnes")


def test_avec_token_valide():
    jeton = create_access_token(42, 2)
    r = client.post(URL, json=CORPS, headers={"Authorization": f"Bearer {jeton}"})
    assert r.status_code == 200


def test_token_invalide_ou_de_rafraichissement_401():
    for jeton in ("pas-un-jwt", create_refresh_token(42, 2)):
        r = client.post(URL, json=CORPS, headers={"Authorization": f"Bearer {jeton}"})
        assert r.status_code == 401


def test_corps_invalide_422():
    assert client.post(URL, json={"texte": ""}).status_code == 422
    assert client.post(URL, json={"texte": "   "}).status_code == 422
    assert client.post(URL, json={"texte": "x" * 2001}).status_code == 422
    assert client.post(URL, json={}).status_code == 422


def test_hybride_avec_llm_simule():
    app.state.llm = FauxLLM({"type_voyage": "famille", "nb_voyageurs": 4, "nb_adultes": 2, "nb_enfants": 2,
                             "preferences": [], "activites_souhaitees": [], "niveau_marche_max": None,
                             "mobilite_reduite": None, "hors_sujet": False})
    corps = client.post(URL, json=CORPS).json()
    # « en famille » sans nombre : le garde-fou écarte les effectifs inventés par le LLM et la question est posée.
    assert corps["methode"] == "hybride" and corps["demande"]["nb_voyageurs"] is None
    assert corps["demande"]["type_voyage"] == "famille"
    assert corps["champs_manquants"] == ["voyageurs"] and corps["question_clarification"].startswith("Combien")
    corps = client.post(URL, json=CORPS | {"texte": CORPS["texte"] + ", nous sommes 4"}).json()
    assert corps["demande"]["nb_voyageurs"] == 4 and corps["champs_manquants"] == []
