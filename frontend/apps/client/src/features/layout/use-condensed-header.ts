"use client";

import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";

import { paths } from "@/routes/paths";

/** Hystérésis : l'en-tête se compacte au-delà de 96 px et ne se redéploie
 *  qu'en dessous de 32 px. Un seuil unique ferait osciller l'état quand
 *  l'utilisateur s'arrête juste autour, d'où un clignotement. */
const CONDENSE_AFTER = 96;
const EXPAND_BEFORE = 32;

/** État de l'en-tête.
 *
 *  La navigation principale (Séjours, Vols, Voitures, Activités, Transferts)
 *  reste **toujours visible** : c'est le repère de l'utilisateur, sur toutes
 *  les pages, comme sur les grands sites de réservation. Au défilement, seule la
 *  rangée « Espace voyageur / Espace prestataire » se replie pour rendre de la
 *  hauteur au contenu ; elle revient en haut de page.
 */
export function useCondensedHeader() {
  const pathname = usePathname();
  const onHome = pathname === "/";
  const onCatalog = pathname === paths.activities;

  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    // L'état ne change qu'en franchissant un seuil ; entre les deux, il est
    // conservé (React ignore un setState à valeur identique : pas de rendu).
    const update = () => {
      const y = window.scrollY;
      if (y > CONDENSE_AFTER) setScrolled(true);
      else if (y < EXPAND_BEFORE) setScrolled(false);
    };
    update(); // état correct si la page est rechargée en cours de défilement

    // `passive` : ce handler ne bloque jamais le défilement.
    window.addEventListener("scroll", update, { passive: true });
    return () => window.removeEventListener("scroll", update);
  }, [pathname]);

  return {
    /** Rangée des espaces repliée (défilement en cours). */
    condensed: scrolled,
    /** La recherche n'a de sens que là où l'on cherche des activités. Sur
     *  l'accueil, le hero est occupé par l'agent IA : la recherche vit donc en
     *  permanence dans l'en-tête. */
    showSearch: onHome || onCatalog,
  };
}
