const CURRENCY = "TND"; // change en "EUR" si besoin
export const formatCurrency = (value: number, locale = "fr-FR") =>
new Intl.NumberFormat(locale, {
style: "currency",
currency: CURRENCY,
maximumFractionDigits: 2,
}).format(Number.isFinite(value) ? value : 0);
export const formatNumber = (value: number, locale = "fr-FR") =>
new Intl.NumberFormat(locale).format(Number.isFinite(value) ? value : 0);
export const formatDateTime = (iso: string, locale = "fr-FR") =>
new Intl.DateTimeFormat(locale, {
dateStyle: "medium",
timeStyle: "short",
}).format(new Date(iso));