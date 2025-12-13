/**
 * TsgResults Component
 * TSG (Ticaret Sicil Gazetesi) agent sonuçları
 *
 * Backend'den gelen veri yapısı:
 * {
 *   firma_adi: string,
 *   tsg_sonuc: {
 *     toplam_ilan: number,
 *     yapilandirilmis_veri: {
 *       "Firma Unvani": string,
 *       "Tescil Konusu": string,
 *       "Mersis Numarasi": string,
 *       "Yoneticiler": string[],
 *       "Imza Yetkilisi": string,
 *       "Sermaye": string,
 *       "Kurulus_Tarihi": string,
 *       "Faaliyet_Konusu": string
 *     },
 *     gazete_bilgisi: {...},
 *     sicil_bilgisi: {...}
 *   }
 * }
 */

import { motion } from 'framer-motion';
import { Building2, Users, Briefcase, TrendingUp, Calendar, FileText, Hash, PenTool } from 'lucide-react';
import { Card } from '@/components/ui/card';

// Backend'den gelen gerçek veri yapısı
interface TsgBackendData {
  firma_adi?: string;
  tsg_sonuc?: {
    toplam_ilan?: number;
    yapilandirilmis_veri?: {
      'Firma Unvani'?: string;
      'Tescil Konusu'?: string;
      'Mersis Numarasi'?: string;
      'Yoneticiler'?: string[];
      'Imza Yetkilisi'?: string;
      'Sermaye'?: string;
      'Kurulus_Tarihi'?: string;
      'Faaliyet_Konusu'?: string;
    };
    gazete_bilgisi?: {
      gazete_no?: string;
      tarih?: string;
      ilan_tipi?: string;
    };
    sicil_bilgisi?: {
      sicil_no?: string;
      sicil_mudurlugu?: string;
    };
  };
  veri_kaynagi?: string;
  status?: string;
}

interface TsgResultsProps {
  data: TsgBackendData;
}

