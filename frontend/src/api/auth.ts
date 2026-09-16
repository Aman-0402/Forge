import { api, tokens } from "./client";

export type Role = "admin" | "faculty" | "student";

export type User = {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  role: Role;
  phone: string;
  avatar: string | null;
  department: { id: number; name: string; code: string } | null;
  profile: Record<string, string | number | null> | null;
  must_change_password: boolean;
  is_active: boolean;
  date_joined: string;
  last_login: string | null;
};

export async function login(email: string, password: string): Promise<void> {
  const res = await api.post("/auth/token/", { email, password });
  tokens.setAccess(res.data.access);
  tokens.setRefresh(res.data.refresh);
}

export async function register(data: {
  email: string;
  password: string;
  first_name: string;
  last_name: string;
}): Promise<void> {
  await api.post("/auth/register/", data);
}

export async function fetchMe(): Promise<User> {
  const res = await api.get<User>("/auth/me/");
  return res.data;
}

export async function changePassword(old_password: string, new_password: string): Promise<void> {
  // Changing the password ends every session; the response carries the new token pair.
  const res = await api.post<{ access: string; refresh: string }>("/auth/change-password/", {
    old_password,
    new_password,
  });
  tokens.setAccess(res.data.access);
  tokens.setRefresh(res.data.refresh);
}

export async function logout(): Promise<void> {
  const refresh = tokens.getRefresh();
  try {
    if (refresh) await api.post("/auth/logout/", { refresh });
  } finally {
    tokens.clear();
  }
}
