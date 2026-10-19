/** Offres de voyage publiques (catalog-service, `/api/v1/offres/*`). */

export interface Stay {
  id: number;
  nom: string;
  type: "hotel" | "riad" | "maison_hotes" | "appartement";
  description: string;
  nom_en?: string | null;
  nom_ar?: string | null;
  description_en?: string | null;
  description_ar?: string | null;
  localisation: string;
  latitude: number | null;
  longitude: number | null;
  etoiles: number | null;
  prix_nuit: number;
  capacite: number;
  /** Liste « piscine,wifi,… » saisie en français. */
  equipements: string | null;
  photos: string | null;
}

export interface Flight {
  id: number;
  compagnie: string;
  numero_vol: string;
  aeroport_depart: string;
  aeroport_arrivee: string;
  ville_depart: string;
  ville_arrivee: string;
  /** Heures locales de chaque aéroport, sans fuseau. */
  depart_le: string;
  arrivee_le: string;
  classe: "economy" | "business";
  prix: number;
  places_totales: number;
  places_disponibles: number;
}

export interface CarRental {
  id: number;
  marque: string;
  modele: string;
  categorie: "economique" | "compacte" | "suv" | "van";
  transmission: "manuelle" | "automatique";
  carburant: "essence" | "diesel" | "hybride" | "electrique";
  nb_places: number;
  agence: string;
  localisation: string;
  prix_jour: number;
  photos: string | null;
}

export interface Transfer {
  id: number;
  depart: string;
  arrivee: string;
  type_vehicule: "taxi" | "grand_taxi" | "berline" | "van" | "minibus";
  capacite: number;
  bagages: number;
  duree: number;
  prix: number;
  description: string | null;
}

/** Contenu métier traduit en base (`*_en`, `*_ar`), repli sur le français. */
export function stayName(stay: Stay, lang?: string): string {
  const base = lang?.split("-")[0];
  if (base === "en") return stay.nom_en?.trim() || stay.nom;
  if (base === "ar") return stay.nom_ar?.trim() || stay.nom;
  return stay.nom;
}

export function stayDescription(stay: Stay, lang?: string): string {
  const base = lang?.split("-")[0];
  if (base === "en") return stay.description_en?.trim() || stay.description;
  if (base === "ar") return stay.description_ar?.trim() || stay.description;
  return stay.description;
}
