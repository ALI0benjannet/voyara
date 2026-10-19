"""Pré-étiquetage des activités pour le moteur IA (étape 2) — n'écrit RIEN en base.

Propose, pour chaque activité, les attributs IA (thèmes, public, niveau de
marche, intérieur, moment idéal) et les écrit dans un CSV à relire. La base
est ouverte en transaction READ ONLY : le script ne peut pas la modifier.
L'import du CSV (tags non validés) est fait à part par
scripts/importer_propositions.py ; la validation, par un humain dans l'admin.

Trois fournisseurs, même format de sortie (validé par app.tags_ia.TagsIA) :
  regles  (défaut)  mots-clés + catégorie + horaires des créneaux. Hors-ligne,
                    gratuit, déterministe et explicable (colonne `raisons`).
  claude            API Claude via le SDK officiel `anthropic`
                    (pip install anthropic ; ANTHROPIC_API_KEY dans .env).
  ollama            modèle local via l'API REST d'Ollama (OLLAMA_URL, défaut
                    http://localhost:11434), sortie contrainte par schéma JSON.
Appels directs et simples : la couche LLM hybride (bascule, journal des
appels, coûts) arrive à l'étape 3 dans le service ai.

Usage (depuis services/catalog) :
    python scripts/pre_etiqueter.py                       # règles, 117 activités
    python scripts/pre_etiqueter.py --fournisseur ollama --modele qwen2.5:7b
    python scripts/pre_etiqueter.py --fournisseur claude --limite 5
    python scripts/pre_etiqueter.py --ids 8,42 --sortie data/etiquetage/essai.csv
"""

import argparse
import csv
import json
import os
import re
import sys
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, time, timezone
from pathlib import Path
from typing import Literal

RACINE_SERVICE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE_SERVICE))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from pydantic import BaseModel, ValidationError  # noqa: E402

from app.tags_ia import MOMENTS, PUBLICS, THEMES, MomentIdeal, Public, TagsIA, Theme  # noqa: E402

DOSSIER_SORTIE = RACINE_SERVICE / "data" / "etiquetage"
MODELE_CLAUDE = "claude-opus-5-5"
MODELE_OLLAMA = "qwen2.5:7b"
COLONNES_CSV = [
    "activity_id", "titre", "categorie", "fournisseur", "modele", "statut",
    "themes", "public", "niveau_marche", "interieur", "moment_ideal",
    "confiance", "raisons", "erreur",
]


@dataclass
class ActiviteSource:
    id: int
    titre: str
    description: str
    categorie: str
    duree: int
    heures: list[time] = field(default_factory=list)


@dataclass
class Proposition:
    tags: TagsIA
    confiance: str = ""
    raisons: list[str] = field(default_factory=list)


# ===========================================================================
# Fournisseur « regles » — mots-clés sur le texte normalisé (sans accents)
# ===========================================================================


# Noms de lieux qui contiennent un mot-clé entier (« Houmt Souk » ⊃ souk) :
# soudés avant la recherche pour ne pas fausser les règles. Les préfixes
# (« Hammamet » ⊃ hammam, « golfe » ⊃ golf) sont réglés par \b dans les motifs.
TOPONYMES = {"houmt souk": "houmtsouk", "chott meriem": "chottmeriem"}


def normaliser(texte: str) -> str:
    texte = unicodedata.normalize("NFKD", texte.lower())
    texte = "".join(c for c in texte if not unicodedata.combining(c))
    texte = re.sub(r"[’'`]", " ", texte)
    for lieu, soude in TOPONYMES.items():
        texte = texte.replace(lieu, soude)
    return texte


