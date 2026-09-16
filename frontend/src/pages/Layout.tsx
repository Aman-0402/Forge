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
  const [menuOpen, setMenuOpen] = useState(false);

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

  const roleLabel = { admin: "Administrator", faculty: "Faculty", student: "Student" }[user.role];

  return (
    <div className="shell">
      <aside
        className={menuOpen ? "sidebar open" : "sidebar"}
        aria-label="Main navigation"
        onClick={(e) => {
          if ((e.target as HTMLElement).closest("a")) setMenuOpen(false);
        }}
      >
        <NavLink to={homeFor(user.role)} className="brand">
          <span className="brand-mark">FORGE</span>
          <span className="brand-sub">LMS</span>
        </NavLink>

        <NavLink to={homeFor(user.role)} end>
          Home
        </NavLink>
        <NavLink to="/courses">{user.role === "student" ? "Course catalog" : "Courses"}</NavLink>
        {user.role === "student" && <NavLink to="/my-learning">My learning</NavLink>}
        <NavLink to="/exams">Exams</NavLink>
        {user.role === "student" && <NavLink to="/my-results">My results</NavLink>}
        {user.role !== "student" && <NavLink to="/question-banks">Question banks</NavLink>}
        <NavLink to="/announcements">Announcements</NavLink>
        <NavLink to="/notifications">
          Notifications
          {unread > 0 && <span className="badge">{unread}</span>}
        </NavLink>

        {user.role === "admin" && (
          <>
            <div className="nav-group">Administration</div>
            <NavLink to="/admin/approvals">Course approvals</NavLink>
            <NavLink to="/admin/users">Users</NavLink>
            <NavLink to="/admin/departments">Departments</NavLink>
            <NavLink to="/admin/categories">Categories</NavLink>
            <NavLink to="/admin/audit-logs">Audit log</NavLink>
          </>
        )}

        <div className="sidebar-foot">
          <div className="who">
            <strong>{`${user.first_name} ${user.last_name}`.trim() || user.email}</strong>
            <span>{roleLabel}</span>
          </div>
          <NavLink to="/me">Profile</NavLink>
          <NavLink to="/change-password">Change password</NavLink>
          <button
            className="secondary small"
            onClick={async () => {
              await logout();
              navigate("/login", { replace: true });
            }}
          >
            Sign out
          </button>
        </div>
      </aside>

      <div className="main">
        <div className="mobile-bar">
          <button className="secondary small" onClick={() => setMenuOpen((o) => !o)}>
            Menu
          </button>
          <span className="brand-mark">FORGE</span>
        </div>
        <main className="page">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