export function TsgResults({ data }: TsgResultsProps) {
  // Veriyi çıkar
  const veri = data?.tsg_sonuc?.yapilandirilmis_veri || {};
  const gazete = data?.tsg_sonuc?.gazete_bilgisi || {};
  const sicil = data?.tsg_sonuc?.sicil_bilgisi || {};
  const toplamIlan = data?.tsg_sonuc?.toplam_ilan || 0;

  // Veri kontrolü - hiç veri yoksa mesaj göster
  const hasAnyData = veri['Firma Unvani'] || veri['Tescil Konusu'] || veri['Mersis Numarasi'] ||
                     (veri['Yoneticiler'] && veri['Yoneticiler'].length > 0) ||
                     veri['Imza Yetkilisi'] || veri['Sermaye'] || veri['Kurulus_Tarihi'] ||
                     veri['Faaliyet_Konusu'] || sicil.sicil_no;

  if (!hasAnyData) {
    return (
      <div className="text-center py-12">
        <FileText className="w-12 h-12 text-gray-400 mx-auto mb-4" />
        <h4 className="font-semibold text-gray-800 mb-1">TSG Verisi Bulunamadı</h4>
        <p className="text-sm text-gray-500">Bu firma için Ticaret Sicil Gazetesi kaydı bulunamadı.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Firma Bilgileri */}
      <Card className="p-5">
        <h4 className="text-sm font-semibold text-gray-700 mb-4 flex items-center gap-2">
          <Building2 className="w-4 h-4 text-kkb-600" />
          Firma Bilgileri
        </h4>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Firma Unvanı */}
          {veri['Firma Unvani'] && (
            <div className="md:col-span-2">
              <span className="text-xs text-gray-500 block">Firma Unvanı</span>
              <span className="text-sm font-medium">{veri['Firma Unvani']}</span>
            </div>
          )}

          {/* Kuruluş Tarihi */}
          {veri['Kurulus_Tarihi'] && (
            <div className="flex items-start gap-3">
              <Calendar className="w-4 h-4 text-gray-400 mt-0.5" />
              <div>
                <span className="text-xs text-gray-500 block">Kuruluş Tarihi</span>
                <span className="text-sm font-medium">{veri['Kurulus_Tarihi']}</span>
              </div>
            </div>
          )}

          {/* Sermaye */}
          {veri['Sermaye'] && (
            <div className="flex items-start gap-3">
              <TrendingUp className="w-4 h-4 text-gray-400 mt-0.5" />
              <div>
                <span className="text-xs text-gray-500 block">Sermaye</span>
                <span className="text-sm font-medium">{veri['Sermaye']}</span>
              </div>
            </div>
          )}

          {/* Mersis No */}
          {veri['Mersis Numarasi'] && (
            <div className="flex items-start gap-3">
              <Hash className="w-4 h-4 text-gray-400 mt-0.5" />
              <div>
                <span className="text-xs text-gray-500 block">Mersis Numarası</span>
                <span className="text-sm font-medium font-mono">{veri['Mersis Numarasi']}</span>
              </div>
            </div>
          )}

          {/* Sicil No */}
          {sicil.sicil_no && (
            <div className="flex items-start gap-3">
              <Hash className="w-4 h-4 text-gray-400 mt-0.5" />
              <div>
                <span className="text-xs text-gray-500 block">Sicil No</span>
                <span className="text-sm font-medium font-mono">{sicil.sicil_no}</span>
              </div>
            </div>
          )}

          {/* Sicil Müdürlüğü */}
          {sicil.sicil_mudurlugu && (
            <div className="flex items-start gap-3">
              <Building2 className="w-4 h-4 text-gray-400 mt-0.5" />
              <div>
                <span className="text-xs text-gray-500 block">Sicil Müdürlüğü</span>
                <span className="text-sm font-medium">{sicil.sicil_mudurlugu}</span>
              </div>
            </div>
          )}

          {/* Tescil Konusu */}
          {veri['Tescil Konusu'] && (
            <div className="flex items-start gap-3 md:col-span-2">
              <FileText className="w-4 h-4 text-gray-400 mt-0.5" />
              <div>
                <span className="text-xs text-gray-500 block">Tescil Konusu</span>
                <span className="text-sm font-medium">{veri['Tescil Konusu']}</span>
              </div>
            </div>
          )}

          {/* Faaliyet Konusu */}
          {veri['Faaliyet_Konusu'] && (
            <div className="flex items-start gap-3 md:col-span-2">
              <Briefcase className="w-4 h-4 text-gray-400 mt-0.5" />
              <div>
                <span className="text-xs text-gray-500 block">Faaliyet Konusu</span>
                <span className="text-sm font-medium">{veri['Faaliyet_Konusu']}</span>
              </div>
            </div>
          )}
        </div>
      </Card>

      {/* Yöneticiler */}
      {veri['Yoneticiler'] && veri['Yoneticiler'].length > 0 && (
        <Card className="p-5">
          <h4 className="text-sm font-semibold text-gray-700 mb-4 flex items-center gap-2">
            <Users className="w-4 h-4 text-kkb-600" />
            Yöneticiler
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {veri['Yoneticiler'].map((yonetici, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
                className="p-3 bg-gray-50 rounded-lg"
              >
                <span className="font-medium text-gray-800 block">{yonetici}</span>
              </motion.div>
            ))}
          </div>
        </Card>
      )}

      {/* İmza Yetkilisi */}
      {veri['Imza Yetkilisi'] && (
        <Card className="p-5">
          <h4 className="text-sm font-semibold text-gray-700 mb-4 flex items-center gap-2">
            <PenTool className="w-4 h-4 text-kkb-600" />
            İmza Yetkilisi
          </h4>
          <div className="p-3 bg-gray-50 rounded-lg">
            <span className="font-medium text-gray-800">{veri['Imza Yetkilisi']}</span>
          </div>
        </Card>
      )}

      {/* Gazete Bilgisi */}
      {(gazete.gazete_no || gazete.tarih) && (
        <Card className="p-5">
          <h4 className="text-sm font-semibold text-gray-700 mb-4 flex items-center gap-2">
            <FileText className="w-4 h-4 text-kkb-600" />
            Gazete Bilgisi
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
            {gazete.gazete_no && (
              <div>
                <span className="text-xs text-gray-500 block">Gazete No</span>
                <span className="font-medium">{gazete.gazete_no}</span>
              </div>
            )}
            {gazete.tarih && (
              <div>
                <span className="text-xs text-gray-500 block">Yayın Tarihi</span>
                <span className="font-medium">{gazete.tarih}</span>
              </div>
            )}
            {gazete.ilan_tipi && (
              <div>
                <span className="text-xs text-gray-500 block">İlan Tipi</span>
                <span className="font-medium">{gazete.ilan_tipi}</span>
              </div>
            )}
          </div>
          {toplamIlan > 0 && (
            <div className="mt-3 pt-3 border-t text-sm text-gray-500">
              Toplam {toplamIlan} TSG ilanı bulundu
            </div>
          )}
        </Card>
      )}
    </div>
  );
}