# Chaque motif est cherché en début de mot (\b) dans le titre + la description.
MOTS_THEMES: dict[str, list[str]] = {
    "plage": [r"plages?\b", r"baignade", r"crique", r"bord de mer", r"sable fin"],
    "nautique": [
        r"plong", r"snorkel", r"tuba", r"kayak", r"jet-?ski", r"voilier", r"a la voile",
        r"bateau", r"barque", r"galion", r"croisiere", r"paddle", r"kitesurf",
        r"parachute ascensionnel", r"peche", r"sortie en mer",
    ],
    "culture": [
        r"musee", r"medina", r"artisan", r"poterie", r"potier", r"ceramique", r"calligraph",
        r"tradition", r"patrimoine", r"architecture", r"mosquee", r"synagogue", r"zaouia",
        r"street art", r"fresque", r"palais", r"musique", r"soufi", r"star wars",
        r"tournage", r"centre culturel", r"costume",
    ],
    "histoire": [
        r"romain", r"punique", r"antiq", r"vestige", r"ruine", r"amphitheatre", r"ribat",
        r"kasbah", r"fort\b", r"forteresse", r"borj", r"historique", r"histoire", r"unesco",
        r"[a-z]+e siecle", r"archeolog", r"mausolee", r"catacombe", r"mosaique",
        r"prehistoire", r"civilisation", r"ksour", r"ksar\b",
    ],
    "nature": [
        r"oasis", r"palmeraie", r"parc national", r"flamants?\b", r"lagune",
        r"reserve naturelle", r"oiseaux", r"montagne", r"cascade", r"canyon", r"gorges",
        r"faune", r"sentier", r"falaise", r"foret", r"oliveraie", r"orangeraie",
        r"vergers?", r"jardins?\b", r"zoo\b", r"animaux", r"tortue", r"randonnee",
        r"chott", r"lac sale", r"pins\b",
    ],
    "gastronomie": [
        r"cuisine", r"degust", r"gourmand", r"diner\b", r"couscous", r"brik", r"pain\b",
        r"harissa", r"huile d olive", r"patisserie", r"food", r"recette", r"criee",
        r"epices", r"makroudh", r"bambalouni", r"deglet",
    ],
    "aventure": [
        r"quad", r"buggy", r"4x4", r"randonnee", r"escalade", r"kitesurf", r"plong",
        r"jet-?ski", r"parachute", r"montgolfiere", r"canyon", r"gorges", r"velo",
        r"cheval", r"equestre", r"dromadaire", r"bivouac", r"kayak", r"manege",
        r"montagnes russes",
    ],
    "detente": [
        r"spa\b", r"hammams?\b", r"thalasso", r"massage", r"yoga", r"relax", r"detente",
        r"bien-etre", r"golf\b", r"au calme", r"couchant", r"coucher (du|de) soleil",
    ],
    "shopping": [
        r"souks?\b", r"boutiques?", r"bijoux", r"negocier", r"etals",
        r"marche hebdomadaire", r"marche du vendredi", r"a emporter",
    ],
    "desert": [
        r"desert", r"dunes?\b", r"sahar", r"\berg\b", r"dromadaire", r"meharee",
        r"bivouac", r"ksar\b", r"ksour", r"chott", r"lac sale", r"troglodyt", r"oasis",
    ],
}

# Thème apporté d'office par la catégorie (le catalogue l'a déjà décidé).
THEME_CATEGORIE: dict[str, str] = {
    "culture": "culture", "mer": "nautique", "desert": "desert", "aventure": "aventure",
    "gastronomie": "gastronomie", "bien-etre": "detente", "golf": "detente",
}
MAX_THEMES = 3

MOTS_ENFANTS = [
    r"enfants?\b", r"en famille", r"familles?\b", r"tous les ages", r"petits et grands",
    r"zoo\b", r"manege", r"parc d attractions", r"planetarium", r"animation",
]
MOTS_ADULTES = [
    r"des 16 ans", r"confirmes", r"pour les couples", r"en duo", r"massage",
    r"thalasso", r"hammams?\b", r"green-fee", r"18 trous",
]
MOTS_COUPLE = [r"couples?\b", r"en duo", r"a deux", r"romantique", r"couchant", r"coucher (du|de) soleil"]
MOTS_GROUPE = [
    r"groupe", r"excursion", r"journee\b", r"circuit", r"galion", r"bateau pirate",
    r"food tour", r"4x4", r"bivouac", r"campement", r"transport", r"cours de cuisine",
    r"animation",
]

