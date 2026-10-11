"use client";

import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Check, Globe } from "lucide-react";

import { SUPPORTED_LANGUAGES, type Language } from "@voyara/i18n";
import { cn } from "@voyara/ui/lib/utils";

import { useHydratedTranslation } from "@/features/i18n/use-hydrated-language";

/** Nom de chaque langue dans sa propre écriture — reconnaissable quelle que
 *  soit la langue actuellement affichée. */
const LANGUAGE_NAMES: Record<Language, string> = {
  fr: "Français",
  en: "English",
  ar: "العربية",
};

/** Sélecteur de langue : ouvre la liste et laisse choisir, plutôt que de
 *  basculer directement — un clic involontaire ne change plus la langue. */
export function LanguageMenu() {
  // `i18n` sert uniquement à `changeLanguage` ; tout ce qui est *rendu* (libellé
  // et attribut `title`) passe par la version figée jusqu'à l'hydratation, sinon
  // le serveur écrit « Changer de langue » et le client « Change language ».
  const { i18n } = useTranslation();
  const { t, language: resolved } = useHydratedTranslation();
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement | null>(null);

  const current = (
    SUPPORTED_LANGUAGES.includes(resolved as Language) ? resolved : "fr"
  ) as Language;

  // Referme au clic extérieur et à la touche Échap.
  useEffect(() => {
    if (!open) return;
    const onPointerDown = (event: MouseEvent) => {
      if (!containerRef.current?.contains(event.target as Node)) setOpen(false);
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  return (
    <div ref={containerRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-haspopup="menu"
        aria-expanded={open}
        title={t("nav.switchLanguage")}
        className="text-foreground/70 hover:text-primary flex flex-col items-center gap-1 transition-colors"
      >
        <Globe className="size-[22px]" strokeWidth={1.6} />
        <span className="text-xs font-medium">{current.toUpperCase()} / DT</span>
      </button>

      {open && (
        <div
          role="menu"
          className="border-border bg-card absolute end-0 top-full z-50 mt-2 min-w-44 overflow-hidden rounded-xl border py-1 shadow-lg"
        >
          {SUPPORTED_LANGUAGES.map((lang) => (
            <button
              key={lang}
              type="button"
              role="menuitemradio"
              aria-checked={current === lang}
              onClick={() => {
                void i18n.changeLanguage(lang);
                setOpen(false);
              }}
              className={cn(
                "hover:bg-muted flex w-full items-center justify-between gap-3 px-4 py-2.5 text-sm transition-colors",
                current === lang ? "text-primary font-semibold" : "text-foreground/80",
              )}
            >
              <span>{LANGUAGE_NAMES[lang]}</span>
              {current === lang && <Check className="size-4" />}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
