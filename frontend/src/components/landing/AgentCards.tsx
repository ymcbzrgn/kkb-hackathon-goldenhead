/**
 * Agent Cards
 * 3 AI Agent tanıtım kartları
 */

import { motion } from 'framer-motion';
import { FileText, Gavel, Newspaper } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { fadeInUp, staggerContainer } from '@/utils/animations';

const agents = [
  {
    id: 'tsg',
    name: 'TSG Agent',
    title: 'Ticaret Sicili Gazetesi',
    description: 'Firma kuruluş bilgileri, ortaklık yapısı, sermaye değişiklikleri ve yönetim kurulu bilgilerini analiz eder.',
    icon: FileText,
    color: 'bg-blue-500',
    features: [
      'Kuruluş tarihi ve sermaye',
      'Ortaklık yapısı analizi',
      'Yönetici değişiklikleri',
      'Sermaye artış/azalış takibi',
    ],
  },
  {
    id: 'ihale',
    name: 'İhale Agent',
    title: 'EKAP / Kamu İhale',
    description: 'Firmanın kamu ihalelerine katılım durumu ve olası yasaklılık bilgilerini kontrol eder.',
    icon: Gavel,
    color: 'bg-amber-500',
    features: [
      'Aktif ihale yasakları',
      'Geçmiş yasaklılık kayıtları',
      'İhale katılım geçmişi',
      'Kamu sözleşmeleri',
    ],
  },
  {
    id: 'news',
    name: 'News Agent',
    title: 'Haber Analizi',
    description: 'Firma hakkındaki güncel haberleri toplar ve sentiment analizi ile değerlendirir.',
    icon: Newspaper,
    color: 'bg-green-500',
    features: [
      'Güncel haber taraması',
      'Sentiment analizi',
      'Trend takibi',
      'İtibar değerlendirmesi',
    ],
  },
];

export function AgentCards() {
  return (
    <section className="py-16 bg-white">
      <div className="container mx-auto px-4">
        {/* Section Header */}
        <motion.div
          variants={fadeInUp}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true }}
          className="text-center mb-12"
        >
          <h2 className="text-2xl md:text-3xl font-bold text-kkb-900 mb-3">
            3 Uzman AI Agent
          </h2>
          <p className="text-gray-600 max-w-2xl mx-auto">
            Her biri kendi alanında uzmanlaşmış yapay zeka agentları, 
            firmanız hakkında kapsamlı veri toplar
          </p>
        </motion.div>

        {/* Agent Cards Grid */}
        <motion.div
          variants={staggerContainer}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true }}
          className="grid grid-cols-1 md:grid-cols-3 gap-6 lg:gap-8"
        >
          {agents.map((agent) => {
            const Icon = agent.icon;
            return (
              <motion.div key={agent.id} variants={fadeInUp}>
                <Card className="h-full hover:shadow-lg transition-shadow">
                  <CardContent className="p-6">
                    {/* Icon */}
                    <div className={`inline-flex items-center justify-center w-14 h-14 rounded-xl ${agent.color} mb-4`}>
                      <Icon className="w-7 h-7 text-white" />
                    </div>

                    {/* Title */}
                    <h3 className="text-xl font-bold text-kkb-900 mb-1">
                      {agent.name}
                    </h3>
                    <p className="text-sm text-accent-600 font-medium mb-3">
                      {agent.title}
                    </p>

                    {/* Description */}
                    <p className="text-gray-600 text-sm mb-4">
                      {agent.description}
                    </p>

                    {/* Features */}
                    <ul className="space-y-2">
                      {agent.features.map((feature, idx) => (
                        <li key={idx} className="flex items-center text-sm text-gray-500">
                          <span className="w-1.5 h-1.5 rounded-full bg-kkb-400 mr-2" />
                          {feature}
                        </li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>
              </motion.div>
            );
          })}
        </motion.div>
      </div>
    </section>
  );
}
