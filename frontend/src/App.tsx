import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import { RequireAuth, RequireRole, homeFor } from "./auth/guards";
import Layout from "./pages/Layout";
import LoginPage from "./pages/LoginPage";
import MePage from "./pages/MePage";
import RegisterPage from "./pages/RegisterPage";
import RoleHome from "./pages/RoleHome";

function RootRedirect() {
  const { user, loading } = useAuth();
  if (loading) return <p>Loading…</p>;
  return <Navigate to={user ? homeFor(user.role) : "/login"} replace />;
}

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
