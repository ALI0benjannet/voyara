"""Accord entre annotateurs : annotation d'origine de l'équipe vs annotation du jeu NLU.

Pour chaque champ comparable des 100 demandes humaines : pourcentage d'accord et, pour les
champs catégoriels, kappa de Cohen (accord corrigé du hasard ; `null` compte comme une catégorie).
Sorties : docs/ia/resultats/accord_annotateurs.md et .csv.

    cd services\\ai ; ..\\..\\.venv\\Scripts\\python scripts\\accord_annotateurs.py
"""

import argparse
import csv
import sys
from collections import Counter
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import jeu_nlu as j  # noqa: E402

DOSSIER_RESULTATS = Path(__file__).resolve().parents[3] / "docs" / "ia" / "resultats"
CHAMPS_CATEGORIELS = ("destination", "langue", "type_voyage", "budget_devise", "budget_base", "ville_depart",
                      "vol", "voiture", "transfert")


def kappa_cohen(a: list, b: list) -> float | None:
    """κ = (p_o − p_e) / (1 − p_e). None si p_e = 1 (une seule catégorie : κ indéfini)."""
    n = len(a)
    if n == 0:
        return None
    cles = [repr(x) for x in a], [repr(x) for x in b]
    p_o = sum(x == y for x, y in zip(*cles)) / n
    freq_a, freq_b = Counter(cles[0]), Counter(cles[1])
    p_e = sum(freq_a[c] * freq_b[c] for c in set(freq_a) | set(freq_b)) / (n * n)
    if p_e == 1:
        return None
    return (p_o - p_e) / (1 - p_e)


def interpreter(k: float | None) -> str:
    """Échelle de Landis et Koch (1977)."""
    if k is None:
        return "indéfini"
    for seuil, libelle in ((0.8, "presque parfait"), (0.6, "substantiel"), (0.4, "modéré"),
                           (0.2, "passable"), (0.0, "faible")):
        if k > seuil:
            return libelle
    return "nul ou négatif"


def calculer(demandes: list[dict]) -> list[dict]:
    paires = [(j.attendu_equipe(d["annotation_equipe"]), d["attendu"]) for d in demandes if d.get("annotation_equipe")]
    lignes = []
    for champ in j.CHAMPS_COMPARES:
        a = [eq[champ] for eq, _ in paires]
        b = [j.valeur_comparable(at, champ) for _, at in paires]
        accords = sum(x == y for x, y in zip(a, b))
        k = kappa_cohen(a, b) if champ in CHAMPS_CATEGORIELS else None
        lignes.append({
            "champ": champ, "n": len(paires), "accords": accords,
            "accord_pct": round(100 * accords / len(paires), 1) if paires else None,
            "kappa": round(k, 3) if k is not None else None,
            "interpretation": interpreter(k) if champ in CHAMPS_CATEGORIELS else "—",
        })
    # Activités : codes normalisés côté équipe, textes tels que dits côté jeu → seul le nombre se compare.
    a = [eq["nb_activites"] for eq, _ in paires]
    b = [len(at["activites_souhaitees"]) for _, at in paires]
    accords = sum(x == y for x, y in zip(a, b))
    lignes.append({
        "champ": "activites (nombre)", "n": len(paires), "accords": accords,
        "accord_pct": round(100 * accords / len(paires), 1) if paires else None, "kappa": None,
        "interpretation": "—",
    })
    return lignes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sortie", type=Path, default=DOSSIER_RESULTATS)
    args = parser.parse_args()

    demandes = j.lire_jsonl(j.DOSSIER_EVAL / j.FICHIER_HUMAINES)
    statuts = Counter(d.get("statut") for d in demandes)
    lignes = calculer(demandes)
    args.sortie.mkdir(parents=True, exist_ok=True)

    with (args.sortie / "accord_annotateurs.csv").open("w", encoding="utf-8", newline="") as f:
        ecrivain = csv.DictWriter(f, fieldnames=list(lignes[0]))
        ecrivain.writeheader()
        ecrivain.writerows(lignes)

    kappas = [l["kappa"] for l in lignes if l["kappa"] is not None]
    md = [
        "# Accord entre annotateurs — jeu NLU (étape 4)",
        "",
        f"> Généré le {date.today().isoformat()} par `services/ai/scripts/accord_annotateurs.py`. "
        f"Annotateur A : équipe (`brut/demandes_equipe.json`) ; annotateur B : annotation du jeu "
        f"(`{j.FICHIER_HUMAINES}`). {lignes[0]['n']} demandes humaines ; statuts : "
        + ", ".join(f"{s} {n}" for s, n in sorted(statuts.items())) + ".",
        "",
        "| Champ | n | Accords | Accord (%) | κ de Cohen | Interprétation |",
        "|---|---|---|---|---|---|",
    ]
    for l in lignes:
        k = "—" if l["kappa"] is None else f"{l['kappa']:.3f}"
        md.append(f"| `{l['champ']}` | {l['n']} | {l['accords']} | {l['accord_pct']} | {k} | {l['interpretation']} |")
    md += [
        "",
        f"κ moyen sur les {len(kappas)} champs catégoriels : **{sum(kappas) / len(kappas):.3f}**." if kappas else "",
        "",
        "Lecture : κ corrige l'accord du hasard (`null` compte comme une catégorie) ; échelle de Landis et "
        "Koch : > 0,8 presque parfait, > 0,6 substantiel, > 0,4 modéré. Les champs numériques ou listes "
        "(voyageurs, durée, montant, autres villes, champs manquants) n'ont qu'un pourcentage d'accord exact. "
        "Pour les activités, l'équipe note des codes normalisés (`nuit_desert`) et le jeu des textes tels que "
        "dits (« nuit sous tente ») : seul le **nombre** d'activités par demande est comparé. "
        "Une partie des désaccords est **voulue** : les règles du README (budget par personne converti en "
        "total, date manquante pour un vol, type de voyage plus strict) ont été appliquées après coup à "
        "l'annotation B.",
        "",
        "**Limite : les deux annotations ne sont pas indépendantes.** B est une pré-annotation faite en "
        "voyant A (ordre des villes, `budget_base` repris de `budget_type`, correspondance des langues). "
        "Les accords sont donc **surestimés**, en particulier à 100 % pour `destination`, `langue` et "
        "`budget_base`. Une mesure indépendante demanderait qu'un second annotateur annote à l'aveugle un "
        "sous-échantillon.",
    ]
    (args.sortie / "accord_annotateurs.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    for l in lignes:
        print(f"{l['champ']:<18} {l['accord_pct']:>5} %  κ={l['kappa']}")
    print(f"→ {args.sortie / 'accord_annotateurs.md'}")


if __name__ == "__main__":
    main()
