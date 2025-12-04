import { Link, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import { FileText, Home } from 'lucide-react';
import { cn } from '@/utils/cn';

const navItems = [
  { path: '/', label: 'Ana Sayfa', icon: Home },
  { path: '/reports', label: 'Raporlar', icon: FileText },
];

export function Header() {
  const location = useLocation();

  return (
    <header className="sticky top-0 z-40 w-full border-b border-gray-200 bg-white/80 backdrop-blur-md">
      <div className="container flex items-center justify-between h-16 px-4 mx-auto">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-3 group">
          <motion.div
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
          >
            <img 
              src="/kkb-logo.png" 
              alt="KKB Logo" 
              className="h-10 w-auto"
            />
          </motion.div>
          <div className="flex flex-col">
            <span className="text-lg font-bold text-kkb-900 tracking-tight">
              Firma İstihbarat
            </span>
            <span className="text-[10px] font-medium text-gray-500 -mt-1">
              AI Destekli Analiz
            </span>
          </div>
        </Link>

        {/* Navigation */}
        <nav className="hidden md:flex items-center gap-1">
          {navItems.map((item) => {
            const isActive = location.pathname === item.path || 
              (item.path !== '/' && location.pathname.startsWith(item.path));
            const Icon = item.icon;

            return (
              <Link
                key={item.path}
                to={item.path}
                className={cn(
                  'relative flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg transition-colors',
                  isActive
                    ? 'text-kkb-900'
                    : 'text-gray-600 hover:text-kkb-700 hover:bg-gray-100'
                )}
              >
                <Icon className="w-4 h-4" />
                {item.label}
                {isActive && (
                  <motion.div
                    layoutId="activeTab"
                    className="absolute inset-0 bg-kkb-100 rounded-lg -z-10"
                    transition={{ type: 'spring', duration: 0.5 }}
                  />
                )}
              </Link>
            );
          })}
        </nav>

        {/* Right side - Badge */}
        <div className="flex items-center gap-3">
          <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 bg-gradient-to-r from-accent-500 to-accent-600 rounded-full shadow-sm">
            <span className="text-xs font-semibold text-white">
              🏆 GoldenHead
            </span>
          </div>
        </div>
      </div>
    </header>
  );
}
