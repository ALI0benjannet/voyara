import type { Metadata } from "next";
import { Plane } from "lucide-react";

import { ComingSoon } from "@/components/layout/ComingSoon";

export const metadata: Metadata = {
  title: "Vols",
  alternates: { canonical: "/flights" },
};

export default function FlightsPage() {
  return <ComingSoon icon={Plane} titleKey="nav.flights" subKey="comingSoon.flights" />;
}
