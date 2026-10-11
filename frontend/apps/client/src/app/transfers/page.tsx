import type { Metadata } from "next";
import { CarTaxiFront } from "lucide-react";

import { ComingSoon } from "@/components/layout/ComingSoon";

export const metadata: Metadata = {
  title: "Transferts",
  alternates: { canonical: "/transfers" },
};

export default function TransfersPage() {
  return <ComingSoon icon={CarTaxiFront} titleKey="nav.transfers" subKey="comingSoon.transfers" />;
}
