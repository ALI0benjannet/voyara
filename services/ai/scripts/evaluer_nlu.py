"""Évaluation du module 1 (NLU) sur le jeu annoté : règles, Ollama seul ou hybride.

    cd services\\ai
    ..\\..\\.venv\\Scripts\\python scripts\\evaluer_nlu.py --methode regles --jeu dev --erreurs
    ..\\..\\.venv\\Scripts\\python scripts\\evaluer_nlu.py --methode hybride --jeu test
    ..\\..\\.venv\\Scripts\\python scripts\\evaluer_nlu.py --methode ollama --jeu test --echantillon 30

Seules les demandes relues (`valide` ou `corrige`) sont évaluées ; les demandes humaines sont
réparties 40 % dev / 60 % test par `jeu_nlu.repartir_dev_test` (graine fixe, stratifiée par langue).
Le LLM est **toujours Ollama** (local, gratuit) : le script construit lui-même un `ClientLLM` en mode
`ollama`, quel que soit `LLM_PROVIDER`. Les sorties brutes du LLM sont mises en cache par demande
(`data/eval/cache/`, non versionné) : un run interrompu reprend où il s'est arrêté, et une
correction des règles ou de la normalisation se réévalue sans rappeler le LLM.

Métriques (définition figée avant l'évaluation, cf. rapport de l'étape 4) :
- F1 de remplissage par champ : une valeur nulle ou par défaut (`null`, liste vide, `indifferent`,
  `false`) compte comme « rien d'extrait » ; précision = valeurs prédites justes / valeurs prédites,
  rappel = valeurs prédites justes / valeurs attendues. Listes : par élément (activités appariées par
  `jeu_nlu.apparier_activites`). Support = nombre de valeurs attendues non vides.
- 28 champs notés (`horaires` non noté, `budget_total_dt` dérivé de `budget_montant`) dont
  `champs_manquants`. Un champ de support < 5 est publié mais sort de la moyenne macro.
- F1 macro (critère « fini ») et F1 micro global ; même règle pour le bloc transport (8 champs).
"""

import argparse
import asyncio
import csv
import hashlib
import json
import random
import subprocess
import sys
import time
import urllib.request
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

RACINE_SERVICE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE_SERVICE))

from scripts import jeu_nlu as j  # noqa: E402

DOSSIER_RESULTATS = RACINE_SERVICE.parents[1] / "docs" / "ia" / "resultats"
DOSSIER_CACHE = j.DOSSIER_EVAL / "cache"
FICHIER_DEMANDES = j.DOSSIER_EVAL / "nlu_demandes.jsonl"
METHODES_SCRIPT = {"regles": "regles", "ollama": "llm", "hybride": "hybride"}
SUPPORT_MIN_MACRO = 5
GRAINE_ECHANTILLON = 20261109

# (nom, extracteur depuis `attendu`, type) — type : scalaire | liste | activites
CHAMPS: tuple[tuple[str, Any, str], ...] = (
    ("destination", lambda a: a["destination"], "scalaire"),
    ("autres_villes", lambda a: a["autres_villes"], "liste"),
    ("date_debut", lambda a: a["date_debut"], "scalaire"),
    ("duree_jours", lambda a: a["duree_jours"], "scalaire"),
    ("nb_nuits", lambda a: a["nb_nuits"], "scalaire"),
    ("budget_montant", lambda a: a["budget_montant"], "scalaire"),
    ("budget_devise", lambda a: a["budget_devise"], "scalaire"),
    ("budget_base", lambda a: a["budget_base"], "scalaire"),
    ("budget_illimite", lambda a: a["budget_illimite"], "scalaire"),
    ("nb_voyageurs", lambda a: a["nb_voyageurs"], "scalaire"),
    ("nb_adultes", lambda a: a["nb_adultes"], "scalaire"),
    ("nb_enfants", lambda a: a["nb_enfants"], "scalaire"),
    ("type_voyage", lambda a: a["type_voyage"], "scalaire"),
    ("preferences", lambda a: a["preferences"], "liste"),
    ("activites_souhaitees", lambda a: a["activites_souhaitees"], "activites"),
    ("niveau_marche_max", lambda a: a["contraintes"]["niveau_marche_max"], "scalaire"),
    ("mobilite_reduite", lambda a: a["contraintes"]["mobilite_reduite"], "scalaire"),
    ("langue", lambda a: a["langue"], "scalaire"),
    ("ville_depart", lambda a: a["ville_depart"], "scalaire"),
    ("vol", lambda a: a["besoins_transport"]["vol"], "scalaire"),
    ("voiture", lambda a: a["besoins_transport"]["voiture"], "scalaire"),
    ("transfert", lambda a: a["besoins_transport"]["transfert"], "scalaire"),
    ("vol_direct", lambda a: a["preferences_transport"]["vol_direct"], "scalaire"),
    ("boite_auto", lambda a: a["preferences_transport"]["boite_auto"], "scalaire"),
    ("priorite", lambda a: a["preferences_transport"]["priorite"], "scalaire"),
    ("budget_inclut_transport", lambda a: a["budget_inclut_transport"], "scalaire"),
    ("hors_sujet", lambda a: a["hors_sujet"], "scalaire"),
    ("champs_manquants", lambda a: a["champs_manquants"], "liste"),
)
CHAMPS_TRANSPORT = ("vol", "voiture", "transfert", "ville_depart", "vol_direct", "boite_auto", "priorite",
                    "budget_inclut_transport")
