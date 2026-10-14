"use client";

import { RequireAuth } from "@/components/auth/RequireAuth";
import ProviderSpacePage from "@/views/ProviderSpacePage";

export default function Page() {
  return (
    <RequireAuth>
      <ProviderSpacePage />
    </RequireAuth>
  );
}
