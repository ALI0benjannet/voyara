"use client";

import { useState, type FormEvent } from "react";
import { Landmark, Mountain, Sparkles, Star, TextSearch, Umbrella, Utensils } from "lucide-react";

import { useHydratedTranslation } from "@/features/i18n/use-hydrated-language";

/** Inspirations proposées sous le champ : un clic pré-remplit la demande. */
const INSPIRATIONS = [
  { key: "culture", icon: Landmark },
  { key: "beach", icon: Umbrella },
  { key: "sahara", icon: Mountain },
  { key: "food", icon: Utensils },
] as const;

/** Bloc « Explorez la Tunisie selon vos envies » de l'accueil.
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
    <div className="bg-secondary/60 relative overflow-hidden rounded-3xl p-6 sm:p-8">
      {/* Étoile en filigrane : décor, jamais lue. */}
      <Star
        aria-hidden
        strokeWidth={1}
        className="text-primary/10 fill-primary/5 pointer-events-none absolute -end-6 -top-6 size-40"
      />

      <div className="relative">
        <span className="bg-primary/10 text-primary-hover inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold">
          <Sparkles aria-hidden className="size-3.5" />
          {t("home.aiPlanner.badge")}
        </span>
        <h2 className="font-display text-foreground mt-4 text-2xl sm:text-3xl">
          {t("home.aiPlanner.title")}
        </h2>
        <p className="text-muted-foreground mt-1.5 text-sm sm:text-base">
          {t("home.aiPlanner.sub")}
        </p>

        <form
          onSubmit={submit}
          className="border-border bg-card mt-5 rounded-2xl border p-4 shadow-[0_8px_24px_rgba(28,54,65,.08)]"
        >
          <div className="flex items-start gap-3">
            <TextSearch aria-hidden className="text-primary mt-0.5 size-5 shrink-0" />
            <textarea
              value={prompt}
              onChange={(e) => {
                setPrompt(e.target.value);
                setSubmitted(false);
              }}
              rows={3}
              placeholder={t("home.aiPlanner.placeholder")}
              aria-label={t("home.aiPlanner.title")}
              className="text-foreground placeholder:text-foreground/40 min-h-20 w-full resize-none bg-transparent text-sm focus:outline-none sm:text-base"
            />
          </div>
          <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
            <span className="text-muted-foreground inline-flex items-center gap-2 text-xs font-medium">
              <span aria-hidden className="bg-gold size-2 rounded-full" />
              {t("home.aiPlanner.status")}
            </span>
            <button
              type="submit"
              className="bg-primary text-primary-foreground hover:bg-primary-hover focus-visible:ring-primary inline-flex items-center gap-2 rounded-full px-5 py-2.5 text-sm font-semibold transition-colors focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:outline-none"
            >
              <Sparkles aria-hidden className="size-4" />
              {t("home.aiPlanner.generate")}
            </button>
          </div>
          {submitted && (
            <p role="status" className="text-muted-foreground mt-3 text-sm">
              {t("home.aiPlanner.soon")}
            </p>
          )}
        </form>

        <p className="text-muted-foreground mt-5 text-xs font-medium">
          {t("home.aiPlanner.inspirations")}
        </p>
        <div className="mt-2 flex flex-wrap gap-2">
          {INSPIRATIONS.map(({ key, icon: Icon }) => (
            <button
              key={key}
              type="button"
              onClick={() => inspire(t(`home.aiPlanner.chips.${key}`))}
              className="border-border bg-card hover:border-primary hover:text-primary focus-visible:ring-primary inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-semibold transition-colors focus-visible:ring-2 focus-visible:outline-none"
            >
              <Icon aria-hidden className="text-primary size-3.5" />
              {t(`home.aiPlanner.chips.${key}`)}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