VALEURS_VIDES = (None, "indifferent", False)


# --- Métriques ------------------------------------------------------------------

@dataclass
class Compteur:
    vp: float = 0
    predits: int = 0
    attendus: int = 0
    exacts: int = 0
    total: int = 0

    @property
    def precision(self) -> float | None:
        return self.vp / self.predits if self.predits else None

    @property
    def rappel(self) -> float | None:
        return self.vp / self.attendus if self.attendus else None

    @property
    def f1(self) -> float | None:
        if not self.predits and not self.attendus:
            return None  # champ jamais présent : non défini
        if not self.predits + self.attendus:
            return None
        return 2 * self.vp / (self.predits + self.attendus)

    @property
    def exactitude(self) -> float | None:
        return self.exacts / self.total if self.total else None


GRAINE_BOOTSTRAP = 20261109
TIRAGES_BOOTSTRAP = 1000


def ic_bootstrap(paires: list[tuple[dict, dict]], retenus: set[str], tirages: int = TIRAGES_BOOTSTRAP,
                 graine: int = GRAINE_BOOTSTRAP) -> dict[str, tuple[float, float] | None]:
    """IC à 95 % (percentiles 2,5 et 97,5) du F1 macro et du F1 transport macro par bootstrap des
    demandes (tirage avec remise, graine fixe). Les champs de la moyenne macro restent ceux du jeu
    complet (`retenus`). Même graine et mêmes demandes (triées par id) : tirages identiques d'une
    méthode à l'autre, donc comparables."""
    if not paires:
        return {"f1_macro": None, "f1_transport": None}
    unitaires = [mesurer([p]) for p in paires]
    alea = random.Random(graine)
    retenus_t = retenus & set(CHAMPS_TRANSPORT)
    macro, transport = [], []
    for _ in range(tirages):
        cumul = {nom: Compteur() for nom, _, _ in CHAMPS}
        for i in (alea.randrange(len(paires)) for _ in paires):
            for nom, c in unitaires[i].items():
                cumul[nom].vp += c.vp
                cumul[nom].predits += c.predits
                cumul[nom].attendus += c.attendus
        m = scores(cumul, retenus=retenus)["f1_macro"]
        t = scores(cumul, CHAMPS_TRANSPORT, retenus=retenus_t)["f1_macro"] if retenus_t else None
        if m is not None:
            macro.append(m)
        if t is not None:
            transport.append(t)

    def borne(valeurs: list[float]) -> tuple[float, float] | None:
        if not valeurs:
            return None
        v = sorted(valeurs)
        return v[int(0.025 * (len(v) - 1))], v[int(round(0.975 * (len(v) - 1)))]

    return {"f1_macro": borne(macro), "f1_transport": borne(transport)}


def _ic(ic: tuple[float, float] | None) -> str:
    return "—" if ic is None else f"[{ic[0]:.3f} ; {ic[1]:.3f}]"


def vide(valeur: Any) -> bool:
    return valeur in VALEURS_VIDES if not isinstance(valeur, list) else not valeur


def egal(predite: Any, attendue: Any) -> bool:
    if isinstance(predite, (int, float)) and isinstance(attendue, (int, float)) \
            and not isinstance(predite, bool) and not isinstance(attendue, bool):
        return abs(predite - attendue) < 0.5
    return predite == attendue


