/**
 * IhaleResults Component
 * İhale yasaklılık agent sonuçları
 *
 * Backend'den gelen veri yapısı:
 * {
 *   firma_adi: string,
 *   vergi_no: string,
 *   taranan_gun_sayisi: number,
 *   bulunan_toplam_yasaklama: number,
 *   yasak_durumu: boolean,
 *   yasak_kayit_no: string,
 *   ihale_kayit_no: string,
 *   yasaklayan_kurum: string,
 *   ihale_idaresi: { adi: string, adresi: string },
 *   yasakli_kisi: { adi: string, vergi_no: string, tc: string, adresi: string },
 *   ortaklar: string[],
 *   kanun_dayanagi: string,
 *   yasak_kapsami: string,
 *   yasak_suresi: string,
 *   resmi_gazete: { sayi: string, tarih: string },
 *   risk_degerlendirmesi: "dusuk" | "orta" | "yuksek",
 *   sorgu_tarihi: string,
 *   kaynak: string
 * }
 */

import { Gavel, CheckCircle2, AlertTriangle, Calendar, Building, Hash, Scale, Users, FileText, Clock } from 'lucide-react';
import { Card } from '@/components/ui/card';

// Backend'den gelen gerçek veri yapısı
interface IhaleBackendData {
  firma_adi?: string;
  vergi_no?: string;
  taranan_gun_sayisi?: number;
  bulunan_toplam_yasaklama?: number;
  yasak_durumu?: boolean;
  yasak_kayit_no?: string;
  ihale_kayit_no?: string;
  yasaklayan_kurum?: string;
  ihale_idaresi?: {
    adi?: string;
    adresi?: string;
  };
  yasakli_kisi?: {
    adi?: string;
    vergi_no?: string;
    tc?: string;
    adresi?: string;
  };
  ortaklar?: Array<{ ad_soyad?: string; tc?: string } | string>;
  kanun_dayanagi?: string;
  yasak_kapsami?: string;
  yasak_suresi?: string;
  resmi_gazete?: {
    sayi?: string;
    tarih?: string;
  };
  risk_degerlendirmesi?: 'dusuk' | 'orta' | 'yuksek';
  sorgu_tarihi?: string;
  kaynak?: string;
}

interface IhaleResultsProps {
  data: IhaleBackendData;
}

function getRiskBadgeStyle(risk?: string) {
  switch (risk) {
    case 'yuksek':
      return 'bg-red-100 text-red-700 border-red-200';
    case 'orta':
      return 'bg-yellow-100 text-yellow-700 border-yellow-200';
    case 'dusuk':
    default:
      return 'bg-green-100 text-green-700 border-green-200';
  }
}

function getRiskLabel(risk?: string) {
  switch (risk) {
    case 'yuksek':
      return 'Yüksek Risk';
    case 'orta':
      return 'Orta Risk';
    case 'dusuk':
    default:
      return 'Düşük Risk';
  }
}

