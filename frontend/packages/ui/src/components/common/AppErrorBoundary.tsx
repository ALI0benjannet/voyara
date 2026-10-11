import { ErrorBoundary, type FallbackProps } from "react-error-boundary";
import { Button } from "@voyara/ui/components/ui/button";

function Fallback({ error, resetErrorBoundary }: FallbackProps) {
  return (
    <div className="flex min-h-dvh flex-col items-center justify-center gap-4 p-6 text-center">
      <h1 className="font-display text-2xl font-bold">Oups, une erreur est survenue</h1>
      <p className="text-muted-foreground max-w-md text-sm">
        {error instanceof Error ? error.message : "Une erreur inattendue est survenue."}
      </p>
      <Button onClick={resetErrorBoundary}>Réessayer</Button>
    </div>
  );
}

export const AppErrorBoundary = ({ children }: { children: React.ReactNode }) => (
  <ErrorBoundary
    FallbackComponent={Fallback}
    onError={(e, info) => console.error("[AppError]", e, info)} // → Sentry plus tard
  >
    {children}
  </ErrorBoundary>
);
