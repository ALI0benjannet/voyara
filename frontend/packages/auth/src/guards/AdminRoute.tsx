import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "@voyara/auth/hooks/use-auth";
import { FullPageLoader } from "@voyara/ui/components/common/FullPageLoader";

type Props = {
  /** Chemin de la page de connexion de l'app courante. */
  loginPath?: string;
  /** Chemin de la page « accès refusé » de l'app courante. */
  forbiddenPath?: string;
};

export function AdminRoute({ loginPath = "/login", forbiddenPath = "/403" }: Props) {
  const { isAuthenticated, isAdmin, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) return <FullPageLoader />;
  if (!isAuthenticated) {
    return <Navigate to={loginPath} state={{ from: location.pathname }} replace />;
  }
  if (!isAdmin) return <Navigate to={forbiddenPath} replace />;

  return <Outlet />;
}
