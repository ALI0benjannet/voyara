"use client";

import { RequireAuth } from "@/components/auth/RequireAuth";
import ProfilePage from "@/features/auth/pages/ProfilePage";

export default function Page() {
  return (
    <RequireAuth>
      <ProfilePage />
    </RequireAuth>
  );
}
