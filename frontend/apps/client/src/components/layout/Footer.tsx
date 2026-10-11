"use client";

import Link from "next/link";

import { env } from "@voyara/api/env";

import { paths } from "@/routes/paths";
import { useHydratedTranslation } from "@/features/i18n/use-hydrated-language";

export function Footer() {
  const { t } = useHydratedTranslation();

  return (
    <footer className="bg-ink text-ink-foreground mt-auto">
      <div className="mx-auto grid max-w-7xl gap-10 px-4 py-12 sm:px-8 md:grid-cols-3">
        <div>
          <div className="font-display text-background mb-2.5 text-2xl">Voyara</div>
          <p className="text-ink-foreground/70 max-w-xs text-sm leading-relaxed">
            {t("app.tagline")}
          </p>
        </div>
        <div>
          <div className="text-gold mb-3.5 text-[13px] font-bold tracking-widest uppercase">
            {t("footer.discover")}
          </div>
          <div className="flex flex-col gap-2 text-sm">
            <Link href={paths.activities} className="text-ink-foreground/80 hover:text-gold">
              {t("nav.activities")}
            </Link>
            <Link href={paths.favorites} className="text-ink-foreground/80 hover:text-gold">
              {t("nav.favorites")}
            </Link>
            <Link href={paths.bookings} className="text-ink-foreground/80 hover:text-gold">
              {t("nav.bookings")}
            </Link>
          </div>
        </div>
        <div>
          <div className="text-gold mb-3.5 text-[13px] font-bold tracking-widest uppercase">
            {t("footer.help")}
          </div>
          <div className="flex flex-col gap-2 text-sm">
            <a href="#" className="text-ink-foreground/80 hover:text-gold">
              Contact
            </a>
            <a href="#" className="text-ink-foreground/80 hover:text-gold">
              FAQ
            </a>
            <Link href="/privacy" className="text-ink-foreground/80 hover:text-gold">
              {t("footer.privacy", "Confidentialité")}
            </Link>
            <Link href="/credits" className="text-ink-foreground/80 hover:text-gold">
              {t("footer.credits", "Crédits photo")}
            </Link>
            <a href={env.VITE_ADMIN_URL} className="text-ink-foreground/80 hover:text-gold">
              {t("footer.admin")}
            </a>
          </div>
        </div>
      </div>
      <div className="border-ink-foreground/15 border-t">
        <div className="text-ink-foreground/50 mx-auto max-w-7xl px-4 py-4 text-[13px] sm:px-8">
          © {new Date().getFullYear()} Voyara
        </div>
      </div>
    </footer>
  );
}
