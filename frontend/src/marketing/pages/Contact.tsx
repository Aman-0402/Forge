import { motion } from 'framer-motion';

const fadeUp = {
  hidden: { opacity: 0, y: 30 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.6, ease: "easeOut" as const } }
};

export default function Contact() {
  return (
    <motion.section
      initial="hidden"
      animate="visible"
      variants={fadeUp}
      style={{ maxWidth: '600px', margin: '40px auto 120px' }}
    >
      <div className="glass-panel" style={{ padding: '40px', borderRadius: '16px' }}>
        <h2 className="section-title" style={{ textAlign: 'center', marginBottom: '8px' }}>Contact Us</h2>
        <p className="section-subtitle" style={{ textAlign: 'center' }}>Have questions? We'd love to hear from you.</p>
        
        <form style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <label style={{ color: 'var(--text-secondary)', fontSize: '14px', fontWeight: 500 }}>Name</label>
            <input 
              type="text" 
              placeholder="Your Name" 
              style={{ padding: '12px 16px', borderRadius: '8px', border: '1px solid rgba(255, 255, 255, 0.1)', background: 'rgba(255, 255, 255, 0.05)', color: 'var(--text-primary)', outline: 'none' }} 
            />
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <label style={{ color: 'var(--text-secondary)', fontSize: '14px', fontWeight: 500 }}>Email</label>
            <input 
              type="email" 
              placeholder="your@email.com" 
              style={{ padding: '12px 16px', borderRadius: '8px', border: '1px solid rgba(255, 255, 255, 0.1)', background: 'rgba(255, 255, 255, 0.05)', color: 'var(--text-primary)', outline: 'none' }} 
            />
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <label style={{ color: 'var(--text-secondary)', fontSize: '14px', fontWeight: 500 }}>Message</label>
            <textarea 
              rows={5}
              placeholder="How can we help you?" 
              style={{ padding: '12px 16px', borderRadius: '8px', border: '1px solid rgba(255, 255, 255, 0.1)', background: 'rgba(255, 255, 255, 0.05)', color: 'var(--text-primary)', outline: 'none', resize: 'vertical' }} 
            />
          </div>
          <button type="button" className="btn btn-primary" style={{ padding: '16px', marginTop: '8px' }}>
            Send Message
          </button>
        </form>
      </div>
    </motion.section>
  );
}
