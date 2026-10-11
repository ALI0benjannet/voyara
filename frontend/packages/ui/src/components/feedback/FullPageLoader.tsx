import { Loader2 } from "lucide-react";
import { useTranslation } from "react-i18next";

export function FullPageLoader() {
  const { t } = useTranslation();
  return (
    <div
      className="flex min-h-[60dvh] items-center justify-center"
      role="status"
      aria-live="polite"
    >
      <Loader2 className="text-primary size-8 animate-spin" />
      <span className="sr-only">{t("states.loading")}</span>
    </div>
  );
}
