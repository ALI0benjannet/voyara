import type { Metadata } from "next";

import { DlTest } from "@/components/dl-test/DlTest";

/** Page TEMPORAIRE de démonstration de la validation Deep Learning (Ons : recherche,
 *  Boutheina : classification), sans LLM. À retirer avec le bouton « DL test » de l'en-tête. */
export const metadata: Metadata = {
  title: "DL test",
  robots: { index: false, follow: false },
};

export default function DlTestPage() {
  return <DlTest />;
}
