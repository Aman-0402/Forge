import { api } from "./client";

export async function sendContactMessage(data: {
  name: string;
  email: string;
  message: string;
}): Promise<void> {
  await api.post("/contact/", data);
}
