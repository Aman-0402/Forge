import { motion } from 'framer-motion';

const fadeUp = {
  hidden: { opacity: 0, y: 30 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.6, ease: "easeOut" as const } }
};

export default function HowWeWork() {
  return (
    <motion.section
      initial="hidden"
      animate="visible"
      variants={fadeUp}
      style={{ padding: '60px 0', marginTop: '40px', marginBottom: '80px', position: 'relative' }}
    >
      <div style={{ textAlign: 'center', marginBottom: '64px' }}>
        <h2 className="section-title">How We Work</h2>
        <p className="section-subtitle" style={{ marginBottom: 0 }}>A proven path from learning to landing your dream job.</p>
      </div>
      
      <div style={{ position: 'relative', display: 'flex', flexDirection: 'column', gap: '48px', maxWidth: '800px', margin: '0 auto' }}>
        {/* Vertical line */}
        <div style={{ position: 'absolute', left: '24px', top: '24px', bottom: '24px', width: '2px', background: 'rgba(255, 255, 255, 0.1)', zIndex: 0 }}></div>
        
        {/* Item 1 */}
        <div style={{ position: 'relative', display: 'flex', gap: '40px', zIndex: 1 }}>
          <div style={{ width: '50px', height: '50px', borderRadius: '50%', background: 'var(--accent-primary)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#000', fontWeight: '900', fontSize: '20px', flexShrink: 0, boxShadow: '0 0 20px rgba(250, 204, 21, 0.4)' }}>
            1
          </div>
          <div className="premium-box" style={{ flex: 1, padding: '32px' }}>
            <h3 style={{ fontSize: '24px', marginBottom: '12px', color: 'var(--text-primary)', fontWeight: 700 }}>Learn from Experts</h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: '16px', lineHeight: 1.6 }}>Master core concepts in DSA and System Design with structured roadmaps curated by top engineers.</p>
          </div>
        </div>

        {/* Item 2 */}
        <div style={{ position: 'relative', display: 'flex', gap: '40px', zIndex: 1 }}>
          <div style={{ width: '50px', height: '50px', borderRadius: '50%', background: 'rgba(20, 20, 20, 0.8)', border: '2px solid var(--accent-primary)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--accent-primary)', fontWeight: '900', fontSize: '20px', flexShrink: 0, backdropFilter: 'blur(10px)' }}>
            2
          </div>
          <div className="premium-box" style={{ flex: 1, padding: '32px' }}>
            <h3 style={{ fontSize: '24px', marginBottom: '12px', color: 'var(--text-primary)', fontWeight: 700 }}>Solve with AI</h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: '16px', lineHeight: 1.6 }}>Leverage our AI-powered coding assistant to unblock yourself immediately when you get stuck.</p>
          </div>
        </div>

        {/* Item 3 */}
        <div style={{ position: 'relative', display: 'flex', gap: '40px', zIndex: 1 }}>
          <div style={{ width: '50px', height: '50px', borderRadius: '50%', background: 'rgba(20, 20, 20, 0.8)', border: '2px solid var(--accent-primary)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--accent-primary)', fontWeight: '900', fontSize: '20px', flexShrink: 0, backdropFilter: 'blur(10px)' }}>
            3
          </div>
          <div className="premium-box" style={{ flex: 1, padding: '32px' }}>
            <h3 style={{ fontSize: '24px', marginBottom: '12px', color: 'var(--text-primary)', fontWeight: 700 }}>Land the Job</h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: '16px', lineHeight: 1.6 }}>Get 1:1 mentorship, resume reviews, and mock interviews to confidently secure your tech role.</p>
          </div>
        </div>
      </div>
    </motion.section>
  );
}
