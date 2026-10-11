"use client";

import { useEffect, type ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";

import { useAuth } from "@voyara/auth/hooks/use-auth";
import { FullPageLoader } from "@voyara/ui/components/feedback/FullPageLoader";

/** Garde client : redirige vers /login?next=… si non connecté. */
export function RequireAuth({ children }: { children: ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.replace(`/login?next=${encodeURIComponent(pathname ?? "/")}`);
    }
  }, [isAuthenticated, isLoading, pathname, router]);

  if (isLoading || !isAuthenticated) return <FullPageLoader />;
  return <>{children}</>;
}

/** Garde inverse : un utilisateur connecté n'a rien à faire sur les pages d'auth. */
export function GuestOnly({ children }: { children: ReactNode }) {
  const { isAuthenticated } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (isAuthenticated) router.replace("/");
  }, [isAuthenticated, router]);

  if (isAuthenticated) return <FullPageLoader />;
  return <>{children}</>;
}