MOTS_MARCHE_ELEVEE = [r"randonnee", r"\bmarche de \d+ km", r"montee vers", r"djebel", r"trek"]
MOTS_MARCHE_DOUCE = [r"facile", r"douce", r"debutants"]
MOTS_MARCHE_MOYENNE = [
    r"a pied", r"medina", r"souks?\b", r"site", r"ruines?", r"vestiges", r"ruelles",
    r"parc\b", r"zoo\b", r"amphitheatre", r"village", r"marche hebdomadaire", r"circuit",
]
MOTS_MARCHE_FAIBLE = [
    r"massage", r"hammams?\b", r"thalasso", r"spa\b", r"yoga", r"bateau", r"galion",
    r"croisiere", r"voilier", r"montgolfiere", r"caleche", r"4x4", r"quad", r"dromadaire",
    r"cheval", r"equestre", r"jet-?ski", r"parachute", r"degust", r"cours de cuisine",
    r"atelier", r"diner\b", r"planetarium", r"musee", r"plong", r"paddle", r"kayak",
    r"voiturette", r"calligraph",
]

# Indices « dedans » forts (comptent double) puis ordinaires.
MOTS_INTERIEUR_FORTS = [
    r"musee", r"hammams?\b", r"spa\b", r"thalasso", r"massage", r"planetarium",
    r"cite des sciences", r"cours de cuisine", r"catacombe",
]
MOTS_INTERIEUR = [r"atelier", r"calligraph", r"souterrain", r"palais", r"demeure"]
MOTS_EXTERIEUR = [
    r"plein air", r"plages?\b", r"bateau", r"randonnee", r"parc\b", r"jardins?\b", r"terrasse",
    r"dunes?\b", r"palmeraie", r"velo", r"ruelles", r"site", r"vestiges", r"golf\b",
    r"desert", r"oasis", r"marche\b", r"cour\b", r"lagune", r"medina", r"souks?\b",
    r"amphitheatre", r"arene",
]

MOTS_SOIR = [
    r"coucher (du|de) soleil", r"couchant", r"\bsoir", r"diner\b", r"\bnuit\b", r"etoiles",
    r"lumiere devient doree", r"s embrase",
]
MOTS_MATIN = [r"lever du (soleil|jour)", r"petit matin", r"matinee", r"au lever"]


def _trouves(motifs: list[str], texte: str) -> list[str]:
    trouves = []
    for motif in motifs:
        m = re.search(r"(?<![a-z0-9])" + motif.removeprefix(r"\b"), texte)
        if m:
            trouves.append(m.group(0).strip())
    return trouves


def _moment_par_creneaux(act: ActiviteSource) -> tuple[str, str] | None:
    """Moment déduit des horaires réels des créneaux (si l'activité est courte).

    Un horaire unique « ordinaire » (9 h, 10 h…) vient souvent du seed et ne dit
    rien du moment idéal : il ne compte que s'il est très tôt ou en fin de journée."""
    if not act.heures or act.duree > 360:
        return None
    minutes = [h.hour * 60 + h.minute for h in act.heures]
    if len(minutes) == 1 and 8 * 60 < minutes[0] < 16 * 60 + 30:
        return None
    if all(m < 12 * 60 for m in minutes) and act.duree <= 240:
        return "matin", "créneaux avant midi"
    if all(m >= 16 * 60 + 30 for m in minutes):
        return "soir", "créneaux à partir de 16 h 30"
    if all(12 * 60 <= m < 16 * 60 + 30 for m in minutes):
        return "apres_midi", "créneaux l'après-midi"
    return None


