"""Pré-étiquetage (règles, Ollama simulé) et import du CSV."""

import json
from datetime import time

import httpx
import pytest
from pydantic import ValidationError

import importer_propositions
import pre_etiqueter
from pre_etiqueter import ActiviteSource, proposer_ollama, proposer_regles


def act(titre, description, categorie="Culture", duree=120, heures=()):
    return ActiviteSource(1, titre, description, categorie, duree, list(heures))


def test_regles_sortie_valide_et_expliquee():
    prop = proposer_regles(act(
        "Croisière au couchant à Djerba",
        "Voilier traditionnel, baignade dans une crique et thé pendant que le soleil tombe.",
        categorie="Mer",
    ))
    assert prop.tags.themes[0] == "nautique"           # thème de la catégorie en tête
    assert "plage" in prop.tags.themes
    assert prop.tags.moment_ideal == "soir"
    assert prop.tags.niveau_marche == 1
    assert prop.raisons and prop.confiance in {"haute", "moyenne", "faible"}


def test_regles_toponymes_ne_trompent_pas():
    # « Hammamet » ne doit pas déclencher « hammam », ni « golfe » le golf, ni « Houmt Souk » le shopping.
    prop = proposer_regles(act(
        "Médina et Kasbah de Hammamet",
        "Les remparts au bord du golfe, puis départ de Houmt Souk.",
    ))
    assert "detente" not in prop.tags.themes
    assert "shopping" not in prop.tags.themes
    assert "famille" in prop.tags.public


def test_regles_randonnee_marche_elevee_et_douce():
    assert proposer_regles(act("Randonnée au djebel", "Montée vers le sommet.", "Aventure")).tags.niveau_marche == 3
    assert proposer_regles(act("Randonnée douce", "Marche facile.", "Aventure")).tags.niveau_marche == 2


def test_regles_moment_par_creneaux():
    tard = proposer_regles(act("Atelier pain", "Pétrir la pâte.", "Gastronomie", heures=[time(17, 0)]))
    assert tard.tags.moment_ideal == "soir"
    # Un créneau unique à 9 h ne prouve rien : on reste « indifferent ».
    neutre = proposer_regles(act("Atelier pain", "Pétrir la pâte.", "Gastronomie", heures=[time(9, 0)]))
    assert neutre.tags.moment_ideal == "indifferent"


def test_regles_famille_et_adultes():
    enfants = proposer_regles(act("Zoo", "Une sortie avec des enfants.", "Famille & loisirs"))
    assert enfants.tags.public == ["famille", "enfants"]
    adultes = proposer_regles(act("Quad", "Conducteur dès 16 ans.", "Aventure"))
    assert "enfants" not in adultes.tags.public and "famille" not in adultes.tags.public


def _ollama_qui_repond(monkeypatch, contenu: dict):
    texte = json.dumps(contenu)

    def faux_post(url, json=None, timeout=None):  # même signature que l'appel réel
        assert url.endswith("/api/chat") and json["format"]["type"] == "object"
        return httpx.Response(
            200, json={"message": {"content": texte}}, request=httpx.Request("POST", url)
        )
    monkeypatch.setattr(httpx, "post", faux_post)


def test_ollama_reponse_valide(monkeypatch):
    _ollama_qui_repond(monkeypatch, {
        "themes": ["desert"], "public": ["couple"], "niveau_marche": 1,
        "interieur": False, "moment_ideal": "soir",
    })
    prop = proposer_ollama(act("Bivouac", "Nuit sous les étoiles."), "modele", "http://ollama")
    assert prop.tags.themes == ["desert"]


def test_ollama_valeur_hors_vocabulaire_rejetee(monkeypatch):
    _ollama_qui_repond(monkeypatch, {
        "themes": ["ski"], "public": ["couple"], "niveau_marche": 1,
        "interieur": False, "moment_ideal": "soir",
    })
    with pytest.raises(ValidationError):
        proposer_ollama(act("Bivouac", "Nuit sous les étoiles."), "modele", "http://ollama")


def test_consigne_llm_liste_tout_le_vocabulaire():
    for valeur in (*pre_etiqueter.THEMES, *pre_etiqueter.PUBLICS, *pre_etiqueter.MOMENTS):
        assert valeur in pre_etiqueter.CONSIGNE


# --- Import du CSV -------------------------------------------------------------

LIGNE = {
    "themes": "plage|nautique", "public": "couple", "niveau_marche": "1",
    "interieur": "non", "moment_ideal": "soir",
}


def test_import_lit_une_ligne_valide():
    tags = importer_propositions.lire_ligne(LIGNE)
    assert tags.themes == ["plage", "nautique"] and tags.interieur is False


@pytest.mark.parametrize(
    "modification",
    [{"themes": "plage|ski"}, {"niveau_marche": "7"}, {"moment_ideal": "nuit"},
     {"interieur": "peut-être"}, {"public": ""}],
)
def test_import_refuse_les_valeurs_interdites(modification):
    with pytest.raises((ValidationError, ValueError)):
        importer_propositions.lire_ligne({**LIGNE, **modification})
