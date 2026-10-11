import { ShieldAlert } from "lucide-react";
import { useTranslation } from "react-i18next";

import { Button } from "@voyara/ui/components/ui/button";
import { useAuth } from "@voyara/auth/hooks/use-auth";
import { env } from "@voyara/api/env";

export default function ForbiddenPage() {
  const { logout } = useAuth();
  const { t } = useTranslation();

  return (
    <div className="mx-auto flex min-h-dvh max-w-md flex-col items-center justify-center gap-4 px-4 text-center">
      <ShieldAlert className="text-destructive size-12" />
      <h1 className="text-2xl font-semibold">{t("admin.forbidden.title")}</h1>
      <p className="text-muted-foreground">{t("admin.forbidden.message")}</p>
      <div className="flex gap-2">
        <Button variant="secondary" onClick={() => window.location.assign(env.VITE_CLIENT_URL)}>
          {t("admin.forbidden.backSite")}
        </Button>
        <Button
          onClick={async () => {
            await logout();
            window.location.assign("/admin/login");
          }}
        >
          {t("admin.forbidden.switchAccount")}
        </Button>
      </div>
    </div>
  );
}
