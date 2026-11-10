"""Orchestration du module 1 : `comprendre(texte, date_reference)`.

Méthode **hybride** (par défaut) :
1. les règles (`regles.extraire`) remplissent les faits explicites : montants, devise, durée, nuits,
   dates, villes, langue, mots-clés de transport ;
2. le LLM, via `ClientLLM.generer(schema_sortie=…, usage="nlu")`, remplit ce qui demande de
   comprendre, sur un schéma réduit : voyageurs, type de voyage, préférences, activités, contraintes,
   hors sujet ;
3. fusion champ par champ (une valeur « sûre » des règles l'emporte), normalisation, validation,
   champs manquants, question de clarification.

Si le LLM est absent, en panne, trop lent ou rend un JSON invalide : réponse des règles seules
(`methode = "regles"`), jamais d'erreur 500. Méthodes `regles` et `llm` (LLM seul, schéma complet)
disponibles pour la comparaison de l'évaluation.
"""

import asyncio
import copy
import logging
import re
import time
from datetime import date
from typing import Any

from pydantic import ValidationError

from app.llm.base import ErreurLLM, LLMRefus
from app.nlu import normalisation as n
from app.nlu.clarification import question_clarification
from app.nlu.prompt import construire_messages
from app.nlu.regles import _JOURS, _NUITS, _RE_DEVISE, _RE_MOIS, NUM, ResultatRegles, _un_de, extraire, nombre
from app.nlu.schemas import (
    DemandeVoyage,
    ReponseComprendre,
    avertissements_demande,
    schema_llm_complet,
    schema_llm_hybride,
)
from scripts import jeu_nlu

logger = logging.getLogger(__name__)

METHODES = ("regles", "hybride", "llm")
AVERTISSEMENT_REPLI = "compréhension simplifiée : LLM indisponible ou trop lent, réponse des règles seules"
MAX_TOKENS_HYBRIDE = 300
MAX_TOKENS_COMPLET = 700
TEMPERATURE = 0.0  # extraction déterministe (jamais envoyée à Claude, cf. couche LLM)


# --- Fusion règles + LLM --------------------------------------------------------

def _activite_presente(activite: str, texte_norm: str) -> bool:
    """Garde-fou anti-invention : la majorité des mots de l'activité figurent dans le message."""
    mots = jeu_nlu.normaliser_activite(activite)
    if not mots:
        return False
    texte_mots = set(jeu_nlu.normaliser_activite(texte_norm))
    return sum(m in texte_mots for m in mots) / len(mots) >= 0.5


# Nombres qui ne sont pas des effectifs : durée, nuits, monnaie, âge, heure, distance, date.
_UNITE_NON_EFFECTIF = re.compile(
    rf"^(?:\s*(?:et|and|ou|or|,|و|-|a)\s*\d+)*\s*(?:{_JOURS}|{_NUITS}|{_RE_DEVISE}|k\b|ans?\b|years?\b|سنوات|سنه|عام|h\b|heures?|hours?|km\b|%|"
    rf"{_RE_MOIS})(?!\w)")
# Effectifs dits sans chiffre : « à deux », « couple », « seul », duel arabe…
_EFFECTIFS_IMPLICITES = (
    (2, _un_de(["a deux", "nous deux", "tous les deux", "two of us", "both of us", "ahna zouz", "couple",
                "en couple", "lune de miel", "honeymoon", "زوجان", "زوجين", "شخصان", "شخصين", "طفلين", "ولدين",
                "صغيرين"])),
    (1, _un_de(["seul", "seule", "solo", "alone", "wa7di", "وحدي", "un bebe", "a baby", "un enfant", "one kid"])),
)


