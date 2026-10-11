import type { ReactNode } from "react";
import { QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { Toaster } from "sonner";
import { queryClient } from "@voyara/api/query-client";
import { AuthProvider } from "@voyara/auth/context/AuthProvider";

export function Providers({ children }: { children: ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      {/* Session expirée → page de login de CETTE app (servie sous /admin) */}
      <AuthProvider loginUrl="/admin/login">
        {children}
        <Toaster position="top-center" richColors closeButton />
      </AuthProvider>
      {import.meta.env.DEV && <ReactQueryDevtools initialIsOpen={false} />}
    </QueryClientProvider>
  );
}
