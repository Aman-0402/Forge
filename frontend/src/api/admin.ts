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
  created: { row: number; email: string; role: Role; invite_link: string | null }[];
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
  (await api.post<AdminUser & { invite_link: string | null }>("/users/", body)).data;

export const updateUser = async (id: number, body: AdminUserInput) =>
  (await api.patch<AdminUser>(`/users/${id}/`, body)).data;

export const deactivateUser = async (id: number) => {
  await api.delete(`/users/${id}/`);
};

export const resetPassword = async (id: number) =>
  (await api.post<{ reset_link: string }>(`/users/${id}/reset-password/`)).data.reset_link;

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

export type ContactMessage = {
  id: number;
  name: string;
  email: string;
  message: string;
  created_at: string;
};

export const listContactMessages = async (q: Query) =>
  (await api.get<Paginated<ContactMessage>>("/contact/messages/", { params: cleanQuery(q) })).data;

export type MarketingStat = {
  id: number;
  order: number;
  value: string;
  suffix: string;
  description: string;
};

export type MarketingStatInput = Omit<MarketingStat, "id">;

export const listAllMarketingStats = async () =>
  (await api.get<MarketingStat[]>("/marketing-stats/")).data;

export const createMarketingStat = async (body: MarketingStatInput) =>
  (await api.post<MarketingStat>("/marketing-stats/", body)).data;

export const updateMarketingStat = async (id: number, body: Partial<MarketingStatInput>) =>
  (await api.patch<MarketingStat>(`/marketing-stats/${id}/`, body)).data;

export const deleteMarketingStat = async (id: number) => {
  await api.delete(`/marketing-stats/${id}/`);
};

export type SiteSettings = {
  registration_open: boolean;
  maintenance_mode: boolean;
  maintenance_message: string;
};

export const getSiteSettings = async () => (await api.get<SiteSettings>("/site-settings/")).data;

export const updateSiteSettings = async (body: Partial<SiteSettings>) =>
  (await api.patch<SiteSettings>("/site-settings/", body)).data;

export type CountRow = { label: string; count: number };

export type ReportsOverview = {
  generated_at: string;
  users_by_role: CountRow[];
  users_active: { active: number; inactive: number };
  courses_by_status: CountRow[];
  enrollments_by_status: CountRow[];
  top_courses_by_enrollment: { course: string; code: string; count: number }[];
  exam_pass_fail: { passed: number; failed: number; ungraded: number };
  coding_submissions_by_verdict: CountRow[];
  problems_by_difficulty: CountRow[];
  contact_messages_total: number;
};

export const getReportsOverview = async () =>
  (await api.get<ReportsOverview>("/reports/overview/")).data;
