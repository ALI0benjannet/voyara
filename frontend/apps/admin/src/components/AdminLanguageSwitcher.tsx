import { useTranslation } from "react-i18next";

import { SUPPORTED_LANGUAGES } from "@voyara/i18n";
import { cn } from "@voyara/ui/lib/utils";

/** Sélecteur de langue de l'admin — même comportement que côté client :
 *  i18next mémorise le choix (localStorage) et bascule `<html dir>` en RTL
 *  pour l'arabe. */
export function AdminLanguageSwitcher() {
  const { i18n } = useTranslation();
  const current = i18n.resolvedLanguage ?? "fr";

  return (
    <div className="mb-2 flex overflow-hidden rounded-md border">
      {SUPPORTED_LANGUAGES.map((lang) => (
        <button
          key={lang}
          type="button"
          onClick={() => void i18n.changeLanguage(lang)}
          aria-pressed={current === lang}
          className={cn(
            "flex-1 px-2 py-1.5 text-xs font-semibold uppercase transition-colors",
            current === lang
              ? "bg-primary text-primary-foreground"
              : "text-muted-foreground hover:bg-muted hover:text-foreground",
          )}
        >
          {lang}
        </button>
      ))}
    </div>
  );
}
