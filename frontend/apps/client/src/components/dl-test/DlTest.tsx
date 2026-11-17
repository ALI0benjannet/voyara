"use client";

import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import { Brain, CheckCircle2, FlaskConical, Loader2, Search, Tags, XCircle } from "lucide-react";

import { cn } from "@voyara/ui/lib/utils";

import {
  CHAMPS_CLASSIF,
  LANGUES,
  METHODES_CLASSIF,
  METHODES_RECHERCHE,
  useClassifDl,
  useExemplesDl,
  usePrechaufferDl,
  useRechercheDl,
  useResultatsDl,
  type ChampClassif,
  type LigneResultat,
} from "@/features/dl-test/api";
import { useHydratedTranslation } from "@/features/i18n/use-hydrated-language";

type Onglet = "recherche" | "classification";

/** Page temporaire « DL test » : résultats mesurés + tests en direct, sans LLM. */
export function DlTest() {
  const { t } = useHydratedTranslation();
  const [onglet, setOnglet] = useState<Onglet>("recherche");

  return (
    <main className="mx-auto max-w-7xl space-y-6 px-4 py-8 sm:px-8">
      <header className="space-y-2">
        <span className="bg-accent/15 text-foreground inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold">
          <FlaskConical aria-hidden className="size-3.5" />
          {t("dlTest.badge")}
        </span>
        <h1 className="font-display text-4xl">{t("dlTest.title")}</h1>
        <p className="text-muted-foreground max-w-3xl">{t("dlTest.subtitle")}</p>
      </header>

      <div role="tablist" className="border-border bg-muted inline-flex gap-1 rounded-full border p-1">
        {(["recherche", "classification"] as const).map((o) => (
          <button
            key={o}
            role="tab"
            aria-selected={onglet === o}
            onClick={() => setOnglet(o)}
            className={cn(
              "flex items-center gap-2 rounded-full px-4 py-2 text-sm font-medium transition-colors",
              onglet === o ? "bg-primary text-primary-foreground" : "text-foreground/70 hover:text-primary",
            )}
          >
            {o === "recherche" ? <Search className="size-4" /> : <Tags className="size-4" />}
            {t(`dlTest.tabs.${o}`)}
          </button>
        ))}
      </div>

      {onglet === "recherche" ? <OngletRecherche /> : <OngletClassification />}
    </main>
  );
}

/* ------------------------------------------------------------------ outils d'affichage */

function Carte({ titre, children, className }: { titre: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={cn("border-border bg-card rounded-2xl border p-5 shadow-sm", className)}>
      <h2 className="font-display mb-3 text-xl">{titre}</h2>
      {children}
    </section>
  );
}

const nombre = (v: unknown, decimales = 3) =>
  typeof v === "number" ? v.toLocaleString("fr-FR", { maximumFractionDigits: decimales, minimumFractionDigits: decimales }) : "—";

/** Cellule chiffrée avec une barre proportionnelle (valeurs entre 0 et 1). */
function CelluleBarre({ valeur, max }: { valeur: unknown; max: number }) {
  const v = typeof valeur === "number" ? valeur : null;
  const meilleure = v !== null && Math.abs(v - max) < 1e-9;
  return (
    <td className="px-2 py-1.5 text-end tabular-nums">
      <div className="flex items-center justify-end gap-2">
        {v !== null && (
          <span className="bg-muted hidden h-1.5 w-16 overflow-hidden rounded-full sm:block">
            <span className="bg-primary block h-full rounded-full" style={{ width: `${Math.max(0, Math.min(1, v)) * 100}%` }} />
          </span>
        )}
        <span className={cn(meilleure && "text-primary font-semibold")}>{nombre(v)}</span>
      </div>
    </td>
  );
}

