import { api } from "./client";

export async function sendContactMessage(data: {
  name: string;
  email: string;
  message: string;
}): Promise<void> {
  await api.post("/contact/", data);
}

export type SiteSettings = {
  registration_open: boolean;
  maintenance_mode: boolean;
  maintenance_message: string;
};

export const getSiteSettings = async () =>
  (await api.get<SiteSettings>("/site-settings/")).data;

export type MarketingStat = {
  id: number;
  order: number;
  value: string;
  suffix: string;
  description: string;
};

export const listMarketingStats = async () =>
  (await api.get<MarketingStat[]>("/marketing-stats/")).data;
