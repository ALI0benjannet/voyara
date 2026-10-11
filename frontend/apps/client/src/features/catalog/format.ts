/** Prix affiché comme dans la maquette : « 45 DT ». */
export function formatPrice(value: number): string {
  return `${Math.round(value)} DT`;
}

/** Durée en minutes → « 2 h », « 1 h 30 », « 2 jours ». Pure (utilisable côté serveur). */
export function formatDuration(minutes: number, lang: string = "fr"): string {
  if (minutes >= 1440) {
    const days = Math.round(minutes / 1440);
    if (lang === "ar") return `${days} أيام`;
    return lang === "en" ? `${days} day${days > 1 ? "s" : ""}` : `${days} jour${days > 1 ? "s" : ""}`;
  }
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  if (h === 0) return `${m} min`;
  if (lang === "en") return m ? `${h} h ${m}` : `${h} hrs`;
  return m ? `${h} h ${m}` : `${h} h`;
}
