import { useCallback, useState } from "react";
import { useTranslation } from "react-i18next";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter, useSearchParams } from "next/navigation";
import { ShieldCheck } from "lucide-react";
import { toast } from "sonner";
import { AuthCard } from "@voyara/ui/components/auth/AuthCards";
import { Button } from "@voyara/ui/components/ui/button";
import { TextField } from "@voyara/ui/components/form/TextField";
import { authApi } from "@voyara/auth/api/auth.api";
import { verifyEmailSchema, type VerifyEmailInput } from "@/features/auth/schemas/authSchemas";
import { getAuthErrorCode } from "@voyara/api/api-error";
import { toApiError } from "@voyara/api/errors";
import { paths } from "@/routes/paths";

export default function VerifyEmailPage() {
  const { t } = useTranslation();
  const router = useRouter();
  const searchParams = useSearchParams();
  const emailParam = searchParams?.get("email") ?? "";
  const [isResending, setIsResending] = useState(false);

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<VerifyEmailInput>({
    resolver: zodResolver(verifyEmailSchema),
    mode: "onTouched",
    defaultValues: { email: emailParam, token: "" },
  });

  const onResend = useCallback(async () => {
    if (!emailParam) {
      toast.error(t("auth.verifyEmail.no_email", "Impossible de renvoyer le code sans e-mail."));
      return;
    }
    setIsResending(true);
    try {
      await authApi.resendVerification({ email: emailParam });
      toast.success(t("auth.verifyEmail.resend_success", "Un nouveau code a été envoyé."));
    } catch {
      toast.error(
        t("auth.verifyEmail.resend_error", "Impossible de renvoyer le code pour le moment."),
      );
    } finally {
      setIsResending(false);
    }
  }, [emailParam, t]);

  const onSubmit = async (data: VerifyEmailInput) => {
    try {
      await authApi.verifyEmail({ email: data.email, token: data.token });
      toast.success(t("auth.verifyEmail.success", { defaultValue: "Vérification réussie !" }));
      router.push(paths.login);
    } catch (error: unknown) {
      const apiError = toApiError(error);
      const code = getAuthErrorCode(error);

      if (apiError.status === 404) {
        setError("email", { type: "server", message: "auth.errors.email_not_found" });
        return;
      }
      if (code === "invalid_token") {
        setError("token", { type: "server", message: "auth.verifyEmail.invalid" });
        return;
      }
      if (apiError.fieldErrors) {
        for (const [field, message] of Object.entries(apiError.fieldErrors)) {
          setError(field as keyof VerifyEmailInput, { type: "server", message });
        }
        return;
      }
      toast.error(t(apiError.message, { defaultValue: t("errors.unexpected") }));
    }
  };

  return (
    <AuthCard
      icon={<ShieldCheck aria-hidden className="size-5" />}
      title={t("auth.verifyEmail.title", "Vérification de l’e-mail")}
      subtitle={t(
        "auth.verifyEmail.subtitle",
        "Saisissez votre e-mail et le code à 4 chiffres reçu par e-mail.",
      )}
    >
      <form
        noValidate
        onSubmit={handleSubmit(onSubmit)}
        aria-busy={isSubmitting}
        className="space-y-5"
      >
        <fieldset disabled={isSubmitting} className="space-y-5 border-0 p-0">
          <TextField
            {...register("email")}
            type="email"
            inputMode="email"
            autoComplete="email"
            label={t("auth.verifyEmail.email", "Adresse e-mail")}
            error={
              errors.email?.message
                ? t(errors.email.message, { defaultValue: errors.email.message })
                : undefined
            }
          />
          <TextField
            {...register("token")}
            type="text"
            inputMode="numeric"
            maxLength={4}
            autoComplete="one-time-code"
            label={t("auth.verifyEmail.code", "Code de vérification")}
            hint={t("auth.verifyEmail.code_hint", "4 chiffres reçus par e-mail")}
            className="text-center text-lg tracking-[0.5em]"
            error={
              errors.token?.message
                ? t(errors.token.message, { defaultValue: errors.token.message })
                : undefined
            }
          />
        </fieldset>

        <div className="space-y-3">
          <Button type="submit" fullWidth size="lg" loading={isSubmitting}>
            {isSubmitting
              ? t("auth.verifyEmail.submitting", "Vérification…")
              : t("auth.verifyEmail.confirm", "Confirmer")}
          </Button>

          <Button variant="outline" fullWidth size="lg" loading={isResending} onClick={onResend}>
            {isResending
              ? t("auth.verifyEmail.resending", "Envoi en cours…")
              : t("auth.verifyEmail.resend", "Renvoyer le code")}
          </Button>
        </div>
      </form>
    </AuthCard>
  );
}
