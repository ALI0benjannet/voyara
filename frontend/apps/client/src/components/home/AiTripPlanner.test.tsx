// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { AxiosError, AxiosHeaders } from "axios";
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

import i18n from "@voyara/i18n";
import ar from "@voyara/i18n/locales/ar/common.json";
import en from "@voyara/i18n/locales/en/common.json";
import fr from "@voyara/i18n/locales/fr/common.json";

import type { ReponseComprendre } from "@/features/ai/comprendre";

import { AiTripPlanner } from "./AiTripPlanner";

// L'appel réseau est simulé au niveau du client axios partagé (@voyara/api).
const post = vi.hoisted(() => vi.fn());
vi.mock("@voyara/api/axios", () => ({ api: { post } }));

const TEXTE = "Je vais à Djerba 3 jours, 300 DT, en famille, culture et plage";

function reponse(champs: Partial<ReponseComprendre> = {}, demande: Partial<ReponseComprendre["demande"]> = {}) {
  return {
    demande: {
      destination: "Djerba", autres_villes: [], duree_jours: 3, nb_nuits: 3, budget_montant: 300,
      budget_devise: "TND", budget_illimite: false, nb_voyageurs: null, nb_adultes: null, nb_enfants: null,
      type_voyage: "famille", preferences: ["plage", "culture"], activites_souhaitees: [], ville_depart: null,
      besoins_transport: { vol: "indifferent", voiture: "indifferent", transfert: "indifferent" },
      hors_sujet: false, ...demande,
    },
    champs_manquants: [], question_clarification: null, avertissements: [], provider: "ollama",
    latence_ms: 15000, methode: "hybride", ...champs,
  } satisfies ReponseComprendre;
}

function erreurHttp(status: number) {
  return new AxiosError("échec", "ERR_BAD_RESPONSE", undefined, undefined, {
    status, statusText: "", data: {}, headers: {}, config: { headers: new AxiosHeaders() },
  });
}

function afficher() {
  const client = new QueryClient({ defaultOptions: { mutations: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <AiTripPlanner />
    </QueryClientProvider>,
  );
  const champ = screen.getByRole("textbox");
  const bouton = screen.getByRole("button", { name: /Générer mon voyage/ });
  return { champ, bouton };
}

function envoyer(champ: HTMLElement, bouton: HTMLElement, texte = TEXTE) {
  fireEvent.change(champ, { target: { value: texte } });
  fireEvent.click(bouton);
}

beforeAll(async () => {
  await i18n.changeLanguage("fr");
});

// Accolades obligatoires : une fonction renvoyée par beforeEach est appelée par vitest comme
// nettoyage après le test (ici, le mock lui-même, qui rejetterait).
beforeEach(() => {
  post.mockReset();
});
afterEach(() => cleanup());

describe("AiTripPlanner — POST /api/ai/comprendre", () => {
  it("désactive le bouton pendant l'appel, puis affiche ce qui a été compris", async () => {
    let repondre!: (valeur: unknown) => void;
    post.mockReturnValue(new Promise((r) => (repondre = r)));
    const { champ, bouton } = afficher();

    envoyer(champ, bouton);
    await screen.findByText("Analyse de votre demande…");
    expect((bouton as HTMLButtonElement).disabled).toBe(true);
    fireEvent.click(bouton); // aucun double envoi
    expect(post).toHaveBeenCalledTimes(1);
    expect(post).toHaveBeenCalledWith("/api/ai/comprendre", { texte: TEXTE }, { timeout: 35_000 });

    await act(async () => repondre({ data: reponse() }));
    await screen.findByText("Ce que nous avons compris");
    expect(screen.getByText("Djerba")).toBeTruthy();
    expect(screen.getByText("3 jours · 3 nuits")).toBeTruthy();
    expect(screen.getByText("300 TND")).toBeTruthy();
    expect(screen.getByText("Famille")).toBeTruthy();
    expect(screen.getByText("Plage, Culture")).toBeTruthy();
    expect(screen.getByText("IA + règles")).toBeTruthy();
    expect(screen.queryByText("Activités")).toBeNull(); // champ vide : non affiché
    expect(screen.queryByText("Transport")).toBeNull();
    expect((bouton as HTMLButtonElement).disabled).toBe(false);
  });

  it("met en évidence la question de clarification", async () => {
    post.mockResolvedValue({
      data: reponse(
        { champs_manquants: ["destination"], question_clarification: "Où souhaitez-vous partir ?", methode: "regles" },
        { destination: null, type_voyage: "couple", nb_voyageurs: 2, nb_adultes: 2, nb_enfants: 0, duree_jours: 4,
          nb_nuits: 4, budget_montant: 250 },
      ),
    });
    const { champ, bouton } = afficher();
    envoyer(champ, bouton, "je suis avec ma femme, 4 jours, 250 dt");

    const question = await screen.findByRole("status");
    expect(question.textContent).toBe("Où souhaitez-vous partir ?");
    expect(screen.getByText("2 personnes · 2 adultes · Couple")).toBeTruthy();
    expect(screen.queryByText("Destination")).toBeNull();
    expect(screen.getByText("Règles")).toBeTruthy();
  });

  it.each([
    [429, "Trop de demandes"],
    [503, "momentanément indisponible"],
    [0, "momentanément indisponible"],
    [422, "n'a pas pu être analysée"],
  ])("erreur %i : message clair, la saisie reste utilisable", async (status, message) => {
    post.mockRejectedValue(status === 0 ? new AxiosError("timeout", "ECONNABORTED") : erreurHttp(status));
    const { champ, bouton } = afficher();
    envoyer(champ, bouton);

    const alerte = await screen.findByRole("alert");
    expect(alerte.textContent).toContain(message);
    await waitFor(() => expect((bouton as HTMLButtonElement).disabled).toBe(false));
    expect(screen.queryByText("Ce que nous avons compris")).toBeNull();
  });

  it("n'envoie rien pour un texte vide", () => {
    const { champ, bouton } = afficher();
    envoyer(champ, bouton, "   ");
    expect(post).not.toHaveBeenCalled();
  });
});

describe("traductions de home.aiPlanner", () => {
  const SUFFIXES_PLURIEL = /_(zero|one|two|few|many|other)$/;
  const cles = (objet: object, prefixe = ""): string[] =>
    Object.entries(objet).flatMap(([cle, valeur]) =>
      typeof valeur === "object" && valeur !== null
        ? cles(valeur, `${prefixe}${cle}.`)
        : [`${prefixe}${cle}`.replace(SUFFIXES_PLURIEL, "")],
    );
  const unique = (liste: string[]) => [...new Set(liste)].sort();

  it("fr, en et ar ont les mêmes clés (pluriels mis à part)", () => {
    const reference = unique(cles(fr.home.aiPlanner));
    expect(unique(cles(en.home.aiPlanner))).toEqual(reference);
    expect(unique(cles(ar.home.aiPlanner))).toEqual(reference);
  });
});
