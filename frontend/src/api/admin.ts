import type { Role } from "./auth";
import { api } from "./client";
import { cleanQuery, type Paginated, type Query } from "./types";

export type Department = {
  id: number;
  name: string;
  code: string;
  description: string;
  user_count: number;
};

export type Profile = Record<string, string | number | null>;

export type AdminUser = {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  role: Role;
  phone: string;
  department: number | null;
  department_detail: { id: number; name: string; code: string } | null;
  profile: Profile | null;
  is_active: boolean;
  must_change_password: boolean;
  date_joined: string;
  last_login: string | null;
};

export type AdminUserInput = Partial<{
  email: string;
  first_name: string;
  last_name: string;
  role: Role;
  phone: string;
  department: number | null;
  profile: Profile;
  password: string;
  is_active: boolean;
}>;

export type BulkImportResult = {
  created: { row: number; email: string; role: Role; temp_password: string | null }[];
  errors: { row: number; errors: unknown }[];
};

export type AuditLog = {
  id: number;
  actor: number | null;
  actor_email: string | null;
  action: string;
  target_type: string;
  target_id: string;
  metadata: Record<string, unknown>;
  ip: string | null;
  created_at: string;
};

export const listUsers = async (q: Query) =>
  (await api.get<Paginated<AdminUser>>("/users/", { params: cleanQuery(q) })).data;

export const createUser = async (body: AdminUserInput) =>
  (await api.post<AdminUser & { temp_password: string | null }>("/users/", body)).data;

export const updateUser = async (id: number, body: AdminUserInput) =>
  (await api.patch<AdminUser>(`/users/${id}/`, body)).data;

export const deactivateUser = async (id: number) => {
  await api.delete(`/users/${id}/`);
};

export const resetPassword = async (id: number) =>
  (await api.post<{ temp_password: string }>(`/users/${id}/reset-password/`)).data.temp_password;

export const bulkImportUsers = async (file: File) => {
  const form = new FormData();
  form.append("file", file);
  return (await api.post<BulkImportResult>("/users/bulk-import/", form)).data;
};

export const listDepartments = async () =>
  (await api.get<Paginated<Department>>("/departments/", { params: { page_size: 100 } })).data
    .results;

export const createDepartment = async (body: Pick<Department, "name" | "code" | "description">) =>
  (await api.post<Department>("/departments/", body)).data;

export const deleteDepartment = async (id: number) => {
  await api.delete(`/departments/${id}/`);
};

export const listAuditLogs = async (q: Query) =>
  (await api.get<Paginated<AuditLog>>("/audit-logs/", { params: cleanQuery(q) })).data;