def nombres_du_texte(texte_norm: str) -> set[int]:
    """Effectifs que le message dit explicitement : chiffres (arabes compris, déjà convertis par la
    normalisation) et mots-nombres (fr / en / darija / arabe), hors durées, montants, âges et dates ;
    plus les effectifs implicites (« à deux », « couple » = 2, « seul » = 1)."""
    trouves: set[int] = set()
    for m in re.finditer(rf"(?:(?<![\w.,])|(?<=(?<!\w)[لوب])){NUM}(?![\w.,]\d)", texte_norm):
        if _UNITE_NON_EFFECTIF.match(texte_norm[m.end():m.end() + 25]):
            continue
        valeur = nombre(m.group(1))
        if valeur is not None:
            trouves.add(valeur)
    for valeur, motif in _EFFECTIFS_IMPLICITES:
        if re.search(motif, texte_norm):
            trouves.add(valeur)
    return trouves


def garder_voyageurs_du_llm(llm: dict[str, Any], texte_norm: str) -> dict[str, int | None]:
    """Garde-fou anti-invention (principe du README : le LLM comprend, les faits viennent du texte).
    `nb_adultes` et `nb_enfants` du LLM ne sont gardés que si le nombre figure dans le message ;
    `nb_voyageurs` aussi, ou s'il s'en déduit directement : locuteur + N (« moi et 3 amis » = 4) ou
    somme de deux nombres dits (« 2 adultes et 3 enfants » = 5). Sinon : vide, comme les règles."""
    dits = nombres_du_texte(texte_norm)
    deduits = dits | {k + 1 for k in dits} | {a + b for a in dits for b in dits}
    valeurs = {cle: n.entier_ou_none(llm.get(cle)) for cle in ("nb_voyageurs", "nb_adultes", "nb_enfants")}
    return {
        "nb_voyageurs": valeurs["nb_voyageurs"] if valeurs["nb_voyageurs"] in deduits else None,
        "nb_adultes": valeurs["nb_adultes"] if valeurs["nb_adultes"] in dits else None,
        "nb_enfants": valeurs["nb_enfants"] if valeurs["nb_enfants"] in dits else None,
    }


def fusionner(regles: ResultatRegles, llm: dict[str, Any], texte: str, transport: bool = False,
              garde_voyageurs: bool = True) -> dict[str, Any]:
    """Champ par champ : règle sûre > LLM > règle non sûre. `transport=True` : variante v2."""
    brut = copy.deepcopy(regles.brut)
    surs = regles.surs
    if brut.get("hors_sujet"):
        return brut  # aucun signal de voyage : décision des règles
    sans_faits = brut["destination"] is None and brut["duree_jours"] is None and brut["budget_montant"] is None
    if llm.get("hors_sujet") is True and sans_faits:
        return n.demande_hors_sujet(brut["langue"])

    texte_norm = n.texte_normalise(texte)
    if "voyageurs" not in surs and any(llm.get(k) is not None for k in ("nb_voyageurs", "nb_adultes", "nb_enfants")):
        if garde_voyageurs:
            brut.update(garder_voyageurs_du_llm(llm, texte_norm))
        else:
            for cle in ("nb_voyageurs", "nb_adultes", "nb_enfants"):
                brut[cle] = n.entier_ou_none(llm.get(cle))
    if "type_voyage" not in surs and llm.get("type_voyage") in jeu_nlu.TYPES_VOYAGE:
        brut["type_voyage"] = llm["type_voyage"]
    if "preferences" not in surs and isinstance(llm.get("preferences"), list):
        brut["preferences"] = [p for p in llm["preferences"] if p in jeu_nlu.THEMES]

    activites_llm = [a for a in llm.get("activites_souhaitees") or []
                     if isinstance(a, str) and _activite_presente(a, texte_norm)]
    activites = list(activites_llm)
    for a in brut["activites_souhaitees"]:  # activités des règles non couvertes par le LLM
        if not any(jeu_nlu.activites_correspondent(a, b) for b in activites):
            activites.append(a)
    brut["activites_souhaitees"] = activites

    if "contraintes" not in surs:
        niveau = n.entier_ou_none(llm.get("niveau_marche_max"))
        brut["contraintes"]["niveau_marche_max"] = niveau if niveau in (1, 2, 3) else None
        brut["contraintes"]["mobilite_reduite"] = True if n.booleen_ou_none(llm.get("mobilite_reduite")) else None
    if transport:
        _fusionner_transport(brut, llm, texte_norm)
    return brut