def proposer_regles(act: ActiviteSource) -> Proposition:
    texte = normaliser(f"{act.titre}. {act.description}")
    raisons: list[str] = []
    indices = 0  # nombre de mots-clés trouvés : sert à la confiance

    # --- Thèmes : catégorie d'abord, puis les plus cités dans le texte
    scores: Counter = Counter()
    for theme, motifs in MOTS_THEMES.items():
        trouves = _trouves(motifs, texte)
        if trouves:
            scores[theme] = len(trouves)
            indices += len(trouves)
            raisons.append(f"{theme} ← {', '.join(trouves[:3])}")
    theme_cat = THEME_CATEGORIE.get(normaliser(act.categorie))
    classes = sorted(scores, key=lambda t: (-scores[t], THEMES.index(t)))
    themes = ([theme_cat] if theme_cat else []) + [t for t in classes if t != theme_cat]
    if theme_cat:
        raisons.append(f"{theme_cat} ← catégorie {act.categorie}")
    themes = themes[:MAX_THEMES] or ["culture"]

    # --- Public
    enfants = _trouves(MOTS_ENFANTS, texte)
    adultes = _trouves(MOTS_ADULTES, texte)
    age = re.search(r"des (\d+) ans", texte)
    age_min = int(age.group(1)) if age else None
    # Catégorie « Famille & loisirs » : public visé famille + enfants seulement.
    est_famille_cat = normaliser(act.categorie).startswith("famille")
    public: list[str] = []
    if (enfants or est_famille_cat or (age_min is not None and age_min <= 12)) and not adultes:
        public += ["famille", "enfants"]
        raisons.append(f"famille/enfants ← {', '.join(enfants) or (f'dès {age_min} ans' if age_min else 'catégorie')}")
    elif not adultes:
        public.append("famille")
    else:
        raisons.append(f"pas d'enfants ← {', '.join(adultes)}")
    couple = _trouves(MOTS_COUPLE, texte)
    if couple or not est_famille_cat:
        public.append("couple")
        if couple:
            raisons.append(f"couple ← {', '.join(couple)}")
    if not (est_famille_cat or "en duo" in texte or "pour les couples" in texte):
        public.append("solo")
    groupe = _trouves(MOTS_GROUPE, texte)
    if groupe:
        public.append("groupe")
        raisons.append(f"groupe ← {', '.join(groupe[:3])}")
    indices += len(enfants) + len(adultes) + len(couple) + len(groupe)
    public = [p for p in PUBLICS if p in public] or ["couple", "solo"]

    # --- Niveau de marche : élevé > moyen > faible, moyen par défaut
    elevee = _trouves(MOTS_MARCHE_ELEVEE, texte)
    douce = _trouves(MOTS_MARCHE_DOUCE, texte)
    moyenne = _trouves(MOTS_MARCHE_MOYENNE, texte)
    faible = _trouves(MOTS_MARCHE_FAIBLE, texte)
    if elevee and not douce:
        niveau, pourquoi = 3, elevee
    elif elevee or moyenne:
        niveau, pourquoi = 2, elevee + douce + moyenne
    elif faible:
        niveau, pourquoi = 1, faible
    else:
        niveau, pourquoi = 2, ["aucun indice, valeur moyenne par défaut"]
    raisons.append(f"marche {niveau} ← {', '.join(pourquoi[:3])}")
    indices += len(elevee) + len(moyenne) + len(faible)

    # --- Intérieur : plus d'indices « dedans » (forts ×2) que « dehors »
    forts = _trouves(MOTS_INTERIEUR_FORTS, texte)
    dedans = 2 * len(forts) + len(_trouves(MOTS_INTERIEUR, texte))
    dehors = len(_trouves(MOTS_EXTERIEUR, texte))
    interieur = dedans > dehors
    indices += len(forts)
    raisons.append(
        f"{'intérieur' if interieur else 'extérieur'} ← dedans {dedans} / dehors {dehors}"
    )

    # --- Moment idéal : texte d'abord, puis horaires des créneaux
    soir, matin = _trouves(MOTS_SOIR, texte), _trouves(MOTS_MATIN, texte)
    if soir and not matin:
        moment, pourquoi_m = "soir", ", ".join(soir)
    elif matin and not soir:
        moment, pourquoi_m = "matin", ", ".join(matin)
    elif (par_creneaux := _moment_par_creneaux(act)) is not None:
        moment, pourquoi_m = par_creneaux
    else:
        moment, pourquoi_m = "indifferent", "aucun indice"
    raisons.append(f"moment {moment} ← {pourquoi_m}")

    confiance = "haute" if indices >= 6 else "moyenne" if indices >= 3 else "faible"
    tags = TagsIA(
        themes=themes, public=public, niveau_marche=niveau,
        interieur=interieur, moment_ideal=moment,
    )
    return Proposition(tags=tags, confiance=confiance, raisons=raisons)


# ===========================================================================
# Fournisseurs LLM — appel direct, même consigne pour Claude et Ollama
# ===========================================================================


class PropositionLLM(BaseModel):
    """Schéma de sortie imposé au LLM (puis revalidé par TagsIA)."""

    themes: list[Theme]
    public: list[Public]
    niveau_marche: Literal[1, 2, 3]
    interieur: bool
    moment_ideal: MomentIdeal


