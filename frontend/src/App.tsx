import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import { RequireAuth, RequireRole, homeFor } from "./auth/guards";
import AnnouncementsPage from "./pages/AnnouncementsPage";
import ChangePasswordPage from "./pages/ChangePasswordPage";
import Layout from "./pages/Layout";
import LoginPage from "./pages/LoginPage";
import MePage from "./pages/MePage";
import NotificationsPage from "./pages/NotificationsPage";
import RegisterPage from "./pages/RegisterPage";
import RoleHome from "./pages/RoleHome";
import AuditLogPage from "./pages/admin/AuditLogPage";
import DepartmentsPage from "./pages/admin/DepartmentsPage";
import UsersPage from "./pages/admin/UsersPage";

function RootRedirect() {
  const { user, loading } = useAuth();
  if (loading) return <p>Loading…</p>;
  return <Navigate to={user ? homeFor(user.role) : "/login"} replace />;
}

const adminOnly = (element: React.ReactNode) => (
  <RequireRole roles={["admin"]}>{element}</RequireRole>
);

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<RootRedirect />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route
            element={
              <RequireAuth>
                <Layout />
              </RequireAuth>
            }
          >
            <Route path="/me" element={<MePage />} />
            <Route path="/change-password" element={<ChangePasswordPage />} />
            <Route path="/notifications" element={<NotificationsPage />} />
            <Route path="/announcements" element={<AnnouncementsPage />} />
            <Route path="/announcements/:id" element={<AnnouncementsPage />} />
            <Route path="/admin/users" element={adminOnly(<UsersPage />)} />
            <Route path="/admin/departments" element={adminOnly(<DepartmentsPage />)} />
            <Route path="/admin/audit-logs" element={adminOnly(<AuditLogPage />)} />
            {(["admin", "faculty", "student"] as const).map((role) => (
              <Route
                key={role}
                path={`/${role}`}
                element={
                  <RequireRole roles={[role]}>
                    <RoleHome role={role} />
                  </RequireRole>
                }
              />
            ))}
          </Route>
          <Route path="*" element={<p>404 — page not found.</p>} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
