import { useEffect } from 'react';
import { motion } from 'framer-motion';
import { Rocket } from 'lucide-react';

const LinkedinIcon = ({ size = 18 }: { size?: number }) => (
  <svg xmlns="http://www.w3.org/2000/svg" width={size} height={size} viewBox="0 0 24 24" fill="currentColor">
    <path d="M19 0h-14c-2.761 0-5 2.239-5 5v14c0 2.761 2.239 5 5 5h14c2.762 0 5-2.239 5-5v-14c0-2.761-2.238-5-5-5zm-11 19h-3v-11h3v11zm-1.5-12.268c-.966 0-1.75-.79-1.75-1.764s.784-1.764 1.75-1.764 1.75.79 1.75 1.764-.783 1.764-1.75 1.764zm13.5 12.268h-3v-5.604c0-3.368-4-3.113-4 0v5.604h-3v-11h3v1.765c1.396-2.586 7-2.777 7 2.476v6.759z"/>
  </svg>
);

const GithubIcon = ({ size = 18 }: { size?: number }) => (
  <svg xmlns="http://www.w3.org/2000/svg" width={size} height={size} viewBox="0 0 24 24" fill="currentColor">
    <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
  </svg>
);
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
    name: 'Ayush Raj',
    role: 'Computer Science Engineering',
    image: ayushImg,
    quote: "I believe every student deserves access to quality DSA education. With AI, we're making personalized mentorship scalable and affordable for everyone.",
    skills: [
      { name: 'AI Visionary' },
      { name: 'AI/ML Specialist' },
      { name: 'Full Stack Development' }
    ],
    linkedin: 'https://www.linkedin.com/in/ayush-raj-478294323/',
    github: 'https://github.com/ayushraj09-ai'
  },
  {
    name: 'Ishan Verma',
    role: 'Computer Science Engineering',
    image: ishanImg,
    quote: "AI isn't replacing teachers; it's empowering them. Our platform combines human expertise with AI to create the ultimate learning experience for DSA mastery.",
    skills: [
      { name: 'Full Stack Development' },
      { name: 'DSA Expert' }
    ],
    linkedin: 'https://www.linkedin.com/in/ishanverma1104/',
    github: 'https://github.com/ishan1104'
  },
  {
    name: 'Love Kumar',
    role: 'Computer Science Engineering',
    image: loveImg,
    quote: "Technology should serve education, not complicate it. We're building an AI-powered platform that adapts to each student's unique learning pace and style.",
    skills: [
      { name: 'Full Stack Architect' },
      { name: 'AI/ML Specialist' }
    ],
    linkedin: 'https://www.linkedin.com/in/love-kumar-619962387/',
    github: 'https://github.com/love371'
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
                  alt={techie.name}
                  loading="lazy"
                  decoding="async"
                  style={{
                    width: '100%', height: '100%', objectFit: 'cover', objectPosition: 'center top',
                    borderRadius: '50%', background: 'var(--accent-primary)',
                    boxShadow: 'inset 0 0 20px rgba(0,0,0,0.5)'
                  }} 
                />
              </div>

              {/* Name and Role */}
              <h2 style={{ fontSize: '18px', fontWeight: 700, marginBottom: '4px', color: '#fff' }}>
                {techie.name}
              </h2>
              <p style={{ color: 'var(--accent-primary)', fontSize: '12px', fontWeight: 500, marginBottom: '16px' }}>
                {techie.role}
              </p>

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

              {/* Social Links */}
              <div style={{ display: 'flex', gap: '12px' }}>
                <a href={techie.linkedin} style={{
                  width: '36px', height: '36px', borderRadius: '50%',
                  background: 'rgba(255, 255, 255, 0.05)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  color: '#fff', transition: 'all 0.2s ease', border: '1px solid rgba(255, 255, 255, 0.1)'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = 'var(--accent-primary)';
                  e.currentTarget.style.color = '#000';
                  e.currentTarget.style.transform = 'scale(1.1)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = 'rgba(255, 255, 255, 0.05)';
                  e.currentTarget.style.color = '#fff';
                  e.currentTarget.style.transform = 'scale(1)';
                }}
                >
                  <LinkedinIcon size={16} />
                </a>
                <a href={techie.github} style={{
                  width: '36px', height: '36px', borderRadius: '50%',
                  background: 'rgba(255, 255, 255, 0.05)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  color: '#fff', transition: 'all 0.2s ease', border: '1px solid rgba(255, 255, 255, 0.1)'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = 'var(--accent-primary)';
                  e.currentTarget.style.color = '#000';
                  e.currentTarget.style.transform = 'scale(1.1)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = 'rgba(255, 255, 255, 0.05)';
                  e.currentTarget.style.color = '#fff';
                  e.currentTarget.style.transform = 'scale(1)';
                }}
                >
                  <GithubIcon size={16} />
                </a>
              </div>
            </motion.div>
          ))}
        </motion.div>
      </motion.section>
      
    </>
  );
}
