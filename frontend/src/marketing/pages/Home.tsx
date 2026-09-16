import { useEffect, useRef, useState } from 'react';
import { motion, useInView, useScroll, useTransform } from 'framer-motion';
import {
  Award, ArrowRight, Binary, Braces, Check, ChevronRight, CirclePlay, Code2, Database,
  Layers3, MessageSquareCode, Network, Sparkles, Star, Target, Terminal, TrendingUp, Users, Zap,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import SoftAurora from '../components/SoftAurora/SoftAurora';
import neeteshImg from '../assets/mentors/Neetesh.png';
import himanshuImg from '../assets/mentors/Himanshu.png';
import jainLogo from '../assets/trusted/Jain-logo.png';
import kceLogo from '../assets/trusted/KCE-logo-color.png';
import lpuLogo from '../assets/trusted/lpulogo.png';
import skcetLogo from '../assets/trusted/skcet-logo.png';
import adaniLogo from '../assets/placement/Adani_logo_2012.svg.png';
import coindcxLogo from '../assets/placement/CoinDCX-Logo.png';
import deliveryLogo from '../assets/placement/delivery.png';
import transunionLogo from '../assets/placement/transunion.png';
import './Home.css';

const reveal = {
  hidden: { opacity: 0, y: 28 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.65, ease: 'easeOut' as const } },
};

const stagger = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.1 } },
};

const programs = [
  { icon: Binary, code: '01', title: 'Data Structures & Algorithms', copy: 'Build pattern recognition through curated problems, visual explanations, and mentor-led reviews.', meta: '12 learning tracks', tone: 'mint' },
  { icon: Layers3, code: '02', title: 'Low Level Design', copy: 'Turn requirements into clean, extensible systems using design patterns and real product scenarios.', meta: '8 design projects', tone: 'amber' },
  { icon: Braces, code: '03', title: 'Object-Oriented Programming', copy: 'Learn the principles behind maintainable code, then apply them in interview-ready exercises.', meta: '40+ guided lessons', tone: 'violet' },
  { icon: Network, code: '04', title: 'System Design', copy: 'Reason about scale, trade-offs, data flow, and architecture with working industry examples.', meta: '6 capstone systems', tone: 'coral' },
];

const roadmap = [
  { step: '01', icon: Target, title: 'Find your baseline', copy: 'A focused assessment maps your strengths, gaps, and target role.' },
  { step: '02', icon: Code2, title: 'Build with intent', copy: 'Follow a tailored path of concepts, practice, and live feedback.' },
  { step: '03', icon: MessageSquareCode, title: 'Rehearse the real thing', copy: 'Mock interviews sharpen how you think, explain, and recover.' },
  { step: '04', icon: Zap, title: 'Enter with confidence', copy: 'Refine your profile and approach interviews with a repeatable system.' },
];

const partnerLogos = [
  { src: jainLogo, alt: 'Jain University' }, { src: kceLogo, alt: 'KCE' },
  { src: lpuLogo, alt: 'Lovely Professional University' }, { src: skcetLogo, alt: 'SKCET' },
  { src: adaniLogo, alt: 'Adani' }, { src: coindcxLogo, alt: 'CoinDCX' },
  { src: deliveryLogo, alt: 'Delhivery' }, { src: transunionLogo, alt: 'TransUnion' },
];

function Counter({ end, suffix = '' }: { end: number; suffix?: string }) {
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true, margin: '-60px' });
  const [value, setValue] = useState(0);

  useEffect(() => {
    if (!inView) return;
    const startedAt = performance.now();
    const duration = 1400;
    let frame = 0;
    const update = (now: number) => {
      const progress = Math.min((now - startedAt) / duration, 1);
      setValue(Math.round(end * (1 - Math.pow(1 - progress, 3))));
      if (progress < 1) frame = requestAnimationFrame(update);
    };
    frame = requestAnimationFrame(update);
    return () => cancelAnimationFrame(frame);
  }, [end, inView]);

  return <span ref={ref}>{value.toLocaleString('en-IN')}{suffix}</span>;
}