CONSIGNE = f"""Tu étiquettes des activités touristiques en Tunisie pour un moteur de recommandation.
Réponds uniquement avec l'objet JSON demandé, en utilisant exclusivement ces valeurs :
- themes : 1 à {MAX_THEMES} valeurs parmi {", ".join(THEMES)} (les plus caractéristiques d'abord)
- public : une ou plusieurs valeurs parmi {", ".join(PUBLICS)} (« enfants » seulement si l'activité convient à des enfants de moins de 12 ans)
- niveau_marche : 1 (faible : on reste assis ou on marche très peu), 2 (moyen : visite à pied), 3 (élevé : randonnée, montée, longue marche)
- interieur : true si l'activité se déroule surtout à l'intérieur (utile en cas de pluie)
- moment_ideal : parmi {", ".join(MOMENTS)}
N'invente rien : déduis uniquement du titre, de la catégorie et de la description."""


def _message(act: ActiviteSource) -> str:
    return f"Titre : {act.titre}\nCatégorie : {act.categorie}\nDescription : {act.description}"


def proposer_claude(act: ActiviteSource, modele: str) -> Proposition:
    import anthropic  # facultatif : seulement pour ce fournisseur

    client = anthropic.Anthropic()  # lit ANTHROPIC_API_KEY (chargée depuis .env)
    reponse = client.messages.parse(
        model=modele,
        max_tokens=1024,
        system=CONSIGNE,
        output_config={"effort": "low"},  # classification courte
        messages=[{"role": "user", "content": _message(act)}],
        output_format=PropositionLLM,
    )
    if reponse.stop_reason == "refusal":
        raise ValueError("refus du modèle")
    sortie = reponse.parsed_output
    if sortie is None:
        raise ValueError(f"réponse vide (stop_reason={reponse.stop_reason})")
    return Proposition(tags=TagsIA(**sortie.model_dump()))


def proposer_ollama(act: ActiviteSource, modele: str, url: str) -> Proposition:
    import httpx

    reponse = httpx.post(
        f"{url.rstrip('/')}/api/chat",
        json={
            "model": modele,
            "stream": False,
            "format": PropositionLLM.model_json_schema(),
            "options": {"temperature": 0},
            "messages": [
                {"role": "system", "content": CONSIGNE},
                {"role": "user", "content": _message(act)},
            ],
        },
        timeout=120,
    )
    reponse.raise_for_status()
    contenu = json.loads(reponse.json()["message"]["content"])
    return Proposition(tags=TagsIA(**PropositionLLM(**contenu).model_dump()))


# ===========================================================================
# Lecture (READ ONLY) et écriture du CSV
# ===========================================================================


def charger_activites(ids: list[int] | None, statut: str | None) -> list[ActiviteSource]:
    from sqlalchemy import select, text

    os.chdir(RACINE_SERVICE)  # .env du service (connexion à la base)
    from app.database import SessionLocal
    from app.models import Activity, Availability, Category

    with SessionLocal() as db:
        db.execute(text("SET TRANSACTION READ ONLY"))  # garantie : aucune écriture
        stmt = select(Activity, Category.nom).join(Category, Activity.category_id == Category.id)
        if ids:
            stmt = stmt.where(Activity.id.in_(ids))
        if statut:
            stmt = stmt.where(Activity.statut == statut)
        lignes = db.execute(stmt.order_by(Activity.id)).all()
        heures: dict[int, set[time]] = {}
        for activity_id, heure in db.execute(
            select(Availability.activity_id, Availability.heure).distinct()
        ):
            heures.setdefault(activity_id, set()).add(heure)
        activites = [
            ActiviteSource(
                id=a.id, titre=a.titre, description=a.description, categorie=nom,
                duree=a.duree, heures=sorted(heures.get(a.id, set())),
            )
            for a, nom in lignes
        ]
        db.rollback()  # fin de la transaction en lecture seule
    return activites


