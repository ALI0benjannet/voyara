"""Fournisseur Ollama : API /api/chat simulée par httpx.MockTransport (aucun appel réel)."""

import json

import httpx
import pytest

from app.llm.base import LLMIndisponible, LLMRequeteInvalide, LLMSortieInvalide, Message, Outil
from app.llm.ollama import OllamaProvider

pytestmark = pytest.mark.anyio


def ollama(gerer):
    requetes = []

    def enregistrer(requete: httpx.Request) -> httpx.Response:
        requetes.append(json.loads(requete.content) if requete.content else None)
        return gerer(requete)

    transport = httpx.MockTransport(enregistrer)
    return OllamaProvider("http://ollama.test", "qwen2.5:7b", transport=transport), requetes


def corps(contenu="", tool_calls=None):
    message = {"role": "assistant", "content": contenu}
    if tool_calls:
        message["tool_calls"] = tool_calls
    return {"model": "qwen2.5:7b", "message": message, "done_reason": "stop",
            "prompt_eval_count": 42, "eval_count": 7}


async def test_requete_et_sortie_json():
    schema = {"type": "object", "properties": {"duree_jours": {"type": "integer"}}, "required": ["duree_jours"]}
    o, requetes = ollama(lambda r: httpx.Response(200, json=corps('{"duree_jours": 3}')))
    r = await o.generer([Message("user", "3 jours f Jerba")], systeme="Extrais.", schema_sortie=schema,
                        max_tokens=500, temperature=0)
    envoye = requetes[0]
    assert envoye["model"] == "qwen2.5:7b" and envoye["stream"] is False
    assert envoye["messages"][0] == {"role": "system", "content": "Extrais."}
    assert envoye["format"] == schema and envoye["options"] == {"num_predict": 500, "temperature": 0}
    assert r.donnees == {"duree_jours": 3}
    assert (r.provider, r.tokens_entree, r.tokens_sortie, r.cout_estime) == ("ollama", 42, 7, 0.0)


async def test_sans_temperature_ni_schema():
    o, requetes = ollama(lambda r: httpx.Response(200, json=corps("Bonjour")))
    r = await o.generer([Message("user", "Salut")])
    assert "format" not in requetes[0] and "temperature" not in requetes[0]["options"]
    assert r.texte == "Bonjour" and r.donnees is None


async def test_appels_outils():
    appel = [{"function": {"name": "meteo", "arguments": {"ville": "Djerba"}}}]
    o, requetes = ollama(lambda r: httpx.Response(200, json=corps(tool_calls=appel)))
    outil = Outil("meteo", "Météo", {"type": "object", "properties": {"ville": {"type": "string"}}})
    r = await o.generer([Message("user", "Météo ?")], outils=[outil])
    assert requetes[0]["tools"][0]["function"]["name"] == "meteo"
    assert [(a.nom, a.arguments) for a in r.appels_outils] == [("meteo", {"ville": "Djerba"})]
    assert r.raison_arret == "tool_use"


async def test_json_invalide():
    o, _ = ollama(lambda r: httpx.Response(200, json=corps("pas du json")))
    with pytest.raises(LLMSortieInvalide):
        await o.generer([Message("user", "x")], schema_sortie={"type": "object"})


async def test_pannes():
    def delai(requete):
        raise httpx.ReadTimeout("lent", request=requete)

    o, _ = ollama(delai)
    with pytest.raises(LLMIndisponible):
        await o.generer([Message("user", "x")])
    o, _ = ollama(lambda r: httpx.Response(500))
    with pytest.raises(LLMIndisponible):
        await o.generer([Message("user", "x")])
    o, _ = ollama(lambda r: httpx.Response(404, json={"error": "model not found"}))
    with pytest.raises(LLMRequeteInvalide):  # modèle non téléchargé
        await o.generer([Message("user", "x")])


async def test_est_joignable():
    o, _ = ollama(lambda r: httpx.Response(200, json={"models": []}))
    assert await o.est_joignable() is True

    def refus(requete):
        raise httpx.ConnectError("refusé", request=requete)

    o, _ = ollama(refus)
    assert await o.est_joignable() is False
