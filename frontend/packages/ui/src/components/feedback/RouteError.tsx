import { isRouteErrorResponse, useNavigate, useRouteError } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Button } from "@voyara/ui/components/ui/button";

export function RouteError() {
  const error = useRouteError();
  const navigate = useNavigate();
  const { t } = useTranslation();

  const message = isRouteErrorResponse(error)
    ? t(`errors.http.${error.status}`, { defaultValue: error.statusText })
    : t("errors.unknown");

  const handleBack = () => {
    if (window.history.length > 1) {
      navigate(-1);
    } else {
      navigate("/", { replace: true });
    }
  };

  return (
    <div className="mx-auto flex min-h-[60dvh] max-w-md flex-col items-center justify-center gap-4 px-4 text-center">
      <h1 className="text-2xl font-semibold">Oups…</h1>
      <p className="text-muted-foreground">{message}</p>
      <div className="flex gap-2">
        <Button variant="secondary" onClick={handleBack}>
          {t("actions.back")}
        </Button>
        <Button onClick={() => window.location.reload()}>{t("actions.retry")}</Button>
      </div>
    </div>
  );
}
