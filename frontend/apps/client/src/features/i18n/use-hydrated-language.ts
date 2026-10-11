"use client";

import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

/** Langue utilisée pour le rendu serveur — voir `packages/i18n` (`lng: "fr"`). */
const SSR_LANGUAGE = "fr";

/**
 * Langue à utiliser pour le rendu, sans provoquer d'erreur d'hydratation.
 *
 * Le SSR rend toujours en français (le serveur n'a pas accès au `localStorage`
 * qui mémorise le choix de l'utilisateur). Si le premier rendu client utilisait
 * directement la langue détectée, React comparerait « Été 2026 » à
 * « Summer 2026 » et invaliderait tout l'arbre.
 *
 * On rend donc le français jusqu'à l'hydratation, puis on bascule sur la vraie
 * langue. Le texte français reste celui qui est indexé par les moteurs.
 */
export function useHydratedLanguage(): string {
  const { i18n } = useTranslation();
  const [hydrated, setHydrated] = useState(false);

  // `useEffect` ne s'exécute qu'après l'hydratation : le premier rendu client
  // est donc identique au HTML du serveur.
  useEffect(() => setHydrated(true), []);

  return hydrated ? (i18n.resolvedLanguage ?? i18n.language ?? SSR_LANGUAGE) : SSR_LANGUAGE;
}

/**
 * Variante pour les libellés d'interface : renvoie une fonction `t` figée sur
 * le français tant que l'hydratation n'a pas eu lieu.
 */
export function useHydratedTranslation() {
  const { t, i18n } = useTranslation();
  const language = useHydratedLanguage();

  // `getFixedT` renvoie un traducteur verrouillé sur une langue donnée.
  return {
    t: language === i18n.language ? t : i18n.getFixedT(language),
    language,
  };
}
