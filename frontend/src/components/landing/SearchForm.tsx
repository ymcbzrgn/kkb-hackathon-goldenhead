/**
 * Search Form
 * Firma adı girişi ve rapor oluşturma formu
 */

import { useState } from 'react';
import { motion } from 'framer-motion';
import { Search, ArrowRight, Building2, Calendar } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useCreateReport } from '@/hooks/useCreateReport';
import { fadeInUp } from '@/utils/animations';

export function SearchForm() {
  const [companyName, setCompanyName] = useState('');
  const [taxNo, setTaxNo] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const { mutate: createReport, isPending } = useCreateReport();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!companyName.trim()) return;

    createReport({
      company_name: companyName.trim(),
      company_tax_no: taxNo.trim() || undefined,
    });
  };

  return (
    <section id="search" className="py-12 bg-white">
      <div className="container mx-auto px-4">
        <motion.div
          variants={fadeInUp}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true }}
          className="max-w-2xl mx-auto"
        >
          {/* Section Title */}
          <div className="text-center mb-8">
            <motion.div
              initial={{ scale: 0 }}
              whileInView={{ scale: 1 }}
              viewport={{ once: true }}
              className="inline-flex items-center justify-center w-14 h-14 rounded-xl bg-gradient-to-br from-accent-400 to-accent-600 mb-4 shadow-lg shadow-accent-500/30"
            >
              <Search className="w-6 h-6 text-white" />
            </motion.div>
            <h2 className="text-2xl md:text-3xl font-bold text-kkb-900 mb-3">
              Firma Analizi Başlat
            </h2>
            <p className="text-gray-600">
              Analiz etmek istediğiniz firmanın adını ve tarih aralığını girin
            </p>
          </div>

          {/* Form Card */}
          <motion.div 
            className="bg-white rounded-2xl shadow-2xl border border-gray-100 p-6 md:p-8 relative overflow-hidden"
            whileHover={{ boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.15)" }}
          >
            {/* Decorative gradient */}
            <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-kkb-600 via-accent-500 to-kkb-600" />
            
            <form onSubmit={handleSubmit} className="space-y-5">
              {/* Company Name Input */}
              <div>
                <label className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-2">
                  <Building2 className="w-4 h-4 text-kkb-600" />
                  Firma Adı <span className="text-red-500">*</span>
                </label>
                <Input
                  type="text"
                  placeholder="Örn: ABC Teknoloji A.Ş."
                  value={companyName}
                  onChange={(e) => setCompanyName(e.target.value)}
                  className="text-lg h-12 bg-gray-50 border-gray-200 focus:bg-white transition-colors"
                  disabled={isPending}
                />
              </div>

              {/* Tax Number Input (Optional) */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Vergi Numarası <span className="text-gray-400">(Opsiyonel)</span>
                </label>
                <Input
                  type="text"
                  placeholder="10 haneli vergi numarası"
                  value={taxNo}
                  onChange={(e) => setTaxNo(e.target.value)}
                  maxLength={10}
                  className="h-12 bg-gray-50 border-gray-200 focus:bg-white transition-colors"
                  disabled={isPending}
                />
              </div>

              {/* Date Range */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-2">
                    <Calendar className="w-4 h-4 text-kkb-600" />
                    Başlangıç Tarihi
                  </label>
                  <Input
                    type="date"
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                    className="h-12 bg-gray-50 border-gray-200 focus:bg-white transition-colors"
                    disabled={isPending}
                  />
                </div>
                <div>
                  <label className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-2">
                    <Calendar className="w-4 h-4 text-kkb-600" />
                    Bitiş Tarihi
                  </label>
                  <Input
                    type="date"
                    value={endDate}
                    onChange={(e) => setEndDate(e.target.value)}
                    className="h-12 bg-gray-50 border-gray-200 focus:bg-white transition-colors"
                    disabled={isPending}
                  />
                </div>
              </div>

              {/* Submit Button */}
              <Button
                type="submit"
                variant="primary"
                size="lg"
                className="w-full mt-6 h-14 text-lg font-semibold shadow-lg shadow-accent-500/30 hover:shadow-xl hover:shadow-accent-500/40 transition-all"
                disabled={!companyName.trim() || isPending}
              >
                {isPending ? (
                  <>
                    <motion.div
                      className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full"
                      animate={{ rotate: 360 }}
                      transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                    />
                    Rapor Oluşturuluyor...
                  </>
                ) : (
                  <>
                    <Search className="w-5 h-5 mr-2" />
                    Analizi Başlat
                    <ArrowRight className="w-5 h-5 ml-2" />
                  </>
                )}
              </Button>
            </form>

            {/* Info Text */}
            <p className="text-xs text-gray-400 text-center mt-4">
              Analiz yaklaşık 2 dakika sürmektedir. Canlı olarak takip edebilirsiniz.
            </p>
          </motion.div>
        </motion.div>
      </div>
    </section>
  );
}
