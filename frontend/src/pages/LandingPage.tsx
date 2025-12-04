/**
 * Landing Page
 * Ana sayfa - Firma arama ve tanıtım
 */

import { Hero, SearchForm, AgentCards, CouncilIntro } from '@/components/landing';

export function LandingPage() {
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Hero Section */}
      <Hero />
      
      {/* Search Form - Overlapping hero */}
      <div className="-mt-8 relative z-20">
        <SearchForm />
      </div>

      {/* Agent Cards */}
      <AgentCards />

      {/* Council Intro */}
      <CouncilIntro />

      {/* CTA Section */}
      <section className="py-16 bg-gradient-to-br from-kkb-900 via-kkb-800 to-kkb-900 relative overflow-hidden">
        {/* Background decoration */}
        <div className="absolute inset-0 opacity-20">
          <div className="absolute top-0 left-1/4 w-64 h-64 bg-accent-500 rounded-full blur-[100px]" />
          <div className="absolute bottom-0 right-1/4 w-64 h-64 bg-blue-500 rounded-full blur-[100px]" />
        </div>
        
        <div className="container relative z-10 mx-auto px-4 text-center">
          <h2 className="text-2xl md:text-3xl font-bold text-white mb-4">
            Hemen Başlayın
          </h2>
          <p className="text-white/70 max-w-xl mx-auto mb-8">
            Firma adını girerek saniyeler içinde kapsamlı bir istihbarat raporu alın
          </p>
          <a
            href="#search"
            className="inline-flex items-center justify-center px-8 py-4 bg-gradient-to-r from-accent-500 to-accent-600 hover:from-accent-600 hover:to-accent-700 text-white font-semibold rounded-xl shadow-lg shadow-accent-500/30 hover:shadow-xl hover:shadow-accent-500/40 transition-all"
          >
            Rapor Oluştur
          </a>
        </div>
      </section>
    </div>
  );
}
