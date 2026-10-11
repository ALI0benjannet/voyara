import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "@voyara/auth/hooks/use-auth";
import { FullPageLoader } from "@voyara/ui/components/common/FullPageLoader";

type Props = {
  /** Chemin de la page de connexion de l'app courante. */
  loginPath?: string;
};

export function ProtectedRoute({ loginPath = "/login" }: Props) {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) return <FullPageLoader />;
  if (!isAuthenticated) {
    return <Navigate to={loginPath} state={{ from: location.pathname }} replace />;
  }

  return <Outlet />;
}
