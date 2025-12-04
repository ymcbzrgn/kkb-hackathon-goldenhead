import { Heart } from 'lucide-react';

export function Footer() {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="w-full border-t border-gray-200 bg-white">
      <div className="container px-4 py-6 mx-auto">
        <div className="flex flex-col items-center justify-between gap-4 md:flex-row">
          {/* Left - KKB Branding */}
          <div className="flex items-center gap-3">
            <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-gradient-to-br from-kkb-800 to-kkb-900">
              <span className="text-sm font-bold text-white">K</span>
            </div>
            <div className="text-sm text-gray-600">
              <span className="font-semibold text-kkb-900">KKB</span>
              {' '}Kredi Kayıt Bürosu
            </div>
          </div>

          {/* Center - Hackathon Info */}
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <span>Agentic AI Hackathon 2025</span>
            <span className="text-accent-500">•</span>
            <span className="flex items-center gap-1">
              Made with <Heart className="w-3.5 h-3.5 text-red-500 fill-red-500" /> by
              <span className="font-semibold text-accent-600">GoldenHead</span>
            </span>
          </div>

          {/* Right - Copyright */}
          <div className="text-sm text-gray-400">
            © {currentYear} Firma İstihbarat Raporu
          </div>
        </div>

        {/* Bottom Gradient Line */}
        <div className="mt-4 h-1 w-full rounded-full bg-gradient-to-r from-kkb-600 via-accent-500 to-kkb-600 opacity-50" />
      </div>
    </footer>
  );
}
