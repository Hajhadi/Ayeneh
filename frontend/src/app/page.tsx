'use client';

import { useState, useEffect, useCallback } from 'react';
import { Eye, TrendingUp, BookOpen, ArrowRight } from 'lucide-react';

const PROMPTS = [
  "What patterns do you notice in your thinking?",
  "Reflect on your recent decisions...",
  "How do you feel about your progress?",
  "What's been on your mind lately?",
];

const PILL_TAGS = [
  { label: 'Reflection', icon: Eye, delayClass: 'landing-tag-1' },
  { label: 'Growth', icon: TrendingUp, delayClass: 'landing-tag-2' },
  { label: 'Knowledge', icon: BookOpen, delayClass: 'landing-tag-3' },
];

export default function HomePage() {
  const [promptIndex, setPromptIndex] = useState(0);
  const [inputValue, setInputValue] = useState('');
  const [isFocused, setIsFocused] = useState(false);

  useEffect(() => {
    const timer = setInterval(() => {
      setPromptIndex((i) => (i + 1) % PROMPTS.length);
    }, 4000);
    return () => clearInterval(timer);
  }, []);

  const handleSend = useCallback(() => {
    if (!inputValue.trim()) return;
    window.location.href = `/chat?q=${encodeURIComponent(inputValue)}`;
  }, [inputValue]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="relative overflow-hidden">
      {/* Animated background */}
      <div className="landing-bg" />

      {/* Floating orbs */}
      <div className="orb animate-float"
        style={{ top: '15%', left: '20%', width: '320px', height: '320px', background: 'radial-gradient(circle, rgba(124,58,237,0.06) 0%, transparent 70%)', animationDelay: '0s' }} />
      <div className="orb animate-float-2"
        style={{ bottom: '20%', right: '15%', width: '280px', height: '280px', background: 'radial-gradient(circle, rgba(34,211,238,0.04) 0%, transparent 70%)', animationDelay: '3s' }} />
      <div className="orb animate-float"
        style={{ top: '60%', left: '60%', width: '240px', height: '240px', background: 'radial-gradient(circle, rgba(245,158,11,0.03) 0%, transparent 70%)', animationDelay: '6s', animationDuration: '12s' }} />

      {/* Content */}
      <div className="landing-content">
        {/* Logo */}
        <div className="landing-logo">
          <div className="relative mb-6">
            <div className="w-16 h-16 rounded-2xl flex items-center justify-center"
              style={{ background: 'linear-gradient(135deg, #7C3AED, #6366F1)', boxShadow: '0 0 40px rgba(124,58,237,0.3)' }}>
              <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
                <circle cx="16" cy="16" r="14" stroke="white" strokeWidth="1.5" opacity="0.8" />
                <circle cx="16" cy="16" r="8" stroke="white" strokeWidth="1" opacity="0.5" />
                <circle cx="16" cy="16" r="2" fill="white" />
              </svg>
            </div>
            <div className="absolute -bottom-1 -right-1 w-4 h-4 rounded-full flex items-center justify-center"
              style={{ background: 'linear-gradient(135deg, #22D3EE, #06B6D4)' }}>
              <div className="w-1.5 h-1.5 rounded-full bg-white" style={{ animation: 'pulse-dot 2s infinite' }} />
            </div>
          </div>
        </div>

        {/* Title */}
        <h1 className="landing-title"
          style={{ fontSize: '48px', fontWeight: 700, letterSpacing: '-0.02em', color: '#fff', marginBottom: '4px' }}>
          Ayeneh
        </h1>

        {/* Persian subtitle */}
        <p className="landing-subtitle"
          style={{ fontSize: '18px', color: '#A78BFA', marginBottom: '24px', letterSpacing: '0.15em' }}>
          آینه
        </p>

        {/* Description */}
        <p className="landing-desc"
          style={{ fontSize: '16px', lineHeight: 1.7, color: '#D1D5DB', maxWidth: '480px', textAlign: 'center', marginBottom: '32px' }}>
          Your Cognitive Mirror for self-observation and growth.
          <br />
          <span style={{ color: '#6B7280', fontStyle: 'italic' }}>
            I reflect back your thinking patterns — not advice, not therapy.
          </span>
        </p>

        {/* Tags */}
        <div className="flex justify-center gap-3 mb-10">
          {PILL_TAGS.map((tag) => (
            <div key={tag.label}
              className={`flex items-center gap-2 px-5 py-2.5 rounded-full cursor-default transition-all duration-300 hover:scale-105 ${tag.delayClass}`}
              style={{ background: 'rgba(124, 58, 237, 0.08)', border: '1px solid rgba(124, 58, 237, 0.15)' }}>
              <tag.icon size={16} style={{ color: '#A78BFA' }} />
              <span style={{ fontSize: '13px', fontWeight: 500, color: '#A78BFA' }}>{tag.label}</span>
            </div>
          ))}
        </div>

        {/* Chat input */}
        <div className="landing-input" style={{ width: '100%', maxWidth: '560px' }}>
          <div className="relative rounded-2xl transition-all duration-500"
            style={{
              background: 'rgba(255,255,255,0.03)',
              border: `1px solid ${isFocused ? '#7C3AED' : 'rgba(124,58,237,0.2)'}`,
              boxShadow: isFocused ? '0 0 30px rgba(124,58,237,0.15)' : 'none',
            }}>
            <textarea
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onFocus={() => setIsFocused(true)}
              onBlur={() => setIsFocused(false)}
              onKeyDown={handleKeyDown}
              placeholder={PROMPTS[promptIndex]}
              rows={4}
              className="w-full bg-transparent outline-none resize-none"
              style={{
                fontSize: '15px',
                color: '#fff',
                padding: '20px 24px',
                paddingRight: '80px',
                lineHeight: '1.7',
                minHeight: '120px',
                borderRadius: '20px',
                transition: 'all 0.3s ease',
              }}
            />
            <button onClick={handleSend} disabled={!inputValue.trim()}
              className="absolute bottom-4 right-4 w-11 h-11 rounded-xl flex items-center justify-center transition-all duration-300"
              style={{
                background: inputValue.trim() ? 'linear-gradient(135deg, #7C3AED, #6366F1)' : 'rgba(124,58,237,0.15)',
                opacity: inputValue.trim() ? 1 : 0.4,
                cursor: inputValue.trim() ? 'pointer' : 'not-allowed',
                boxShadow: inputValue.trim() ? '0 4px 20px rgba(124,58,237,0.4)' : 'none',
              }}>
              <ArrowRight size={18} className="text-white" />
            </button>
          </div>
        </div>

        {/* Footer */}
        <div className="landing-footer mt-10 text-center">
          <p style={{ fontSize: '12px', color: '#6B7280', letterSpacing: '0.05em', lineHeight: '1.8' }}>
            Ayeneh reflects your thinking patterns — not advice, not therapy, just a mirror.
          </p>
          <div className="flex items-center justify-center gap-2 mt-2">
            <div className="w-1 h-1 rounded-full bg-emerald-500" />
            <span style={{ fontSize: '11px', color: '#4B5563', letterSpacing: '0.05em' }}>
              · Ayeneh v1.0 · Ready
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
