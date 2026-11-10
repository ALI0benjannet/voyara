"use client";

import type { ReactNode } from "react";
import { CircleHelp } from "lucide-react";

import type { ReponseComprendre } from "@/features/ai/comprendre";
import { useHydratedTranslation } from "@/features/i18n/use-hydrated-language";

const PREFIXE = "home.aiPlanner.understood";

/** Une ligne de la carte : rien n'est rendu si la valeur est vide. */
function Ligne({ libelle, children }: { libelle: string; children: ReactNode }) {
  if (children === null || children === undefined || children === "") return null;
  return (
    <div className="flex flex-wrap gap-x-2 gap-y-0.5">
      <dt className="text-muted-foreground min-w-24 font-medium">{libelle}</dt>
      <dd className="text-foreground">{children}</dd>
    </div>
  );
}

/** Carte « Ce que nous avons compris » : rendu de la réponse de `POST /api/ai/comprendre`.
 *  Composant de présentation pur (aucun appel réseau). Les champs vides ne sont pas affichés ;
 *  la question de clarification, si elle existe, est mise en évidence. */
export function AiUnderstanding({ reponse }: { reponse: ReponseComprendre }) {
  const { t, language } = useHydratedTranslation();
  const d = reponse.demande;
  const nombre = new Intl.NumberFormat(language === "ar" ? "ar-TN" : language);
  const k = (cle: string, options?: Record<string, unknown>) => t(`${PREFIXE}.${cle}`, options);

  const destination = [d.destination, ...d.autres_villes].filter(Boolean).join(", ");
  const duree = [
    d.duree_jours ? k("days", { count: d.duree_jours }) : null,
    d.nb_nuits ? k("nights", { count: d.nb_nuits }) : null,
  ]
    .filter(Boolean)
    .join(" · ");
  const budget = d.budget_illimite
    ? k("unlimited")
    : d.budget_montant
      ? `${nombre.format(Math.round(d.budget_montant))} ${d.budget_devise ?? ""}`.trim()
      : null;
  const voyageurs = [
    d.nb_voyageurs ? k("people", { count: d.nb_voyageurs }) : null,
    d.nb_adultes ? k("adults", { count: d.nb_adultes }) : null,
    d.nb_enfants ? k("children", { count: d.nb_enfants }) : null,
    d.type_voyage ? k(`types.${d.type_voyage}`) : null,
  ]
    .filter(Boolean)
    .join(" · ");
  const preferences = d.preferences.map((theme) => k(`themes.${theme}`, { defaultValue: theme })).join(", ");
  const transport = (["vol", "voiture", "transfert"] as const)
    .filter((cle) => d.besoins_transport[cle] !== "indifferent")
    .map((cle) => k(`need.${cle}_${d.besoins_transport[cle]}`))
    .join(" · ");

  return (
    <section
      aria-label={k("title")}
      className="border-border bg-background/60 mt-3 rounded-xl border p-3 text-start text-sm"
    >
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-foreground text-sm font-semibold">{k("title")}</h3>
        <span
          title={k(`method.${reponse.methode}`)}
          className="text-muted-foreground border-border rounded-full border px-2 py-0.5 text-[0.65rem] font-medium"
        >
          {k(`method.${reponse.methode}`)}
        </span>
      </div>

      {!d.hors_sujet && (
        <dl className="mt-2 space-y-1">
          <Ligne libelle={k("destination")}>{destination}</Ligne>
          <Ligne libelle={k("duration")}>{duree}</Ligne>
          <Ligne libelle={k("budget")}>{budget}</Ligne>
          <Ligne libelle={k("travellers")}>{voyageurs}</Ligne>
          <Ligne libelle={k("preferences")}>{preferences}</Ligne>
          <Ligne libelle={k("activities")}>{d.activites_souhaitees.join(", ")}</Ligne>
          <Ligne libelle={k("departure")}>{d.ville_depart}</Ligne>
          <Ligne libelle={k("transport")}>{transport}</Ligne>
        </dl>
      )}

      {reponse.question_clarification && (
        <p
          role="status"
          className="bg-gold/15 text-foreground border-gold/40 mt-3 flex items-start gap-2 rounded-lg border px-3 py-2 font-medium"
        >
          <CircleHelp aria-hidden className="text-primary mt-0.5 size-4 shrink-0" />
          <span>{reponse.question_clarification}</span>
        </p>
      )}
    </section>
  );
}
