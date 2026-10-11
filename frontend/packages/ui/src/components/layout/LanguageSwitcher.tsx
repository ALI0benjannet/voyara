import { Globe, Check } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Button } from "@voyara/ui/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@voyara/ui/components/ui/dropdown-menu";
import { SUPPORTED_LANGUAGES, type Language } from "@voyara/i18n";

const LABELS: Record<Language, string> = { fr: "Français", en: "English", ar: "العربية" };

export function LanguageSwitcher() {
  const { i18n, t } = useTranslation();
  const current = (i18n.resolvedLanguage ?? "fr") as Language;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="sm" aria-label={t("language.label")}>
          <Globe className="size-4" />
          <span className="ms-2 hidden sm:inline">{LABELS[current]}</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        {SUPPORTED_LANGUAGES.map((lng) => (
          <DropdownMenuItem
            key={lng}
            onSelect={() => i18n.changeLanguage(lng)}
            className="justify-between gap-6"
          >
            {LABELS[lng]}
            {current === lng && <Check className="size-4" />}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