function LearningConsole() {
  return (
    <motion.div className="learning-console-wrap" initial={{ opacity: 0, x: 34, rotateY: -8 }} animate={{ opacity: 1, x: 0, rotateY: -4 }} transition={{ duration: 0.9, delay: 0.2, ease: 'easeOut' }}>
      <div className="console-orbit console-orbit-one" /><div className="console-orbit console-orbit-two" />
      <div className="learning-console">
        <div className="console-topbar">
          <div className="window-controls"><i /><i /><i /></div>
          <div className="console-file"><Code2 size={14} /> learning_path.ts</div>
          <span className="console-live"><i /> LIVE</span>
        </div>
        <div className="console-body">
          <div className="console-rail" aria-hidden="true"><Terminal size={17} /><Database size={17} /><Network size={17} /></div>
          <div className="code-window" aria-label="Personalized learning path preview">
            <div className="code-line"><span>01</span><code><b>const</b> goal = <em>'product engineer'</em>;</code></div>
            <div className="code-line"><span>02</span><code><b>const</b> roadmap = forge({`{`}</code></div>
            <div className="code-line active"><span>03</span><code>&nbsp;&nbsp;focus: [<em>'DSA'</em>, <em>'LLD'</em>],</code></div>
            <div className="code-line"><span>04</span><code>&nbsp;&nbsp;mentor: <em>'weekly'</em>,</code></div>
            <div className="code-line"><span>05</span><code>&nbsp;&nbsp;practice: <strong>true</strong></code></div>
            <div className="code-line"><span>06</span><code>{`}`});</code></div>
          </div>
        </div>
        <div className="console-progress">
          <div className="progress-copy"><span>Weekly momentum</span><strong>82%</strong></div>
          <div className="progress-track"><motion.i initial={{ scaleX: 0 }} animate={{ scaleX: 0.82 }} transition={{ duration: 1.2, delay: 0.8 }} /></div>
          <div className="console-metrics">
            <div><Check size={15} /><span><b>24</b> solved</span></div>
            <div><Zap size={15} /><span><b>7</b> day streak</span></div>
            <div><Users size={15} /><span><b>1:1</b> review</span></div>
          </div>
        </div>
      </div>
      <motion.div className="floating-chip chip-top" animate={{ y: [0, -8, 0] }} transition={{ duration: 4, repeat: Infinity }}><Sparkles size={16} /> AI hint unlocked</motion.div>
      <motion.div className="floating-chip chip-bottom" animate={{ y: [0, 8, 0] }} transition={{ duration: 4.5, repeat: Infinity }}><Check size={16} /> Pattern mastered</motion.div>
    </motion.div>
  );
}

const TYPING_LINES = ['Learn the logic.', 'Own the', 'interview.'];
const TYPING_SPEED_MS = 55;
const LINE_PAUSE_MS = 300;

function TypingHeadline() {
  const [displayed, setDisplayed] = useState(TYPING_LINES.map(() => ''));
  const [lineIndex, setLineIndex] = useState(0);
  const [charIndex, setCharIndex] = useState(0);
  const [done, setDone] = useState(false);

  useEffect(() => {
    if (done) return;
    const currentLine = TYPING_LINES[lineIndex];

    if (charIndex < currentLine.length) {
      const timeout = setTimeout(() => {
        setDisplayed((prev) => {
          const next = [...prev];
          next[lineIndex] = currentLine.slice(0, charIndex + 1);
          return next;
        });
        setCharIndex((c) => c + 1);
      }, TYPING_SPEED_MS);
      return () => clearTimeout(timeout);
    }

    if (lineIndex < TYPING_LINES.length - 1) {
      const timeout = setTimeout(() => {
        setLineIndex((l) => l + 1);
        setCharIndex(0);
      }, LINE_PAUSE_MS);
      return () => clearTimeout(timeout);
    }

    setDone(true);
  }, [charIndex, lineIndex, done]);

  return (
    <motion.h1 initial={{ opacity: 0, y: 22 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.7, delay: 0.08 }}>
      {displayed[0]}
      <br />
      <span>
        {displayed[1]}
        <br />
        {displayed[2]}
        <i className={`typing-cursor ${done ? 'is-done' : ''}`} aria-hidden="true" />
      </span>
    </motion.h1>
  );
}

