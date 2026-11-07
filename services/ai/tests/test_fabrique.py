"""Fabrique et bascule Claude -> Ollama, avec des fournisseurs simulés et un journal en mémoire."""

import asyncio

import pytest

from app.llm.base import LLMIndisponible, LLMProvider, LLMRefus, LLMSortieInvalide, Message, ReponseLLM
from app.llm.fabrique import ClientLLM, creer_client_llm
from app.llm.journal import JournalMemoire

pytestmark = pytest.mark.anyio
MESSAGES = [Message("user", "Bonjour")]


class Faux(LLMProvider):
    def __init__(self, nom, resultat=None, cle_presente=True):
        self.nom = nom
        self.resultat = resultat
        self.cle_presente = cle_presente
        self.appels = 0

    @property
    def modele(self):
        return f"modele-{self.nom}"

    async def generer(self, messages, systeme=None, outils=None, schema_sortie=None,
                      max_tokens=16000, temperature=None):
        self.appels += 1
        if isinstance(self.resultat, Exception):
            raise self.resultat
        return ReponseLLM(texte=f"réponse {self.nom}", provider=self.nom, modele=self.modele,
                          tokens_entree=10, tokens_sortie=5, latence_ms=12, cout_estime=0.0)


def client(mode, claude, ollama):
    journal = JournalMemoire()
    return ClientLLM(mode, claude, ollama, journal), journal


async def test_auto_sans_cle_bascule_directement():
    claude, ollama = Faux("claude", cle_presente=False), Faux("ollama")
    llm, journal = client("auto", claude, ollama)
    r = await llm.generer(MESSAGES, usage="essai")
    assert claude.appels == 0 and r.provider == "ollama" and r.bascule_depuis == "claude"
    assert [(ligne["provider"], ligne["statut"], ligne["erreur"]) for ligne in journal.lignes] == [
        ("claude", "bascule", "ANTHROPIC_API_KEY absente"), ("ollama", "succes", None)]
    assert journal.lignes[1]["appel_parent_id"] == 1 and journal.lignes[1]["usage"] == "essai"


async def test_auto_bascule_sur_panne():
    llm, journal = client("auto", Faux("claude", LLMIndisponible("délai dépassé", "claude")), Faux("ollama"))
    r = await llm.generer(MESSAGES)
    assert r.provider == "ollama"
    assert [ligne["statut"] for ligne in journal.lignes] == ["bascule", "succes"]
    assert "délai dépassé" in journal.lignes[0]["erreur"]


async def test_auto_claude_disponible():
    ollama = Faux("ollama")
    llm, journal = client("auto", Faux("claude"), ollama)
    r = await llm.generer(MESSAGES)
    assert r.provider == "claude" and r.bascule_depuis is None and ollama.appels == 0
    assert journal.lignes[0]["tokens_entree"] == 10 and journal.lignes[0]["statut"] == "succes"


async def test_pas_de_bascule_sur_refus():
    ollama = Faux("ollama")
    llm, journal = client("auto", Faux("claude", LLMRefus("refus", "claude", "cyber")), ollama)
    with pytest.raises(LLMRefus):
        await llm.generer(MESSAGES)
    assert ollama.appels == 0 and journal.lignes[0]["statut"] == "refus"


async def test_pas_de_bascule_sur_sortie_invalide():
    ollama = Faux("ollama")
    llm, journal = client("auto", Faux("claude", LLMSortieInvalide("json", "claude")), ollama)
    with pytest.raises(LLMSortieInvalide):
        await llm.generer(MESSAGES)
    assert ollama.appels == 0 and journal.lignes[0]["statut"] == "erreur"


async def test_latence_journalisee_meme_en_erreur():
    class Lent(Faux):
        async def generer(self, *args, **kwargs):
            await asyncio.sleep(0.05)
            raise LLMIndisponible("délai dépassé", self.nom)

    llm, journal = client("ollama", Faux("claude"), Lent("ollama"))
    with pytest.raises(LLMIndisponible):
        await llm.generer(MESSAGES)
    assert journal.lignes[0]["latence_ms"] >= 40  # le temps perdu est mesuré, pas 0


async def test_auto_les_deux_en_panne():
    llm, journal = client("auto", Faux("claude", LLMIndisponible("x", "claude")),
                          Faux("ollama", LLMIndisponible("y", "ollama")))
    with pytest.raises(LLMIndisponible):
        await llm.generer(MESSAGES)
    assert [ligne["statut"] for ligne in journal.lignes] == ["bascule", "erreur"]


async def test_modes_stricts_ne_basculent_jamais():
    ollama = Faux("ollama")
    llm, journal = client("claude", Faux("claude", LLMIndisponible("x", "claude")), ollama)
    with pytest.raises(LLMIndisponible):
        await llm.generer(MESSAGES)
    assert ollama.appels == 0 and journal.lignes[0]["statut"] == "erreur"

    claude = Faux("claude")
    llm, _ = client("ollama", claude, Faux("ollama"))
    assert (await llm.generer(MESSAGES)).provider == "ollama" and claude.appels == 0


def test_mode_inconnu_et_fabrique():
    with pytest.raises(ValueError):
        ClientLLM("gpt", Faux("claude"), Faux("ollama"), JournalMemoire())

    class Reglages:
        LLM_PROVIDER, ANTHROPIC_API_KEY, CLAUDE_MODEL, CLAUDE_EFFORT = "auto", None, "claude-sonnet-5-5", "low"
        CLAUDE_TIMEOUT_S, CLAUDE_MAX_RETRIES, CLAUDE_FALLBACKS = 30.0, 0, False
        OLLAMA_URL, OLLAMA_MODEL, OLLAMA_TIMEOUT_S = "http://x:11434", "qwen2.5:7b", 60.0

    llm = creer_client_llm(Reglages, JournalMemoire())
    assert llm.mode == "auto" and llm.claude.cle_presente is False
    assert (llm.claude.modele, llm.claude.effort, llm.ollama.modele) == ("claude-sonnet-5-5", "low", "qwen2.5:7b")
