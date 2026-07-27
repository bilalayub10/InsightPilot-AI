import { ReactNode, useState } from 'react';
import { Link, useLocation } from 'wouter';
import { LayoutDashboard, UploadCloud, Home, Menu, X, BarChart2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export function Layout({ children }: { children: ReactNode }) {
  const [location] = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const navItems = [
    { href: '/', label: 'Home', icon: Home },
    { href: '/upload', label: 'Upload Dataset', icon: UploadCloud },
    { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  ];

  return (
    <div className="min-h-screen flex flex-col bg-background">
      {/* Navbar */}
      <header className="sticky top-0 z-40 w-full bg-card border-b border-border shadow-sm">
        <div className="flex h-16 items-center px-4 md:px-6 justify-between">
          <div className="flex items-center gap-2">
            <Link href="/" className="flex items-center gap-2">
              <div className="bg-primary text-primary-foreground p-1.5 rounded-md">
                <BarChart2 className="w-5 h-5" />
              </div>
              <span className="font-bold text-xl tracking-tight text-sidebar">InsightPilot</span>
              <span className="text-primary font-semibold text-xl">AI</span>
            </Link>
          </div>
          
          <nav className="hidden md:flex items-center gap-6">
            {navItems.map((item) => (
              <Link 
                key={item.href} 
                href={item.href}
                className={`text-sm font-medium transition-colors hover:text-primary ${
                  location === item.href ? 'text-primary' : 'text-muted-foreground'
                }`}
              >
                {item.label}
              </Link>
            ))}
          </nav>

          <button 
            className="md:hidden p-2 text-muted-foreground hover:text-foreground"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          >
            {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>
      </header>

      {/* Mobile Menu */}
      <AnimatePresence>
        {mobileMenuOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="md:hidden border-b border-border bg-card overflow-hidden"
          >
            <nav className="flex flex-col py-4">
              {navItems.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={() => setMobileMenuOpen(false)}
                  className={`flex items-center gap-3 px-6 py-3 text-sm font-medium ${
                    location === item.href 
                      ? 'bg-primary/10 text-primary border-l-4 border-primary' 
                      : 'text-muted-foreground hover:bg-muted/50 hover:text-foreground border-l-4 border-transparent'
                  }`}
                >
                  <item.icon className="w-5 h-5" />
                  {item.label}
                </Link>
              ))}
            </nav>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="flex flex-1 overflow-hidden">
        {/* Desktop Sidebar */}
        <aside className="hidden md:flex w-64 flex-col bg-sidebar text-sidebar-foreground flex-shrink-0">
          <div className="py-6 px-4 space-y-1">
            <div className="text-xs font-semibold text-sidebar-foreground/50 uppercase tracking-wider mb-4 px-2">
              Menu
            </div>
            {navItems.map((item) => {
              const isActive = location === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 ${
                    isActive
                      ? 'bg-primary text-primary-foreground shadow-md'
                      : 'text-sidebar-foreground/70 hover:bg-sidebar-foreground/10 hover:text-sidebar-foreground'
                  }`}
                >
                  <item.icon className={`w-5 h-5 ${isActive ? 'text-primary-foreground' : 'text-sidebar-foreground/50'}`} />
                  {item.label}
                </Link>
              );
            })}
          </div>
          
          <div className="mt-auto p-6">
            <div className="bg-sidebar-foreground/5 rounded-xl p-4 border border-sidebar-foreground/10">
              <h4 className="text-sm font-medium mb-1">Need help?</h4>
              <p className="text-xs text-sidebar-foreground/60 mb-3">Check out our documentation for tips.</p>
              <button className="w-full text-xs font-medium bg-sidebar-foreground/10 hover:bg-sidebar-foreground/20 py-2 rounded-md transition-colors text-sidebar-foreground">
                View Docs
              </button>
            </div>
          </div>
        </aside>

        {/* Main Content */}
        <main className="flex-1 overflow-y-auto bg-background p-4 md:p-8">
          <div className="max-w-7xl mx-auto">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
