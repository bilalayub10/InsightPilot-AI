/**
 * InsightPilot — AI Copilot Chat Panel
 *
 * A full chat interface that lets users ask natural-language questions
 * about their dataset and receive Senior BI Consultant responses.
 *
 * Domain suggestions are defined in lib/copilot-suggestions.ts.
 */

import { useState, useRef, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Send, Bot, User, Sparkles, TrendingUp, AlertTriangle,
  BarChart2, HelpCircle, Lightbulb, RefreshCw, ChevronRight,
} from 'lucide-react';
import { queryCopilot } from '@workspace/api-client-react';
import { getSuggestions } from '../lib/copilot-suggestions';

// ─── Types ─────────────────────────────────────────────────────────────────────

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  reasoning?: string;
  confidence?: number;
  followUps?: string[];
  timestamp: Date;
  error?: boolean;
}

interface Props {
  datasetId: string;
  domain?: string;
}

// ─── Mini markdown renderer ─────────────────────────────────────────────────────

function renderMarkdown(text: string) {
  const lines = text.split('\n');
  const elements: React.ReactNode[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    if (line.startsWith('## ')) {
      elements.push(
        <p key={i} className="font-semibold text-foreground mt-3 mb-1">
          {inlineFormat(line.slice(3))}
        </p>
      );
    } else if (line.startsWith('# ')) {
      elements.push(
        <p key={i} className="font-bold text-foreground mt-3 mb-1">
          {inlineFormat(line.slice(2))}
        </p>
      );
    } else if (line.startsWith('- ') || line.startsWith('• ')) {
      elements.push(
        <div key={i} className="flex items-start gap-2 my-0.5">
          <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-primary/60 shrink-0" />
          <span>{inlineFormat(line.slice(2))}</span>
        </div>
      );
    } else if (line.trim() === '') {
      if (elements.length > 0) elements.push(<div key={`sp-${i}`} className="h-1.5" />);
    } else {
      elements.push(<span key={i}>{inlineFormat(line)}{'\n'}</span>);
    }
    i++;
  }

  return <>{elements}</>;
}

function inlineFormat(text: string): React.ReactNode {
  const parts = text.split(/(\*\*[^*]+\*\*|__[^_]+__)/g);
  return (
    <>
      {parts.map((part, idx) => {
        if (part.startsWith('**') && part.endsWith('**'))
          return <strong key={idx} className="font-semibold text-foreground">{part.slice(2, -2)}</strong>;
        if (part.startsWith('__') && part.endsWith('__'))
          return <strong key={idx} className="font-semibold text-foreground">{part.slice(2, -2)}</strong>;
        return <span key={idx}>{part}</span>;
      })}
    </>
  );
}

// ─── Typing indicator ───────────────────────────────────────────────────────────

function TypingDots() {
  return (
    <div className="flex items-center gap-1 px-1 py-1">
      {[0, 1, 2].map(i => (
        <motion.span
          key={i}
          className="w-1.5 h-1.5 rounded-full bg-primary/60"
          animate={{ opacity: [0.3, 1, 0.3], y: [0, -3, 0] }}
          transition={{ duration: 1, repeat: Infinity, delay: i * 0.18 }}
        />
      ))}
    </div>
  );
}

// ─── Confidence badge ───────────────────────────────────────────────────────────

function ConfidencePill({ value }: { value: number }) {
  const color =
    value >= 80 ? 'bg-green-100 text-green-700'
    : value >= 50 ? 'bg-amber-100 text-amber-700'
    : 'bg-red-100 text-red-700';
  return (
    <span className={`inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full ${color}`}>
      {value}% confidence
    </span>
  );
}

// ─── Main component ─────────────────────────────────────────────────────────────