def ligne_csv(act: ActiviteSource, fournisseur: str, modele: str, prop: Proposition | None,
              erreur: str = "") -> dict:
    base = {
        "activity_id": act.id, "titre": act.titre, "categorie": act.categorie,
        "fournisseur": fournisseur, "modele": modele, "erreur": erreur,
    }
    if prop is None:
        return {**base, "statut": "erreur"}
    t = prop.tags
    return {
        **base,
        "statut": "ok",
        "themes": "|".join(t.themes),
        "public": "|".join(t.public),
        "niveau_marche": t.niveau_marche,
        "interieur": "oui" if t.interieur else "non",
        "moment_ideal": t.moment_ideal,
        "confiance": prop.confiance,
        "raisons": " ; ".join(prop.raisons),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--fournisseur", choices=["regles", "claude", "ollama"], default="regles")
    parser.add_argument("--modele", help=f"défaut : {MODELE_CLAUDE} (claude), {MODELE_OLLAMA} (ollama)")
    parser.add_argument("--ids", help="liste d'id séparés par des virgules")
    parser.add_argument("--statut", choices=["publiee", "en_attente", "refusee"])
    parser.add_argument("--limite", type=int, help="n'étiqueter que les N premières activités")
    parser.add_argument("--sortie", type=Path, help="CSV produit (défaut : data/etiquetage/propositions_<fournisseur>.csv)")
    args = parser.parse_args()

    from dotenv import load_dotenv

    load_dotenv(RACINE_SERVICE / ".env")  # ANTHROPIC_API_KEY / OLLAMA_URL éventuels

    modele = {
        "regles": "regles-v1",
        "claude": args.modele or MODELE_CLAUDE,
        "ollama": args.modele or MODELE_OLLAMA,
    }[args.fournisseur]
    if args.fournisseur == "claude" and not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY absente de services/catalog/.env : utiliser --fournisseur regles ou ollama.")
    ollama_url = os.environ.get("OLLAMA_URL", "http://localhost:11434")

    ids = [int(x) for x in args.ids.split(",")] if args.ids else None
    activites = charger_activites(ids, args.statut)
    if args.limite:
        activites = activites[: args.limite]

    sortie = args.sortie or DOSSIER_SORTIE / f"propositions_{args.fournisseur}.csv"
    if not sortie.is_absolute():
        sortie = RACINE_SERVICE / sortie
    sortie.parent.mkdir(parents=True, exist_ok=True)

    lignes, erreurs = [], 0
    for act in activites:
        try:
            if args.fournisseur == "regles":
                prop = proposer_regles(act)
            elif args.fournisseur == "claude":
                prop = proposer_claude(act, modele)
            else:
                prop = proposer_ollama(act, modele, ollama_url)
            lignes.append(ligne_csv(act, args.fournisseur, modele, prop))
        except (ValidationError, ValueError, KeyError) as exc:  # réponse LLM hors vocabulaire
            if args.fournisseur == "regles":
                raise
            erreurs += 1
            lignes.append(ligne_csv(act, args.fournisseur, modele, None, str(exc)[:300]))
        except Exception as exc:  # LLM : réseau, quota, modèle absent… on continue
            if args.fournisseur == "regles":
                raise  # en local, une exception est un bogue : on ne la masque pas
            erreurs += 1
            lignes.append(ligne_csv(act, args.fournisseur, modele, None, f"{type(exc).__name__}: {exc}"[:300]))

    # utf-8-sig : le CSV s'ouvre correctement dans Excel (accents, arabe)
    with sortie.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLONNES_CSV)
        writer.writeheader()
        writer.writerows(lignes)

    ok = [l for l in lignes if l["statut"] == "ok"]
    print(f"{len(activites)} activité(s) lue(s) en lecture seule, {len(ok)} proposition(s), {erreurs} erreur(s).")
    print(f"CSV : {sortie}  ({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC, fournisseur {args.fournisseur}, modèle {modele})")
    if ok:
        compte = lambda cle: Counter(v for l in ok for v in str(l[cle]).split("|"))  # noqa: E731
        print("Thèmes   :", dict(compte("themes").most_common()))
        print("Public   :", dict(compte("public").most_common()))
        print("Marche   :", dict(sorted(compte("niveau_marche").items())))
        print("Intérieur:", dict(compte("interieur").most_common()))
        print("Moment   :", dict(compte("moment_ideal").most_common()))
        print("Confiance:", dict(compte("confiance").most_common()))


if __name__ == "__main__":
    main()
