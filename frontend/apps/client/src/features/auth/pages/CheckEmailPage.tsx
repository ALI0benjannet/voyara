import { MailCheck } from "lucide-react";
import { useTranslation } from "react-i18next";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { AuthCard } from "@voyara/ui/components/auth/AuthCards";
import { Button } from "@voyara/ui/components/ui/button";
import { useResendCooldown } from "@/features/auth/hooks/useResendCooldown";
import { paths } from "@/routes/paths";

export default function CheckEmailPage() {
  const { t } = useTranslation();
  const router = useRouter();
  const searchParams = useSearchParams();
  const { secondsLeft, canResend, start } = useResendCooldown();

  const email = searchParams?.get("email") ?? "";

  const handleGoToVerify = () => {
    if (!email) return;
    router.push(`${paths.resetPassword}?email=${encodeURIComponent(email)}`);
  };

  return (
    <AuthCard
      icon={<MailCheck aria-hidden className="size-5" />}
      title={t("auth.checkEmail.title")}
      subtitle={t("auth.checkEmail.description", {
        email: email || t("auth.checkEmail.fallback_email"),
      })}
      footer={
        <Link
          href={paths.login}
          className="text-foreground decoration-input hover:decoration-primary font-medium underline underline-offset-4 transition"
        >
          {t("auth.checkEmail.back_to_login")}
        </Link>
      }
    >
      <div className="space-y-3">
        {email && (
          <Button fullWidth size="lg" onClick={handleGoToVerify}>
            {t("auth.checkEmail.open_verification", "Saisir le code reçu")}
          </Button>
        )}

        <Button fullWidth size="lg" variant="outline" disabled={!canResend} onClick={start}>
          {canResend
            ? t("auth.checkEmail.resend")
            : t("auth.checkEmail.resend_wait", { seconds: secondsLeft })}
        </Button>
      </div>
    </AuthCard>
  );
}
