'use client';

import { useCallback, useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { ArrowUpRight, BookOpen, Eye, Settings2, Sparkles, TrendingUp } from 'lucide-react';

const PROMPTS = [
  'What pattern is asking for your attention today?',
  'Reflect on a decision you keep revisiting…',
  'What changed in the way you saw this week?',
  'Name the thought that keeps returning.',
];

const PILL_TAGS = [
  { label: 'Reflection', icon: Eye },
  { label: 'Growth', icon: TrendingUp },
  { label: 'Knowledge', icon: BookOpen },
];

const reveal = {
  hidden: { opacity: 0, y: 22 },
  visible: (delay = 0) => ({ opacity: 1, y: 0, transition: { delay, duration: 0.72, ease: [0.22, 1, 0.36, 1] } }),
};

export default function HomePage() {
  const router = useRouter();
  const [promptIndex, setPromptIndex] = useState(0);
  const [inputValue, setInputValue] = useState('');
  const [isFocused, setIsFocused] = useState(false);

  useEffect(() => {
    const timer = setInterval(() => setPromptIndex((i) => (i + 1) % PROMPTS.length), 5000);
    return () => clearInterval(timer);
  }, []);

  const handleSend = useCallback(() => {
    if (!inputValue.trim()) return;
    sessionStorage.setItem('ayeneh_initial_prompt', inputValue.trim());
    router.push('/chat');
  }, [inputValue, router]);

  const handleKeyDown = (event: React.KeyboardEvent) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      handleSend();
    }
  };

  return (
    <main className="mirror-landing">
      <div className="mirror-noise" aria-hidden="true" />
      <div className="mirror-aurora mirror-aurora-one" aria-hidden="true" />
      <div className="mirror-aurora mirror-aurora-two" aria-hidden="true" />

      <header className="mirror-topbar">
        <a href="/" className="mirror-brand" aria-label="Ayeneh home">
          <span className="mirror-brand-orbit"><span /></span>
          <span>Ayeneh</span>
        </a>
        <div className="mirror-topbar-actions">
          <div className="mirror-status"><i /> private by design</div>
          <Link href="/settings" className="mirror-settings-link" aria-label="Model and app settings"><Settings2 size={18} /></Link>
        </div>
      </header>

      <section className="mirror-hero">
        <motion.div className="mirror-kicker" initial="hidden" animate="visible" variants={reveal} custom={0.05}>
          <Sparkles size={14} /> A quieter place to think
        </motion.div>

        <motion.div className="mirror-symbol" initial={{ opacity: 0, scale: 0.72 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.9, ease: [0.16, 1, 0.3, 1] }}>
          <div className="mirror-symbol-ring mirror-symbol-ring-one" />
          <div className="mirror-symbol-ring mirror-symbol-ring-two" />
          <div className="mirror-symbol-core"><span /></div>
          <div className="mirror-symbol-spark" />
        </motion.div>

        <motion.h1 initial="hidden" animate="visible" variants={reveal} custom={0.16}>
          See the pattern
          <em>beneath the moment.</em>
        </motion.h1>
        <motion.p className="mirror-lede" initial="hidden" animate="visible" variants={reveal} custom={0.27}>
          Ayeneh is a cognitive mirror for noticing how you think, decide and grow — over time.
        </motion.p>

        <motion.div className="mirror-compose" initial="hidden" animate="visible" variants={reveal} custom={0.38}>
          <div className={`mirror-compose-shell ${isFocused ? 'mirror-compose-focused' : ''}`}>
            <div className="mirror-compose-label"><span className="mirror-live-dot" /> begin a reflection</div>
            <textarea
              value={inputValue}
              onChange={(event) => setInputValue(event.target.value)}
              onFocus={() => setIsFocused(true)}
              onBlur={() => setIsFocused(false)}
              onKeyDown={handleKeyDown}
              placeholder={PROMPTS[promptIndex]}
              rows={3}
              aria-label="Start a reflection"
            />
            <div className="mirror-compose-footer">
              <span>Private space · press Enter to reflect</span>
              <motion.button
                type="button"
                onClick={handleSend}
                disabled={!inputValue.trim()}
                whileHover={inputValue.trim() ? { scale: 1.04, y: -2 } : undefined}
                whileTap={inputValue.trim() ? { scale: 0.96 } : undefined}
                aria-label="Start reflection"
              ><ArrowUpRight size={19} /></motion.button>
            </div>
          </div>
        </motion.div>

        <motion.div className="mirror-pills" initial="hidden" animate="visible" variants={reveal} custom={0.5}>
          {PILL_TAGS.map(({ label, icon: Icon }) => <span key={label}><Icon size={15} />{label}</span>)}
        </motion.div>
      </section>

      <motion.section className="mirror-insight-strip" initial="hidden" animate="visible" variants={reveal} custom={0.62}>
        <div className="mirror-insight-copy">
          <span className="mirror-mini-label"><Sparkles size={11} /> THE LONG VIEW</span>
          <h2>Small moments become <strong>clearer patterns.</strong></h2>
        </div>
        <div className="mirror-signal" aria-label="Pattern signal preview">
          <div className="mirror-signal-meta"><span>your inner signal</span><b>steady</b></div>
          <div className="mirror-signal-line"><i /><i /><i /><i /><i /><i /><i /><i /><i /></div>
        </div>
      </motion.section>

      <footer className="mirror-footer">
        <span>AYENEH <b>·</b> v1.0</span>
        <span>not advice · not therapy · just a mirror</span>
      </footer>
    </main>
  );
}
