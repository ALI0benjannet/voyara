"use client";

import { useHydratedTranslation } from "@/features/i18n/use-hydrated-language";

/** Rend une clé i18n depuis un composant serveur.
 *
 *  Les pages du catalogue sont rendues côté serveur (SEO) et n'ont pas accès à
 *  la langue choisie dans le navigateur : elles importaient donc le JSON
 *  français en dur. Ce composant client rend la clé dans la langue active, tout
 *  en laissant le SSR produire le texte français indexable.
 *
 *  `useHydratedTranslation` diffère le passage à la langue de l'utilisateur
 *  jusqu'après l'hydratation, sans quoi React verrait « Été 2026 » côté serveur
 *  et « Summer 2026 » côté client, et regénérerait tout l'arbre. */
export function T({
  k,
  values,
  fallback,
}: {
  k: string;
  values?: Record<string, unknown>;
  fallback?: string;
}) {
  const { t } = useHydratedTranslation();
  return <>{fallback ? t(k, fallback, values) : t(k, values)}</>;
}
