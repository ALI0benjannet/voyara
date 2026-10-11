import type { MetadataRoute } from "next";

import { fetchActivities } from "@/lib/server-api";
import { SITE_URL } from "@/lib/site";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const activities = await fetchActivities({ size: 50 });

  const activityEntries: MetadataRoute.Sitemap = activities.items.map((activity) => ({
    url: `${SITE_URL}/activities/${activity.id}`,
    changeFrequency: "weekly",
    priority: 0.8,
  }));

  return [
    { url: SITE_URL, changeFrequency: "daily", priority: 1 },
    { url: `${SITE_URL}/activities`, changeFrequency: "daily", priority: 0.9 },
    ...activityEntries,
  ];
}
