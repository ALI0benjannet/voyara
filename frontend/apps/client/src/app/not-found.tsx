import Link from "next/link";

export default function NotFound() {
  return (
    <main className="mx-auto flex min-h-[60dvh] max-w-md flex-col items-center justify-center gap-4 px-4 text-center">
      <h1 className="font-display text-5xl">404</h1>
      <p className="text-muted-foreground">Cette page n'existe pas ou a été déplacée.</p>
      <Link
        href="/"
        className="bg-ink text-background hover:bg-primary inline-block rounded-full px-6 py-2.5 font-semibold"
      >
        Retour à l'accueil
      </Link>
    </main>
  );
}
