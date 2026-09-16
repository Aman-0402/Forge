import { useEffect, useState } from "react";
import { Navigate, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { unreadCount } from "../api/notifications";
import { useAuth } from "../auth/AuthContext";
import { homeFor } from "../auth/guards";

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [unread, setUnread] = useState(0);

  useEffect(() => {
    const refresh = () =>
      unreadCount()
        .then(setUnread)
        .catch(() => setUnread(0));
    refresh();
    window.addEventListener("forge:notifications-changed", refresh);
    return () => window.removeEventListener("forge:notifications-changed", refresh);
  }, [location.pathname]);

  if (!user) return null;
  if (user.must_change_password && location.pathname !== "/change-password") {
    return <Navigate to="/change-password" replace />;
  }

  return (
    <>
      <nav className="nav">
        <strong>Forge LMS</strong>
        <NavLink to={homeFor(user.role)} end>
          Home
        </NavLink>
        {user.role === "admin" && (
          <>
            <NavLink to="/admin/users">Users</NavLink>
            <NavLink to="/admin/departments">Departments</NavLink>
            <NavLink to="/admin/audit-logs">Audit log</NavLink>
          </>
        )}
        <NavLink to="/announcements">Announcements</NavLink>
        <NavLink to="/notifications">
          Notifications{unread > 0 && <span className="badge">{unread}</span>}
        </NavLink>
        <span className="spacer" />
        <NavLink to="/me">
          {user.email} ({user.role})
        </NavLink>
        <NavLink to="/change-password">Password</NavLink>
        <button
          className="secondary"
          onClick={async () => {
            await logout();
            navigate("/login", { replace: true });
          }}
        >
          Logout
        </button>
      </nav>
      <main className="page">
        <Outlet />
      </main>
    </>
  );
}
