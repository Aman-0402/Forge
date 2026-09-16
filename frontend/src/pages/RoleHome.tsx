import type { Role } from "../api/auth";
import { useAuth } from "../auth/AuthContext";

const TITLES: Record<Role, string> = {
  admin: "Admin dashboard",
  faculty: "Faculty dashboard",
  student: "Student dashboard",
};

export default function RoleHome({ role }: { role: Role }) {
  const { user } = useAuth();
  return (
    <>
      <h1>{TITLES[role]}</h1>
      <p>Welcome, {user?.first_name || user?.email}. Modules arrive in later phases.</p>
    </>
  );
}
