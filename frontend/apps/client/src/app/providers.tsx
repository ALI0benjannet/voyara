"use client";

import type { ReactNode } from "react";
import { QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "sonner";

import "@voyara/i18n"; // initialise i18next (fr par défaut côté serveur)
import { queryClient } from "@voyara/api/query-client";
import { AuthProvider } from "@voyara/auth/context/AuthProvider";

export function Providers({ children }: { children: ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider loginUrl="/login">
        {children}
        <Toaster position="top-center" richColors closeButton />
      </AuthProvider>
    </QueryClientProvider>
  );
}
