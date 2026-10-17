"use client";

import { useState, type FormEvent } from "react";
import { Landmark, Mountain, Sparkles, TextSearch, Umbrella, Utensils } from "lucide-react";

import { useHydratedTranslation } from "@/features/i18n/use-hydrated-language";

/** Inspirations proposées sous le champ : un clic pré-remplit la demande. */
const INSPIRATIONS = [
  { key: "culture", icon: Landmark },
  { key: "beach", icon: Umbrella },
  { key: "sahara", icon: Mountain },
  { key: "food", icon: Utensils },
] as const;

/** Agent IA de l'accueil — point d'entrée principal du hero.
 *
 *  Le titre et le sous-titre vivent dans le hero (`app/page.tsx`) ; ce
 *  composant porte la carte de saisie et les inspirations. La recherche
 *  classique a rejoint l'en-tête (voir `useCondensedHeader`).
 *
 *  Emplacement réservé à l'agent IA (moteur prévu dans `services/ai`,
 *  ADR-007) : l'interface est en place, mais la demande n'est encore envoyée
 *  nulle part — valider affiche seulement un message « bientôt disponible ».
 *  Le branchement se fera ici, dans `submit`. */
export function AiTripPlanner() {
  const { t } = useHydratedTranslation();
  const [prompt, setPrompt] = useState("");
  const [submitted, setSubmitted] = useState(false);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    // TODO(agent IA) : appeler le service ai via le gateway.
    setSubmitted(true);
  };

  const inspire = (label: string) => {
    setPrompt((current) => (current.trim() ? `${current.trim()}, ${label}` : label));
    setSubmitted(false);
  };

  return (
    <div className="border-border bg-card/95 mx-auto max-w-[46rem] rounded-2xl border p-4 text-start shadow-[0_18px_44px_rgba(28,54,65,.25)] backdrop-blur-sm">
      <span className="bg-primary/10 text-primary-hover inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold">
        <Sparkles aria-hidden className="size-3.5" />
        {t("home.aiPlanner.badge")}
      </span>

      <form onSubmit={submit} className="border-border bg-background/60 mt-3 rounded-xl border p-3">
        <div className="flex items-start gap-3">
          <TextSearch aria-hidden className="text-primary mt-0.5 size-4 shrink-0" />
          <textarea
            value={prompt}
            onChange={(e) => {
              setPrompt(e.target.value);
              setSubmitted(false);
            }}
            rows={2}
            placeholder={t("home.aiPlanner.placeholder")}
            aria-label={t("home.aiPlanner.title")}
            className="text-foreground placeholder:text-foreground/40 min-h-11 w-full resize-none bg-transparent text-sm focus:outline-none"
          />
        </div>
        <div className="mt-2 flex flex-wrap items-center justify-between gap-3">
          <span className="text-muted-foreground inline-flex items-center gap-2 text-xs font-medium">
            <span aria-hidden className="bg-gold size-2 rounded-full" />
            {t("home.aiPlanner.status")}
          </span>
          <button
            type="submit"
            className="bg-primary text-primary-foreground hover:bg-primary-hover focus-visible:ring-primary inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold transition-colors focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:outline-none"
          >
            <Sparkles aria-hidden className="size-4" />
            {t("home.aiPlanner.generate")}
          </button>
        </div>
        {submitted && (
          <p role="status" className="text-muted-foreground mt-2 text-xs">
            {t("home.aiPlanner.soon")}
          </p>
        )}
      </form>

      {/* Une seule ligne, sans défilement : les pastilles se partagent la
          largeur restante (2 × 2 sur mobile, où le libellé est masqué). */}
      <div className="mt-3 flex items-center gap-2">
        <span className="text-muted-foreground hidden shrink-0 text-xs font-medium sm:inline">
          {t("home.aiPlanner.inspirations")}
        </span>
        <div className="grid flex-1 grid-cols-2 gap-1.5 sm:grid-cols-4">
          {INSPIRATIONS.map(({ key, icon: Icon }) => (
            <button
              key={key}
              type="button"
              onClick={() => inspire(t(`home.aiPlanner.chips.${key}`))}
              className="border-border bg-card hover:border-primary hover:text-primary focus-visible:ring-primary inline-flex min-w-0 items-center justify-center gap-1 rounded-full border px-2 py-1 text-xs font-semibold transition-colors focus-visible:ring-2 focus-visible:outline-none"
            >
              <Icon aria-hidden className="text-primary size-3.5 shrink-0" />
              <span className="truncate">{t(`home.aiPlanner.chips.${key}`)}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
