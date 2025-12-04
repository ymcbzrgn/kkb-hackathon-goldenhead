/**
 * Council Intro
 * 6 Kişilik Sanal Kredi Komitesi Tanıtımı
 */

import { motion } from 'framer-motion';
import { Users, MessageCircle, Award, Scale } from 'lucide-react';
import { fadeInUp, staggerContainer } from '@/utils/animations';

// Council members with their photos
const councilMembers = [
  {
    id: 'risk_analyst',
    name: 'Mehmet Bey',
    role: 'Baş Risk Analisti',
    photo: '/council/risk_analyst.png',
    color: 'from-red-500 to-red-600',
    borderColor: 'border-red-400',
  },
  {
    id: 'business_analyst',
    name: 'Ayşe Hanım',
    role: 'İş Geliştirme Müdürü',
    photo: '/council/business_analyst.png',
    color: 'from-green-500 to-green-600',
    borderColor: 'border-green-400',
  },
  {
    id: 'legal_expert',
    name: 'Av. Zeynep Hanım',
    role: 'Hukuk Müşaviri',
    photo: '/council/legal_expert.png',
    color: 'from-purple-500 to-purple-600',
    borderColor: 'border-purple-400',
  },
  {
    id: 'media_analyst',
    name: 'Deniz Bey',
    role: 'İtibar Analisti',
    photo: '/council/media_analyst.png',
    color: 'from-blue-500 to-blue-600',
    borderColor: 'border-blue-400',
  },
  {
    id: 'sector_expert',
    name: 'Prof. Dr. Ali Bey',
    role: 'Sektör Uzmanı',
    photo: '/council/sector_expert.png',
    color: 'from-amber-500 to-amber-600',
    borderColor: 'border-amber-400',
  },
  {
    id: 'moderator',
    name: 'Genel Müdür Yrd.',
    role: 'Komite Başkanı',
    photo: '/council/moderator.png',
    color: 'from-kkb-700 to-kkb-900',
    borderColor: 'border-kkb-500',
  },
];

export function CouncilIntro() {
  return (
    <section className="py-20 bg-gradient-to-b from-gray-50 to-white relative overflow-hidden">
      {/* Background decoration */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 -left-20 w-40 h-40 bg-accent-500/10 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 -right-20 w-40 h-40 bg-kkb-500/10 rounded-full blur-3xl" />
      </div>

      <div className="container mx-auto px-4 relative z-10">
        {/* Section Header */}
        <motion.div
          variants={fadeInUp}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true }}
          className="text-center mb-16"
        >
          <motion.div 
            className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-kkb-700 to-kkb-900 mb-6 shadow-lg shadow-kkb-900/30"
            whileHover={{ scale: 1.05, rotate: 5 }}
          >
            <Users className="w-8 h-8 text-white" />
          </motion.div>
          <h2 className="text-3xl md:text-4xl font-bold text-kkb-900 mb-4">
            6 Kişilik Sanal Kredi Komitesi
          </h2>
          <p className="text-gray-600 max-w-2xl mx-auto text-lg">
            Farklı bakış açılarına sahip 6 uzman üye, toplanan verileri değerlendirerek 
            nihai kredi puanını ve kararı belirler
          </p>
        </motion.div>

        {/* Council Members Grid */}
        <motion.div
          variants={staggerContainer}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true }}
          className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-6"
        >
          {councilMembers.map((member, index) => (
            <motion.div 
              key={member.id} 
              variants={fadeInUp}
              whileHover={{ y: -8, scale: 1.02 }}
              transition={{ type: "spring", stiffness: 300 }}
            >
              <div className="group relative bg-white rounded-2xl p-5 shadow-lg hover:shadow-2xl transition-all duration-300 text-center border border-gray-100">
                {/* Glow effect on hover */}
                <div className={`absolute inset-0 rounded-2xl bg-gradient-to-br ${member.color} opacity-0 group-hover:opacity-10 transition-opacity`} />
                
                {/* Photo */}
                <div className="relative mb-4">
                  <div className={`absolute inset-0 rounded-full bg-gradient-to-br ${member.color} blur-md opacity-30 group-hover:opacity-50 transition-opacity`} />
                  <motion.div
                    className={`relative w-20 h-20 mx-auto rounded-full overflow-hidden border-3 ${member.borderColor} shadow-lg`}
                    whileHover={{ scale: 1.1 }}
                  >
                    <img 
                      src={member.photo} 
                      alt={member.name}
                      className="w-full h-full object-cover"
                    />
                  </motion.div>
                  {/* Online indicator */}
                  <div className="absolute bottom-0 right-1/2 translate-x-6 w-4 h-4 bg-green-500 rounded-full border-2 border-white shadow-sm" />
                </div>

                {/* Name */}
                <h3 className="font-bold text-kkb-900 text-sm mb-1 group-hover:text-kkb-700 transition-colors">
                  {member.name}
                </h3>

                {/* Role */}
                <p className="text-xs text-gray-500 leading-tight">
                  {member.role}
                </p>

                {/* Decorative number */}
                <div className="absolute top-2 right-2 w-6 h-6 rounded-full bg-gray-100 flex items-center justify-center">
                  <span className="text-xs font-bold text-gray-400">{index + 1}</span>
                </div>
              </div>
            </motion.div>
          ))}
        </motion.div>

        {/* Process Features */}
        <motion.div
          variants={fadeInUp}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true }}
          className="mt-16"
        >
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-4xl mx-auto">
            <div className="flex items-center gap-4 p-4 bg-white rounded-xl shadow-sm border border-gray-100">
              <div className="w-12 h-12 rounded-xl bg-green-100 flex items-center justify-center flex-shrink-0">
                <MessageCircle className="w-6 h-6 text-green-600" />
              </div>
              <div>
                <h4 className="font-semibold text-kkb-900 text-sm">Gerçek Zamanlı</h4>
                <p className="text-xs text-gray-500">Canlı konuşma akışı</p>
              </div>
            </div>

            <div className="flex items-center gap-4 p-4 bg-white rounded-xl shadow-sm border border-gray-100">
              <div className="w-12 h-12 rounded-xl bg-accent-100 flex items-center justify-center flex-shrink-0">
                <Award className="w-6 h-6 text-accent-600" />
              </div>
              <div>
                <h4 className="font-semibold text-kkb-900 text-sm">Bireysel Puanlama</h4>
                <p className="text-xs text-gray-500">Her üye kendi puanını verir</p>
              </div>
            </div>

            <div className="flex items-center gap-4 p-4 bg-white rounded-xl shadow-sm border border-gray-100">
              <div className="w-12 h-12 rounded-xl bg-kkb-100 flex items-center justify-center flex-shrink-0">
                <Scale className="w-6 h-6 text-kkb-700" />
              </div>
              <div>
                <h4 className="font-semibold text-kkb-900 text-sm">Konsensüs Kararı</h4>
                <p className="text-xs text-gray-500">Ortak değerlendirme</p>
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