def comparer(champ_type: str, predite: Any, attendue: Any) -> tuple[float, int, int, bool]:
    """(vrais positifs, nb prédits non vides, nb attendus non vides, exact)."""
    if champ_type == "scalaire":
        p, a = not vide(predite), not vide(attendue)
        juste = egal(predite, attendue)
        return float(p and a and juste), int(p), int(a), juste or (not p and not a)
    predite, attendue = list(predite or []), list(attendue or [])
    if champ_type == "activites":
        vp = j.apparier_activites(predite, attendue)
    else:
        vp = len(set(predite) & set(attendue))
    exact = vp == len(predite) == len(attendue)
    return float(vp), len(predite), len(attendue), exact


def mesurer(paires: list[tuple[dict, dict]]) -> dict[str, Compteur]:
    """paires = [(attendu, prédit)] → compteur par champ."""
    compteurs = {nom: Compteur() for nom, _, _ in CHAMPS}
    for attendu, predit in paires:
        for nom, lire, champ_type in CHAMPS:
            vp, p, a, exact = comparer(champ_type, lire(predit), lire(attendu))
            c = compteurs[nom]
            c.vp += vp
            c.predits += p
            c.attendus += a
            c.exacts += int(exact)
            c.total += 1
    return compteurs


def scores(compteurs: dict[str, Compteur], champs: tuple[str, ...] | None = None,
           retenus: set[str] | None = None) -> dict[str, Any]:
    """F1 macro (champs de support ≥ 5, ou `retenus` imposés) et F1 micro (tous les champs)."""
    noms = champs or tuple(compteurs)
    dans_macro = [c for c in noms if (retenus is not None and c in retenus)
                  or (retenus is None and compteurs[c].attendus >= SUPPORT_MIN_MACRO)]
    f1s = [compteurs[c].f1 for c in dans_macro if compteurs[c].f1 is not None]
    vp = sum(compteurs[c].vp for c in noms)
    total = sum(compteurs[c].predits + compteurs[c].attendus for c in noms)
    return {
        "f1_macro": sum(f1s) / len(f1s) if f1s else None,
        "f1_micro": 2 * vp / total if total else None,
        "champs_macro": dans_macro,
        "exclus": [c for c in noms if c not in dans_macro],
    }


def matrice(paires: list[tuple[dict, dict]], lire) -> tuple[list[str], dict[tuple[str, str], int]]:
    cases: Counter = Counter()
    for attendu, predit in paires:
        cases[(str(lire(attendu)), str(lire(predit)))] += 1
    valeurs = sorted({v for paire in cases for v in paire}, key=lambda v: (v == "None", v))
    return valeurs, dict(cases)


# --- Demandes -------------------------------------------------------------------

def echantillon_stratifie(demandes: list[dict], taille: int, graine: int = GRAINE_ECHANTILLON) -> list[dict]:
    """Sous-échantillon stratifié par langue (proportionnel, plus forts restes), déterministe."""
    par_langue: dict[str, list[dict]] = defaultdict(list)
    for d in sorted(demandes, key=lambda d: d["id"]):
        par_langue[d["attendu"]["langue"]].append(d)
    total = len(demandes)
    parts = {lg: taille * len(g) / total for lg, g in par_langue.items()}
    quotas = {lg: int(p) for lg, p in parts.items()}
    for lg in sorted(parts, key=lambda lg: parts[lg] - quotas[lg], reverse=True)[:taille - sum(quotas.values())]:
        quotas[lg] += 1
    alea = random.Random(graine)
    choisis = []
    for lg in sorted(par_langue):
        groupe = list(par_langue[lg])
        alea.shuffle(groupe)
        choisis += groupe[:quotas[lg]]
    return sorted(choisis, key=lambda d: d["id"])


def regenerer_nlu_demandes() -> int:
    """data/eval/nlu_demandes.jsonl : toutes les demandes retenues (relues), avec leur jeu."""
    lignes = j.demandes_du_jeu("dev") + j.demandes_du_jeu("test")
    j.ecrire_jsonl(FICHIER_DEMANDES, sorted(lignes, key=lambda d: (d["jeu"], d["id"])))
    return len(lignes)


# --- LLM avec cache -------------------------------------------------------------