export function IhaleResults({ data }: IhaleResultsProps) {
  // Yasak durumu kontrolü - hem yasak_durumu hem de bulunan_toplam_yasaklama > 0 kontrol et
  // Eğer yasak_durumu true ise veya bu firmaya ait yasaklama varsa
  const hasYasak = data?.yasak_durumu === true;

  // Resmi Gazete'de bulunan toplam yasaklama (genel sistem)
  const toplamYasaklama = data?.bulunan_toplam_yasaklama || 0;

  return (
    <div className="space-y-6">
      {/* Durum Kartı */}
      <Card className="p-5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className={`p-3 rounded-full ${hasYasak ? 'bg-red-100' : 'bg-green-100'}`}>
              {hasYasak ? (
                <AlertTriangle className="w-6 h-6 text-red-600" />
              ) : (
                <CheckCircle2 className="w-6 h-6 text-green-600" />
              )}
            </div>
            <div>
              <h4 className="text-lg font-semibold">
                {hasYasak ? 'Aktif İhale Yasağı Mevcut' : 'İhale Yasağı Bulunmuyor'}
              </h4>
              <p className="text-sm text-gray-500">
                {hasYasak
                  ? 'Firma şu anda kamu ihalelerine katılma yasağı altındadır.'
                  : 'Firma kamu ihalelerine katılabilir durumda.'}
              </p>
            </div>
          </div>

          {/* Risk Badge */}
          {data?.risk_degerlendirmesi && (
            <span className={`px-3 py-1 text-sm font-medium rounded-full border ${getRiskBadgeStyle(data.risk_degerlendirmesi)}`}>
              {getRiskLabel(data.risk_degerlendirmesi)}
            </span>
          )}
        </div>

        {/* Tarama Bilgisi */}
        {(data?.taranan_gun_sayisi || toplamYasaklama > 0) && (
          <div className="mt-4 pt-4 border-t flex flex-wrap gap-4 text-sm text-gray-500">
            {data.taranan_gun_sayisi && (
              <div className="flex items-center gap-1">
                <Clock className="w-4 h-4" />
                <span>Son {data.taranan_gun_sayisi} gün tarandı</span>
              </div>
            )}
            {toplamYasaklama > 0 && (
              <div className="flex items-center gap-1">
                <FileText className="w-4 h-4" />
                <span>
                  Resmi Gazete'de {toplamYasaklama} yasaklama kararı incelendi
                  {!hasYasak && ' (bu firmaya ait değil)'}
                </span>
              </div>
            )}
          </div>
        )}
      </Card>

      {/* Aktif Yasak Detayı */}
      {hasYasak && (
        <Card className="p-5">
          <h4 className="text-sm font-semibold text-red-700 mb-4 flex items-center gap-2">
            <Gavel className="w-4 h-4" />
            Yasak Detayları
          </h4>

          <div className="space-y-4">
            {/* Yasaklayan Kurum */}
            {data.yasaklayan_kurum && (
              <div className="flex items-start gap-3">
                <Building className="w-4 h-4 text-gray-400 mt-0.5" />
                <div>
                  <span className="text-xs text-gray-500 block">Yasaklayan Kurum</span>
                  <span className="text-sm font-medium">{data.yasaklayan_kurum}</span>
                </div>
              </div>
            )}

            {/* İhale İdaresi */}
            {data.ihale_idaresi?.adi && (
              <div className="flex items-start gap-3">
                <Building className="w-4 h-4 text-gray-400 mt-0.5" />
                <div>
                  <span className="text-xs text-gray-500 block">İhale İdaresi</span>
                  <span className="text-sm font-medium">{data.ihale_idaresi.adi}</span>
                  {data.ihale_idaresi.adresi && (
                    <span className="text-xs text-gray-400 block">{data.ihale_idaresi.adresi}</span>
                  )}
                </div>
              </div>
            )}

            {/* Kayıt Numaraları */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {data.yasak_kayit_no && (
                <div className="flex items-start gap-3">
                  <Hash className="w-4 h-4 text-gray-400 mt-0.5" />
                  <div>
                    <span className="text-xs text-gray-500 block">Yasak Kayıt No</span>
                    <span className="text-sm font-medium font-mono">{data.yasak_kayit_no}</span>
                  </div>
                </div>
              )}

              {data.ihale_kayit_no && (
                <div className="flex items-start gap-3">
                  <Hash className="w-4 h-4 text-gray-400 mt-0.5" />
                  <div>
                    <span className="text-xs text-gray-500 block">İhale Kayıt No</span>
                    <span className="text-sm font-medium font-mono">{data.ihale_kayit_no}</span>
                  </div>
                </div>
              )}
            </div>

            {/* Yasak Kapsamı ve Süresi */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {data.yasak_kapsami && (
                <div className="flex items-start gap-3">
                  <Scale className="w-4 h-4 text-gray-400 mt-0.5" />
                  <div>
                    <span className="text-xs text-gray-500 block">Yasak Kapsamı</span>
                    <span className="text-sm font-medium">{data.yasak_kapsami}</span>
                  </div>
                </div>
              )}

              {data.yasak_suresi && (
                <div className="flex items-start gap-3">
                  <Calendar className="w-4 h-4 text-gray-400 mt-0.5" />
                  <div>
                    <span className="text-xs text-gray-500 block">Yasak Süresi</span>
                    <span className="text-sm font-medium">{data.yasak_suresi}</span>
                  </div>
                </div>
              )}
            </div>

            {/* Kanun Dayanağı */}
            {data.kanun_dayanagi && (
              <div className="flex items-start gap-3">
                <Scale className="w-4 h-4 text-gray-400 mt-0.5" />
                <div>
                  <span className="text-xs text-gray-500 block">Kanun Dayanağı</span>
                  <span className="text-sm font-medium">{data.kanun_dayanagi}</span>
                </div>
              </div>
            )}

            {/* Yasaklı Kişi */}
            {data.yasakli_kisi?.adi && (
              <div className="flex items-start gap-3">
                <Users className="w-4 h-4 text-gray-400 mt-0.5" />
                <div>
                  <span className="text-xs text-gray-500 block">Yasaklı Kişi/Firma</span>
                  <span className="text-sm font-medium">{data.yasakli_kisi.adi}</span>
                  {data.yasakli_kisi.vergi_no && (
                    <span className="text-xs text-gray-400 block">VKN: {data.yasakli_kisi.vergi_no}</span>
                  )}
                </div>
              </div>
            )}

            {/* Ortaklar */}
            {data.ortaklar && data.ortaklar.length > 0 && (
              <div className="flex items-start gap-3">
                <Users className="w-4 h-4 text-gray-400 mt-0.5" />
                <div>
                  <span className="text-xs text-gray-500 block">Ortaklar</span>
                  <div className="flex flex-wrap gap-2 mt-1">
                    {data.ortaklar.map((ortak, i) => (
                      <span key={i} className="text-xs bg-gray-100 px-2 py-1 rounded">
                        {typeof ortak === 'string' ? ortak : ortak.ad_soyad}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Resmi Gazete */}
            {data.resmi_gazete && (data.resmi_gazete.sayi || data.resmi_gazete.tarih) && (
              <div className="flex items-start gap-3">
                <FileText className="w-4 h-4 text-gray-400 mt-0.5" />
                <div>
                  <span className="text-xs text-gray-500 block">Resmi Gazete</span>
                  <span className="text-sm font-medium">
                    {data.resmi_gazete.sayi && `Sayı: ${data.resmi_gazete.sayi}`}
                    {data.resmi_gazete.sayi && data.resmi_gazete.tarih && ' - '}
                    {data.resmi_gazete.tarih && `Tarih: ${data.resmi_gazete.tarih}`}
                  </span>
                </div>
              </div>
            )}
          </div>
        </Card>
      )}

      {/* Temiz Sicil - Yasak Yoksa */}
      {!hasYasak && (
        <Card className="p-5">
          <div className="text-center py-6">
            <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <CheckCircle2 className="w-8 h-8 text-green-600" />
            </div>
            <h4 className="font-semibold text-gray-800 mb-1">Temiz Sicil</h4>
            <p className="text-sm text-gray-500">
              Resmi Gazete kayıtlarında bu firma için aktif ihale yasağı bulunmamaktadır.
            </p>
            {data?.kaynak && (
              <p className="text-xs text-gray-400 mt-2">
                Kaynak: {data.kaynak}
              </p>
            )}
          </div>
        </Card>
      )}
    </div>
  );
}
