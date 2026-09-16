import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import { Boxes, LayoutGrid, Diamond, Network, BookOpen, MoreVertical } from 'lucide-react';
import '../styles/marketing-programs.css';

const fadeUp = {
  hidden: { opacity: 0, y: 30 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.6, ease: "easeOut" as const } }
};

const staggerContainer = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.1 }
  }
};

export default function Programs() {
  return (
    <motion.section
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true, margin: "-100px" }}
      variants={staggerContainer}
      className="programs-page"
    >
      <motion.div variants={fadeUp} className="featured-section">
        <h2 className="section-title-small">Featured</h2>
        <div className="featured-grid">
          {[
            { title: 'DSA', icon: Boxes, color: '16, 185, 129' },
            { title: 'Low Level Design (LLD)', icon: LayoutGrid, color: '212, 185, 140' },
            { title: 'All Problems', icon: Diamond, color: '168, 85, 247' },
            { title: 'OOPS', icon: Network, color: '236, 72, 153' }
          ].map((item, i) => (
            <div key={i} className="glass-panel" style={{ 
              borderRadius: '24px', 
              padding: '24px 16px', 
              display: 'flex', 
              flexDirection: 'column', 
              alignItems: 'center',
              border: '1px solid rgba(255,255,255,0.05)',
              transition: 'transform 0.3s ease, border-color 0.3s ease, box-shadow 0.3s ease',
              cursor: 'pointer'
            }}
            onMouseOver={(e) => {
              e.currentTarget.style.transform = 'translateY(-5px)';
              e.currentTarget.style.borderColor = `rgba(${item.color}, 0.4)`;
              e.currentTarget.style.boxShadow = `0 10px 30px rgba(${item.color}, 0.1)`;
            }}
            onMouseOut={(e) => {
              e.currentTarget.style.transform = 'translateY(0)';
              e.currentTarget.style.borderColor = 'rgba(255,255,255,0.05)';
              e.currentTarget.style.boxShadow = 'none';
            }}
            >
              <div style={{ 
                width: '100%', 
                aspectRatio: '16/9', 
                background: `linear-gradient(135deg, rgba(${item.color}, 0.25) 0%, rgba(${item.color}, 0.05) 100%)`, 
                borderRadius: '16px',
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                marginBottom: '20px',
                border: `1px solid rgba(${item.color}, 0.2)`,
                backdropFilter: 'blur(10px)'
              }}>
                <item.icon size={36} color="#fff" />
              </div>
              <div style={{ fontWeight: 600, fontSize: '16px', color: '#fff', textAlign: 'center' }}>
                {item.title}
              </div>
            </div>
          ))}
        </div>
      </motion.div>

      <motion.div variants={fadeUp} className="course-section">
        <div className="course-section-header">
          <h2 className="section-title-small" style={{ marginBottom: 0 }}>Data Structures And Algorithms</h2>
          <BookOpen size={16} color="#9ca3af" />
        </div>
        
        <div className="dsa-course-grid">
          <div className="dsa-course-card teal">
            <div className="dsa-course-card-indicator"></div>
            <div className="course-header">
              <h3 className="course-title">DSA</h3>
              <button className="course-icon-btn"><MoreVertical size={16} /></button>
            </div>
            <p className="course-desc">Learn DSA Basics to Advanced</p>
            <Link to="/programs" className="course-btn">Start Learning</Link>
          </div>

          <div className="dsa-course-card teal">
            <div className="dsa-course-card-indicator"></div>
            <div className="course-header">
              <h3 className="course-title">All Problems</h3>
              <button className="course-icon-btn"><MoreVertical size={16} /></button>
            </div>
            <p className="course-desc">Premium + Company Specific Problems</p>
            <Link to="/programs" className="course-btn">Start Learning</Link>
          </div>

          <div className="dsa-course-card teal">
            <div className="dsa-course-card-indicator"></div>
            <div className="course-header">
              <h3 className="course-title">DSA (Concept Revision)</h3>
              <button className="course-icon-btn"><MoreVertical size={16} /></button>
            </div>
            <p className="course-desc">Learn It Pattern-wise</p>
            <Link to="/programs" className="course-btn">Start Learning</Link>
          </div>

          <div className="dsa-course-card teal">
            <div className="dsa-course-card-indicator"></div>
            <div className="course-header">
              <h3 className="course-title">DSA (Quick Revision)</h3>
              <button className="course-icon-btn"><MoreVertical size={16} /></button>
            </div>
            <p className="course-desc">For Last Week Revision</p>
            <Link to="/programs" className="course-btn">Start Learning</Link>
          </div>
        </div>
      </motion.div>

      <motion.div variants={fadeUp} className="course-section">
        <div className="course-section-header">
          <h2 className="section-title-small" style={{ marginBottom: 0 }}>Design</h2>
        </div>
        
        <div className="dsa-course-grid">
          <div className="dsa-course-card magenta">
            <div className="dsa-course-card-indicator"></div>
            <div className="course-header">
              <h3 className="course-title">OOPS</h3>
              <button className="course-icon-btn"><MoreVertical size={16} /></button>
            </div>
            <p className="course-desc">Learn OOPS Basics to Advanced</p>
            <Link to="/programs" className="course-btn">Start Learning</Link>
          </div>

          <div className="dsa-course-card magenta">
            <div className="dsa-course-card-indicator"></div>
            <div className="course-header">
              <h3 className="course-title">Low Level Design (LLD)</h3>
              <button className="course-icon-btn"><MoreVertical size={16} /></button>
            </div>
            <p className="course-desc">Learn Low Level Design (LLD) Basics to Advanced</p>
            <Link to="/programs" className="course-btn">Start Learning</Link>
          </div>
        </div>
      </motion.div>

    </motion.section>
  );
}