class ClientLLMCache:
    """Enveloppe d'un `ClientLLM` : sorties brutes mises en cache par (demande, schéma)."""

    def __init__(self, client: Any, chemin: Path, reessayer: bool = False):
        self.client = client
        self.chemin = chemin
        self.entrees: dict[str, dict] = {}
        if chemin.exists():
            for ligne in chemin.read_text(encoding="utf-8").splitlines():
                if ligne.strip():
                    e = json.loads(ligne)
                    if reessayer and "erreur" in e:
                        continue
                    self.entrees[e["cle"]] = e
        self.cle_courante = ""
        self.derniere: dict | None = None
        self.appels_reels = 0

    def cle(self, demande: dict) -> str:
        empreinte = hashlib.sha256(f"{demande['texte']}|{demande['date_reference']}".encode()).hexdigest()[:12]
        return f"{demande['id']}:{empreinte}"

    async def generer(self, messages, **params):
        from app.llm.base import LLMIndisponible, LLMSortieInvalide, ReponseLLM

        cle = self.cle_courante + (":complet" if "budget_montant" in (params.get("schema_sortie") or {}).get("properties", {}) else ":hybride")
        if cle not in self.entrees:
            self.appels_reels += 1
            debut = time.perf_counter()
            try:
                r = await self.client.generer(messages, **params)
                e = {"cle": cle, "donnees": r.donnees, "provider": r.provider, "modele": r.modele,
                     "latence_ms": r.latence_ms, "tokens_sortie": r.tokens_sortie}
            except Exception as exc:  # noqa: BLE001 — mémorisé, puis relevé comme le ferait le client
                e = {"cle": cle, "erreur": f"{type(exc).__name__}: {exc}",
                     "latence_ms": round((time.perf_counter() - debut) * 1000)}
            self.entrees[cle] = e
            with self.chemin.open("a", encoding="utf-8") as f:
                f.write(json.dumps(e, ensure_ascii=False) + "\n")
        e = self.derniere = self.entrees[cle]
        if "erreur" in e:
            if e["erreur"].startswith("LLMSortieInvalide"):
                raise LLMSortieInvalide(e["erreur"], "ollama")
            raise LLMIndisponible(e["erreur"], "ollama")
        return ReponseLLM(texte="", provider=e["provider"], modele=e["modele"], donnees=e["donnees"],
                          latence_ms=e["latence_ms"], tokens_sortie=e.get("tokens_sortie", 0))


def creer_client_ollama() -> Any:
    """ClientLLM en mode `ollama` imposé : aucun appel payant possible depuis ce script."""
    from app.config import settings
    from app.database import SessionLocal
    from app.llm.claude import ClaudeProvider
    from app.llm.fabrique import ClientLLM
    from app.llm.journal import JournalLLM
    from app.llm.ollama import OllamaProvider

    ollama = OllamaProvider(settings.OLLAMA_URL, settings.OLLAMA_MODEL, settings.OLLAMA_TIMEOUT_S)
    claude = ClaudeProvider(api_key=None, modele=settings.CLAUDE_MODEL)  # jamais appelé (mode ollama)
    return ClientLLM("ollama", claude, ollama, JournalLLM(SessionLocal))


# --- Run ------------------------------------------------------------------------

@dataclass
class Resultat:
    demande: dict
    predit: dict
    latence_ms: int
    methode: str
    repli: bool
    llm_latence_ms: int | None = None


@dataclass
class Run:
    methode: str
    jeu: str
    resultats: list[Resultat] = field(default_factory=list)
    modele: str | None = None
    appels_reels: int = 0
    duree_s: float = 0.0


async def executer(methode: str, demandes: list[dict], cache: ClientLLMCache | None, verbeux: bool = True,
                   transport_llm: bool = False, garde_voyageurs: bool = True) -> Run:
    from app.nlu.extraction import AVERTISSEMENT_REPLI, comprendre

    run = Run(methode, demandes[0]["jeu"] if demandes else "")
    debut_run = time.perf_counter()
    for i, d in enumerate(demandes, start=1):
        if cache is not None:
            cache.cle_courante = cache.cle(d)
            cache.derniere = None
        appels_avant = cache.appels_reels if cache is not None else 0
        debut = time.perf_counter()
        reponse = await comprendre(d["texte"], date.fromisoformat(d["date_reference"]), client_llm=cache,
                                   methode=METHODES_SCRIPT[methode], transport_llm=transport_llm,
                                   garde_voyageurs=garde_voyageurs)
        local_ms = round((time.perf_counter() - debut) * 1000)
        llm_ms = cache.derniere.get("latence_ms") if cache is not None and cache.derniere else None
        if cache is not None and cache.derniere and cache.derniere.get("modele"):
            run.modele = cache.derniere["modele"]
        predit = reponse.demande.vers_attendu()
        # Appel réel : le temps mesuré inclut déjà le LLM ; sortie en cache : on ajoute la latence d'origine.
        appel_reel = cache is not None and cache.appels_reels > appels_avant
        latence = local_ms if appel_reel or cache is None else local_ms + (llm_ms or 0)
        run.resultats.append(Resultat(d, predit, latence,
                                      reponse.methode, AVERTISSEMENT_REPLI in reponse.avertissements, llm_ms))
        if verbeux and cache is not None:
            print(f"  [{i}/{len(demandes)}] {d['id']} {reponse.methode} {((llm_ms or 0) / 1000):.0f} s", flush=True)
    run.duree_s = time.perf_counter() - debut_run
    run.appels_reels = cache.appels_reels if cache else 0
    return run


