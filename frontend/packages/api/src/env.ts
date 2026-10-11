import { z } from "zod";

/**
 * Variables d'environnement front — compatibles Vite (admin) ET Next.js (client).
 * - Vite  : import.meta.env.VITE_*
 * - Next  : process.env.NEXT_PUBLIC_* (inlinées au build, accès littéral requis)
 */

type RawEnv = {
  VITE_API_URL?: string;
  VITE_APP_NAME?: string;
  VITE_ADMIN_URL?: string;
  VITE_CLIENT_URL?: string;
};

const viteEnv: RawEnv | undefined =
  typeof import.meta !== "undefined" && (import.meta as { env?: RawEnv }).env?.VITE_API_URL
    ? (import.meta as { env?: RawEnv }).env
    : undefined;

const raw: RawEnv = viteEnv ?? {
  VITE_API_URL: process.env.NEXT_PUBLIC_API_URL,
  VITE_APP_NAME: process.env.NEXT_PUBLIC_APP_NAME,
  VITE_ADMIN_URL: process.env.NEXT_PUBLIC_ADMIN_URL,
  VITE_CLIENT_URL: process.env.NEXT_PUBLIC_CLIENT_URL,
};

const schema = z.object({
  VITE_API_URL: z.string().min(1),
  VITE_APP_NAME: z.string().default("Voyara"),
  /** URL de l'app admin (micro-frontend séparé). En prod même domaine : "/admin". */
  VITE_ADMIN_URL: z.string().default("/admin"),
  /** URL de l'app client (pour revenir depuis l'admin). */
  VITE_CLIENT_URL: z.string().default("/"),
});

const parsed = schema.safeParse(raw);
if (!parsed.success) {
  console.error(parsed.error.flatten().fieldErrors);
  throw new Error("❌ Variables d'environnement invalides");
}

export const env = parsed.data;
