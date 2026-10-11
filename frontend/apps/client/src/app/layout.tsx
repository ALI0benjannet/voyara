import { Suspense } from "react";
import type { Metadata } from "next";
import { Albert_Sans, Marcellus } from "next/font/google";

import { Navbar } from "@/components/layout/Navbar";
import { Footer } from "@/components/layout/Footer";
import { Providers } from "./providers";
import { SITE_URL } from "@/lib/site";

import "./globals.css";

const albertSans = Albert_Sans({
  subsets: ["latin"],
  variable: "--font-albert-sans",
  display: "swap",
});

const marcellus = Marcellus({
  weight: "400",
  subsets: ["latin"],
  variable: "--font-marcellus",
  display: "swap",
});

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: "Voyara — Activités et expériences en Tunisie",
    template: "%s | Voyara",
  },
  description:
    "Réservez les plus belles activités touristiques de Tunisie : mer, désert, culture, gastronomie. Annulation gratuite jusqu'à 48 h avant le départ.",
  icons: { icon: "/icon.png", apple: "/icon.png" },
  openGraph: {
    type: "website",
    siteName: "Voyara",
    locale: "fr_FR",
    images: ["/logo.png"],
  },
  alternates: { canonical: "/" },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    /* `suppressHydrationWarning` : le module i18n ajuste `lang` et `dir` sur
       <html> dès son chargement (RTL en arabe), donc avant l'hydratation. */
    <html
      lang="fr"
      className={`${albertSans.variable} ${marcellus.variable}`}
      suppressHydrationWarning
    >
      <body className="flex min-h-dvh flex-col antialiased">
        <Providers>
          <Suspense fallback={null}>
            <Navbar />
          </Suspense>
          <div className="flex-1">{children}</div>
          <Footer />
        </Providers>
      </body>
    </html>
  );
}
