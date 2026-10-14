import { useState } from "react";
import { useTranslation } from "react-i18next";
import { CalendarClock, Mail, MapPin, Megaphone } from "lucide-react";

import { cn } from "@voyara/ui/lib/utils";

import { ANNONCE_TYPES, usePublicAnnonces, type AnnonceType } from "@/features/prestataire/hooks";

export default function OpportunitiesPage() {
  const { t, i18n } = useTranslation();
  const { data: annonces, isLoading } = usePublicAnnonces();
  const [type, setType] = useState<AnnonceType | null>(null);

  const items = (annonces ?? []).filter((a) => !type || a.type === type);
  const chip = (active: boolean) =>
    cn(
      "rounded-full border px-4 py-1.5 text-sm font-medium transition-colors",
      active ? "border-primary bg-primary text-white" : "border-border hover:border-primary",
    );

  return (
    <main className="mx-auto max-w-7xl px-4 py-10 sm:px-8">
      <h1 className="font-display mb-2 text-4xl">{t("nav.opportunities")}</h1>
      <p className="text-muted-foreground mb-6">{t("opportunities.subtitle")}</p>

      <div className="mb-8 flex flex-wrap gap-2">
        <button type="button" className={chip(type === null)} onClick={() => setType(null)}>
          {t("opportunities.all")}
        </button>
        {ANNONCE_TYPES.map((value) => (
          <button
            key={value}
            type="button"
            className={chip(type === value)}
            onClick={() => setType(value)}
          >
            {t(`provider.types.${value}`)}
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="grid gap-5 md:grid-cols-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="bg-muted h-48 animate-pulse rounded-2xl" />
          ))}
        </div>
      ) : items.length === 0 ? (
        <div className="border-input bg-card rounded-2xl border border-dashed px-5 py-20 text-center">
          <Megaphone className="text-primary/35 mx-auto mb-3 size-10" />
          <div className="text-muted-foreground">{t("opportunities.empty")}</div>
        </div>
      ) : (
        <div className="grid gap-5 md:grid-cols-2">
          {items.map((annonce) => (
            <article key={annonce.id} className="border-border bg-card rounded-2xl border p-6">
              <span className="bg-primary/10 text-primary mb-3 inline-block rounded-full px-3 py-1 text-xs font-semibold">
                {t(`provider.types.${annonce.type}`)}
              </span>
              <h2 className="mb-2 text-lg font-semibold">{annonce.titre}</h2>
              <p className="text-foreground/80 mb-4 text-sm whitespace-pre-line">
                {annonce.description}
              </p>
              <div className="text-muted-foreground flex flex-wrap gap-x-5 gap-y-2 text-sm">
                {annonce.localisation && (
                  <span className="flex items-center gap-1.5">
                    <MapPin className="size-4" /> {annonce.localisation}
                  </span>
                )}
                {annonce.date_limite && (
                  <span className="flex items-center gap-1.5">
                    <CalendarClock className="size-4" />
                    {t("opportunities.until")}{" "}
                    {new Date(annonce.date_limite).toLocaleDateString(i18n.language)}
                  </span>
                )}
                <span className="flex items-center gap-1.5">
                  <Mail className="size-4" /> {annonce.contact}
                </span>
              </div>
            </article>
          ))}
        </div>
      )}
    </main>
  );
}
