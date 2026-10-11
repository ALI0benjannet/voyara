import { useCallback, useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslation } from "react-i18next";
import { useRouter, useSearchParams } from "next/navigation";
import { KeyRound, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { AuthCard } from "@voyara/ui/components/auth/AuthCards";
import { Alert } from "@voyara/ui/components/ui/alert";
import { Button } from "@voyara/ui/components/ui/button";
import { TextField } from "@voyara/ui/components/form/TextField";
import { PasswordStrength } from "@/features/auth/components/PasswordStrength";
import { useResetPasswordForm } from "@/features/auth/hooks/useResetPasswordForm";
import { verifyCodeSchema, type VerifyCodeInput } from "@/features/auth/schemas/authSchemas";
import { authApi } from "@voyara/auth/api/auth.api";
import { paths } from "@/routes/paths";

type TokenState = "idle" | "checking" | "valid" | "invalid";

export default function ResetPasswordPage() {
  const { t } = useTranslation();
  const router = useRouter();
  const searchParams = useSearchParams();

  const token = searchParams?.get("token") ?? "";
  const email = searchParams?.get("email") ?? "";

  const [tokenState, setTokenState] = useState<TokenState>("idle");
  const [tokenError, setTokenError] = useState<string | null>(null);
  const [isResending, setIsResending] = useState(false);

  const { form, onSubmit, password } = useResetPasswordForm();
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = form;

  const codeForm = useForm<VerifyCodeInput>({
    resolver: zodResolver(verifyCodeSchema),
    mode: "onTouched",
    defaultValues: { code: "" },
  });
  const {
    register: registerCode,
    handleSubmit: handleSubmitCode,
    formState: { errors: codeErrors, isSubmitting: isCodeSubmitting },
  } = codeForm;

  const onSubmitCode = useCallback(
    (data: VerifyCodeInput) => {
      const next = new URLSearchParams();
      next.set("token", data.code);
      if (email) next.set("email", email);
      router.push(`${paths.resetPassword}?${next.toString()}`);
    },
    [router, email],
  );

  useEffect(() => {
    if (!token) {
      setTokenState("invalid");
      setTokenError(null);
      return;
    }

    let cancelled = false;
    setTokenState("checking");
    setTokenError(null);

    authApi
      .validateResetToken(token)
      .then(() => {
        if (!cancelled) setTokenState("valid");
      })
      .catch(() => {
        if (cancelled) return;
        setTokenState("invalid");
        setTokenError(t("auth.resetPassword.invalid_token", "Code invalide ou expiré."));
      });

    return () => {
      cancelled = true;
    };
  }, [token, t]);

  const onResend = useCallback(async () => {
    if (!email) {
      toast.error(
        t("auth.resetPassword.no_email", "Impossible de renvoyer le code sans adresse e-mail."),
      );
      return;
    }
    setIsResending(true);
    try {
      await authApi.forgotPassword({ email });
      toast.success(t("auth.resetPassword.resent", "Un nouveau code a été envoyé."));
    } catch {
      toast.error(
        t("auth.resetPassword.resend_error", "Impossible de renvoyer le code pour le moment."),
      );
    } finally {
      setIsResending(false);
    }
  }, [email, t]);

  return (
    <AuthCard
      icon={<KeyRound aria-hidden className="size-5" />}
      title={t("auth.resetPassword.title")}
      subtitle={t("auth.resetPassword.subtitle")}
    >
      {/* Étape 1 : saisie du code */}
      {tokenState === "invalid" || !token ? (
        <form
          noValidate
          onSubmit={handleSubmitCode(onSubmitCode)}
          aria-busy={isCodeSubmitting}
          className="space-y-5"
        >
          <h2 className="text-foreground text-base font-semibold">
            {t("auth.resetPassword.code_step", "Entrer le code de réinitialisation")}
          </h2>

          {tokenError && <Alert>{tokenError}</Alert>}

          <fieldset disabled={isCodeSubmitting} className="space-y-5 border-0 p-0">
            <TextField
              {...registerCode("code")}
              type="text"
              inputMode="numeric"
              maxLength={4}
              autoComplete="one-time-code"
              className="text-center text-lg tracking-[0.5em]"
              label={t("auth.resetPassword.code_label", "Code de réinitialisation")}
              error={codeErrors.code?.message ? t(codeErrors.code.message) : undefined}
            />
          </fieldset>

          <div className="space-y-3">
            <Button type="submit" fullWidth size="lg" loading={isCodeSubmitting}>
              {t("auth.resetPassword.verify_code", "Valider le code")}
            </Button>
            <Button
              variant="outline"
              fullWidth
              size="lg"
              disabled={!email}
              loading={isResending}
              onClick={onResend}
            >
              {t("auth.resetPassword.resend_code", "Renvoyer le code par e-mail")}
            </Button>
          </div>
        </form>
      ) : tokenState === "checking" ? (
        /* Étape intermédiaire : vérification */
        <div className="border-border bg-muted/50/70 text-muted-foreground flex flex-col items-center gap-3 rounded-2xl border p-10">
          <Loader2 aria-hidden className="size-5 animate-spin" />
          <p className="text-sm">{t("auth.resetPassword.validating", "Vérification du code…")}</p>
        </div>
      ) : (
        /* Étape 2 : nouveau mot de passe */
        <form
          noValidate
          onSubmit={handleSubmit(onSubmit)}
          aria-busy={isSubmitting}
          className="space-y-5"
        >
          <h2 className="text-foreground text-base font-semibold">
            {t("auth.resetPassword.new_password_step", "Créer un nouveau mot de passe")}
          </h2>

          {errors.root?.serverError?.message && <Alert>{t(errors.root.serverError.message)}</Alert>}

          <fieldset disabled={isSubmitting} className="space-y-5 border-0 p-0">
            <TextField
              {...register("new_password")}
              type="password"
              autoComplete="new-password"
              label={t("auth.resetPassword.new_password")}
              error={errors.new_password?.message ? t(errors.new_password.message) : undefined}
            />
            <PasswordStrength password={password} />
            <TextField
              {...register("confirm_password")}
              type="password"
              autoComplete="new-password"
              label={t("auth.resetPassword.confirm_password")}
              error={
                errors.confirm_password?.message ? t(errors.confirm_password.message) : undefined
              }
            />
          </fieldset>

          <Button type="submit" fullWidth size="lg" loading={isSubmitting}>
            {isSubmitting ? t("auth.resetPassword.submitting") : t("auth.resetPassword.submit")}
          </Button>
        </form>
      )}
    </AuthCard>
  );
}
