import type { ReactNode } from "react";
import { AlertTriangle, CheckCircle2, Info } from "lucide-react";
import { cn } from "@voyara/ui/lib/utils";

const styles = {
  error: "border-red-200 bg-red-50 text-red-700",
  success: "border-emerald-200 bg-emerald-50 text-emerald-700",
  info: "border-border bg-muted/50 text-foreground/85",
} as const;

const icons = { error: AlertTriangle, success: CheckCircle2, info: Info };

export function Alert({
  tone = "error",
  children,
}: {
  tone?: keyof typeof styles;
  children: ReactNode;
}) {
  const Icon = icons[tone];
  return (
    <div
      role="alert"
      className={cn("flex items-start gap-3 rounded-2xl border px-4 py-3 text-sm", styles[tone])}
    >
      <Icon aria-hidden className="mt-0.5 size-4 shrink-0" />
      <span>{children}</span>
    </div>
  );
}
