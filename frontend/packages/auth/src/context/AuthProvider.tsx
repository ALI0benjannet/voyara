import {
  createContext,
  useCallback,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import { authApi } from "@voyara/auth/api/auth.api";
import type { LoginPayload } from "@voyara/auth/types/auth.types";
import type { User } from "@voyara/auth/types/user";
import { setSessionExpiredHandler } from "@voyara/api/axios";
import { authStore } from "@voyara/auth/stores/auth.store";
import { queryKeys } from "@voyara/api/query-keys";

type AuthContextValue = {
  user: User | null;
  isAuthenticated: boolean;
  isAdmin: boolean;
  isLoading: boolean;
  login: (payload: LoginPayload) => Promise<User>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<User | null>;
};

export const AuthContext = createContext<AuthContextValue | null>(null);

/** Normalise la réponse brute de /auth/me vers le type User du front. */
function mapMeToUser(me: Awaited<ReturnType<typeof authApi.me>>): User {
  return {
    id: me.id.toString(),
    email: me.email,
    nom: me.nom,
    prenom: me.prenom,
    full_name: `${me.prenom} ${me.nom}`.trim(),
    role: me.role,
    is_verified: me.is_active,
    preferred_language: undefined,
    avatar_url: me.avatar_url ?? null,
  };
}

type AuthProviderProps = {
  children: ReactNode;
  /** Où renvoyer l'utilisateur quand la session expire (diffère entre apps client et admin). */
  loginUrl?: string;
};

export function AuthProvider({ children, loginUrl = "/login" }: AuthProviderProps) {
  const queryClient = useQueryClient();

  // Abonnement réactif au store : re-render dès que le token change.
  const accessToken = authStore((state) => state.accessToken);

  // Le token est restauré depuis `localStorage` (zustand/persist), auquel le
  // serveur n'a pas accès : le SSR rend donc toujours l'état « déconnecté ».
  // Si le premier rendu client utilisait le token restauré, React comparerait
  // deux arbres différents (badge de favoris, menu du compte…) et invaliderait
  // la page. On attend donc l'hydratation avant de considérer l'utilisateur
  // connecté — l'écart ne dure qu'un rendu.
  const [hydrated, setHydrated] = useState(false);
  useEffect(() => setHydrated(true), []);

  const hasToken = hydrated && Boolean(accessToken);

  // Restauration de session au rechargement de la page
  const { data: user, isLoading } = useQuery<User | null>({
    queryKey: queryKeys.auth.me,
    queryFn: async () => mapMeToUser(await authApi.me()),
    enabled: hasToken,
    retry: false,
    staleTime: 5 * 60_000,
  });

  const refreshUser = useCallback(async () => {
    const refreshedUser = mapMeToUser(await authApi.me());
    queryClient.setQueryData(queryKeys.auth.me, refreshedUser);
    return refreshedUser;
  }, [queryClient]);

  const clearSession = useCallback(() => {
    authStore.getState().logout();
    queryClient.setQueryData(queryKeys.auth.me, null);
    queryClient.removeQueries({ queryKey: queryKeys.auth.me });
  }, [queryClient]);

  // Le refresh a échoué → l'intercepteur axios nous prévient
  useEffect(() => {
    setSessionExpiredHandler(() => {
      clearSession();
      window.location.assign(`${loginUrl}?reason=session_expired`);
    });
    return () => setSessionExpiredHandler(() => {});
  }, [clearSession, loginUrl]);

  const login = useCallback(
    async (payload: LoginPayload) => {
      const { access_token, refresh_token } = await authApi.login(payload);

      // 1. Les tokens AVANT tout appel authentifié
      authStore.getState().setTokens(access_token, refresh_token ?? null);

      // 2. Puis on récupère le profil
      const userResult = mapMeToUser(await authApi.me());
      queryClient.setQueryData(queryKeys.auth.me, userResult);
      return userResult;
    },
    [queryClient],
  );

  const logout = useCallback(async () => {
    try {
      const refreshToken = authStore.getState().refreshToken;
      await authApi.logout(refreshToken ?? undefined);
    } catch {
      // On ignore l'échec réseau : la session locale doit partir quoi qu'il arrive.
    } finally {
      clearSession();
      queryClient.clear();
    }
  }, [clearSession, queryClient]);

  const value = useMemo<AuthContextValue>(
    () => ({
      user: user ?? null,
      isAuthenticated: hasToken && Boolean(user),
      isAdmin: user?.role === "admin",
      isLoading: hasToken && isLoading,
      login,
      logout,
      refreshUser,
    }),
    [user, hasToken, isLoading, login, logout, refreshUser],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
