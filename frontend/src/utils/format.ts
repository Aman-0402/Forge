export function formatDate(value: string | null | undefined): string {
  return value ? new Date(value).toLocaleString() : "—";
}

export function fullName(u: { first_name: string; last_name: string; email: string }): string {
  return `${u.first_name} ${u.last_name}`.trim() || u.email;
}
