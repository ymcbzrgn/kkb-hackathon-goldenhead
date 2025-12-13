/**
 * Hero Section
 * Landing sayfasının üst kısmı - gradient bg, başlık, açıklama
 */

import { motion } from 'framer-motion';
import { Zap, Shield } from 'lucide-react';
import { fadeInUp, staggerContainer } from '@/utils/animations';

export function Hero() {
  return (
    <section className="relative overflow-hidden bg-gradient-to-br from-kkb-900 via-kkb-800 to-kkb-700 py-16 lg:py-24">
      {/* Animated Background Shapes */}
      <div className="absolute inset-0 overflow-hidden">
        {/* Glowing orbs */}
        <motion.div
          className="absolute top-1/4 left-1/4 w-96 h-96 bg-accent-500/20 rounded-full blur-[100px]"
          animate={{ 
            scale: [1, 1.2, 1],
            opacity: [0.3, 0.5, 0.3],
          }}
          transition={{ duration: 5, repeat: Infinity, ease: "easeInOut" }}
        />
        <motion.div
          className="absolute bottom-1/4 right-1/4 w-80 h-80 bg-blue-500/20 rounded-full blur-[80px]"
          animate={{ 
            scale: [1.2, 1, 1.2],
            opacity: [0.4, 0.2, 0.4],
          }}
          transition={{ duration: 7, repeat: Infinity, ease: "easeInOut" }}
        />
        <motion.div
          className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-gradient-to-r from-accent-500/10 to-kkb-600/10 rounded-full blur-[120px]"
          animate={{ rotate: 360 }}
          transition={{ duration: 30, repeat: Infinity, ease: "linear" }}
        />
        
        {/* Floating particles */}
        {[...Array(6)].map((_, i) => (
          <motion.div
            key={i}
            className="absolute w-2 h-2 bg-white/30 rounded-full"
            style={{
              left: `${15 + i * 15}%`,
              top: `${20 + (i % 3) * 25}%`,
            }}
            animate={{
              y: [0, -30, 0],
              opacity: [0.3, 0.7, 0.3],
            }}
            transition={{
              duration: 3 + i * 0.5,
              repeat: Infinity,
              delay: i * 0.3,
            }}
          />
        ))}
      </div>

      <div className="container relative z-10 mx-auto px-4">
        <motion.div
          variants={staggerContainer}
          initial="hidden"
          animate="visible"
          className="text-center max-w-4xl mx-auto"
        >
          {/* KKB Logo - White version */}
          <motion.div variants={fadeInUp} className="mb-8">
            <motion.div 
              className="inline-flex items-center justify-center w-20 h-20 rounded-2xl bg-white/10 backdrop-blur-md border border-white/20 shadow-2xl shadow-black/20"
              whileHover={{ scale: 1.05, rotate: 3 }}
              transition={{ type: "spring", stiffness: 300 }}
            >
              <img 
                src="/kkb-logo-white.png" 
                alt="KKB Logo" 
                className="w-14 h-14 object-contain brightness-0 invert"
              />
            </motion.div>
          </motion.div>

          {/* Title with gradient */}
          <motion.h1 
            variants={fadeInUp}
            className="text-4xl md:text-5xl lg:text-6xl font-bold text-white mb-6"
          >
            Firma İstihbarat
            <span className="block bg-gradient-to-r from-accent-400 via-accent-300 to-yellow-300 bg-clip-text text-transparent">
              Raporu
            </span>
          </motion.h1>

          {/* Subtitle */}
          <motion.p 
            variants={fadeInUp}
            className="text-lg md:text-xl text-white/80 mb-10 max-w-2xl mx-auto leading-relaxed"
          >
            Yapay zeka destekli 3 uzman agent ve 6 kişilik sanal kredi komitesi ile 
            kapsamlı firma risk analizi
          </motion.p>

          {/* Stats with icons */}
          <motion.div 
            variants={fadeInUp}
            className="flex flex-wrap justify-center gap-6 md:gap-10"
          >
            <motion.div 
              className="flex items-center gap-3 px-5 py-3 bg-white/10 backdrop-blur-sm rounded-xl border border-white/10"
              whileHover={{ scale: 1.05, backgroundColor: "rgba(255,255,255,0.15)" }}
            >
              <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-400 to-blue-600 flex items-center justify-center">
                <Zap className="w-5 h-5 text-white" />
              </div>
              <div className="text-left">
                <div className="text-2xl font-bold text-white">3</div>
                <div className="text-xs text-white/60">AI Agent</div>
              </div>
            </motion.div>

            <motion.div 
              className="flex items-center gap-3 px-5 py-3 bg-white/10 backdrop-blur-sm rounded-xl border border-white/10"
              whileHover={{ scale: 1.05, backgroundColor: "rgba(255,255,255,0.15)" }}
            >
              <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-purple-400 to-purple-600 flex items-center justify-center">
                <Shield className="w-5 h-5 text-white" />
              </div>
              <div className="text-left">
                <div className="text-2xl font-bold text-white">6</div>
                <div className="text-xs text-white/60">Komite Üyesi</div>
              </div>
            </motion.div>

          </motion.div>
        </motion.div>
      </div>

      {/* Smooth gradient transition to content */}
      <div className="absolute bottom-0 left-0 right-0 h-24 bg-gradient-to-t from-white to-transparent" />
    </section>
  );
}
