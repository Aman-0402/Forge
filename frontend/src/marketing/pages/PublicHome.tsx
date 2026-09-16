// Not from dsaclone. "/" needs to behave differently for the two audiences Forge
// actually has: an anonymous visitor sees the marketing Home page (below); someone
// already signed in is sent straight to their dashboard instead of the pitch page.
import { Navigate } from "react-router-dom";
import { useAuth } from "../../auth/AuthContext";
import { homeFor } from "../../auth/guards";
import Home from "./Home";

export default function PublicHome() {
  const { user, loading } = useAuth();
  if (loading) return null;
  if (user) return <Navigate to={homeFor(user.role)} replace />;
  return <Home />;
}
