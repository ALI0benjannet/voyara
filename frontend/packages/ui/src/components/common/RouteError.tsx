import { isRouteErrorResponse, useRouteError } from "react-router-dom";

export function RouteError() {
  const error = useRouteError();

  if (isRouteErrorResponse(error)) {
    return (
      <div className="p-8">
        {error.status} {error.statusText}
      </div>
    );
  }

  return <div className="p-8">Une erreur inattendue est survenue.</div>;
}
