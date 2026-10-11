import Link from "next/link";
import { useTranslation } from "react-i18next";
import { Mail } from "lucide-react";
import { AuthCard } from "@voyara/ui/components/auth/AuthCards";
import { Alert } from "@voyara/ui/components/ui/alert";
import { Button } from "@voyara/ui/components/ui/button";
import { TextField } from "@voyara/ui/components/form/TextField";
import { useForgotPasswordForm } from "@/features/auth/hooks/useForgotPasswordForm";
import { paths } from "@/routes/paths";

export default function ForgotPasswordPage() {
  const { t } = useTranslation();
  const { form, onSubmit } = useForgotPasswordForm();
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = form;

  const serverError = errors.root?.serverError?.message;

  return (
    <AuthCard
      icon={<Mail aria-hidden className="size-5" />}
      title={t("auth.forgotPassword.title")}
      subtitle={t("auth.forgotPassword.subtitle")}
      footer={
        <Link
          href={paths.login}
          className="text-foreground decoration-input hover:decoration-primary font-medium underline underline-offset-4 transition"
        >
          {t("auth.forgotPassword.back_to_login")}
        </Link>
      }
    >
      <form
        noValidate
        onSubmit={handleSubmit(onSubmit)}
        aria-busy={isSubmitting}
        className="space-y-5"
      >
        {serverError && <Alert>{t(serverError, { defaultValue: serverError })}</Alert>}

        <fieldset disabled={isSubmitting} className="space-y-5 border-0 p-0">
          <TextField
            {...register("email")}
            type="email"
            inputMode="email"
            autoComplete="email"
            autoFocus
            label={t("auth.forgotPassword.email")}
            error={errors.email?.message ? t(errors.email.message) : undefined}
          />
        </fieldset>

        <Button type="submit" fullWidth size="lg" loading={isSubmitting}>
          {isSubmitting ? t("auth.forgotPassword.submitting") : t("auth.forgotPassword.submit")}
        </Button>
      </form>
    </AuthCard>
  );
}