def _pct(x: float | None) -> str:
    return "—" if x is None else f"{x:.3f}"


# --- Provenance (en tête de chaque fichier de résultats) -------------------------

def _git(*args: str) -> str | None:
    try:
        sortie = subprocess.run(["git", *args], cwd=RACINE_SERVICE, capture_output=True, text=True,
                                timeout=15, check=True)
        return sortie.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None


def info_ollama(modele: str | None) -> dict[str, str | None]:
    """Version du serveur Ollama et empreinte (digest) du modèle, lues sur l'API locale."""
    from app.config import settings

    base = settings.OLLAMA_URL.rstrip("/")
    info: dict[str, str | None] = {"version": None, "digest": None}
    try:
        with urllib.request.urlopen(f"{base}/api/version", timeout=5) as r:
            info["version"] = json.loads(r.read()).get("version")
        with urllib.request.urlopen(f"{base}/api/tags", timeout=5) as r:
            for m in json.loads(r.read()).get("models", []):
                if m.get("name") == modele or m.get("model") == modele:
                    info["digest"] = (m.get("digest") or "")[:12] or None
    except (OSError, ValueError):
        pass
    return info


def provenance(run: Run, variante: str, note: str | None, avec_llm: bool, garde: bool | None = None) -> list[str]:
    from app.nlu.extraction import TEMPERATURE

    commit = _git("rev-parse", "--short", "HEAD") or "inconnu"
    statut = _git("status", "--porcelain")
    modifs = "inconnu" if statut is None else (
        f"oui ({len(statut.splitlines())} fichiers modifiés ou non suivis)" if statut else "non")
    if avec_llm:
        modele = run.modele or "inconnu"
        o = info_ollama(run.modele)
        llm = (f"Ollama `{modele}` (digest `{o['digest'] or 'inconnu'}`), serveur Ollama "
               f"{o['version'] or 'inconnu'} · temperature {TEMPERATURE}")
    else:
        llm = "aucun (règles seules)"
    lignes = [
        "## Provenance",
        "",
        "| Élément | Valeur |",
        "|---|---|",
        f"| Commit Git | `{commit}` |",
        f"| Modifications non commitées | {modifs} |",
        f"| Variante | {variante if run.methode == 'hybride' else '—'} |",
        f"| Garde-fou des voyageurs | {'—' if garde is None else 'oui' if garde else 'non (code du résultat officiel v1)'} |",
        f"| LLM | {llm} |",
        f"| Demandes évaluées | {len(run.resultats)} |",
        f"| Date | {datetime.now().strftime('%Y-%m-%d %H:%M')} |",
        f"| Replis sur les règles | {sum(x.repli for x in run.resultats)} |",
        f"| Appels LLM réels (hors cache) | {run.appels_reels} |",
    ]
    if note:
        lignes.append(f"| Note | {note} |")
    return lignes + [""]


async def _predictions_regles(demandes: list[dict]) -> list[dict]:
    from app.nlu.extraction import comprendre

    return [(await comprendre(d["texte"], date.fromisoformat(d["date_reference"]), methode="regles")).demande.vers_attendu()
            for d in demandes]


def conditions_api(run: Run, delai_s: float) -> dict[str, Any]:
    """Ce que la route renverrait sur ce poste : un appel Ollama (latence mesurée, en cache) plus long
    que `delai_s` y finit sur les règles seules. Aucun nouvel appel au LLM."""
    trop_lents = [i for i, x in enumerate(run.resultats)
                  if x.methode == "hybride" and (x.llm_latence_ms or 0) > delai_s * 1000]
    regles = asyncio.run(_predictions_regles([run.resultats[i].demande for i in trop_lents]))
    remplace = dict(zip(trop_lents, regles))
    paires = [(x.demande["attendu"], remplace.get(i, x.predit)) for i, x in enumerate(run.resultats)]
    compteurs = mesurer(paires)
    return {"delai_s": delai_s, "concernes": len(trop_lents), "n": len(run.resultats),
            "scores": scores(compteurs), "transport": scores(compteurs, CHAMPS_TRANSPORT)}


