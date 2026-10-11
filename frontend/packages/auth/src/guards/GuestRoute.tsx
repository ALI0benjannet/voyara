import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "@voyara/auth/hooks/use-auth";

type Props = {
  /** Destination quand un utilisateur déjà connecté visite une page invité. */
  authenticatedRedirect?: string;
  /** Destination spécifique aux admins (URL absolue possible : app admin séparée). */
  adminRedirect?: string;
};

export function GuestRoute({ authenticatedRedirect = "/", adminRedirect }: Props) {
  const { isAuthenticated, isAdmin } = useAuth();

  if (isAuthenticated) {
    if (isAdmin && adminRedirect) {
      // L'admin vit dans un micro-frontend séparé → navigation pleine page
      window.location.assign(adminRedirect);
      return null;
    }
    return <Navigate to={authenticatedRedirect} replace />;
  }
  return <Outlet />;
}
