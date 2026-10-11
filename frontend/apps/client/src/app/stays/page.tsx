import type { Metadata } from "next";
import { BedDouble } from "lucide-react";

import { ComingSoon } from "@/components/layout/ComingSoon";

export const metadata: Metadata = {
  title: "Séjours",
  alternates: { canonical: "/stays" },
};

export default function StaysPage() {
  return <ComingSoon icon={BedDouble} titleKey="nav.stays" subKey="comingSoon.stays" />;
}
