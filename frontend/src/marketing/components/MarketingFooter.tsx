import { Link, useLocation } from 'react-router-dom';
import { ArrowUpRight, Code2, Mail } from 'lucide-react';

export default function Footer() {
  const location = useLocation();
  const isAuthPage = location.pathname === '/login' || location.pathname === '/register';

  if (isAuthPage) return null;

  return (
    <footer className="footer-container">
      <div className="footer-inner">
        <div className="footer-grid">
          <div className="footer-col-main">
            <Link to="/" className="footer-brand"><span><Code2 size={20} /></span> DSA <b>Forge</b></Link>
            <p>Structured learning, deliberate practice, and human mentorship for ambitious developers.</p>
            <a className="footer-email" href="mailto:support@aidsaforge.com"><Mail size={15} /> support@aidsaforge.com</a>
          </div>
          <div className="footer-column"><h3>Explore</h3><div>
            {[{ name:'Programs',path:'/programs' },{ name:'Masterclasses',path:'/master-class' },{ name:'Our method',path:'/how-we-work' },{ name:'Mentors',path:'/techies' }].map((item) => <Link key={item.name} to={item.path}>{item.name}</Link>)}
          </div></div>
          <div className="footer-column"><h3>Get started</h3><div>
            {[{ name:'Create account',path:'/register' },{ name:'Log in',path:'/login' },{ name:'Talk to us',path:'/contact' }].map((item) => <Link key={item.name} to={item.path}>{item.name}</Link>)}
          </div></div>
          <div className="footer-callout"><span>Ready to build momentum?</span><Link to="/register">Join DSA Forge <ArrowUpRight size={16} /></Link></div>
        </div>
        <div className="footer-bottom-bar">
          <p>© {new Date().getFullYear()} DSA Forge. Built for better technical careers.</p>
          <span>Learn deeply. Build confidently.</span>
        </div>
      </div>
    </footer>
  );
}
