"use client";

import { useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { useTranslation } from "react-i18next";
import type { Map as MapLibreMap, Marker, StyleSpecification } from "maplibre-gl";

import { formatPrice } from "@/features/catalog/format";

import "maplibre-gl/dist/maplibre-gl.css";
import "./map-theme.css";

/** Point affiché sur la carte (sous-ensemble d'`Activity` : la carte n'a pas
 *  besoin de la description ni des photos). */
export interface MapPoint {
  id: number;
  titre: string;
  prix: number;
  localisation: string;
  latitude: number;
  longitude: number;
}

/** Centre de repli : la Tunisie, quand aucune activité n'est géolocalisée. */
const TUNISIA: [number, number] = [9.6, 34.0]; // MapLibre attend [lng, lat]

/** Fond de carte vectoriel OpenStreetMap (schéma OpenMapTiles), servi
 *  gratuitement par OpenFreeMap — pas de clé API, pas de quota. */
const STYLE_URL = "https://tiles.openfreemap.org/styles/liberty";

/** Langues de l'interface → clé de nom dans les tuiles OpenMapTiles.
 *  `name:latin` translittère quand la langue n'existe pas dans les données. */
const NAME_FIELD: Record<string, string> = {
  fr: "name:fr",
  en: "name:en",
  ar: "name:ar",
};

/** Expression MapLibre : nom dans la langue demandée, sinon translittération
 *  latine, sinon le nom local. Évite les libellés vides sur les lieux qui
 *  n'ont pas de traduction (fréquent pour les petites localités tunisiennes). */
function labelExpression(lang: string) {
  const field = NAME_FIELD[lang] ?? "name:latin";
  return ["coalesce", ["get", field], ["get", "name:latin"], ["get", "name"]];
}

export interface ActivityMapProps {
  points: MapPoint[];
  /** Cliquer un marqueur ouvre la fiche activité (catalogue). */
  linkToActivity?: boolean;
  /** Zoom fixe quand il n'y a qu'un seul point (page détail). */
  singleZoom?: number;
  className?: string;
  /** Libellé lu par les lecteurs d'écran. */
  hint?: string;
}

/** Carte interactive OpenStreetMap rendue par MapLibre GL (tuiles vectorielles).
 *  Le vectoriel permet de changer la langue des libellés à la volée — impossible
 *  avec des tuiles raster, où le texte est gravé dans l'image.
 *  MapLibre touche à `window` dès l'import : monter via `ActivityMapLoader`. */
export function ActivityMap({
  points,
  linkToActivity = false,
  singleZoom = 13,
  className,
  hint,
}: ActivityMapProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const markersRef = useRef<Marker[]>([]);
  const loadedRef = useRef(false);
  const router = useRouter();
  const { t, i18n } = useTranslation();
  const lang = i18n.language?.split("-")[0] ?? "fr";

  // Évite de recréer les effets quand seule l'identité du router change.
  const routerRef = useRef(router);
  routerRef.current = router;

  // 1. Création de la carte — une seule fois, pour la vie du composant.
  useEffect(() => {
    let cancelled = false;
    if (!containerRef.current) return;

    // Import dynamique : garde MapLibre hors du bundle serveur.
    void import("maplibre-gl").then((mod) => {
      const maplibregl = mod.default ?? mod;
      if (cancelled || !containerRef.current || mapRef.current) return;

      const map = new maplibregl.Map({
        container: containerRef.current,
        style: STYLE_URL as unknown as StyleSpecification,
        center: TUNISIA,
        zoom: 5,
        attributionControl: false,
        // La molette scrolle la page ; le zoom s'active au clic sur la carte.
        scrollZoom: false,
      });

      map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-left");
      map.addControl(
        new maplibregl.AttributionControl({
          compact: true,
          customAttribution:
            '<a href="https://www.openstreetmap.org/copyright">© OpenStreetMap</a> · <a href="https://openfreemap.org">OpenFreeMap</a>',
        }),
        "bottom-right",
      );
      map.on("click", () => map.scrollZoom.enable());
      map.on("mouseout", () => map.scrollZoom.disable());
      map.on("load", () => {
        loadedRef.current = true;
      });

      mapRef.current = map;
    });

    return () => {
      cancelled = true;
      for (const marker of markersRef.current) marker.remove();
      markersRef.current = [];
      mapRef.current?.remove();
      mapRef.current = null;
      loadedRef.current = false;
    };
  }, []);

  // 2. Langue des libellés — rejouée à chaque changement de langue de l'app.
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    const applyLanguage = () => {
      const style = map.getStyle();
      if (!style?.layers) return;
      const expression = labelExpression(lang);
      for (const layer of style.layers) {
        // Seules les couches de symboles portent du texte.
        if (layer.type !== "symbol") continue;
        if (!("layout" in layer) || !layer.layout?.["text-field"]) continue;
        try {
          map.setLayoutProperty(layer.id, "text-field", expression);
        } catch {
          // Une couche peut refuser l'expression (champ absent du schéma) :
          // on la laisse dans sa langue d'origine plutôt que de casser la carte.
        }
      }
    };

    if (loadedRef.current && map.isStyleLoaded()) applyLanguage();
    else map.once("load", applyLanguage);
  }, [lang]);

  // 3. Marqueurs — resynchronisés quand les filtres du catalogue changent.
  useEffect(() => {
    let cancelled = false;
    void import("maplibre-gl").then((mod) => {
      const maplibregl = mod.default ?? mod;
      const map = mapRef.current;
      if (cancelled || !map) return;

      for (const marker of markersRef.current) marker.remove();
      markersRef.current = [];

      for (const point of points) {
        const el = document.createElement("button");
        el.type = "button";
        el.className = "tb-pin";
        el.textContent = linkToActivity
          ? `${formatPrice(point.prix)} · ${point.localisation}`
          : point.localisation;
        el.setAttribute(
          "aria-label",
          linkToActivity ? `${point.titre} — ${formatPrice(point.prix)}` : point.titre,
        );
        if (linkToActivity) {
          el.addEventListener("click", (event) => {
            event.stopPropagation();
            routerRef.current.push(`/activities/${point.id}`);
          });
        } else {
          el.disabled = true;
        }

        const marker = new maplibregl.Marker({ element: el, anchor: "bottom" })
          .setLngLat([point.longitude, point.latitude])
          .addTo(map);
        markersRef.current.push(marker);
      }

      if (points.length === 1) {
        const only = points[0]!;
        map.jumpTo({ center: [only.longitude, only.latitude], zoom: singleZoom });
      } else if (points.length > 1) {
        const bounds = new maplibregl.LngLatBounds();
        for (const p of points) bounds.extend([p.longitude, p.latitude]);
        map.fitBounds(bounds, { padding: 64, maxZoom: 11, animate: false });
      }
    });
    return () => {
      cancelled = true;
    };
  }, [points, linkToActivity, singleZoom]);

  return (
    <div className={className}>
      <div
        ref={containerRef}
        role="application"
        aria-label={hint ?? t("catalog.mapHint")}
        className="size-full"
      />
    </div>
  );
}

export default ActivityMap;
