import { motion } from 'framer-motion';
import { Link } from 'wouter';
import { BarChart2, Shield, Zap, Target, ArrowRight, BrainCircuit, Activity, Database } from 'lucide-react';

export default function Landing() {
  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col font-sans overflow-x-hidden">
      {/* Navigation */}
      <header className="fixed top-0 left-0 right-0 z-50 bg-background/80 backdrop-blur-md border-b border-border">
        <div className="max-w-7xl mx-auto px-6 h-20 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="bg-primary text-primary-foreground p-1.5 rounded-lg shadow-lg shadow-primary/30">
              <BarChart2 className="w-6 h-6" />
            </div>
            <span className="font-bold text-2xl tracking-tight text-sidebar">InsightPilot</span>
            <span className="text-primary font-semibold text-2xl">AI</span>
          </div>
          <div className="flex items-center gap-6">
            <Link href="/upload" className="text-sm font-semibold text-muted-foreground hover:text-primary transition-colors">
              Platform
            </Link>
            <Link href="/dashboard" className="text-sm font-semibold text-muted-foreground hover:text-primary transition-colors">
              Dashboard
            </Link>
            <Link href="/upload" className="px-5 py-2.5 bg-sidebar text-sidebar-foreground hover:bg-sidebar/90 rounded-full text-sm font-semibold transition-all">
              Launch App
            </Link>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="pt-40 pb-20 px-6 relative">
        <div className="absolute inset-0 -z-10 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-primary/10 via-background to-background"></div>
        <div className="max-w-5xl mx-auto text-center">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
          >
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/10 text-primary font-medium text-sm mb-8 border border-primary/20">
              <Zap className="w-4 h-4" />
              <span>Next-Gen Analytics Engine</span>
            </div>
            <h1 className="text-6xl md:text-8xl font-bold tracking-tight text-sidebar mb-8 leading-[1.1]">
              Transform raw data into <br className="hidden md:block" />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary to-blue-400">
                executive clarity.
              </span>
            </h1>
            <p className="text-xl text-muted-foreground mb-12 max-w-3xl mx-auto leading-relaxed">
              Upload your datasets and let InsightPilot AI automatically extract KPIs, spot anomalies, and generate actionable insights in seconds. Bloomberg precision meets modern SaaS.
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <Link 
                href="/upload" 
                className="px-8 py-4 bg-primary text-primary-foreground hover:bg-primary/90 rounded-full text-lg font-semibold transition-all shadow-xl shadow-primary/20 flex items-center gap-2"
              >
                Start Analyzing <ArrowRight className="w-5 h-5" />
              </Link>
              <Link 
                href="/dashboard" 
                className="px-8 py-4 bg-white text-sidebar border border-border hover:bg-gray-50 rounded-full text-lg font-semibold transition-all shadow-sm"
              >
                View Live Demo
              </Link>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Feature Section: The Terminal */}
      <section className="py-24 px-6 bg-sidebar text-sidebar-foreground relative overflow-hidden">
        <div className="absolute top-0 right-0 w-1/2 h-full bg-gradient-to-l from-primary/10 to-transparent pointer-events-none"></div>
        <div className="max-w-7xl mx-auto">
          <div className="grid md:grid-cols-2 gap-16 items-center">
            <motion.div 
              initial={{ opacity: 0, x: -30 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              className="space-y-8"
            >
              <h2 className="text-4xl md:text-5xl font-bold tracking-tight">
                Your data command center.
              </h2>
              <p className="text-lg text-sidebar-foreground/70 leading-relaxed">
                We replaced clunky spreadsheets with an autonomous intelligence layer. Drop your CSV, and InsightPilot maps schemas, detects trends, and compiles a comprehensive dashboard instantly.
              </p>
              
              <ul className="space-y-4">
                {[
                  { icon: BrainCircuit, text: 'Autonomous AI Insights generation' },
                  { icon: Activity, text: 'Real-time KPI extraction & tracking' },
                  { icon: Database, text: 'Instant schema recognition for CSV/Excel' }
                ].map((item, i) => (
                  <li key={i} className="flex items-center gap-4">
                    <div className="bg-primary/20 p-2 rounded-lg text-primary">
                      <item.icon className="w-5 h-5" />
                    </div>
                    <span className="font-medium text-sidebar-foreground/90">{item.text}</span>
                  </li>
                ))}
              </ul>
            </motion.div>

            <motion.div 
              initial={{ opacity: 0, scale: 0.95 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true }}
              className="relative"
            >
              <div className="aspect-[4/3] rounded-2xl bg-card border border-border/10 shadow-2xl overflow-hidden p-6 relative">
                {/* Abstract UI representation */}
                <div className="flex gap-4 mb-8">
                  <div className="w-1/4 h-24 bg-sidebar/5 rounded-xl border border-sidebar/10 p-4">
                    <div className="w-8 h-2 bg-primary/40 rounded mb-4"></div>
                    <div className="w-16 h-6 bg-sidebar/20 rounded"></div>
                  </div>
                  <div className="w-1/4 h-24 bg-sidebar/5 rounded-xl border border-sidebar/10 p-4">
                    <div className="w-8 h-2 bg-primary/40 rounded mb-4"></div>
                    <div className="w-16 h-6 bg-sidebar/20 rounded"></div>
                  </div>
                  <div className="w-1/2 h-24 bg-sidebar/5 rounded-xl border border-sidebar/10 p-4">
                    <div className="w-full h-12 bg-green-500/10 rounded mt-2"></div>
                  </div>
                </div>
                <div className="w-full h-48 bg-sidebar/5 rounded-xl border border-sidebar/10"></div>
              </div>
              <div className="absolute -inset-4 border border-primary/20 rounded-3xl -z-10"></div>
            </motion.div>
          </div>
        </div>
      </section>

      {/* Grid of value props */}
      <section className="py-32 px-6 bg-background">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-20">
            <h2 className="text-4xl font-bold text-sidebar mb-4">Engineered for velocity</h2>
            <p className="text-muted-foreground text-lg">Stop building dashboards. Start making decisions.</p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            {[
              { title: 'Zero Configuration', icon: Shield, desc: 'No mapping fields, no building charts. Drop your data and let the engine do the heavy lifting.' },
              { title: 'Executive Precision', icon: Target, desc: 'Clean, dense, authoritative UI. Every pixel earns its place on your screen.' },
              { title: 'Actionable Clarity', icon: BrainCircuit, desc: 'AI reads the data and tells you exactly what is happening and why it matters.' }
            ].map((feature, i) => (
              <div key={i} className="p-8 rounded-2xl bg-card border border-border hover:shadow-xl transition-shadow group">
                <div className="bg-primary/10 w-14 h-14 rounded-xl flex items-center justify-center text-primary mb-6 group-hover:scale-110 transition-transform">
                  <feature.icon className="w-7 h-7" />
                </div>
                <h3 className="text-xl font-bold text-sidebar mb-3">{feature.title}</h3>
                <p className="text-muted-foreground leading-relaxed">
                  {feature.desc}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-24 px-6 border-t border-border bg-card">
        <div className="max-w-4xl mx-auto text-center space-y-8">
          <h2 className="text-4xl md:text-5xl font-bold text-sidebar">Ready to elevate your analytics?</h2>
          <p className="text-xl text-muted-foreground">Join the next generation of data-driven leaders.</p>
          <div className="pt-4">
            <Link 
              href="/upload" 
              className="px-10 py-5 bg-sidebar text-sidebar-foreground hover:bg-sidebar/90 rounded-full text-lg font-bold transition-all shadow-xl inline-flex items-center gap-2"
            >
              Get Started Now <ArrowRight className="w-5 h-5" />
            </Link>
          </div>
        </div>
      </section>

      <footer className="py-12 border-t border-border bg-background text-center text-muted-foreground text-sm">
        <div className="flex items-center justify-center gap-2 mb-4">
          <BarChart2 className="w-5 h-5 text-primary" />
          <span className="font-bold text-sidebar">InsightPilot AI</span>
        </div>
        <p>&copy; {new Date().getFullYear()} InsightPilot AI. All rights reserved.</p>
      </footer>
    </div>
  );
}
