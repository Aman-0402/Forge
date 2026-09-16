// Adapted from dsaclone/src/App.tsx's AppContent(): same header, mobile menu and
// footer, but rendering an <Outlet/> instead of owning its own <Routes>, since Forge's
// App.tsx already owns the router. Route paths /signup -> /register to match Forge's
// existing auth routes; everything else is unchanged from dsaclone.
import { useEffect, useRef, useState, type CSSProperties } from "react";
import { ArrowUpRight, Code2, Menu, X } from "lucide-react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { homeFor } from "../auth/guards";
import MaintenanceBanner from "../components/MaintenanceBanner";
import { useSiteSettings } from "../hooks/useSiteSettings";
import MarketingFooter from "./components/MarketingFooter";
import "./styles/marketing-tokens.css";
import "./styles/marketing-app.css";

const navItems = [
  { to: "/", label: "Home", end: true },
  { to: "/programs", label: "Programs" },
  { to: "/master-class", label: "Masterclass" },
  { to: "/how-we-work", label: "Our Method" },
  { to: "/techies", label: "Mentors" },
  { to: "/contact", label: "Contact" },
];

export default function MarketingLayout() {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isScrolled, setIsScrolled] = useState(false);
  const location = useLocation();
  const { user } = useAuth();
  const settings = useSiteSettings();
  const bannerRef = useRef<HTMLDivElement>(null);
  const [bannerOffset, setBannerOffset] = useState(0);

  useEffect(() => {
    setBannerOffset(settings?.maintenance_mode ? (bannerRef.current?.offsetHeight ?? 0) : 0);
  }, [settings?.maintenance_mode, settings?.maintenance_message]);

  useEffect(() => {
    const updateHeaderState = () => setIsScrolled(window.scrollY > 20);
    updateHeaderState();
    window.addEventListener("scroll", updateHeaderState, { passive: true });
    return () => window.removeEventListener("scroll", updateHeaderState);
  }, []);

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: "instant" });
  }, [location.pathname]);

  useEffect(() => {
    document.body.style.overflow = isMobileMenuOpen ? "hidden" : "";
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setIsMobileMenuOpen(false);
    };
    if (isMobileMenuOpen) document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.body.style.overflow = "";
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [isMobileMenuOpen]);

  return (
    <div
      className="marketing-site"
      style={{ "--mkt-banner-offset": `${bannerOffset}px` } as CSSProperties}
    >
      <div className="app-container">
        {/* Outside .main-content on purpose: that container has padding-top reserved
            for the fixed header, so anything inside it renders below the header, not
            above it. This needs to sit at the true top of the page. */}
        <div ref={bannerRef}>
          <MaintenanceBanner settings={settings} />
        </div>
        <main className="main-content">
          <header className={`header ${isScrolled ? "header-scrolled" : ""}`}>
            <div className="header-inner">
              <Link to="/" className="logo" aria-label="DSA Forge home">
                <span className="logo-mark">
                  <Code2 size={19} />
                </span>
                <span>
                  DSA <b>Forge</b>
                </span>
              </Link>

              <nav className="top-nav desktop-nav" aria-label="Primary">
                {navItems.map((item) => (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    end={item.end}
                    className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}
                  >
                    {item.label}
                  </NavLink>
                ))}
              </nav>

              <div className="header-actions">
                {user ? (
                  <Link to={homeFor(user.role)} className="btn btn-primary desktop-nav-action">
                    Go to dashboard
                  </Link>
                ) : (
                  <>
                    <Link to="/login" className="btn btn-outline desktop-nav-action">
                      Log in
                    </Link>
                    <Link to="/register" className="btn btn-primary desktop-nav-action">
                      Join free
                    </Link>
                  </>
                )}
                <button
                  className={`menu-toggle ${isMobileMenuOpen ? "is-open" : ""}`}
                  onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
                  aria-label={isMobileMenuOpen ? "Close navigation menu" : "Open navigation menu"}
                  aria-expanded={isMobileMenuOpen}
                  aria-controls="site-menu"
                >
                  {isMobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
                </button>
              </div>
            </div>
          </header>

          {isMobileMenuOpen && (
            <div className="site-menu-overlay" onClick={() => setIsMobileMenuOpen(false)}>
              <aside
                id="site-menu"
                className="site-menu-panel"
                role="dialog"
                aria-modal="true"
                aria-label="Site navigation"
                onClick={(event) => event.stopPropagation()}
              >
                <div className="site-menu-heading">
                  <span>Navigation</span>
                  <small>DSA Forge</small>
                </div>
                <nav className="site-menu-nav">
                  {navItems.map((item, index) => (
                    <NavLink
                      key={item.to}
                      to={item.to}
                      end={item.end}
                      className={({ isActive }) => `site-menu-link ${isActive ? "active" : ""}`}
                      onClick={() => setIsMobileMenuOpen(false)}
                    >
                      <span>0{index + 1}</span>
                      <strong>{item.label}</strong>
                      <ArrowUpRight size={20} />
                    </NavLink>
                  ))}
                </nav>
                <div className="site-menu-actions">
                  {user ? (
                    <Link
                      to={homeFor(user.role)}
                      className="btn btn-primary"
                      onClick={() => setIsMobileMenuOpen(false)}
                    >
                      Go to dashboard <ArrowUpRight size={16} />
                    </Link>
                  ) : (
                    <>
                      <Link to="/login" className="btn btn-outline" onClick={() => setIsMobileMenuOpen(false)}>
                        Log in
                      </Link>
                      <Link
                        to="/register"
                        className="btn btn-primary"
                        onClick={() => setIsMobileMenuOpen(false)}
                      >
                        Join free <ArrowUpRight size={16} />
                      </Link>
                    </>
                  )}
                </div>
                <p className="site-menu-note">Learn deeply. Build confidently.</p>
              </aside>
            </div>
          )}

          <div className="page-container">
            <Outlet />
          </div>
          <MarketingFooter />
        </main>
      </div>
    </div>
  );
}
