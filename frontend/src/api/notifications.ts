import { api } from "./client";
import { cleanQuery, type Paginated, type Query } from "./types";

export type Notification = {
  id: number;
  title: string;
  body: string;
  kind: string;
  link: string;
  is_read: boolean;
  read_at: string | null;
  created_at: string;
};

export type Audience = "all" | "faculty" | "students" | "department" | "course";

export type Announcement = {
  id: number;
  title: string;
  body: string;
  audience: Audience;
  department: number | null;
  department_code: string | null;
  course: number | null;
  course_title: string | null;
  author: number | null;
  author_name: string | null;
  published_at: string;
  expires_at: string | null;
  delivered_at: string | null;
  created_at: string;
  updated_at: string;
};

export type AnnouncementInput = {
  title: string;
  body: string;
  audience: Audience;
  department?: number | null;
  course?: number | null;
  published_at?: string;
  expires_at?: string | null;
};

export const listNotifications = async (q: Query) =>
  (await api.get<Paginated<Notification>>("/notifications/", { params: cleanQuery(q) })).data;

export const unreadCount = async () =>
  (await api.get<{ count: number }>("/notifications/unread-count/")).data.count;

export const markRead = async (id: number) => {
  await api.post(`/notifications/${id}/read/`);
};

export const markAllRead = async () =>
  (await api.post<{ updated: number }>("/notifications/read-all/")).data.updated;

export const listAnnouncements = async (q: Query) =>
  (await api.get<Paginated<Announcement>>("/announcements/", { params: cleanQuery(q) })).data;

export const createAnnouncement = async (body: AnnouncementInput) =>
  (await api.post<Announcement>("/announcements/", body)).data;

export const deleteAnnouncement = async (id: number) => {
  await api.delete(`/announcements/${id}/`);
};