export function AICopilot({ datasetId, domain }: Props) {
  const [messages, setMessages]         = useState<Message[]>([]);
  const [input, setInput]               = useState('');
  const [isLoading, setIsLoading]       = useState(false);
  const [showReasoning, setShowReasoning] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef  = useRef<HTMLTextAreaElement>(null);

  const suggestions = getSuggestions(domain);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const sendQuestion = useCallback(async (question: string) => {
    if (!question.trim() || isLoading) return;

    const userMsg: Message = {
      id: `u-${Date.now()}`,
      role: 'user',
      content: question.trim(),
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsLoading(true);

    try {
      const data = await queryCopilot({ datasetId, question: question.trim() });

      const assistantMsg: Message = {
        id: `a-${Date.now()}`,
        role: 'assistant',
        content: data.answer,
        reasoning: data.reasoning,
        confidence: data.confidence,
        followUps: data.follow_up_questions ?? [],
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, assistantMsg]);
    } catch {
      const errorMsg: Message = {
        id: `e-${Date.now()}`,
        role: 'assistant',
        content: "I couldn't generate a response right now. Please try again.",
        timestamp: new Date(),
        error: true,
      };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  }, [datasetId, isLoading]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendQuestion(input);
    }
  };

  return (
    <div className="flex flex-col rounded-2xl border border-border bg-card shadow-sm overflow-hidden">
      {/* ── Header ── */}
      <div className="flex items-center gap-3 px-6 py-5 border-b border-border bg-gradient-to-r from-primary/5 to-violet-500/5">
        <div className="w-9 h-9 rounded-xl bg-primary/10 flex items-center justify-center shrink-0">
          <Sparkles className="w-4 h-4 text-primary" />
        </div>
        <div>
          <h3 className="text-base font-semibold text-foreground">AI Copilot</h3>
          <p className="text-xs text-muted-foreground">
            Ask anything about your dataset · Senior BI Consultant
          </p>
        </div>
        {domain && domain !== 'generic' && (
          <span className="ml-auto text-[11px] font-medium px-2.5 py-1 rounded-full bg-primary/10 text-primary capitalize">
            {domain.replace(/_/g, ' ')}
          </span>
        )}
      </div>

      {/* ── Chat area ── */}
      <div className="flex flex-col min-h-[420px] max-h-[560px] overflow-y-auto px-5 py-4 gap-4 scroll-smooth">

        {/* Empty state */}
        {messages.length === 0 && !isLoading && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex flex-col items-center justify-center flex-1 py-10 text-center gap-3"
          >
            <div className="w-14 h-14 rounded-2xl bg-primary/8 flex items-center justify-center">
              <Bot className="w-7 h-7 text-primary/70" />
            </div>
            <p className="text-sm font-medium text-foreground">Ask me about your data</p>
            <p className="text-xs text-muted-foreground max-w-xs leading-relaxed">
              I'll answer like a Senior Business Intelligence Consultant — evidence-based, no hallucinations.
            </p>
          </motion.div>
        )}

        {/* Messages */}
        <AnimatePresence initial={false}>
          {messages.map(msg => (
            <motion.div
              key={msg.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.25 }}
              className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}
            >
              {/* Avatar */}
              <div className={`shrink-0 w-7 h-7 rounded-lg flex items-center justify-center mt-0.5 ${
                msg.role === 'user'
                  ? 'bg-primary text-primary-foreground'
                  : msg.error
                    ? 'bg-destructive/10 text-destructive'
                    : 'bg-violet-100 text-violet-600'
              }`}>
                {msg.role === 'user'
                  ? <User className="w-3.5 h-3.5" />
                  : <Bot className="w-3.5 h-3.5" />}
              </div>

              {/* Bubble */}
              <div className={`flex flex-col gap-2 max-w-[82%] ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                <div className={`rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                  msg.role === 'user'
                    ? 'bg-primary text-primary-foreground rounded-tr-sm'
                    : msg.error
                      ? 'bg-destructive/8 text-destructive border border-destructive/20 rounded-tl-sm'
                      : 'bg-muted/60 text-foreground rounded-tl-sm'
                }`}>
                  {msg.role === 'assistant' && !msg.error
                    ? renderMarkdown(msg.content)
                    : msg.content}
                </div>

                {/* Assistant meta */}
                {msg.role === 'assistant' && !msg.error && (
                  <div className="flex flex-wrap items-center gap-2 px-1">
                    {msg.confidence !== undefined && <ConfidencePill value={msg.confidence} />}
                    {msg.reasoning && (
                      <button
                        onClick={() => setShowReasoning(showReasoning === msg.id ? null : msg.id)}
                        className="text-[11px] text-muted-foreground hover:text-foreground flex items-center gap-0.5 transition-colors"
                      >
                        <Lightbulb className="w-3 h-3" />
                        {showReasoning === msg.id ? 'Hide reasoning' : 'Show reasoning'}
                      </button>
                    )}
                    <span className="text-[10px] text-muted-foreground ml-auto">
                      {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                )}

                {/* Reasoning panel */}
                <AnimatePresence>
                  {showReasoning === msg.id && msg.reasoning && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: 'auto' }}
                      exit={{ opacity: 0, height: 0 }}
                      className="rounded-xl bg-amber-50 border border-amber-200 px-4 py-3 text-xs text-amber-800 leading-relaxed max-w-full"
                    >
                      <p className="font-semibold mb-1 flex items-center gap-1.5">
                        <Lightbulb className="w-3 h-3" /> Reasoning
                      </p>
                      {msg.reasoning}
                    </motion.div>
                  )}
                </AnimatePresence>

                {/* Follow-up questions */}
                {msg.role === 'assistant' && !msg.error && (msg.followUps?.length ?? 0) > 0 && (
                  <div className="flex flex-col gap-1.5 w-full mt-1">
                    {msg.followUps!.map((q, qi) => (
                      <button
                        key={qi}
                        onClick={() => sendQuestion(q)}
                        disabled={isLoading}
                        className="text-left text-xs px-3 py-2 rounded-xl border border-primary/20 bg-primary/5 text-primary hover:bg-primary/10 transition-colors flex items-center gap-2 group disabled:opacity-40"
                      >
                        <ChevronRight className="w-3 h-3 shrink-0 group-hover:translate-x-0.5 transition-transform" />
                        {q}
                      </button>
                    ))}
                  </div>
                )}

                {/* User timestamp */}
                {msg.role === 'user' && (
                  <span className="text-[10px] text-muted-foreground px-1">
                    {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </span>
                )}
              </div>
            </motion.div>
          ))}
        </AnimatePresence>

        {/* Typing indicator */}
        {isLoading && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="flex gap-3"
          >
            <div className="shrink-0 w-7 h-7 rounded-lg bg-violet-100 flex items-center justify-center mt-0.5">
              <Bot className="w-3.5 h-3.5 text-violet-600" />
            </div>
            <div className="bg-muted/60 rounded-2xl rounded-tl-sm px-4 py-3">
              <TypingDots />
            </div>
          </motion.div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* ── Suggested questions ── */}
      {messages.length === 0 && (
        <div className="px-5 pb-3 flex flex-wrap gap-2">
          {suggestions.slice(0, 6).map((q, i) => {
            const icons = [TrendingUp, AlertTriangle, BarChart2, HelpCircle, Lightbulb, RefreshCw];
            const Icon = icons[i % icons.length];
            return (
              <button
                key={q}
                onClick={() => sendQuestion(q)}
                disabled={isLoading}
                className="flex items-center gap-1.5 text-xs px-3 py-2 rounded-xl border border-border bg-accent/40 text-foreground hover:bg-accent hover:border-primary/30 transition-colors disabled:opacity-40"
              >
                <Icon className="w-3 h-3 text-muted-foreground" />
                {q}
              </button>
            );
          })}
        </div>
      )}

      {/* ── Input area ── */}
      <div className="border-t border-border px-4 py-3 bg-background/50">
        <div className="flex items-end gap-2 rounded-xl border border-border bg-background focus-within:border-primary/50 focus-within:ring-2 focus-within:ring-primary/10 transition-all px-3 py-2">
          <textarea
            ref={inputRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask a business question… (Enter to send)"
            rows={1}
            disabled={isLoading}
            className="flex-1 resize-none bg-transparent text-sm text-foreground placeholder:text-muted-foreground outline-none min-h-[22px] max-h-[120px] leading-relaxed disabled:opacity-50"
            style={{ overflowY: input.split('\n').length > 3 ? 'auto' : 'hidden' }}
          />
          <button
            onClick={() => sendQuestion(input)}
            disabled={!input.trim() || isLoading}
            className="shrink-0 w-8 h-8 rounded-lg bg-primary text-primary-foreground flex items-center justify-center hover:bg-primary/90 disabled:opacity-40 disabled:cursor-not-allowed transition-all active:scale-95"
          >
            {isLoading
              ? <RefreshCw className="w-3.5 h-3.5 animate-spin" />
              : <Send className="w-3.5 h-3.5" />}
          </button>
        </div>
        <p className="text-[10px] text-muted-foreground mt-1.5 px-1">
          Shift+Enter for new line · Answers grounded in your dataset only
        </p>
      </div>
    </div>
  );
}
