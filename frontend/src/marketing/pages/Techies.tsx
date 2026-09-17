import { useEffect } from 'react';
import { motion } from 'framer-motion';
import { Rocket } from 'lucide-react';
import SoftAurora from '../components/SoftAurora/SoftAurora';

// Assets
import ayushImg from '../assets/teachers/ceo.png';
import ishanImg from '../assets/teachers/co-founder.png';
import loveImg from '../assets/teachers/2ndco.png';

const fadeUp = {
  hidden: { opacity: 0, y: 30 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.6, ease: "easeOut" as const } }
};

const staggerContainer = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.2 }
  }
};

const techies = [
  {
    title: 'Founder & AI Lead',
    image: ayushImg,
    quote: "I believe every student deserves access to quality DSA education. With AI, we're making personalized mentorship scalable and affordable for everyone.",
    skills: [
      { name: 'AI Visionary' },
      { name: 'AI/ML Specialist' },
      { name: 'Full Stack Development' }
    ]
  },
  {
    title: 'Co-Founder & Platform Engineer',
    image: ishanImg,
    quote: "AI isn't replacing teachers; it's empowering them. Our platform combines human expertise with AI to create the ultimate learning experience for DSA mastery.",
    skills: [
      { name: 'Full Stack Development' },
      { name: 'DSA Expert' }
    ]
  },
  {
    title: 'Co-Founder & Full-Stack Architect',
    image: loveImg,
    quote: "Technology should serve education, not complicate it. We're building an AI-powered platform that adapts to each student's unique learning pace and style.",
    skills: [
      { name: 'Full Stack Architect' },
      { name: 'AI/ML Specialist' }
    ]
  }
];

export default function Techies() {
  useEffect(() => {
    window.scrollTo(0, 0);
  }, []);

  return (
    <>
      <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, zIndex: -2 }}>
        <SoftAurora
          speed={0.6}
          scale={1.5}
          brightness={1}
          color1="#f7f7f7"
          color2="#facc15"
          noiseFrequency={2.5}
          noiseAmplitude={1}
          bandHeight={0.5}
          bandSpread={1}
          octaveDecay={0.1}
          layerOffset={0}
          colorSpeed={1}
          enableMouseInteraction
          mouseInfluence={0.25}
        />
      </div>
      <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'radial-gradient(circle at center, rgba(10,10,10,0.1) 0%, rgba(10,10,10,0.85) 100%)', zIndex: -1 }}></div>

      <motion.section 
        initial="hidden"
        animate="visible"
        variants={staggerContainer}
        style={{
          minHeight: '100vh',
          padding: '70px 20px 60px',
          maxWidth: '1500px',
          margin: '0 auto',
          textAlign: 'center'
        }}
      >
        <motion.div variants={fadeUp} style={{ marginBottom: '32px' }}>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', color: 'var(--accent-primary)', marginBottom: '12px', fontSize: '14px', fontWeight: 600 }}>
            <Rocket size={14} /> Meet the Builders
          </div>
          <h1 style={{ fontSize: '34px', fontWeight: 700, marginBottom: '12px', lineHeight: 1.1 }}>
            The Minds Behind <span style={{ color: 'var(--accent-primary)' }}>DSA-Forge</span>
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '14px', maxWidth: '500px', margin: '0 auto' }}>
            We're a team of passionate engineers and educators on a mission to democratize premium tech education through artificial intelligence.
          </p>
        </motion.div>

        <motion.div variants={staggerContainer} className="techies-grid">
          {techies.map((techie, idx) => (
            <motion.div key={idx} variants={fadeUp} className="glass-panel" style={{
              borderRadius: '20px',
              padding: '20px 16px',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              position: 'relative',
              overflow: 'hidden',
              background: 'rgba(20, 20, 20, 0.8)',
              border: '1px solid rgba(255, 255, 255, 0.05)',
              transition: 'transform 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275), box-shadow 0.4s ease'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = 'translateY(-10px)';
              e.currentTarget.style.boxShadow = '0 20px 40px rgba(250, 204, 21, 0.15)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = 'translateY(0)';
              e.currentTarget.style.boxShadow = 'none';
            }}
            >
              {/* Profile Image with Glowing Ring */}
              <div style={{ 
                position: 'relative', width: '95px', height: '95px', marginBottom: '12px',
                borderRadius: '50%', padding: '4px',
                background: 'rgba(250, 204, 21, 0.2)',
                boxShadow: '0 0 30px rgba(250, 204, 21, 0.2)'
              }}>
                <img
                  src={techie.image}
                  alt={techie.title}
                  loading="lazy"
                  decoding="async"
                  style={{
                    width: '100%', height: '100%', objectFit: 'cover', objectPosition: 'center top',
                    borderRadius: '50%', background: 'var(--accent-primary)',
                    boxShadow: 'inset 0 0 20px rgba(0,0,0,0.5)'
                  }} 
                />
              </div>

              {/* Title */}
              <h2 style={{ fontSize: '16px', fontWeight: 700, marginBottom: '16px', color: 'var(--accent-primary)' }}>
                {techie.title}
              </h2>

              {/* Quote */}
              <div style={{ 
                position: 'relative',
                padding: '0 16px',
                marginBottom: '24px',
                flex: 1,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                width: '100%'
              }}>
                {/* Decorative quote marks */}
                <div style={{ position: 'absolute', top: '-10px', left: '0px', color: 'rgba(250, 204, 21, 0.2)', fontSize: '40px', fontFamily: 'serif', lineHeight: 1 }}>"</div>
                <div style={{ position: 'absolute', bottom: '-20px', right: '0px', color: 'rgba(250, 204, 21, 0.2)', fontSize: '40px', fontFamily: 'serif', lineHeight: 1 }}>"</div>
                <p style={{ fontStyle: 'italic', color: 'var(--text-secondary)', fontSize: '13px', lineHeight: 1.7, margin: 0, position: 'relative', zIndex: 1, textAlign: 'center' }}>
                  {techie.quote}
                </p>
              </div>

              {/* Skills */}
              <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'center', alignItems: 'center', gap: '16px', marginBottom: '28px', width: '100%' }}>
                {techie.skills.map((skill, skillIdx) => (
                  <div key={skillIdx} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <div style={{ width: '5px', height: '5px', borderRadius: '50%', background: 'var(--accent-primary)' }} />
                    <span style={{ color: 'rgba(255,255,255,0.9)', fontSize: '13px', fontWeight: 500 }}>{skill.name}</span>
                  </div>
                ))}
              </div>

            </motion.div>
          ))}
        </motion.div>
      </motion.section>
      
    </>
  );
}