def lignes_conditions_api(api: dict[str, Any]) -> list[str]:
    part = api["concernes"] / max(api["n"], 1)
    return [
        "## Conditions API",
        "",
        f"Simulation depuis le cache (aucun nouvel appel) : chaque demande dont l'appel Ollama a dépassé "
        f"`NLU_DELAI_LLM_S` = {api['delai_s']:g} s reçoit la sortie des règles seules, comme la route. "
        "Le résultat officiel reste le F1 sans limite de temps ci-dessous ; celui-ci est une donnée pour l'étape 9.",
        "",
        "| Conditions API | Valeur |",
        "|---|---|",
        f"| Demandes au-delà de {api['delai_s']:g} s (repli sur les règles) | {api['concernes']} / {api['n']} ({part:.1%}) |",
        f"| F1 macro en conditions API | {_pct(api['scores']['f1_macro'])} |",
        f"| F1 transport macro en conditions API | {_pct(api['transport']['f1_macro'])} |",
        "",
    ]


def rapport_markdown(run: Run, titre_suffixe: str, compteurs: dict[str, Compteur], s: dict, st: dict,
                     par_groupe: dict[str, dict[str, Any]], matrices: dict[str, Any],
                     entete: list[str] | None = None, ic: dict | None = None) -> str:
    ic = ic or {"f1_macro": None, "f1_transport": None}
    r = run.resultats
    replis = sum(x.repli for x in r)
    methodes = Counter(x.methode for x in r)
    lignes = [
        f"# Évaluation NLU — méthode `{run.methode}`, jeu `{run.jeu}`{titre_suffixe}",
        "",
        *(entete or []),
        f"> Généré le {date.today().isoformat()} par `services/ai/scripts/evaluer_nlu.py`. "
        f"{len(r)} demandes relues (`valide` ou `corrige`). "
        + (f"LLM : Ollama `{run.modele}` (local). " if run.modele else "Aucun LLM. ")
        + "Coût : **0 DT** (aucun appel payant).",
        "",
        "## Scores",
        "",
        "| Score | Valeur |",
        "|---|---|",
        f"| **F1 macro** (champs de support ≥ {SUPPORT_MIN_MACRO}, critère « fini » ≥ 0,85) | **{_pct(s['f1_macro'])}** |",
        f"| F1 micro global (28 champs) | {_pct(s['f1_micro'])} |",
        f"| **F1 transport macro** (8 champs, support ≥ {SUPPORT_MIN_MACRO}) | **{_pct(st['f1_macro'])}** |",
        f"| F1 transport micro | {_pct(st['f1_micro'])} |",
        f"| IC 95 % du F1 macro (bootstrap, {TIRAGES_BOOTSTRAP} tirages, graine {GRAINE_BOOTSTRAP}) | {_ic(ic['f1_macro'])} |",
        f"| IC 95 % du F1 transport macro (idem) | {_ic(ic['f1_transport'])} |",
        f"| Latence moyenne | {sum(x.latence_ms for x in r) / max(len(r), 1) / 1000:.1f} s |",
        f"| Méthode effective | {', '.join(f'{k} {v}' for k, v in sorted(methodes.items()))} |",
        f"| Replis sur les règles (LLM en panne, trop lent ou JSON invalide) | {replis} |",
        f"| Coût | 0 DT |",
        "",
        f"Champs hors moyenne macro (support < {SUPPORT_MIN_MACRO}) : "
        + (", ".join(f"`{c}` ({compteurs[c].attendus})" for c in s["exclus"]) or "aucun") + ".",
        "",
        "## Par champ",
        "",
        "| Champ | Support | Précision | Rappel | F1 | Exactitude | Macro |",
        "|---|---|---|---|---|---|---|",
    ]
    for nom, _, _ in CHAMPS:
        c = compteurs[nom]
        lignes.append(f"| `{nom}`{' (transport)' if nom in CHAMPS_TRANSPORT else ''} | {c.attendus} | "
                      f"{_pct(c.precision)} | {_pct(c.rappel)} | {_pct(c.f1)} | {_pct(c.exactitude)} | "
                      f"{'oui' if nom in s['champs_macro'] else 'non'} |")
    lignes += ["", "## Par langue et par source", "",
               "| Groupe | n | F1 macro | F1 micro | F1 transport macro |", "|---|---|---|---|---|"]
    for groupe, valeurs in par_groupe.items():
        lignes.append(f"| {groupe} | {valeurs['n']} | {_pct(valeurs['f1_macro'])} | {_pct(valeurs['f1_micro'])} | "
                      f"{_pct(valeurs['f1_transport'])} |")
    lignes += ["", "(F1 macro d'un groupe : mêmes champs que la moyenne globale.)", "", "## Matrices d'erreurs", ""]
    for nom, (valeurs, cases) in matrices.items():
        lignes += [f"**`{nom}`** (lignes : attendu, colonnes : prédit)", "",
                   "| attendu \\ prédit | " + " | ".join(valeurs) + " |",
                   "|---" * (len(valeurs) + 1) + "|"]
        for v in valeurs:
            lignes.append(f"| {v} | " + " | ".join(str(cases.get((v, w), 0) or "·") for w in valeurs) + " |")
        lignes.append("")
    return "\n".join(lignes) + "\n"


