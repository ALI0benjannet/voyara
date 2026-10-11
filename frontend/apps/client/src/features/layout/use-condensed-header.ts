"use client";

import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";

import { paths } from "@/routes/paths";

/** Défilement (px) au-delà duquel l'en-tête se condense sur une seule ligne.
 *  Correspond à peu près au moment où le hero de l'accueil sort de l'écran. */
const CONDENSE_THRESHOLD = 320;

/** État de l'en-tête : déployé (2 rangées) ou condensé (1 seule).
 *
 *  Condensé, l'en-tête ne garde que le logo, la recherche et les icônes ; les
 *  onglets de navigation disparaissent pour libérer de la hauteur — le modèle
 *  des grands sites de réservation.
 *
 *  Sur le catalogue il n'y a pas de hero à laisser défiler : l'en-tête y est
 *  condensé d'emblée, avec la recherche toujours accessible.
 */
export function useCondensedHeader() {
  const pathname = usePathname();
  const onHome = pathname === "/";
  const onCatalog = pathname === paths.activities;

  // Sur le catalogue, l'état est connu sans attendre le moindre défilement.
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    if (!onHome) return;

    const update = () => setScrolled(window.scrollY > CONDENSE_THRESHOLD);
    update(); // état correct si la page est rechargée en cours de défilement

    // `passive` : ce handler ne bloque jamais le défilement.
    window.addEventListener("scroll", update, { passive: true });
    return () => window.removeEventListener("scroll", update);
  }, [onHome]);

  const condensed = onCatalog || (onHome && scrolled);

  return {
    condensed,
    /** La recherche n'a de sens que là où l'on cherche des activités. */
    showSearch: (onHome || onCatalog) && condensed,
    /** Les onglets s'effacent une fois l'en-tête condensé. */
    showTabs: !condensed,
  };
}
