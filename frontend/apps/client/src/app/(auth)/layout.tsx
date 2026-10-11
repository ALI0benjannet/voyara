"use client";

import { Suspense } from "react";
import Link from "next/link";
import { useTranslation } from "react-i18next";

import { GuestOnly } from "@/components/auth/RequireAuth";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  const { t } = useTranslation();

  return (
    <GuestOnly>
      <div className="mx-auto flex min-h-[calc(100dvh-4rem)] w-full max-w-md flex-col justify-center px-4 py-12">
        <div className="mb-8 flex flex-col items-center gap-2 text-center">
          <Link href="/" className="flex items-center gap-2 font-semibold">
            <img src="/logo.png" alt="" className="size-9 object-contain" />
            <span className="font-display text-xl">{t("app.name")}</span>
          </Link>
          <p className="text-muted-foreground text-sm">{t("app.tagline")}</p>
        </div>
        <div className="bg-card rounded-lg border p-6 shadow-sm sm:p-8">
          <Suspense fallback={null}>{children}</Suspense>
        </div>
      </div>
    </GuestOnly>
  );
}
