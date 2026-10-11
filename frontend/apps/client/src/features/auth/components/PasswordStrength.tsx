import { Check, X } from "lucide-react";
import { useMemo } from "react";
import { useTranslation } from "react-i18next";

type PasswordStrengthProps = {
  password: string;
};

export function PasswordStrength({ password }: PasswordStrengthProps) {
  const { t } = useTranslation();

  const criteria = useMemo(() => {
    const checks = [
      { label: t("auth.password_strength.length"), passed: password.length >= 8 },
      { label: t("auth.password_strength.lower"), passed: /[a-z]/.test(password) },
      { label: t("auth.password_strength.upper"), passed: /[A-Z]/.test(password) },
      { label: t("auth.password_strength.digit"), passed: /[0-9]/.test(password) },
      { label: t("auth.password_strength.special"), passed: /[^A-Za-z0-9]/.test(password) },
    ];

    const score = checks.filter((criterion) => criterion.passed).length;
    const levelKey = score <= 1 ? "weak" : score <= 3 ? "fair" : score <= 4 ? "good" : "strong";

    return { checks, score, levelKey };
  }, [password, t]);

  if (!password) {
    return null;
  }

  const segments = [0, 1, 2, 3, 4];

  return (
    <div className="space-y-3" aria-live="polite">
      <div className="flex gap-1" aria-hidden="true">
        {segments.map((segment) => {
          const isActive = segment < criteria.score;
          const tone = isActive
            ? criteria.score <= 1
              ? "bg-red-500"
              : criteria.score <= 3
                ? "bg-gold"
                : criteria.score <= 4
                  ? "bg-primary"
                  : "bg-green-600"
            : "bg-input";

          return <div key={segment} className={`h-2 flex-1 rounded-full ${tone}`} />;
        })}
      </div>
      <p className="text-muted-foreground text-sm">
        {t(`auth.password_strength.${criteria.levelKey}`)}
      </p>
      <ul className="text-muted-foreground space-y-2 text-sm">
        {criteria.checks.map((criterion) => (
          <li key={criterion.label} className="flex items-center gap-2">
            {criterion.passed ? (
              <Check aria-hidden="true" className="text-primary size-4" />
            ) : (
              <X aria-hidden="true" className="text-foreground/45 size-4" />
            )}
            <span>{criterion.label}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