function Tableau({
  lignes,
  colonnes,
  libelles,
  colonneNom = "approche",
}: {
  lignes: LigneResultat[];
  colonnes: string[];
  libelles: Record<string, string>;
  colonneNom?: string;
}) {
  const { t } = useHydratedTranslation();
  if (!lignes.length) return <p className="text-muted-foreground text-sm">{t("dlTest.noData")}</p>;
  const max = Object.fromEntries(
    colonnes.map((c) => [c, Math.max(...lignes.map((l) => (typeof l[c] === "number" ? (l[c] as number) : -Infinity)))]),
  );
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-muted-foreground border-border border-b text-xs">
            <th className="px-2 py-1.5 text-start font-medium">{libelles[colonneNom] ?? colonneNom}</th>
            {colonnes.map((c) => (
              <th key={c} className="px-2 py-1.5 text-end font-medium">
                {libelles[c] ?? c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {lignes.map((l, i) => (
            <tr key={i} className="border-border/60 border-b last:border-0">
              <td className="px-2 py-1.5 font-medium">{String(l[colonneNom] ?? "")}</td>
              {colonnes.map((c) => (
                <CelluleBarre key={c} valeur={l[c]} max={max[c]} />
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Erreur() {
  const { t } = useHydratedTranslation();
  return <p className="text-destructive text-sm">{t("dlTest.error")}</p>;
}

function SelectExemple({
  options,
  onChoisir,
}: {
  options: { valeur: string; libelle: string }[];
  onChoisir: (valeur: string) => void;
}) {
  const { t } = useHydratedTranslation();
  return (
    <select
      defaultValue=""
      onChange={(e) => e.target.value && onChoisir(e.target.value)}
      className="border-border bg-background h-10 w-full rounded-lg border px-3 text-sm sm:w-80"
      aria-label={t("dlTest.examples")}
    >
      <option value="">{t("dlTest.examples")}</option>
      {options.map((o) => (
        <option key={o.valeur} value={o.valeur}>
          {o.libelle}
        </option>
      ))}
    </select>
  );
}

/* ------------------------------------------------------------------ recherche (Ons) */

function OngletRecherche() {
  const { t } = useHydratedTranslation();
  const resultats = useResultatsDl();
  const exemples = useExemplesDl();
  const recherche = useRechercheDl();
  usePrechaufferDl();
  const [requete, setRequete] = useState("");
  const [essais, setEssais] = useState(0);

  const lancer = (texte: string) => {
    const r = texte.trim();
    if (!r || recherche.isPending) return;
    setEssais(0);
    recherche.mutate(r);
  };

  // e5 se charge en arrière-plan au premier usage : on relance la même recherche toutes les
  // 5 s (au plus 5 min) jusqu'à ce que tous les modèles aient répondu.
  const enChargement = recherche.data
    ? METHODES_RECHERCHE.some((m) => recherche.data.methodes[m]?.en_chargement)
    : false;
  const { data: derniere, mutate: relancer } = recherche;
  useEffect(() => {
    if (!enChargement || !derniere || essais >= 60) return;
    const minuteur = setTimeout(() => {
      setEssais((n) => n + 1);
      relancer(derniere.requete);
    }, 5000);
    return () => clearTimeout(minuteur);
  }, [enChargement, derniere, relancer, essais]);
  const submit = (e: FormEvent) => {
    e.preventDefault();
    lancer(requete);
  };

  const r = resultats.data?.recherche;
  const lib = {
    approche: t("dlTest.col.approach"),
    modele: t("dlTest.col.model"),
    "Recall@5": "Recall@5",
    "Recall@10": "Recall@10",
    "nDCG@10": "nDCG@10",
    MRR: "MRR",
    ...Object.fromEntries(LANGUES.map((lg) => [`nDCG@10_${lg}`, t(`dlTest.lang.${lg}`)])),
  };

  return (
    <div className="space-y-6">
      <Carte titre={<span className="flex items-center gap-2"><Brain className="text-primary size-5" />{t("dlTest.search.liveTitle")}</span>}>
        <p className="text-muted-foreground mb-3 text-sm">{t("dlTest.search.liveHelp")}</p>
        <form onSubmit={submit} className="flex flex-col gap-2 sm:flex-row">
          <input
            value={requete}
            onChange={(e) => setRequete(e.target.value)}
            maxLength={300}
            placeholder={t("dlTest.search.placeholder")}
            className="border-border bg-background h-10 flex-1 rounded-lg border px-3 text-sm"
          />
          <SelectExemple
            options={(exemples.data?.recherche ?? []).map((q) => ({
              valeur: q.requete,
              libelle: `${q.id} · ${t(`dlTest.lang.${q.langue}`)} · ${q.requete}`,
            }))}
            onChoisir={(v) => {
              setRequete(v);
              lancer(v);
            }}
          />
          <button
            type="submit"
            disabled={!requete.trim() || recherche.isPending}
            className="bg-primary text-primary-foreground hover:bg-primary-hover flex h-10 items-center justify-center gap-2 rounded-lg px-5 text-sm font-semibold disabled:opacity-60"
          >
            {recherche.isPending ? <Loader2 className="size-4 animate-spin" /> : <Search className="size-4" />}
            {t("dlTest.search.submit")}
          </button>
        </form>
        {recherche.isPending && <p className="text-muted-foreground mt-3 text-sm">{t("dlTest.firstCall")}</p>}
        {recherche.isError && <div className="mt-3"><Erreur /></div>}

        {recherche.data && (
          <div className="mt-4 space-y-3">
            {recherche.data.requete_test ? (
              <p className="text-sm">
                {t("dlTest.search.fromTest", { id: recherche.data.requete_test.id })}{" "}
                <span className="text-muted-foreground">{recherche.data.requete_test.pertinentes.join(" · ")}</span>
              </p>
            ) : (
              <p className="text-muted-foreground text-sm">{t("dlTest.search.freeQuery")}</p>
            )}
            <div className="grid gap-4 lg:grid-cols-3">
              {METHODES_RECHERCHE.map((m) => {
                const res = recherche.data.methodes[m];
                return (
                  <div key={m} className="border-border rounded-xl border p-3">
                    <div className="mb-2 flex items-baseline justify-between gap-2">
                      <h3 className="font-semibold">{t(`dlTest.search.methods.${m}`)}</h3>
                      {res?.disponible && (
                        <span className="text-muted-foreground text-xs tabular-nums">{res.latence_ms} ms</span>
                      )}
                    </div>
                    {!res?.disponible ? (
                      <p className="text-muted-foreground text-sm">{t("dlTest.unavailable")}</p>
                    ) : res.en_chargement ? (
                      <p className="text-muted-foreground flex items-center gap-2 text-sm">
                        <Loader2 className="size-4 animate-spin" />
                        {t("dlTest.loadingModel")}
                      </p>
                    ) : res.erreur ? (
                      <p className="text-destructive text-sm">{t("dlTest.modelError")}</p>
                    ) : (
                      <>
                        {recherche.data.requete_test && (
                          <p className="mb-2 text-xs">
                            {t("dlTest.search.firstRelevant")}{" "}
                            <b>{res.rang_premiere_pertinente ?? "—"}</b>
                          </p>
                        )}
                        <ol className="space-y-1">
                          {res.resultats.map((a) => (
                            <li
                              key={a.rang}
                              className={cn(
                                "flex gap-2 rounded-md px-2 py-1 text-sm",
                                a.pertinente && "bg-emerald-500/15 text-emerald-900 dark:text-emerald-200",
                              )}
                            >
                              <span className="text-muted-foreground w-5 shrink-0 tabular-nums">{a.rang}</span>
                              <span className="min-w-0 flex-1">
                                <span className="block truncate" title={a.titre}>{a.titre}</span>
                                <span className="text-muted-foreground text-xs">{a.ville}</span>
                              </span>
                              <span className="text-muted-foreground shrink-0 text-xs tabular-nums">{nombre(a.score)}</span>
                            </li>
                          ))}
                        </ol>
                      </>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </Carte>

      {resultats.isError && <Erreur />}
      <div className="grid gap-6 lg:grid-cols-2">
        <Carte titre={t("dlTest.search.globalTitle")} className="lg:col-span-2">
          <p className="text-muted-foreground mb-3 text-sm">{t("dlTest.search.globalHelp")}</p>
          <Tableau lignes={r?.global ?? []} colonnes={["Recall@5", "Recall@10", "nDCG@10", "MRR"]} libelles={lib} />
        </Carte>
        <Carte titre={t("dlTest.byLanguage")}>
          <Tableau lignes={r?.global ?? []} colonnes={LANGUES.map((lg) => `nDCG@10_${lg}`)} libelles={lib} />
        </Carte>
        <Carte titre={t("dlTest.search.modelChoice")}>
          <Tableau lignes={r?.choix_modele ?? []} colonnes={["nDCG@10", "Recall@5", "MRR"]} libelles={lib} colonneNom="modele" />
        </Carte>
        <Carte titre={t("dlTest.search.lossTitle")} className="lg:col-span-2">
          <p className="text-muted-foreground mb-3 text-sm">{t("dlTest.search.lossHelp")}</p>
          <Pertes lignes={r?.pertes ?? []} />
        </Carte>
      </div>
    </div>
  );
}

/** Perte moyenne par époque, une ligne par run (variante · graine). */
function Pertes({ lignes }: { lignes: LigneResultat[] }) {
  const { t } = useHydratedTranslation();
  if (!lignes.length) return <p className="text-muted-foreground text-sm">{t("dlTest.noData")}</p>;
  const runs = new Map<string, Record<number, number>>();
  for (const l of lignes) {
    const cle = `${l.run} · ${t("dlTest.seed")} ${l.graine}`;
    runs.set(cle, { ...(runs.get(cle) ?? {}), [Number(l.epoque)]: Number(l.perte) });
  }
  const epoques = [...new Set(lignes.map((l) => Number(l.epoque)))].sort((a, b) => a - b);
  const max = Math.max(...lignes.map((l) => Number(l.perte)));
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-muted-foreground border-border border-b text-xs">
            <th className="px-2 py-1.5 text-start font-medium">{t("dlTest.col.run")}</th>
            {epoques.map((e) => (
              <th key={e} className="px-2 py-1.5 text-end font-medium">{t("dlTest.epoch")} {e}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {[...runs].map(([cle, pertes]) => (
            <tr key={cle} className="border-border/60 border-b last:border-0">
              <td className="px-2 py-1.5 font-medium">{cle}</td>
              {epoques.map((e) => (
                <td key={e} className="px-2 py-1.5 text-end tabular-nums">
                  <div className="flex items-center justify-end gap-2">
                    <span className="bg-muted hidden h-1.5 w-16 overflow-hidden rounded-full sm:block">
                      <span className="bg-accent block h-full rounded-full" style={{ width: `${((pertes[e] ?? 0) / max) * 100}%` }} />
                    </span>
                    {nombre(pertes[e])}
                  </div>
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/* ------------------------------------------------------------------ classification (Boutheina) */

function OngletClassification() {
  const { t } = useHydratedTranslation();
  const resultats = useResultatsDl();
  const exemples = useExemplesDl();
  const classif = useClassifDl();
  const [texte, setTexte] = useState("");
  const [attendu, setAttendu] = useState<Record<ChampClassif, string> | null>(null);

  const lancer = (valeur: string) => {
    const v = valeur.trim();
    if (v && !classif.isPending) classif.mutate(v);
  };
  const submit = (e: FormEvent) => {
    e.preventDefault();
    setAttendu(null);
    lancer(texte);
  };

  const c = resultats.data?.classification;
  // F1 macro par approche (lignes) et par champ (colonnes) : baseline règles en tête.
  const lignesF1 = pivoter([...(c?.regles ?? []), ...(c?.global ?? [])], "F1_macro");
  const lib = {
    approche: t("dlTest.col.approach"),
    ...Object.fromEntries(CHAMPS_CLASSIF.map((ch) => [ch, t(`dlTest.classif.fields.${ch}`)])),
    ...Object.fromEntries(LANGUES.map((lg) => [`F1_${lg}`, t(`dlTest.lang.${lg}`)])),
  };

  return (
    <div className="space-y-6">
      <Carte titre={<span className="flex items-center gap-2"><Brain className="text-primary size-5" />{t("dlTest.classif.liveTitle")}</span>}>
        <p className="text-muted-foreground mb-3 text-sm">{t("dlTest.classif.liveHelp")}</p>
        <form onSubmit={submit} className="space-y-2">
          <textarea
            value={texte}
            onChange={(e) => setTexte(e.target.value)}
            rows={2}
            maxLength={2000}
            placeholder={t("dlTest.classif.placeholder")}
            className="border-border bg-background w-full rounded-lg border px-3 py-2 text-sm"
          />
          <div className="flex flex-col gap-2 sm:flex-row">
            <SelectExemple
              options={(exemples.data?.classification ?? []).map((d) => ({
                valeur: d.id,
                libelle: `${d.id} · ${t(`dlTest.lang.${d.langue}`)} · ${d.texte.slice(0, 70)}`,
              }))}
              onChoisir={(id) => {
                const d = exemples.data?.classification.find((x) => x.id === id);
                if (!d) return;
                setTexte(d.texte);
                setAttendu(d.attendu);
                lancer(d.texte);
              }}
            />
            <button
              type="submit"
              disabled={!texte.trim() || classif.isPending}
              className="bg-primary text-primary-foreground hover:bg-primary-hover flex h-10 items-center justify-center gap-2 rounded-lg px-5 text-sm font-semibold disabled:opacity-60"
            >
              {classif.isPending ? <Loader2 className="size-4 animate-spin" /> : <Tags className="size-4" />}
              {t("dlTest.classif.submit")}
            </button>
          </div>
        </form>
        {classif.isError && <div className="mt-3"><Erreur /></div>}

        {classif.data && (
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-muted-foreground border-border border-b text-xs">
                  <th className="px-2 py-1.5 text-start font-medium">{t("dlTest.classif.field")}</th>
                  {attendu && <th className="px-2 py-1.5 text-start font-medium">{t("dlTest.classif.expected")}</th>}
                  {METHODES_CLASSIF.map((m) => (
                    <th key={m} className="px-2 py-1.5 text-start font-medium">
                      {t(`dlTest.classif.methods.${m}`)}
                      {classif.data.methodes[m]?.disponible && (
                        <span className="ms-1 font-normal tabular-nums">({classif.data.methodes[m].latence_ms} ms)</span>
                      )}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {CHAMPS_CLASSIF.map((ch) => (
                  <tr key={ch} className="border-border/60 border-b last:border-0">
                    <td className="px-2 py-2 font-medium">{t(`dlTest.classif.fields.${ch}`)}</td>
                    {attendu && <td className="px-2 py-2">{t(`dlTest.classif.labels.${attendu[ch]}`)}</td>}
                    {METHODES_CLASSIF.map((m) => {
                      const res = classif.data.methodes[m];
                      const p = res?.predictions?.[ch];
                      if (!res?.disponible || !p) {
                        return <td key={m} className="text-muted-foreground px-2 py-2">{t("dlTest.unavailable")}</td>;
                      }
                      const juste = attendu ? attendu[ch] === p.etiquette : null;
                      return (
                        <td key={m} className="px-2 py-2">
                          <span className="inline-flex items-center gap-1.5">
                            {juste === true && <CheckCircle2 className="size-4 text-emerald-600" />}
                            {juste === false && <XCircle className="text-destructive size-4" />}
                            {t(`dlTest.classif.labels.${p.etiquette}`)}
                            {p.confiance !== null && (
                              <span className="text-muted-foreground text-xs tabular-nums">{nombre(p.confiance, 2)}</span>
                            )}
                          </span>
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Carte>

      {resultats.isError && <Erreur />}
      <div className="grid gap-6 lg:grid-cols-2">
        <Carte titre={t("dlTest.classif.globalTitle")} className="lg:col-span-2">
          <p className="text-muted-foreground mb-3 text-sm">{t("dlTest.classif.globalHelp")}</p>
          <Tableau lignes={lignesF1} colonnes={[...CHAMPS_CLASSIF]} libelles={lib} />
        </Carte>
        {CHAMPS_CLASSIF.map((ch) => (
          <Carte key={ch} titre={`${t("dlTest.byLanguage")} — ${t(`dlTest.classif.fields.${ch}`)}`}>
            <Tableau
              lignes={[...(c?.regles ?? []), ...(c?.global ?? [])].filter((l) => l.champ === ch && l.F1_fr != null)}
              colonnes={LANGUES.map((lg) => `F1_${lg}`)}
              libelles={lib}
            />
          </Carte>
        ))}
      </div>
    </div>
  );
}

/** Lignes (approche, champ, valeur) → une ligne par approche, une colonne par champ. */
function pivoter(lignes: LigneResultat[], valeur: string): LigneResultat[] {
  const parApproche = new Map<string, LigneResultat>();
  for (const l of lignes) {
    const nom = String(l.approche);
    parApproche.set(nom, { ...(parApproche.get(nom) ?? { approche: nom }), [String(l.champ)]: l[valeur] });
  }
  return [...parApproche.values()];
}