export default function Home() {
  const heroRef = useRef<HTMLElement>(null);
  const { scrollYProgress } = useScroll({ target: heroRef, offset: ['start start', 'end start'] });
  const heroY = useTransform(scrollYProgress, [0, 1], [0, 110]);
  const heroOpacity = useTransform(scrollYProgress, [0, 0.85], [1, 0.2]);

  return (
    <div className="home-page">
      <div className="aurora-stage" aria-hidden="true">
        <SoftAurora speed={0.45} scale={1.7} brightness={0.9} color1="#22d3ee" color2="#facc15" noiseFrequency={2.2} noiseAmplitude={0.85} bandHeight={0.48} bandSpread={1.2} octaveDecay={0.15} layerOffset={0.35} colorSpeed={0.7} enableMouseInteraction mouseInfluence={0.16} />
      </div>

      <section className="home-hero" ref={heroRef}>
        <motion.div className="hero-copy" style={{ y: heroY, opacity: heroOpacity }}>
          <motion.div className="eyebrow" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}><span><Sparkles size={14} /> Your technical career, engineered</span></motion.div>
          <TypingHeadline />
          <motion.p initial={{ opacity: 0, y: 22 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.7, delay: 0.16 }}>A mentor-guided learning system for DSA, design, and technical interviews. Build real depth, practise with purpose, and walk into the room ready.</motion.p>
          <motion.div className="hero-actions" initial={{ opacity: 0, y: 22 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.7, delay: 0.24 }}>
            <Link to="/programs" className="btn btn-primary btn-large">Explore programs <ArrowRight size={18} /></Link>
            <Link to="/how-we-work" className="text-link"><CirclePlay size={20} /> See how it works</Link>
          </motion.div>
          <motion.div className="hero-proof" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.8, delay: 0.4 }}>
            <div className="proof-avatars"><img src={neeteshImg} alt="DSA Forge mentor Neetesh Parashar" /><img src={himanshuImg} alt="DSA Forge mentor Himanshu Sharma" /><span>5K+</span></div>
            <div><span className="proof-stars"><Star size={14} fill="currentColor" /><Star size={14} fill="currentColor" /><Star size={14} fill="currentColor" /><Star size={14} fill="currentColor" /><Star size={14} fill="currentColor" /></span><small>Learners guided by industry mentors</small></div>
          </motion.div>
        </motion.div>
        <LearningConsole />
      </section>

      <section className="logo-ribbon" aria-label="Institutions and placement partners">
        <p>Trusted across campuses and hiring teams</p>
        <div className="logo-track">{[...partnerLogos, ...partnerLogos].map((logo, index) => <img key={`${logo.alt}-${index}`} src={logo.src} alt={index < partnerLogos.length ? logo.alt : ''} aria-hidden={index >= partnerLogos.length} loading="lazy" decoding="async" />)}</div>
      </section>

      <motion.section id="programs" className="home-section programs-section" initial="hidden" whileInView="visible" viewport={{ once: true, margin: '-100px' }} variants={stagger}>
        <motion.div className="section-heading split-heading" variants={reveal}>
          <div><span className="section-kicker">The learning stack</span><h2>Master what interviews<br />actually measure.</h2></div>
          <div><p>From first principles to production thinking, every track connects concept, practice, and communication.</p><Link to="/programs" className="text-link">View all programs <ArrowRight size={17} /></Link></div>
        </motion.div>
        <div className="program-grid">{programs.map((program) => (
          <motion.article key={program.title} className={`program-card ${program.tone}`} variants={reveal} whileHover={{ y: -8 }}>
            <div className="program-card-head"><span>{program.code}</span><program.icon size={24} /></div><h3>{program.title}</h3><p>{program.copy}</p>
            <div className="program-meta"><span>{program.meta}</span><Link to="/programs" aria-label={`Explore ${program.title}`}><ArrowRight size={18} /></Link></div>
          </motion.article>
        ))}</div>
      </motion.section>

      <motion.section className="outcomes-band" initial="hidden" whileInView="visible" viewport={{ once: true, margin: '-80px' }} variants={stagger}>
        <motion.div className="outcome" variants={reveal} whileHover={{ y: -6 }}>
          <span className="outcome-icon"><TrendingUp size={26} /></span>
          <div><strong><Counter end={95} suffix="%" /></strong><span className="outcome-copy">learn more consistently with guided AI practice</span></div>
        </motion.div>
        <motion.div className="outcome" variants={reveal} whileHover={{ y: -6 }}>
          <span className="outcome-icon"><Users size={26} /></span>
          <div><strong><Counter end={5000} suffix="+" /></strong><span className="outcome-copy">learners found clarity through mentorship</span></div>
        </motion.div>
        <motion.div className="outcome" variants={reveal} whileHover={{ y: -6 }}>
          <span className="outcome-icon"><Award size={26} /></span>
          <div><strong><Counter end={85} suffix="%" /></strong><span className="outcome-copy">reported stronger interview confidence</span></div>
        </motion.div>
      </motion.section>

      <section className="home-section roadmap-section">
        <motion.div className="roadmap-intro" initial="hidden" whileInView="visible" viewport={{ once: true, margin: '-100px' }} variants={reveal}>
          <span className="section-kicker">Your route, not a playlist</span><h2>A clear path from "I'm stuck" to "I've got this."</h2>
          <p>DSA Forge combines structured learning, deliberate practice, and human feedback into one momentum-building loop.</p>
          <Link to="/how-we-work" className="btn btn-outline">Explore our method <ArrowRight size={17} /></Link>
        </motion.div>
        <motion.div className="roadmap-list" initial="hidden" whileInView="visible" viewport={{ once: true, margin: '-80px' }} variants={stagger}>
          {roadmap.map((item) => <motion.article key={item.step} className="roadmap-item" variants={reveal}><div className="roadmap-icon"><item.icon size={21} /></div><span>{item.step}</span><div><h3>{item.title}</h3><p>{item.copy}</p></div></motion.article>)}
        </motion.div>
      </section>

      <motion.section className="masterclass-feature" initial={{ opacity: 0, scale: 0.97 }} whileInView={{ opacity: 1, scale: 1 }} viewport={{ once: true, margin: '-100px' }} transition={{ duration: 0.7 }}>
        <div className="masterclass-copy"><span className="section-kicker">Live masterclass</span><h2>One focused evening.<br />One skill unlocked.</h2><p>Fast, practical sessions led by working experts. Ask questions live, practise the concept, and keep the recording.</p><div className="feature-checks"><span><Check size={16} /> 2-hour live session</span><span><Check size={16} /> Hands-on exercises</span><span><Check size={16} /> Lifetime recording</span></div><Link to="/master-class" className="btn btn-primary btn-large">Reserve a seat <ArrowRight size={18} /></Link></div>
        <div className="masterclass-ticket"><div className="ticket-top"><span>DSA FORGE / LIVE</span><Sparkles size={18} /></div><div className="ticket-main"><small>STARTING AT</small><strong><sup>₹</sup>49</strong><p>Core tech masterclass</p></div><div className="ticket-bottom"><span>50+ sessions</span><span>4.8 average rating</span></div></div>
      </motion.section>

      <section className="home-section mentor-section">
        <motion.div className="section-heading" initial="hidden" whileInView="visible" viewport={{ once: true }} variants={reveal}><span className="section-kicker">Learn beside experience</span><h2>Mentors who teach the thinking,<br />not just the answer.</h2></motion.div>
        <div className="mentor-showcase">{[
          { image: neeteshImg, name: 'Neetesh Parashar', role: 'Advanced DSA & AI Trainer', experience: '8+ years', focus: 'Algorithms & AI' },
          { image: himanshuImg, name: 'Himanshu Sharma', role: 'Full Stack & System Design Expert', experience: '7+ years', focus: 'Systems & Web' },
        ].map((mentor, index) => (
          <motion.article className="mentor-profile" key={mentor.name} initial={{ opacity: 0, y: 28 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.6, delay: index * 0.12 }}>
            <div className="mentor-photo"><img src={mentor.image} alt={mentor.name} loading="lazy" decoding="async" /><span><Star size={14} fill="currentColor" /> {index === 0 ? '4.8' : '4.9'}</span></div>
            <div className="mentor-copy"><small>MENTOR 0{index + 1}</small><h3>{mentor.name}</h3><p>{mentor.role}</p><div><span>{mentor.experience}</span><i /><span>{mentor.focus}</span></div></div><Link to="/techies" aria-label={`Meet ${mentor.name}`}><ChevronRight size={22} /></Link>
          </motion.article>
        ))}</div>
      </section>

      <motion.section className="final-cta" initial="hidden" whileInView="visible" viewport={{ once: true, margin: '-100px' }} variants={stagger}>
        <motion.span className="section-kicker" variants={reveal}>Your next move starts here</motion.span><motion.h2 variants={reveal}>Stop collecting tutorials.<br /><span>Start building momentum.</span></motion.h2><motion.p variants={reveal}>Choose a focused track, meet your mentors, and turn preparation into progress you can feel.</motion.p><motion.div className="hero-actions" variants={reveal}><Link to="/register" className="btn btn-primary btn-large">Start learning free <ArrowRight size={18} /></Link><Link to="/contact" className="btn btn-outline btn-large">Talk to an advisor</Link></motion.div>
      </motion.section>
    </div>
  );
}
