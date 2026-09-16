import { motion } from 'framer-motion';
import { ArrowRight } from 'lucide-react';

const fadeUp = {
  hidden: { opacity: 0, y: 30 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.6, ease: "easeOut" as const } }
};

export default function MasterClass() {
  return (
    <>
      <motion.section
        className="hero"
        initial="hidden"
        animate="visible"
        variants={fadeUp}
      >
        <h1>Expert-Led Master Classes</h1>
        <p>Deep dive into specific topics with industry veterans. Each session is designed to give you practical, hands-on experience in just a few hours.</p>
      </motion.section>

      <motion.section
        className="offer-banner"
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true, margin: "-100px" }}
        variants={fadeUp}
        whileHover={{ scale: 1.02 }}
        transition={{ duration: 0.3 }}
        style={{ marginBottom: '120px' }}
      >
        <div className="offer-badge">Limited Time Offer</div>
        <div className="offer-content">
          <h3>Upcoming Master Class: Advanced System Design</h3>
          <p>Learn Scalability Patterns in Just 2 Hours!</p>
        </div>
        <div>
          <button className="btn btn-primary" style={{ padding: '16px 32px', fontSize: '18px' }}>
            Register for just ₹49 <ArrowRight size={20} />
          </button>
        </div>
      </motion.section>
    </>
  );
}
