"""Photos de démonstration du catalogue (idempotent).

Télécharge une photo libre de droits par activité depuis Wikimedia Commons,
l'enregistre dans `static/activities/` (même emplacement que les uploads admin)
et renseigne le champ `photos` de l'activité.

Les activités qui ont déjà une photo ne sont pas touchées : le script ne
remplace jamais une image uploadée depuis l'admin.

Usage (depuis services/catalog) : python scripts/seed_photos.py
"""

import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal  # noqa: E402
from app.models import Activity  # noqa: E402

# La console Windows est en cp1252 : sans cela, un titre accentué fait planter
# le script *après* le téléchargement, et le commit est perdu.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PHOTO_DIR = Path(__file__).resolve().parent.parent / "static" / "activities"
# Attribution des photos, consommée par la page /credits du site client.
CREDITS_FILE = (
    Path(__file__).resolve().parents[3]
    / "frontend"
    / "apps"
    / "client"
    / "src"
    / "app"
    / "credits"
    / "photo-credits.json"
)
USER_AGENT = "Voyara/1.0 (projet étudiant ; seed de démonstration)"

# Fichiers Wikimedia Commons choisis à la main pour coller au sujet de chaque
# activité. Tous sous licence libre (CC BY / CC BY-SA / domaine public) —
# l'attribution est portée par la page « crédits photo » du site.
PHOTOS: dict[str, tuple[str, str]] = {
    # titre d'activité : (fichier Commons, licence)
    "Sidi Bou Saïd & Carthage": ("Sidi Bou Said 02.jpg", "CC BY-SA 4.0"),
    "Plongée aux récifs de Tabarka": ("Tabarka les aiguilles.jpg", "CC BY-SA 4.0"),
    "Bivouac dans le désert de Douz": ("Sand desert near Douz.jpg", "CC BY-SA 4.0"),
    "Food tour de la médina de Tunis": ("Souk el attarine à Tunis.jpg", "CC BY-SA 4.0"),
    "Kayak sur le lac de Bizerte": ("Old port of Bizerte, 2008.jpg", "CC BY 3.0"),
    "Montgolfière sur les oasis de Tozeur": ("Tozeur Oasis at sunset.jpg", "CC BY 2.0"),
    "Croisière au couchant à Djerba": ("Djerba plage.jpg", "CC BY-SA 4.0"),
    "Randonnée au Cap Bon": ("Les côtes de Korbous Takelsa.jpg", "CC BY-SA 4.0"),
}

# Largeur des vignettes téléchargées : suffisant pour le hero de la page détail
# sans stocker des originaux de 20 Mo.
THUMB_WIDTH = 1600


def commons_info(filename: str) -> tuple[str | None, str, str]:
    """Résout (url de vignette, auteur, page de description) via l'API Commons."""
    api = (
        "https://commons.wikimedia.org/w/api.php?action=query&format=json"
        f"&titles={urllib.parse.quote('File:' + filename)}"
        f"&prop=imageinfo&iiprop=url|extmetadata&iiurlwidth={THUMB_WIDTH}"
    )
    request = urllib.request.Request(api, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        data = json.load(response)
    for page in (data.get("query", {}).get("pages", {}) or {}).values():
        info = (page.get("imageinfo") or [{}])[0]
        meta = info.get("extmetadata", {})
        # `Artist` contient du HTML (lien vers le profil) : on garde le texte.
        artist = re.sub(r"<[^>]+>", "", meta.get("Artist", {}).get("value", "")).strip()
        return (
            info.get("thumburl") or info.get("url"),
            artist or "Auteur inconnu",
            info.get("descriptionurl", ""),
        )
    return None, "Auteur inconnu", ""


def download(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def with_retry(action, attempts: int = 4):
    """Commons applique un quota (HTTP 429) : on réessaie en espaçant."""
    for attempt in range(attempts):
        try:
            return action()
        except urllib.error.HTTPError as exc:
            if exc.code != 429 or attempt == attempts - 1:
                raise
            time.sleep(3 * (attempt + 1))
    raise RuntimeError("quota Commons non levé")


def main() -> None:
    PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    db = SessionLocal()
    updated = skipped = failed = 0
    credits: list[dict[str, str]] = []
    try:
        for titre, (commons_file, licence) in PHOTOS.items():
            activity = db.query(Activity).filter(Activity.titre == titre).first()
            if activity is None:
                print(f"  ? activité absente : {titre}")
                continue
            if activity.photos:
                print(f"  = {titre} a déjà une photo, ignorée")
                skipped += 1
                continue

            try:
                url, artist, page_url = with_retry(lambda: commons_info(commons_file))
                if not url:
                    raise RuntimeError("fichier introuvable sur Commons")
                content = with_retry(lambda: download(url))
            except Exception as exc:  # réseau, fichier renommé, quota…
                print(f"  ! {titre} : {exc}")
                failed += 1
                continue

            # Même convention de nom que l'upload admin : <id>-<hash><ext>
            extension = Path(urllib.parse.urlparse(url).path).suffix.lower() or ".jpg"
            digest = hashlib.md5(content).hexdigest()
            filename = f"{activity.id}-{digest}{extension}"
            (PHOTO_DIR / filename).write_bytes(content)

            activity.photos = f"/static/activities/{filename}"
            db.commit()  # commit au fil de l'eau : un quota atteint plus loin
            updated += 1  # ne fait pas perdre les photos déjà récupérées
            credits.append(
                {
                    "activite": titre,
                    "fichier": commons_file,
                    "auteur": artist,
                    "licence": licence,
                    "source": page_url,
                }
            )
            print(f"  + {titre} <- {commons_file} ({licence}, {artist})")
            time.sleep(1)  # reste sous le quota de Commons

        db.commit()

        # Fichier d'attribution : CC BY / CC BY-SA imposent de créditer l'auteur.
        if credits:
            existing = []
            if CREDITS_FILE.exists():
                existing = json.loads(CREDITS_FILE.read_text(encoding="utf-8"))
            known = {c["fichier"] for c in existing}
            existing.extend(c for c in credits if c["fichier"] not in known)
            CREDITS_FILE.parent.mkdir(parents=True, exist_ok=True)
            CREDITS_FILE.write_text(
                json.dumps(existing, ensure_ascii=False, indent=2) + chr(10),
                encoding="utf-8",
            )
            print(f"Crédits écrits dans {CREDITS_FILE}")

        print(f"Terminé : {updated} photo(s) ajoutée(s), {skipped} ignorée(s), {failed} échec(s).")
    finally:
        db.close()


if __name__ == "__main__":
    main()
