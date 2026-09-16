import { Link, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { homeFor } from "../auth/guards";

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  if (!user) return null;

  return (
    <>
      <nav className="nav">
        <strong>Forge LMS</strong>
        <Link to={homeFor(user.role)}>Home</Link>
        <Link to="/me">Profile</Link>
        <span className="spacer" />
        <span>
          {user.email} ({user.role})
        </span>
        <button
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
