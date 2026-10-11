export type BookingStats = {
total: number;
pending: number;
confirmed: number;
cancelled: number;
last_30_days: number;
};
export type RevenueStats = {
total: number;
last_30_days: number;
pending: number;
average_basket: number;
};
export type UserStats = {
total: number;
active: number;
verified: number;
admins: number;
new_30_days: number;
};
export type ActivityStats = {
total: number;
categories: number;
upcoming_availabilities: number;
};
export type RecentBooking = {
id: number;
client: string;
email: string;
activity: string;
statut: "pending" | "confirmed" | "cancelled";
montant_total: number;
date_reservation: string;
};
export type DashboardStats = {
bookings: BookingStats;
revenue: RevenueStats;
users: UserStats;
activities: ActivityStats;
recent_bookings: RecentBooking[];
generated_at: string;
};
export type Page<T> = {
items: T[];
total: number;
page: number;
size: number;
pages: number;
};
export type AdminUserRow = {
id: number;
nom: string;
prenom: string;
email: string;
role: "tourist" | "admin";
is_active: boolean;
is_verified: boolean;
phone: string | null;
date_inscription: string;
};
export type AdminBookingRow = {
id: number;
user_id: number;
client: string;
email: string;
activity_id: number;
activity: string;
statut: "pending" | "confirmed" | "cancelled";
montant_total: number;
date_reservation: string;
};
export type AdminActivityRow = {
id: number;
titre: string;
prix: number;
duree: number;
localisation: string;
category: string | null;
bookings_count: number;
};
export type AdminPaymentRow = {
id: number;
booking_id: number;
client: string;
montant: number;
type: string;
methode: string;
statut: string;
date_paiement: string;
};