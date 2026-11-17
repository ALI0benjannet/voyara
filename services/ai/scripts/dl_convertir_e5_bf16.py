"""Convertit modeles/multilingual-e5-base en bfloat16 (≈ 560 Mo au lieu de 1,1 Go).

Pour la page « DL test » sur un poste à peu de mémoire : le fichier float32 ne peut pas être
ouvert d'un bloc quand la mémoire virtuelle libre est insuffisante (erreur Windows 1455). Le
fichier est donc lu tenseur par tenseur (sans mmap) et réécrit au fil de l'eau, sans jamais
tout garder en mémoire. Les classements obtenus sont quasi identiques (arrondis bf16).

Usage (depuis services/ai) :
    ..\\..\\.venv\\Scripts\\python scripts\\dl_convertir_e5_bf16.py
"""

import json
import shutil
import struct
import sys
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.dl import chemins  # noqa: E402

TAILLES = {"F32": 4, "F16": 2, "BF16": 2, "I64": 8}
TRANCHE = 16 * 1024 * 1024  # multiple de 4 octets


def convertir(source: Path, cible: Path) -> None:
    cible.mkdir(parents=True, exist_ok=True)
    for f in source.rglob("*"):
        if f.is_file() and f.name != "model.safetensors":
            dest = cible / f.relative_to(source)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, dest)

    with (source / "model.safetensors").open("rb") as entree:
        n = struct.unpack("<Q", entree.read(8))[0]
        entete = json.loads(entree.read(n))
        debut_donnees = 8 + n
        meta = entete.pop("__metadata__", None)

        nouvel, decalage = {}, 0
        for nom, info in entete.items():
            dtype = "BF16" if info["dtype"] == "F32" else info["dtype"]
            taille = int(np.prod(info["shape"])) * TAILLES[dtype] if info["shape"] else TAILLES[dtype]
            nouvel[nom] = {"dtype": dtype, "shape": info["shape"], "data_offsets": [decalage, decalage + taille]}
            decalage += taille
        if meta:
            nouvel["__metadata__"] = meta
        octets_entete = json.dumps(nouvel, separators=(",", ":")).encode()
        octets_entete += b" " * (-len(octets_entete) % 8)

        with (cible / "model.safetensors").open("wb") as sortie:
            sortie.write(struct.pack("<Q", len(octets_entete)))
            sortie.write(octets_entete)
            for nom, info in nouvel.items():
                if nom == "__metadata__":
                    continue
                ancien = entete[nom]
                a, b = ancien["data_offsets"]
                entree.seek(debut_donnees + a)
                restant = b - a
                while restant:  # tranches de 16 Mo : la table de vocabulaire seule pèse 732 Mo
                    brut = entree.read(min(TRANCHE, restant))
                    restant -= len(brut)
                    if ancien["dtype"] == "F32":
                        t = torch.from_numpy(np.frombuffer(brut, dtype=np.float32).copy()).to(torch.bfloat16)
                        brut = t.view(torch.int16).numpy().tobytes()
                    sortie.write(brut)
    print(f"Converti : {cible} ({(cible / 'model.safetensors').stat().st_size / 1e6:.0f} Mo)")


if __name__ == "__main__":
    convertir(chemins.E5_LOCAL, chemins.E5_LOCAL_BF16)
