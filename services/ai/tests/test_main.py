"""Point d'entrée FastAPI : santé, extension pgvector, routes publiques (Ollama simulé)."""

import httpx
from fastapi.testclient import TestClient

from app.main import app


def test_health_et_health_detaillee():
    with TestClient(app) as client:  # déclenche le lifespan : extension vector + tables
        app.state.llm.ollama.transport = httpx.MockTransport(lambda r: httpx.Response(200, json={"models": []}))
        assert client.get("/health").json()["status"] == "ok"

        corps = client.get("/api/ai/health").json()
        assert corps["status"] == "ok" and corps["base"] == "ok"
        assert corps["pgvector"] not in (None, "absente")  # extension vector active
        assert corps["llm"]["provider"] in ("claude", "ollama", "auto")
        assert corps["llm"]["ollama"]["joignable"] is True
        assert set(corps["llm"]["claude"]) == {"modele", "cle_configuree"}  # jamais la clé elle-même


def test_routes_exposees():
    chemins = set(app.openapi()["paths"])
    # Démonstration temporaire de la validation DL (page « DL test ») : 6 routes publiques sans LLM.
    dl = {f"/api/ai/dl/{r}" for r in ("resultats", "etat", "exemples", "prechauffer", "rechercher", "classifier")}
    assert chemins == {"/health", "/api/ai/health", "/api/ai/comprendre"} | dl
    assert not any("/internal" in c for c in chemins)