def _fusionner_transport(brut: dict[str, Any], llm: dict[str, Any], texte_norm: str) -> None:
    """Hybride v2 : un besoin trouvé par mot-clé (oui / non) ou une ville de départ trouvée par motif
    sont « sûrs » et gardés ; sinon la valeur du LLM est prise. Une ville de départ du LLM n'est
    retenue que si elle figure dans le message (garde-fou anti-invention)."""
    for cle in ("vol", "voiture", "transfert"):
        if brut["besoins_transport"].get(cle, "indifferent") == "indifferent" and llm.get(cle) in jeu_nlu.BESOINS:
            brut["besoins_transport"][cle] = llm[cle]
    ville = llm.get("ville_depart")
    if brut["ville_depart"] is None and isinstance(ville, str) and ville.strip():
        mentions = {m.ville for m in n.trouver_villes(texte_norm)}
        canonique = n.ville_canonique(ville)
        if canonique in mentions or n.texte_normalise(ville.strip()) in texte_norm:
            brut["ville_depart"] = canonique


def depuis_llm_complet(donnees: dict[str, Any], date_reference: date) -> dict[str, Any]:
    """Sortie à plat du schéma complet → dictionnaire brut (montant tel que dit)."""
    d = dict(donnees)
    debut = d.get("date_debut")
    try:
        debut = date.fromisoformat(str(debut)) if debut else None
    except ValueError:
        debut = None
    return {
        "destination": d.get("destination"), "autres_villes": d.get("autres_villes") or [],
        "date_debut": debut.isoformat() if debut and debut >= date_reference else None,
        "duree_jours": d.get("duree_jours"), "nb_nuits": d.get("nb_nuits"),
        "budget_montant": d.get("budget_montant"), "budget_devise": d.get("budget_devise"),
        "budget_base": d.get("budget_base"), "budget_illimite": bool(d.get("budget_illimite")),
        "nb_voyageurs": d.get("nb_voyageurs"), "nb_adultes": d.get("nb_adultes"), "nb_enfants": d.get("nb_enfants"),
        "type_voyage": d.get("type_voyage"), "preferences": d.get("preferences") or [],
        "activites_souhaitees": d.get("activites_souhaitees") or [],
        "contraintes": {"niveau_marche_max": d.get("niveau_marche_max"),
                        "mobilite_reduite": d.get("mobilite_reduite"), "horaires": None},
        "langue": d.get("langue"), "ville_depart": d.get("ville_depart"),
        "besoins_transport": {k: d.get(k) for k in ("vol", "voiture", "transfert")},
        "preferences_transport": {k: d.get(k) for k in ("vol_direct", "boite_auto", "priorite")},
        "hors_sujet": d.get("hors_sujet") is True,
    }


# --- Validation tolérante -------------------------------------------------------

def construire_demande(d: dict[str, Any]) -> DemandeVoyage:
    """Validation Pydantic ; un champ refusé est remis à sa valeur par défaut (jamais d'erreur 500)."""
    d = copy.deepcopy(d)
    for _ in range(10):
        try:
            return DemandeVoyage.model_validate(d)
        except ValidationError as exc:
            for erreur in exc.errors():
                chemin = [str(p) for p in erreur["loc"] if not isinstance(p, int)]
                if not chemin:  # validateur de modèle (ville_depart = destination)
                    d["ville_depart"] = None
                    continue
                cible = d
                for cle in chemin[:-1]:
                    cible = cible.setdefault(cle, {})
                defaut = DemandeVoyage.model_fields.get(chemin[0])
                if len(chemin) == 1 and defaut is not None:
                    cible[chemin[0]] = defaut.get_default(call_default_factory=True)
                else:
                    cible.pop(chemin[-1], None)
                if chemin[0] == "budget_montant":
                    d["budget_devise"] = d["budget_base"] = None
    return DemandeVoyage.model_validate(n.demande_hors_sujet(d.get("langue", "fr")) | {"hors_sujet": False})


