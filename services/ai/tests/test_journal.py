"""Journal `llm_appels` sur la vraie base `voyara_ai` (transaction annulée après chaque test)."""

from contextlib import contextmanager

import pytest

from app.llm.base import Message, ReponseLLM
from app.llm.fabrique import ClientLLM
from app.llm.journal import JournalLLM
from app.models import LlmAppel
from tests.test_fabrique import Faux

pytestmark = pytest.mark.anyio


@pytest.fixture
def journal(db):
    @contextmanager
    def session_de_test():
        yield db  # la session du test : ses commit() deviennent des points de sauvegarde

    return JournalLLM(session_de_test)


async def test_ligne_ecrite(db, journal):
    identifiant = await journal.enregistrer("claude", "claude-sonnet-5-5", "succes", "essai",
                                            tokens_entree=1200, tokens_sortie=300, latence_ms=850,
                                            cout_estime=0.0054)
    ligne = db.get(LlmAppel, identifiant)
    assert (ligne.provider, ligne.statut, ligne.usage) == ("claude", "succes", "essai")
    assert (ligne.tokens_entree, ligne.tokens_sortie, ligne.latence_ms) == (1200, 300, 850)
    assert ligne.cout_estime == pytest.approx(0.0054) and ligne.cree_le is not None


async def test_erreur_tronquee_sans_secret(db, journal):
    identifiant = await journal.enregistrer("ollama", "qwen2.5:7b", "erreur",
                                            erreur=RuntimeError("x" * 2000))
    erreur = db.get(LlmAppel, identifiant).erreur
    assert erreur.startswith("RuntimeError: ") and len(erreur) == 500


async def test_chaine_de_bascule_en_base(db, journal):
    llm = ClientLLM("auto", Faux("claude", cle_presente=False), Faux("ollama"), journal)
    await llm.generer([Message("user", "Bonjour")], usage="essai")
    bascule, succes = db.query(LlmAppel).filter(LlmAppel.usage == "essai").order_by(LlmAppel.id).all()[-2:]
    assert (bascule.provider, bascule.statut) == ("claude", "bascule")
    assert (succes.provider, succes.statut, succes.appel_parent_id) == ("ollama", "succes", bascule.id)


async def test_base_indisponible_ne_casse_pas_l_appel():
    def session_en_panne():
        raise ConnectionError("base injoignable")

    llm = ClientLLM("ollama", Faux("claude"), Faux("ollama"), JournalLLM(session_en_panne))
    reponse = await llm.generer([Message("user", "Bonjour")])
    assert isinstance(reponse, ReponseLLM) and reponse.provider == "ollama"
