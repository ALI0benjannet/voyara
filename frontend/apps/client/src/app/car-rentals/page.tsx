import type { Metadata } from "next";
import { Car } from "lucide-react";

import { ComingSoon } from "@/components/layout/ComingSoon";

export const metadata: Metadata = {
  title: "Voitures de location",
  alternates: { canonical: "/car-rentals" },
};

export default function CarRentalsPage() {
  return <ComingSoon icon={Car} titleKey="nav.carRentals" subKey="comingSoon.carRentals" />;
}
