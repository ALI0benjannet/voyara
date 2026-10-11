import { BedDouble, Car, CarTaxiFront, Plane, type LucideIcon } from "lucide-react";

/** Les quatre offres de voyage gérées par la même page générique. La clé sert
 *  aussi de segment i18n (`admin.travel.<clé>`). */
export type TravelResource = "stays" | "flights" | "carRentals" | "transfers";

export type FieldType = "text" | "textarea" | "number" | "select" | "checkbox" | "datetime";

export interface FieldDef {
  name: string;
  type: FieldType;
  required?: boolean;
  /** Valeurs possibles d'un `select` ; libellés sous `admin.travel.options.<valeur>`. */
  options?: string[];
  min?: number;
  max?: number;
  step?: number;
  /** Valeur initiale d'un nouvel élément. */
  initial?: string | boolean;
  /** Occupe toute la largeur du formulaire. */
  wide?: boolean;
}

export interface ColumnDef {
  field: string;
  format?: "currency" | "datetime" | "option" | "bool";
}

export interface TravelConfig {
  /** Segment d'URL, côté admin comme côté API (`/api/v1/<path>`). */
  path: string;
  icon: LucideIcon;
  fields: FieldDef[];
  columns: ColumnDef[];
  /** Libellé d'une ligne dans les confirmations de suppression. */
  label: (row: Record<string, unknown>) => string;
}

export const TRAVEL_CONFIG: Record<TravelResource, TravelConfig> = {
  stays: {
    path: "stays",
    icon: BedDouble,
    fields: [
      { name: "nom", type: "text", required: true },
      {
        name: "type",
        type: "select",
        required: true,
        options: ["hotel", "riad", "maison_hotes", "appartement"],
        initial: "hotel",
      },
      { name: "description", type: "textarea", required: true, wide: true },
      { name: "localisation", type: "text", required: true },
      { name: "etoiles", type: "number", min: 1, max: 5 },
      { name: "prix_nuit", type: "number", required: true, min: 0, step: 0.01 },
      { name: "capacite", type: "number", required: true, min: 1, max: 50, initial: "2" },
      { name: "latitude", type: "number", step: 0.000001 },
      { name: "longitude", type: "number", step: 0.000001 },
      { name: "equipements", type: "text", wide: true },
      { name: "nom_en", type: "text" },
      { name: "nom_ar", type: "text" },
      { name: "description_en", type: "textarea", wide: true },
      { name: "description_ar", type: "textarea", wide: true },
      { name: "actif", type: "checkbox", initial: true },
    ],
    columns: [
      { field: "nom" },
      { field: "type", format: "option" },
      { field: "localisation" },
      { field: "etoiles" },
      { field: "capacite" },
      { field: "actif", format: "bool" },
      { field: "prix_nuit", format: "currency" },
    ],
    label: (row) => String(row.nom),
  },

  flights: {
    path: "flights",
    icon: Plane,
    fields: [
      { name: "compagnie", type: "text", required: true },
      { name: "numero_vol", type: "text", required: true },
      { name: "ville_depart", type: "text", required: true },
      { name: "aeroport_depart", type: "text", required: true },
      { name: "ville_arrivee", type: "text", required: true },
      { name: "aeroport_arrivee", type: "text", required: true },
      { name: "depart_le", type: "datetime", required: true },
      { name: "arrivee_le", type: "datetime", required: true },
      {
        name: "classe",
        type: "select",
        required: true,
        options: ["economy", "business"],
        initial: "economy",
      },
      { name: "prix", type: "number", required: true, min: 0, step: 0.01 },
      { name: "places_totales", type: "number", required: true, min: 0, max: 900 },
    ],
    columns: [
      { field: "numero_vol" },
      { field: "compagnie" },
      { field: "ville_depart" },
      { field: "ville_arrivee" },
      { field: "depart_le", format: "datetime" },
      { field: "places_disponibles" },
      { field: "prix", format: "currency" },
    ],
    label: (row) => `${row.numero_vol} ${row.aeroport_depart} → ${row.aeroport_arrivee}`,
  },

  carRentals: {
    path: "car-rentals",
    icon: Car,
    fields: [
      { name: "marque", type: "text", required: true },
      { name: "modele", type: "text", required: true },
      {
        name: "categorie",
        type: "select",
        required: true,
        options: ["economique", "compacte", "suv", "van"],
        initial: "economique",
      },
      {
        name: "transmission",
        type: "select",
        required: true,
        options: ["manuelle", "automatique"],
        initial: "manuelle",
      },
      {
        name: "carburant",
        type: "select",
        required: true,
        options: ["essence", "diesel", "hybride", "electrique"],
        initial: "essence",
      },
      { name: "nb_places", type: "number", required: true, min: 2, max: 9, initial: "5" },
      { name: "agence", type: "text", required: true },
      { name: "localisation", type: "text", required: true },
      { name: "prix_jour", type: "number", required: true, min: 0, step: 0.01 },
      { name: "disponible", type: "checkbox", initial: true },
    ],
    columns: [
      { field: "marque" },
      { field: "modele" },
      { field: "categorie", format: "option" },
      { field: "transmission", format: "option" },
      { field: "agence" },
      { field: "disponible", format: "bool" },
      { field: "prix_jour", format: "currency" },
    ],
    label: (row) => `${row.marque} ${row.modele}`,
  },

  transfers: {
    path: "transfers",
    icon: CarTaxiFront,
    fields: [
      { name: "depart", type: "text", required: true },
      { name: "arrivee", type: "text", required: true },
      {
        name: "type_vehicule",
        type: "select",
        required: true,
        options: ["taxi", "grand_taxi", "berline", "van", "minibus"],
        initial: "berline",
      },
      { name: "capacite", type: "number", required: true, min: 1, max: 30, initial: "3" },
      { name: "bagages", type: "number", min: 0, max: 30, initial: "0" },
      { name: "duree", type: "number", required: true, min: 1 },
      { name: "prix", type: "number", required: true, min: 0, step: 0.01 },
      { name: "description", type: "textarea", wide: true },
      { name: "actif", type: "checkbox", initial: true },
    ],
    columns: [
      { field: "depart" },
      { field: "arrivee" },
      { field: "type_vehicule", format: "option" },
      { field: "capacite" },
      { field: "duree" },
      { field: "actif", format: "bool" },
      { field: "prix", format: "currency" },
    ],
    label: (row) => `${row.depart} → ${row.arrivee}`,
  },
};
