import { useEffect, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { useLocation, useNavigate } from "react-router-dom";

import { AuthCard } from "@voyara/ui/components/auth/AuthCards";
import { TextField } from "@voyara/ui/components/form/TextField";
import { Button } from "@voyara/ui/components/ui/button";
import { Alert } from "@voyara/ui/components/ui/alert";
import { useAuth } from "@voyara/auth/hooks/use-auth";
import { getAuthErrorCode } from "@voyara/api/api-error";
import { env } from "@voyara/api/env";

/** Code d'erreur renvoyé par l'API -> clé i18n (résolue au rendu). */
const ERROR_KEYS: Record<string, string> = {
  invalid_credentials: "admin.login.errBadCredentials",
  email_not_verified: "admin.login.errUnverified",
  account_disabled: "admin.login.errDisabled",
  rate_limited: "admin.login.errRateLimited",
};

export default function LoginPage() {
  const { t } = useTranslation();
  const { login, isAuthenticated, isAdmin } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // Déjà connecté ? (session partagée en prod : même domaine)
  useEffect(() => {
    if (isAuthenticated && isAdmin) {
      const from = (location.state as { from?: string } | null)?.from;
      navigate(from ?? "/dashboard", { replace: true });
    }
    // connecté mais pas admin → il peut se reconnecter avec un autre compte
  }, [isAuthenticated, isAdmin, location.state, navigate]);

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const user = await login({ email, password });
      if (user.role !== "admin") {
        setError(t("admin.login.errNotAdmin"));
        return;
      }
      const from = (location.state as { from?: string } | null)?.from;
      navigate(from ?? "/dashboard", { replace: true });
    } catch (err) {
      const code = getAuthErrorCode(err);
      setError(ERROR_KEYS[code] ? t(ERROR_KEYS[code]!) : t("admin.login.errGeneric"));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AuthCard
      icon={
        <span className="bg-card flex size-9 items-center justify-center rounded-lg p-1">
          <img src="/admin/logo.png" alt="" className="size-full object-contain" />
        </span>
      }
      title={t("admin.login.title")}
      subtitle={t("admin.login.subtitle")}
      footer={
        <a
          href={env.VITE_CLIENT_URL}
          className="text-muted-foreground underline-offset-4 hover:underline"
        >
          ← Retour au site
        </a>
      }
    >
      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        {error && <Alert tone="error">{error}</Alert>}

        <TextField
          label={t("admin.login.email")}
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(event) => setEmail(event.target.value)}
        />
        <TextField
          label={t("admin.login.password")}
          type="password"
          autoComplete="current-password"
          required
          value={password}
          onChange={(event) => setPassword(event.target.value)}
        />

        <Button type="submit" fullWidth loading={submitting}>
          {t("admin.login.submit")}
        </Button>
      </form>
    </AuthCard>
  );
}