# --- Point d'entrée -------------------------------------------------------------

async def _appeler_llm(client_llm: Any, texte: str, complet: bool, delai_s: float | None, transport: bool = False):
    systeme, messages = construire_messages(texte, complet=complet, transport=transport)
    appel = client_llm.generer(
        messages, systeme=systeme,
        schema_sortie=schema_llm_complet() if complet else schema_llm_hybride(transport=transport),
        max_tokens=MAX_TOKENS_COMPLET if complet else MAX_TOKENS_HYBRIDE,
        temperature=TEMPERATURE, usage="nlu",
    )
    reponse = await (asyncio.wait_for(appel, timeout=delai_s) if delai_s else appel)
    if not isinstance(reponse.donnees, dict):
        raise ValueError("sortie du LLM sans objet JSON")
    return reponse


async def comprendre(texte: str, date_reference: date, client_llm: Any | None = None,
                     methode: str = "hybride", delai_s: float | None = None,
                     transport_llm: bool = False, garde_voyageurs: bool = True) -> ReponseComprendre:
    """Texte libre → `ReponseComprendre`. Ne lève pas : toute panne du LLM finit sur les règles.
    `transport_llm=True` : variante hybride v2 (ablation de l'évaluation, pas utilisée par la route)."""
    if methode not in METHODES:
        raise ValueError(f"méthode inconnue : {methode!r}")
    debut = time.perf_counter()
    regles = extraire(texte, date_reference)
    brut, provider, methode_eff, avertissements = regles.brut, "regles", "regles", []

    if methode != "regles" and client_llm is not None and not (methode == "hybride" and regles.brut["hors_sujet"]):
        try:
            v2 = transport_llm and methode == "hybride"
            reponse = await _appeler_llm(client_llm, texte, complet=methode == "llm", delai_s=delai_s, transport=v2)
            if methode == "llm":
                brut = depuis_llm_complet(reponse.donnees, date_reference)
                brut["langue"] = brut["langue"] if brut["langue"] in jeu_nlu.LANGUES else regles.brut["langue"]
            else:
                brut = fusionner(regles, reponse.donnees, texte, transport=v2, garde_voyageurs=garde_voyageurs)
            provider, methode_eff = reponse.provider, methode
        except LLMRefus:
            # Un refus de sécurité n'est jamais contourné : la demande est traitée comme hors sujet.
            brut, provider, methode_eff = n.demande_hors_sujet(regles.brut["langue"]), "regles", "regles"
        except (ErreurLLM, asyncio.TimeoutError, ValueError, TypeError, KeyError) as exc:
            logger.warning("NLU : repli sur les règles (%s : %s)", type(exc).__name__, exc)
            avertissements.append(AVERTISSEMENT_REPLI)
    # Hybride sans aucun signal de voyage : les règles suffisent (pas d'appel LLM), methode = regles.

    normalise = n.normaliser_demande(brut)
    demande = construire_demande(normalise)
    attendu = demande.vers_attendu()
    manquants = attendu["champs_manquants"]
    return ReponseComprendre(
        demande=demande,
        champs_manquants=manquants,
        question_clarification=question_clarification(
            manquants, demande.langue, demande.besoins_transport.vol == "oui", demande.hors_sujet),
        avertissements=avertissements + avertissements_demande(demande),
        provider=provider,
        latence_ms=round((time.perf_counter() - debut) * 1000),
        methode=methode_eff,
    )
