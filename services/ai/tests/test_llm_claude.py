"""Fournisseur Claude : requête envoyée et normalisation, avec un faux client SDK (aucun appel réel)."""

from types import SimpleNamespace

import anthropic
import httpx2
import pytest

from app.llm.base import LLMCleAbsente, LLMIndisponible, LLMRefus, LLMRequeteInvalide, Message, Outil
from app.llm.claude import BETA_REPLI_SERVEUR, ClaudeProvider

pytestmark = pytest.mark.anyio

REQUETE_HTTP = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
OUTIL = Outil("meteo", "Météo d'une ville", {
    "type": "object", "properties": {"ville": {"type": "string"}},
    "required": ["ville"], "additionalProperties": False,
})


def bloc(type_, **champs):
    return SimpleNamespace(type=type_, **champs)


def reponse(*blocs, stop_reason="end_turn", entree=120, sortie=30, modele="claude-sonnet-5-5"):
    return SimpleNamespace(content=list(blocs), stop_reason=stop_reason, model=modele, stop_details=None,
                           usage=SimpleNamespace(input_tokens=entree, output_tokens=sortie))


class FauxClient:
    def __init__(self, resultat):
        self.appels = []

        async def create(**requete):
            self.appels.append(requete)
            if isinstance(resultat, Exception):
                raise resultat
            return resultat

        self.beta = SimpleNamespace(messages=SimpleNamespace(create=create))


def provider(resultat, **options):
    client = FauxClient(resultat)
    return ClaudeProvider("cle-de-test", "claude-sonnet-5-5", client=client, **options), client


async def test_requete_envoyee():
    claude, client = provider(reponse(bloc("text", text="Bonjour")))
    await claude.generer([Message("user", "Salut")], systeme="Tu es Voyara.", outils=[OUTIL],
                         max_tokens=2000, temperature=0.2)
    requete = client.appels[0]
    assert requete["model"] == "claude-sonnet-5-5" and requete["max_tokens"] == 2000
    assert requete["system"] == "Tu es Voyara."
    assert requete["messages"] == [{"role": "user", "content": "Salut"}]
    assert requete["tools"][0] == {"name": "meteo", "description": "Météo d'une ville",
                                   "input_schema": OUTIL.schema, "strict": True}
    assert requete["output_config"] == {"effort": "medium"}
    # Version d'API 2026-10-21 : temperature refusée ; choix d'outil forcé refusé sur Sonnet 5.5.
    assert "temperature" not in requete and "tool_choice" not in requete
    assert requete["betas"] == [BETA_REPLI_SERVEUR] and requete["fallbacks"] == "default"


async def test_strict_seulement_si_schema_ferme():
    ouvert = Outil("libre", "Sans contrainte", {"type": "object", "properties": {}})
    claude, client = provider(reponse(bloc("text", text="ok")))
    await claude.generer([Message("user", "x")], outils=[ouvert])
    assert "strict" not in client.appels[0]["tools"][0]


async def test_sortie_structuree_et_cout():
    claude, client = provider(reponse(bloc("thinking", thinking=""), bloc("text", text='{"ville": "Djerba"}'),
                                      entree=1_000, sortie=500))
    schema = {"type": "object", "properties": {"ville": {"type": "string"}}, "required": ["ville"],
              "additionalProperties": False}
    r = await claude.generer([Message("user", "Je vais à Jerba")], schema_sortie=schema)
    assert client.appels[0]["output_config"]["format"] == {"type": "json_schema", "schema": schema}
    assert r.donnees == {"ville": "Djerba"} and r.texte == '{"ville": "Djerba"}'
    assert (r.tokens_entree, r.tokens_sortie) == (1_000, 500)
    assert r.cout_estime == pytest.approx(0.007)  # 1000 x 2 $ + 500 x 10 $ par million
    assert len(r.blocs_bruts) == 2  # le bloc thinking est conservé pour l'historique


async def test_appel_outil_normalise():
    claude, _ = provider(reponse(bloc("tool_use", id="tu_1", name="meteo", input={"ville": "Tozeur"}),
                                 stop_reason="tool_use"))
    r = await claude.generer([Message("user", "Météo à Tozeur ?")], outils=[OUTIL])
    assert r.raison_arret == "tool_use"
    assert [(a.id, a.nom, a.arguments) for a in r.appels_outils] == [("tu_1", "meteo", {"ville": "Tozeur"})]


async def test_options_desactivables():
    claude, client = provider(reponse(bloc("text", text="ok")), effort=None, replis_serveur=False)
    await claude.generer([Message("user", "x")])
    assert not {"betas", "fallbacks", "output_config"} & set(client.appels[0])


async def test_modele_de_repli_compte_au_bon_tarif():
    claude, _ = provider(reponse(bloc("text", text="ok"), modele="claude-opus-5-5", entree=1_000, sortie=0))
    r = await claude.generer([Message("user", "x")])
    assert r.modele == "claude-opus-5-5" and r.cout_estime == pytest.approx(0.004)


async def test_refus_de_securite():
    refus = reponse(stop_reason="refusal")
    refus.stop_details = SimpleNamespace(category="cyber")
    claude, _ = provider(refus)
    with pytest.raises(LLMRefus) as exc:
        await claude.generer([Message("user", "x")])
    assert exc.value.categorie == "cyber"


async def test_cle_absente_sans_appel():
    with pytest.raises(LLMCleAbsente):
        await ClaudeProvider(None, "claude-sonnet-5-5").generer([Message("user", "x")])


def _statut(cls, code):
    return cls(str(code), response=httpx2.Response(code, request=REQUETE_HTTP), body=None)


@pytest.mark.parametrize("erreur, attendue", [
    (anthropic.APITimeoutError(request=REQUETE_HTTP), LLMIndisponible),
    (anthropic.APIConnectionError(request=REQUETE_HTTP), LLMIndisponible),
    (_statut(anthropic.RateLimitError, 429), LLMIndisponible),
    (_statut(anthropic.InternalServerError, 503), LLMIndisponible),
    (_statut(anthropic.AuthenticationError, 401), LLMCleAbsente),
    (_statut(anthropic.BadRequestError, 400), LLMRequeteInvalide),
    (_statut(anthropic.NotFoundError, 404), LLMRequeteInvalide),
])
async def test_erreurs_sdk_traduites(erreur, attendue):
    claude, _ = provider(erreur)
    with pytest.raises(attendue):
        await claude.generer([Message("user", "x")])