def analyser(run: Run, sortie: Path, titre_suffixe: str, entete: list[str] | None = None) -> dict[str, Any]:
    paires = [(x.demande["attendu"], x.predit) for x in run.resultats]
    compteurs = mesurer(paires)
    s = scores(compteurs)
    retenus = set(s["champs_macro"])
    st = scores(compteurs, CHAMPS_TRANSPORT)
    ic = ic_bootstrap(paires, retenus)
    groupes: dict[str, list] = defaultdict(list)
    for x, p in zip(run.resultats, paires):
        groupes[f"langue = {x.demande['attendu']['langue']}"].append(p)
        groupes[f"source = {x.demande['source']}"].append(p)
    par_groupe = {}
    for nom in sorted(groupes):
        cg = mesurer(groupes[nom])
        par_groupe[nom] = {"n": len(groupes[nom]), **{k: v for k, v in scores(cg, retenus=retenus).items()
                                                      if k in ("f1_macro", "f1_micro")},
                           "f1_transport": scores(cg, CHAMPS_TRANSPORT, retenus=retenus & set(CHAMPS_TRANSPORT))["f1_macro"]}
    matrices = {"type_voyage": matrice(paires, lambda a: a["type_voyage"])}
    for cle in ("vol", "voiture", "transfert"):
        matrices[f"besoins_transport.{cle}"] = matrice(paires, lambda a, k=cle: a["besoins_transport"][k])

    sortie.parent.mkdir(parents=True, exist_ok=True)
    sortie.with_suffix(".md").write_text(rapport_markdown(run, titre_suffixe, compteurs, s, st, par_groupe, matrices, entete, ic),
                                         encoding="utf-8")
    with sortie.with_suffix(".csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["champ", "transport", "support", "precision", "rappel", "f1", "exactitude", "dans_macro"])
        for nom, _, _ in CHAMPS:
            c = compteurs[nom]
            w.writerow([nom, nom in CHAMPS_TRANSPORT, c.attendus, _pct(c.precision), _pct(c.rappel), _pct(c.f1),
                        _pct(c.exactitude), nom in s["champs_macro"]])
        w.writerow([])
        w.writerow(["f1_macro", _pct(s["f1_macro"])])
        w.writerow(["f1_micro", _pct(s["f1_micro"])])
        w.writerow(["f1_transport_macro", _pct(st["f1_macro"])])
        w.writerow(["f1_transport_micro", _pct(st["f1_micro"])])
        w.writerow(["ic95_f1_macro", _ic(ic["f1_macro"])])
        w.writerow(["ic95_f1_transport_macro", _ic(ic["f1_transport"])])
    return {"compteurs": compteurs, "scores": s, "transport": st, "par_groupe": par_groupe, "ic": ic}


def afficher_erreurs(run: Run) -> None:
    """Écarts champ par champ — réservé au jeu dev (mise au point des règles et du prompt)."""
    for x in run.resultats:
        ecarts = []
        for nom, lire, champ_type in CHAMPS:
            p, a = lire(x.predit), lire(x.demande["attendu"])
            if not comparer(champ_type, p, a)[3]:
                ecarts.append(f"{nom}: {a!r} → {p!r}")
        if ecarts:
            print(f"{x.demande['id']} | {x.demande['texte'][:110]}")
            for e in ecarts:
                print(f"    {e}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--methode", choices=tuple(METHODES_SCRIPT), default="regles")
    parser.add_argument("--jeu", choices=("dev", "test"), default="dev")
    parser.add_argument("--limite", type=int, help="seulement les N premières demandes (essai)")
    parser.add_argument("--echantillon", type=int, help="sous-échantillon stratifié par langue de N demandes")
    parser.add_argument("--erreurs", action="store_true", help="afficher les écarts (jeu dev uniquement)")
    parser.add_argument("--reessayer", action="store_true", help="rappeler le LLM pour les erreurs en cache")
    parser.add_argument("--variante", choices=("v1", "v2"), default="v1",
                        help="hybride v2 = transport aussi proposé par le LLM (ablation, cache séparé)")
    parser.add_argument("--note", help="remarque ajoutée à la provenance du fichier de résultats")
    parser.add_argument("--sans-garde", action="store_true",
                        help="hybride sans le garde-fou des voyageurs (code du résultat officiel v1)")
    args = parser.parse_args()
    if args.erreurs and args.jeu != "dev":
        sys.exit("--erreurs est réservé au jeu dev : le jeu test ne sert qu'à l'évaluation finale")
    v2 = args.variante == "v2"
    if v2 and args.methode != "hybride":
        sys.exit("--variante v2 ne concerne que la méthode hybride")

    total = regenerer_nlu_demandes()
    demandes = sorted(j.demandes_du_jeu(args.jeu), key=lambda d: d["id"])
    suffixe_fichier, suffixe_titre = ("_v2", " — v2 exploratoire (transport aussi par le LLM)") if v2 else ("", "")
    if args.methode == "hybride" and not args.sans_garde:
        suffixe_fichier += "_garde"
        suffixe_titre += " — avec garde-fou des voyageurs"
    if args.echantillon:
        demandes = echantillon_stratifie(demandes, args.echantillon)
        suffixe_fichier += f"_ech{args.echantillon}"
        suffixe_titre += f" (échantillon stratifié de {len(demandes)})"
    if args.limite:
        demandes = demandes[:args.limite]
        suffixe_fichier += f"_lim{args.limite}"
        suffixe_titre += f" ({len(demandes)} premières demandes)"

    cache = None
    if args.methode != "regles":
        DOSSIER_CACHE.mkdir(parents=True, exist_ok=True)
        # v1 et v2 ont des caches séparés : aucune sortie d'une variante ne sert à l'autre.
        fichier_cache = "nlu_llm_v2.jsonl" if v2 else "nlu_llm.jsonl"
        cache = ClientLLMCache(creer_client_ollama(), DOSSIER_CACHE / fichier_cache, reessayer=args.reessayer)
        print(f"Ollama : {len(cache.entrees)} sorties déjà en cache")
    print(f"{FICHIER_DEMANDES.name} : {total} demandes retenues · évaluation : {len(demandes)} demandes "
          f"({args.methode}, {args.jeu})", flush=True)

    run = asyncio.run(executer(args.methode, demandes, cache, transport_llm=v2,
                               garde_voyageurs=not args.sans_garde))
    run.jeu = args.jeu
    sortie = DOSSIER_RESULTATS / f"nlu_{args.methode}_{args.jeu}{suffixe_fichier}"
    entete = provenance(run, args.variante, args.note, avec_llm=cache is not None,
                        garde=None if args.methode != "hybride" else not args.sans_garde)
    api = None
    if args.methode == "hybride":
        from app.config import settings

        api = conditions_api(run, settings.NLU_DELAI_LLM_S)
        entete += lignes_conditions_api(api)
    resultat = analyser(run, sortie, suffixe_titre, entete)
    s, st = resultat["scores"], resultat["transport"]
    print(f"\nF1 macro {_pct(s['f1_macro'])} · F1 micro {_pct(s['f1_micro'])} · "
          f"F1 transport macro {_pct(st['f1_macro'])} · micro {_pct(st['f1_micro'])}")
    print(f"IC 95 % bootstrap : F1 macro {_ic(resultat['ic']['f1_macro'])} · "
          f"F1 transport macro {_ic(resultat['ic']['f1_transport'])}")
    print(f"Hors macro (support < {SUPPORT_MIN_MACRO}) : "
          + ", ".join(f"{c} ({resultat['compteurs'][c].attendus})" for c in s["exclus"]))
    print(f"Replis : {sum(x.repli for x in run.resultats)} · appels LLM réels : {run.appels_reels} · "
          f"durée {run.duree_s:.0f} s · latence moyenne {sum(x.latence_ms for x in run.resultats) / max(len(run.resultats), 1) / 1000:.1f} s")
    if api:
        print(f"Conditions API (> {api['delai_s']:g} s → règles) : {api['concernes']}/{api['n']} demandes "
              f"({api['concernes'] / max(api['n'], 1):.1%}) · F1 macro {_pct(api['scores']['f1_macro'])} · "
              f"F1 transport macro {_pct(api['transport']['f1_macro'])}")
    print(f"→ {sortie.with_suffix('.md')}")
    if args.erreurs:
        print()
        afficher_erreurs(run)


if __name__ == "__main__":
    main()
