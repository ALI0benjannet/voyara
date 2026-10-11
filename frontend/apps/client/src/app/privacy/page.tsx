import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Politique de confidentialité",
  description:
    "Quelles données Voyara collecte, pourquoi, combien de temps, et comment exercer vos droits (accès, suppression de compte).",
  alternates: { canonical: "/privacy" },
};

/** Page statique — rendue côté serveur, indexable. */
export default function PrivacyPage() {
  return (
    <main className="mx-auto max-w-3xl px-4 py-12 sm:px-8">
      <h1 className="font-display mb-2 text-4xl">Politique de confidentialité</h1>
      <p className="text-muted-foreground mb-10">Dernière mise à jour : août 2026</p>

      <div className="text-foreground/85 space-y-8 text-[15px] leading-relaxed">
        <section>
          <h2 className="font-display mb-2 text-2xl">Données que nous collectons</h2>
          <ul className="list-disc space-y-1.5 ps-5">
            <li>
              <b>Compte</b> : nom, prénom, adresse e-mail, mot de passe (stocké uniquement sous
              forme hachée — jamais en clair), téléphone et photo de profil si vous les renseignez.
            </li>
            <li>
              <b>Réservations</b> : activités réservées, dates, nombre de voyageurs, montants.
            </li>
            <li>
              <b>Préférences</b> : favoris, avis déposés, langue d'affichage.
            </li>
          </ul>
        </section>

        <section>
          <h2 className="font-display mb-2 text-2xl">Pourquoi nous les utilisons</h2>
          <p>
            Uniquement pour faire fonctionner le service : gérer votre compte et vos réservations,
            vous envoyer les e-mails indispensables (confirmation de compte, réinitialisation de mot
            de passe, confirmations de réservation). Nous ne vendons ni ne partageons vos données
            avec des tiers à des fins publicitaires.
          </p>
        </section>

        <section>
          <h2 className="font-display mb-2 text-2xl">Comment elles sont protégées</h2>
          <ul className="list-disc space-y-1.5 ps-5">
            <li>Mots de passe hachés (PBKDF2-SHA256) — nous ne pouvons pas les lire.</li>
            <li>Jetons de connexion à durée courte, révocables à tout moment (déconnexion).</li>
            <li>
              Données réparties par domaine (comptes, réservations, avis) dans des bases distinctes,
              accessibles uniquement par le service concerné.
            </li>
          </ul>
        </section>

        <section>
          <h2 className="font-display mb-2 text-2xl">Vos droits</h2>
          <p className="mb-2">
            Conformément aux principes du RGPD et à la loi tunisienne sur la protection des données
            personnelles :
          </p>
          <ul className="list-disc space-y-1.5 ps-5">
            <li>
              <b>Accès et rectification</b> : vos informations sont consultables et modifiables à
              tout moment depuis votre page profil.
            </li>
            <li>
              <b>Suppression</b> : le bouton « Supprimer mon compte » (page profil) anonymise
              immédiatement et définitivement vos données personnelles et révoque toutes vos
              sessions.
            </li>
          </ul>
        </section>

        <section>
          <h2 className="font-display mb-2 text-2xl">Contact</h2>
          <p>
            Pour toute question relative à vos données : <b>privacy@voyara.example</b>.
          </p>
        </section>
      </div>
    </main>
  );
}
