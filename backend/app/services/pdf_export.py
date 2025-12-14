"""
PDF Export Service
Kapsamli Firma Istihbarat Raporu PDF olusturma
"""
from typing import Optional
from io import BytesIO
from datetime import datetime
import os

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image, KeepTogether
)
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY


class PDFExportService:
    """PDF export servis sinifi - Kapsamli Firma Istihbarat Raporu"""

    # Turkce -> ASCII karakter haritasi
    TR_CHAR_MAP = {
        'ı': 'i', 'İ': 'I', 'ğ': 'g', 'Ğ': 'G',
        'ü': 'u', 'Ü': 'U', 'ş': 's', 'Ş': 'S',
        'ö': 'o', 'Ö': 'O', 'ç': 'c', 'Ç': 'C',
    }

    # Renkler
    KKB_BLUE = colors.HexColor('#1e3a8a')
    KKB_LIGHT_BLUE = colors.HexColor('#3b82f6')
    HEADER_BG = colors.HexColor('#1e3a8a')
    ROW_ALT_BG = colors.HexColor('#f8fafc')
    SUCCESS_GREEN = colors.HexColor('#16a34a')
    WARNING_ORANGE = colors.HexColor('#ea580c')
    DANGER_RED = colors.HexColor('#dc2626')
    INFO_BLUE = colors.HexColor('#0284c7')

    # Risk renk kodlari
    RISK_COLORS = {
        "dusuk": colors.HexColor('#16a34a'),
        "orta_dusuk": colors.HexColor('#84cc16'),
        "orta": colors.HexColor('#eab308'),
        "orta_yuksek": colors.HexColor('#ea580c'),
        "yuksek": colors.HexColor('#dc2626')
    }

    # Karar renk kodlari
    DECISION_COLORS = {
        "onay": colors.HexColor('#16a34a'),
        "sartli_onay": colors.HexColor('#ea580c'),
        "red": colors.HexColor('#dc2626'),
        "inceleme_gerek": colors.HexColor('#0284c7')
    }

    # Risk ve karar ceviri
    RISK_LABELS = {
        "dusuk": "DUSUK RISK",
        "orta_dusuk": "ORTA-DUSUK RISK",
        "orta": "ORTA RISK",
        "orta_yuksek": "ORTA-YUKSEK RISK",
        "yuksek": "YUKSEK RISK"
    }

    DECISION_LABELS = {
        "onay": "ONAY",
        "sartli_onay": "SARTLI ONAY",
        "red": "RED",
        "inceleme_gerek": "INCELEME GEREKLI"
    }

    # Council uye isimleri
    COUNCIL_MEMBER_NAMES = {
        "risk_analyst": "Risk Analisti",
        "business_analyst": "Is Analisti",
        "legal_expert": "Hukuk Uzmani",
        "media_analyst": "Medya Analisti",
        "sector_expert": "Sektor Uzmani",
        "moderator": "Moderator"
    }

    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._create_custom_styles()
        # Logo yolu
        self.logo_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'assets',
            'kkb-logo.png'
        )

    @classmethod
    def _sanitize_text(cls, text) -> str:
        """Turkce karakterleri ASCII'ye cevir - PDF uyumlulugu icin"""
        if text is None:
            return ""
        if not isinstance(text, str):
            text = str(text)
        for tr_char, ascii_char in cls.TR_CHAR_MAP.items():
            text = text.replace(tr_char, ascii_char)
        return text

    def _create_custom_styles(self):
        """Ozel PDF stilleri olustur"""
        # Ana baslik stili
        self.styles.add(ParagraphStyle(
            name='MainTitle',
            parent=self.styles['Heading1'],
            fontSize=22,
            textColor=self.KKB_BLUE,
            spaceAfter=20,
            spaceBefore=10,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))

        # Bolum basligi
        self.styles.add(ParagraphStyle(
            name='SectionTitle',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=colors.white,
            spaceAfter=12,
            spaceBefore=20,
            fontName='Helvetica-Bold',
            backColor=self.KKB_BLUE,
            leftIndent=10,
            rightIndent=10,
            borderPadding=8
        ))

        # Alt bolum basligi
        self.styles.add(ParagraphStyle(
            name='SubSectionTitle',
            parent=self.styles['Heading3'],
            fontSize=12,
            textColor=self.KKB_BLUE,
            spaceAfter=8,
            spaceBefore=12,
            fontName='Helvetica-Bold'
        ))

        # Normal metin
        self.styles.add(ParagraphStyle(
            name='CustomBodyText',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=6,
            alignment=TA_JUSTIFY
        ))

        # Kucuk metin
        self.styles.add(ParagraphStyle(
            name='CustomSmallText',
            parent=self.styles['Normal'],
            fontSize=8,
            spaceAfter=4,
            textColor=colors.grey
        ))

        # Council konusma metni
        self.styles.add(ParagraphStyle(
            name='SpeechText',
            parent=self.styles['Normal'],
            fontSize=9,
            spaceAfter=8,
            leftIndent=20,
            alignment=TA_JUSTIFY
        ))

        # Konusmaci adi
        self.styles.add(ParagraphStyle(
            name='SpeakerName',
            parent=self.styles['Normal'],
            fontSize=10,
            fontName='Helvetica-Bold',
            textColor=self.KKB_BLUE,
            spaceBefore=8
        ))

    def generate_report_pdf(self, report_data: dict) -> BytesIO:
        """
        Kapsamli rapor PDF'i olusturur.

        Args:
            report_data: Rapor verileri dict olarak

        Returns:
            BytesIO: PDF dosyasi binary stream olarak
        """
        pdf_buffer = BytesIO()
        doc = SimpleDocTemplate(
            pdf_buffer,
            pagesize=A4,
            rightMargin=1.5*cm,
            leftMargin=1.5*cm,
            topMargin=1.5*cm,
            bottomMargin=1.5*cm
        )

        # PDF icerigi
        story = []

        # 1. Kapak sayfasi
        story.extend(self._create_cover_page(report_data))
        story.append(PageBreak())

        # 2. Yonetici Ozeti
        story.extend(self._create_executive_summary(report_data))
        story.append(PageBreak())

        # 3. TSG Agent - Sirket Bilgileri
        story.extend(self._create_tsg_section(report_data))
        story.append(PageBreak())

        # 4. Ihale Agent - Kamu Ihale Durumu
        story.extend(self._create_ihale_section(report_data))

        # 5. News Agent - Medya Analizi
        story.extend(self._create_news_section(report_data))
        story.append(PageBreak())

        # 6. Council Degerlendirmesi
        story.extend(self._create_council_section(report_data))

        # 7. Footer
        story.extend(self._create_footer())

        # PDF olustur
        doc.build(story)
        pdf_buffer.seek(0)

        return pdf_buffer

    def _create_cover_page(self, report_data: dict) -> list:
        """Kapak sayfasi olusturur - Profesyonel tasarim"""
        elements = []

        # Ust banner - mavi arka plan
        banner_content = [['']]
        banner = Table(banner_content, colWidths=[18*cm], rowHeights=[0.5*cm])
        banner.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), self.KKB_BLUE),
        ]))
        elements.append(banner)

        elements.append(Spacer(1, 1*cm))

        # Logo
        if os.path.exists(self.logo_path):
            try:
                logo = Image(self.logo_path, width=6*cm, height=2.4*cm)
                logo.hAlign = 'CENTER'
                elements.append(logo)
            except Exception:
                pass

        elements.append(Spacer(1, 0.8*cm))

        # Ana baslik
        title = Paragraph(
            "FIRMA ISTIHBARAT RAPORU",
            self.styles['MainTitle']
        )
        elements.append(title)

        elements.append(Spacer(1, 0.5*cm))

        # Alt baslik
        subtitle = Paragraph(
            "<font color='#64748b'>Kapsamli Risk Degerlendirmesi</font>",
            ParagraphStyle(
                name='Subtitle',
                parent=self.styles['Normal'],
                fontSize=14,
                alignment=TA_CENTER
            )
        )
        elements.append(subtitle)

        elements.append(Spacer(1, 2*cm))

        # Firma bilgileri kutusu - TSG'den gelen verileri kullan
        # TSG verisinden firma unvani ve mersis no al
        agent_results = report_data.get('agent_results', {})
        tsg_data = agent_results.get('tsg', {}).get('data', {})
        tsg_sonuc = tsg_data.get('tsg_sonuc', {})
        yapilandirilmis = tsg_sonuc.get('yapilandirilmis_veri', {})
        sicil_bilgisi = tsg_sonuc.get('sicil_bilgisi', {})

        # TSG'den firma unvani (varsa), yoksa report'tan
        company_name = (
            yapilandirilmis.get('Firma Unvani') or
            tsg_data.get('firma_adi') or
            report_data.get('company_name', 'Bilinmiyor')
        )
        company_name = self._sanitize_text(company_name)

        # Mersis No veya Vergi No
        mersis_no = yapilandirilmis.get('Mersis Numarasi')
        sicil_no = sicil_bilgisi.get('sicil_no')
        tax_no = report_data.get('company_tax_no')

        # Firma bilgi satirlari
        company_box_data = [
            [Paragraph(f"<b>{company_name}</b>",
                      ParagraphStyle(name='CompanyName', fontSize=16, alignment=TA_CENTER, textColor=self.KKB_BLUE))]
        ]

        # Mersis No varsa ekle
        if mersis_no:
            company_box_data.append([Paragraph(f"MERSiS No: {self._sanitize_text(mersis_no)}",
                      ParagraphStyle(name='MersisNo', fontSize=11, alignment=TA_CENTER, textColor=colors.HexColor('#475569')))])

        # Sicil No varsa ekle
        if sicil_no:
            sicil_mud = sicil_bilgisi.get('sicil_mudurlugu', '')
            sicil_text = f"Sicil No: {self._sanitize_text(sicil_no)}"
            if sicil_mud:
                sicil_text += f" ({self._sanitize_text(sicil_mud)})"
            company_box_data.append([Paragraph(sicil_text,
                      ParagraphStyle(name='SicilNo', fontSize=11, alignment=TA_CENTER, textColor=colors.HexColor('#475569')))])

        # Vergi No varsa ekle (TSG'de yoksa)
        if tax_no and not mersis_no:
            company_box_data.append([Paragraph(f"Vergi No: {self._sanitize_text(tax_no)}",
                      ParagraphStyle(name='TaxNo', fontSize=11, alignment=TA_CENTER, textColor=colors.grey))])

        company_box = Table(company_box_data, colWidths=[14*cm])
        company_box.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOX', (0, 0), (-1, -1), 2, self.KKB_BLUE),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
            ('TOPPADDING', (0, 0), (-1, -1), 20),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 20),
        ]))
        elements.append(company_box)

        elements.append(Spacer(1, 2*cm))

        # Sonuc kartlari - Modern tasarim
        final_score = report_data.get('final_score')
        risk_level = report_data.get('risk_level', '')
        decision = report_data.get('decision', '')

        if final_score is not None:
            risk_color = self.RISK_COLORS.get(risk_level, colors.grey)
            decision_color = self.DECISION_COLORS.get(decision, colors.grey)
            risk_label = self.RISK_LABELS.get(risk_level, risk_level.upper() if risk_level else '-')
            decision_label = self.DECISION_LABELS.get(decision, decision.upper() if decision else '-')

            # Risk Skoru karti
            score_card = Table([
                [Paragraph("<font color='white' size='9'><b>RISK SKORU</b></font>",
                          ParagraphStyle(name='sc1', alignment=TA_CENTER))],
                [Paragraph(f"<font color='white' size='28'><b>{final_score}</b></font>",
                          ParagraphStyle(name='sc2', alignment=TA_CENTER))],
                [Paragraph("<font color='#94a3b8' size='10'>/100</font>",
                          ParagraphStyle(name='sc3', alignment=TA_CENTER))]
            ], colWidths=[4.5*cm])
            score_card.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), self.KKB_BLUE),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, -1), (-1, -1), 12),
                ('ROUNDEDCORNERS', [5, 5, 5, 5]),
            ]))

            # Risk Seviyesi karti
            risk_bg = colors.HexColor('#fef3c7') if 'orta' in risk_level else (
                colors.HexColor('#dcfce7') if risk_level == 'dusuk' else colors.HexColor('#fee2e2'))
            risk_card = Table([
                [Paragraph(f"<font color='#64748b' size='9'><b>RISK SEVIYESI</b></font>",
                          ParagraphStyle(name='rc1', alignment=TA_CENTER))],
                [Paragraph(f"<font color='#{risk_color.hexval()[2:]}' size='12'><b>{risk_label}</b></font>",
                          ParagraphStyle(name='rc2', alignment=TA_CENTER))]
            ], colWidths=[4.5*cm])
            risk_card.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), risk_bg),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 15),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
            ]))

            # Karar karti
            decision_bg = colors.HexColor('#dcfce7') if decision == 'onay' else (
                colors.HexColor('#fef3c7') if decision == 'sartli_onay' else colors.HexColor('#fee2e2'))
            decision_card = Table([
                [Paragraph(f"<font color='#64748b' size='9'><b>KARAR</b></font>",
                          ParagraphStyle(name='dc1', alignment=TA_CENTER))],
                [Paragraph(f"<font color='#{decision_color.hexval()[2:]}' size='12'><b>{decision_label}</b></font>",
                          ParagraphStyle(name='dc2', alignment=TA_CENTER))]
            ], colWidths=[4.5*cm])
            decision_card.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), decision_bg),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 15),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
            ]))

            # Kartlari yan yana diz
            cards_row = Table([[score_card, risk_card, decision_card]], colWidths=[5*cm, 5*cm, 5*cm])
            cards_row.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            elements.append(cards_row)

        elements.append(Spacer(1, 2*cm))

        # Rapor bilgileri
        created_at = self._format_datetime(report_data.get('created_at'))
        completed_at = self._format_datetime(report_data.get('completed_at'))

        info_data = [
            ["Rapor Tarihi:", created_at],
            ["Tamamlanma:", completed_at],
        ]

        if report_data.get('duration_seconds'):
            duration = report_data['duration_seconds']
            minutes = duration // 60
            seconds = duration % 60
            info_data.append(["Sure:", f"{minutes} dakika {seconds} saniye"])

        info_table = Table(info_data, colWidths=[4*cm, 10*cm])
        info_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.grey),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        elements.append(info_table)

        return elements

    def _create_executive_summary(self, report_data: dict) -> list:
        """Yonetici ozeti bolumu"""
        elements = []

        # Bolum basligi
        elements.append(self._create_section_header("YONETICI OZETI"))
        elements.append(Spacer(1, 0.5*cm))

        # Karar ozeti
        if report_data.get('decision_summary'):
            elements.append(Paragraph(
                f"<b>Degerlendirme Ozeti:</b>",
                self.styles['SubSectionTitle']
            ))
            elements.append(Paragraph(
                self._sanitize_text(report_data['decision_summary']),
                self.styles['CustomBodyText']
            ))
            elements.append(Spacer(1, 0.5*cm))

        # Council karari varsa ozet bilgiler
        council = report_data.get('council_decision') or report_data.get('council_data')
        if council:
            # Konsensus
            consensus = council.get('consensus')
            if consensus is not None:
                consensus_pct = int(consensus * 100) if consensus <= 1 else int(consensus)
                elements.append(Paragraph(
                    f"<b>Komite Konsensus Orani:</b> %{consensus_pct}",
                    self.styles['CustomBodyText']
                ))

            # Sartlar
            conditions = council.get('conditions', [])
            if conditions and isinstance(conditions, list) and len(conditions) > 0:
                elements.append(Spacer(1, 0.3*cm))
                elements.append(Paragraph("<b>Sartlar ve Oneriler:</b>", self.styles['SubSectionTitle']))
                for i, condition in enumerate(conditions, 1):
                    elements.append(Paragraph(
                        f"{i}. {self._sanitize_text(condition)}",
                        self.styles['CustomBodyText']
                    ))

            # Muhalefet notu
            dissent = council.get('dissent_note')
            if dissent:
                elements.append(Spacer(1, 0.3*cm))
                elements.append(Paragraph(
                    f"<b>Muhalefet Notu:</b> {self._sanitize_text(dissent)}",
                    self.styles['CustomBodyText']
                ))

        elements.append(Spacer(1, 0.5*cm))

        # Agent sonuclari ozet tablosu
        elements.append(Paragraph("<b>Veri Kaynaklari Ozeti:</b>", self.styles['SubSectionTitle']))
        elements.append(Spacer(1, 0.3*cm))

        agent_results = report_data.get('agent_results', {})
        tsg_data = report_data.get('tsg_data') or agent_results.get('tsg', {}).get('data', {})
        ihale_data = report_data.get('ihale_data') or agent_results.get('ihale', {}).get('data', {})
        news_data = report_data.get('news_data') or agent_results.get('news', {}).get('data', {})

        summary_rows = [
            ["Kaynak", "Durum", "Ozet Bulgu"]
        ]

        # TSG ozet
        tsg_status = "Tamamlandi" if tsg_data else "Veri Yok"
        tsg_summary = "-"
        if tsg_data:
            ortaklar = tsg_data.get('ortaklar', [])
            sermaye = tsg_data.get('sermaye', 0)
            tsg_summary = f"{len(ortaklar)} ortak, {self._format_currency(sermaye)} sermaye"
        summary_rows.append(["Ticaret Sicili", tsg_status, self._sanitize_text(tsg_summary)])

        # Ihale ozet
        ihale_status = "Tamamlandi" if ihale_data else "Veri Yok"
        ihale_summary = "-"
        if ihale_data:
            yasak = ihale_data.get('yasak_durumu', False)
            ihale_summary = "AKTIF YASAK MEVCUT!" if yasak else "Yasak bulunmuyor"
        summary_rows.append(["Kamu Ihalesi", ihale_status, self._sanitize_text(ihale_summary)])

        # News ozet
        news_status = "Tamamlandi" if news_data else "Veri Yok"
        news_summary = "-"
        if news_data:
            toplam = news_data.get('toplam_haber', 0)
            sentiment = news_data.get('sentiment_score', 0)
            trend = news_data.get('trend', 'stabil')
            trend_text = {'yukari': 'Yukselis', 'asagi': 'Dusus', 'stabil': 'Stabil'}.get(trend, trend)
            news_summary = f"{toplam} haber, Sentiment: {sentiment:.1f}, Trend: {trend_text}"
        summary_rows.append(["Medya Analizi", news_status, self._sanitize_text(news_summary)])

        summary_table = Table(summary_rows, colWidths=[4*cm, 3*cm, 8*cm])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.KKB_BLUE),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, self.ROW_ALT_BG]),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(summary_table)

        return elements

    def _create_tsg_section(self, report_data: dict) -> list:
        """TSG Agent - Sirket Bilgileri bolumu"""
        elements = []

        elements.append(self._create_section_header("SIRKET BILGILERI (Ticaret Sicili)"))
        elements.append(Spacer(1, 0.5*cm))

        agent_results = report_data.get('agent_results', {})
        tsg_data = report_data.get('tsg_data') or agent_results.get('tsg', {}).get('data', {})

        if not tsg_data:
            elements.append(Paragraph(
                "<i>Ticaret Sicili verisi bulunamadi.</i>",
                self.styles['CustomBodyText']
            ))
            return elements

        # TSG sonuc verisini al
        tsg_sonuc = tsg_data.get('tsg_sonuc', {})
        yapilandirilmis = tsg_sonuc.get('yapilandirilmis_veri', {})
        sicil_bilgisi = tsg_sonuc.get('sicil_bilgisi', {})
        gazete_bilgisi = tsg_sonuc.get('gazete_bilgisi', {})

        # Temel bilgiler
        elements.append(Paragraph("<b>Temel Bilgiler</b>", self.styles['SubSectionTitle']))

        basic_info = []

        # Firma Unvani
        firma_unvani = yapilandirilmis.get('Firma Unvani') or tsg_data.get('firma_adi')
        if firma_unvani:
            basic_info.append(["Firma Unvani:", self._sanitize_text(firma_unvani)])

        # Mersis Numarasi
        mersis = yapilandirilmis.get('Mersis Numarasi')
        if mersis:
            basic_info.append(["MERSiS No:", self._sanitize_text(mersis)])

        # Sicil bilgileri
        if sicil_bilgisi.get('sicil_no'):
            basic_info.append(["Sicil No:", self._sanitize_text(sicil_bilgisi['sicil_no'])])
        if sicil_bilgisi.get('sicil_mudurlugu'):
            basic_info.append(["Sicil Mudurlugu:", self._sanitize_text(sicil_bilgisi['sicil_mudurlugu'])])

        # Kurulus tarihi
        kurulus = yapilandirilmis.get('Kurulus_Tarihi') or tsg_data.get('kurulus_tarihi')
        if kurulus:
            basic_info.append(["Kurulus Tarihi:", self._sanitize_text(kurulus)])

        # Sermaye
        sermaye = yapilandirilmis.get('Sermaye') or tsg_data.get('sermaye')
        if sermaye:
            para_birimi = tsg_data.get('sermaye_para_birimi', 'TL')
            basic_info.append(["Sermaye:", f"{self._format_currency(sermaye)} {para_birimi}"])

        # Faaliyet konusu
        faaliyet = yapilandirilmis.get('Faaliyet_Konusu') or tsg_data.get('faaliyet_konusu')
        if faaliyet:
            basic_info.append(["Faaliyet Konusu:", self._sanitize_text(faaliyet)])

        # Tescil konusu
        tescil = yapilandirilmis.get('Tescil Konusu')
        if tescil:
            basic_info.append(["Tescil Konusu:", self._sanitize_text(tescil)])

        # Imza yetkilisi
        imza = yapilandirilmis.get('Imza Yetkilisi')
        if imza:
            basic_info.append(["Imza Yetkilisi:", self._sanitize_text(imza)])

        if basic_info:
            basic_table = Table(basic_info, colWidths=[4*cm, 11*cm])
            basic_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('TEXTCOLOR', (0, 0), (0, -1), colors.grey),
            ]))
            elements.append(basic_table)
            elements.append(Spacer(1, 0.5*cm))

        # Gazete Bilgileri (yeni eklenen)
        if gazete_bilgisi:
            elements.append(Paragraph("<b>Gazete Bilgileri</b>", self.styles['SubSectionTitle']))
            gazete_info = []
            if gazete_bilgisi.get('gazete_no'):
                gazete_info.append(["Gazete No:", self._sanitize_text(gazete_bilgisi['gazete_no'])])
            if gazete_bilgisi.get('tarih'):
                gazete_info.append(["Tarih:", self._sanitize_text(gazete_bilgisi['tarih'])])
            if gazete_bilgisi.get('ilan_tipi'):
                gazete_info.append(["Ilan Tipi:", self._sanitize_text(gazete_bilgisi['ilan_tipi'])])

            if gazete_info:
                gazete_table = Table(gazete_info, colWidths=[4*cm, 11*cm])
                gazete_table.setStyle(TableStyle([
                    ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
                    ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                    ('TEXTCOLOR', (0, 0), (0, -1), colors.grey),
                ]))
                elements.append(gazete_table)
                elements.append(Spacer(1, 0.5*cm))

        # Toplam ilan sayisi
        toplam_ilan = tsg_sonuc.get('toplam_ilan', 0)
        if toplam_ilan:
            elements.append(Paragraph(
                f"<b>Toplam Bulunan Ilan Sayisi:</b> {toplam_ilan}",
                self.styles['CustomBodyText']
            ))
            elements.append(Spacer(1, 0.3*cm))

        # Ortaklik yapisi
        ortaklar = tsg_data.get('ortaklar', [])
        if ortaklar:
            elements.append(Paragraph("<b>Ortaklik Yapisi</b>", self.styles['SubSectionTitle']))

            ortak_rows = [["Ortak Adi", "Pay Orani"]]
            for ortak in ortaklar:
                ad = self._sanitize_text(ortak.get('ad', '-'))
                pay = ortak.get('pay_orani', 0)
                ortak_rows.append([ad, f"%{pay:.1f}"])

            ortak_table = Table(ortak_rows, colWidths=[10*cm, 5*cm])
            ortak_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), self.KKB_BLUE),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('ALIGN', (1, 0), (1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, self.ROW_ALT_BG]),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            elements.append(ortak_table)
            elements.append(Spacer(1, 0.5*cm))

        # Yonetim kurulu / Yoneticiler
        yonetim = yapilandirilmis.get('Yoneticiler', []) or tsg_data.get('yonetim_kurulu', [])
        if yonetim:
            elements.append(Paragraph("<b>Yonetim Kurulu</b>", self.styles['SubSectionTitle']))

            yk_rows = [["Ad Soyad", "Gorev"]]
            for uye in yonetim:
                # Handle both string and dict formats
                if isinstance(uye, str):
                    ad = self._sanitize_text(uye)
                    gorev = "-"
                elif isinstance(uye, dict):
                    ad = self._sanitize_text(uye.get('ad', '-'))
                    gorev = self._sanitize_text(uye.get('gorev', '-'))
                else:
                    ad = self._sanitize_text(str(uye))
                    gorev = "-"
                yk_rows.append([ad, gorev])

            yk_table = Table(yk_rows, colWidths=[10*cm, 5*cm])
            yk_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), self.KKB_BLUE),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, self.ROW_ALT_BG]),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            elements.append(yk_table)
            elements.append(Spacer(1, 0.5*cm))

        # Sermaye degisiklikleri
        sermaye_deg = tsg_data.get('sermaye_degisiklikleri', [])
        if sermaye_deg:
            elements.append(Paragraph("<b>Sermaye Degisiklikleri</b>", self.styles['SubSectionTitle']))

            sd_rows = [["Tarih", "Eski Sermaye", "Yeni Sermaye"]]
            for deg in sermaye_deg:
                tarih = self._sanitize_text(deg.get('tarih', '-'))
                eski = self._format_currency(deg.get('eski', 0))
                yeni = self._format_currency(deg.get('yeni', 0))
                sd_rows.append([tarih, eski, yeni])

            sd_table = Table(sd_rows, colWidths=[5*cm, 5*cm, 5*cm])
            sd_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), self.KKB_BLUE),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, self.ROW_ALT_BG]),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            elements.append(sd_table)
            elements.append(Spacer(1, 0.5*cm))

        # Yonetici degisiklikleri
        yonetici_deg = tsg_data.get('yonetici_degisiklikleri', [])
        if yonetici_deg:
            elements.append(Paragraph("<b>Yonetici Degisiklikleri</b>", self.styles['SubSectionTitle']))

            yd_rows = [["Tarih", "Gorev", "Eski", "Yeni"]]
            for deg in yonetici_deg:
                tarih = self._sanitize_text(deg.get('tarih', '-'))
                gorev = self._sanitize_text(deg.get('gorev', '-'))
                eski = self._sanitize_text(deg.get('eski', '-'))
                yeni = self._sanitize_text(deg.get('yeni', '-'))
                yd_rows.append([tarih, gorev, eski, yeni])

            yd_table = Table(yd_rows, colWidths=[3*cm, 4*cm, 4*cm, 4*cm])
            yd_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), self.KKB_BLUE),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, self.ROW_ALT_BG]),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            elements.append(yd_table)

        return elements

    def _create_ihale_section(self, report_data: dict) -> list:
        """Ihale Agent - Kamu Ihale Durumu bolumu"""
        elements = []

        elements.append(self._create_section_header("KAMU IHALE DURUMU (EKAP)"))
        elements.append(Spacer(1, 0.5*cm))

        agent_results = report_data.get('agent_results', {})
        ihale_data = report_data.get('ihale_data') or agent_results.get('ihale', {}).get('data', {})

        if not ihale_data:
            elements.append(Paragraph(
                "<i>Kamu ihale verisi bulunamadi.</i>",
                self.styles['CustomBodyText']
            ))
            elements.append(Spacer(1, 0.5*cm))
            return elements

        # Sorgu bilgileri
        elements.append(Paragraph("<b>Sorgu Bilgileri</b>", self.styles['SubSectionTitle']))
        sorgu_info = []
        if ihale_data.get('kaynak'):
            sorgu_info.append(["Kaynak:", self._sanitize_text(ihale_data['kaynak'])])
        if ihale_data.get('sorgu_tarihi'):
            sorgu_info.append(["Sorgu Tarihi:", self._sanitize_text(str(ihale_data['sorgu_tarihi'])[:19])])
        if ihale_data.get('taranan_gun_sayisi'):
            sorgu_info.append(["Taranan Gun:", f"{ihale_data['taranan_gun_sayisi']} gun"])
        if ihale_data.get('risk_degerlendirmesi'):
            sorgu_info.append(["Risk Degerlendirmesi:", self._sanitize_text(ihale_data['risk_degerlendirmesi']).upper()])

        if sorgu_info:
            sorgu_table = Table(sorgu_info, colWidths=[4*cm, 11*cm])
            sorgu_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('TEXTCOLOR', (0, 0), (0, -1), colors.grey),
            ]))
            elements.append(sorgu_table)
            elements.append(Spacer(1, 0.3*cm))

        # Timeout uyarisi
        if ihale_data.get('timeout'):
            timeout_text = Paragraph(
                f"<font color='#ea580c'><b>! Uyari:</b> {self._sanitize_text(ihale_data.get('timeout_mesaj', 'Tarama timeout oldu'))}</font>",
                self.styles['CustomBodyText']
            )
            elements.append(timeout_text)
            elements.append(Spacer(1, 0.3*cm))

        # Yasak durumu
        yasak_durumu = ihale_data.get('yasak_durumu', False)

        if yasak_durumu:
            # Kirmizi uyari kutusu
            warning_text = Paragraph(
                "<font color='white'><b>! DIKKAT: AKTIF KAMU IHALE YASAGI MEVCUT</b></font>",
                ParagraphStyle(name='WarningText', fontSize=12, alignment=TA_CENTER)
            )
            warning_table = Table([[warning_text]], colWidths=[15*cm])
            warning_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), self.DANGER_RED),
                ('TOPPADDING', (0, 0), (-1, -1), 12),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ]))
            elements.append(warning_table)
            elements.append(Spacer(1, 0.5*cm))
        else:
            # Yesil onay kutusu
            ok_text = Paragraph(
                "<font color='white'><b>Aktif kamu ihale yasagi bulunmamaktadir</b></font>",
                ParagraphStyle(name='OkText', fontSize=12, alignment=TA_CENTER)
            )
            ok_table = Table([[ok_text]], colWidths=[15*cm])
            ok_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), self.SUCCESS_GREEN),
                ('TOPPADDING', (0, 0), (-1, -1), 12),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ]))
            elements.append(ok_table)
            elements.append(Spacer(1, 0.5*cm))

        # Aktif yasak detayi
        aktif_yasak = ihale_data.get('aktif_yasak')
        if aktif_yasak:
            elements.append(Paragraph("<b>Aktif Yasak Detayi</b>", self.styles['SubSectionTitle']))

            yasak_info = [
                ["Sebep:", self._sanitize_text(aktif_yasak.get('sebep', '-'))],
                ["Baslangic:", self._sanitize_text(aktif_yasak.get('baslangic', '-'))],
                ["Bitis:", self._sanitize_text(aktif_yasak.get('bitis', '-'))],
                ["Kurum:", self._sanitize_text(aktif_yasak.get('kurum', '-'))],
            ]

            yasak_table = Table(yasak_info, colWidths=[3*cm, 12*cm])
            yasak_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#fef2f2')),
                ('BOX', (0, 0), (-1, -1), 1, self.DANGER_RED),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            elements.append(yasak_table)
            elements.append(Spacer(1, 0.5*cm))

        # Yasaklamalar listesi (gecmis_yasaklar veya yasaklamalar)
        gecmis_yasaklar = ihale_data.get('gecmis_yasaklar', []) or ihale_data.get('yasaklamalar', [])
        if gecmis_yasaklar:
            elements.append(Paragraph("<b>Gecmis Yasaklar</b>", self.styles['SubSectionTitle']))

            gecmis_rows = [["Sebep", "Baslangic", "Bitis", "Kurum"]]
            for yasak in gecmis_yasaklar:
                gecmis_rows.append([
                    self._sanitize_text(yasak.get('sebep', '-')),
                    self._sanitize_text(yasak.get('baslangic', '-')),
                    self._sanitize_text(yasak.get('bitis', '-')),
                    self._sanitize_text(yasak.get('kurum', '-'))
                ])

            gecmis_table = Table(gecmis_rows, colWidths=[5*cm, 3*cm, 3*cm, 4*cm])
            gecmis_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), self.KKB_BLUE),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, self.ROW_ALT_BG]),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ]))
            elements.append(gecmis_table)

        elements.append(Spacer(1, 0.5*cm))
        return elements

    def _create_news_section(self, report_data: dict) -> list:
        """News Agent - Medya Analizi bolumu"""
        elements = []

        elements.append(self._create_section_header("MEDYA ANALIZI"))
        elements.append(Spacer(1, 0.5*cm))

        agent_results = report_data.get('agent_results', {})
        news_data = report_data.get('news_data') or agent_results.get('news', {}).get('data', {})

        if not news_data:
            elements.append(Paragraph(
                "<i>Medya analizi verisi bulunamadi.</i>",
                self.styles['CustomBodyText']
            ))
            elements.append(Spacer(1, 0.5*cm))
            return elements

        # Ozet istatistikler
        elements.append(Paragraph("<b>Haber Istatistikleri</b>", self.styles['SubSectionTitle']))

        # Ozet verisini al (nested veya flat)
        ozet = news_data.get('ozet', {})
        toplam = ozet.get('toplam', 0) or news_data.get('toplam_haber', 0)
        pozitif = ozet.get('olumlu', 0) or news_data.get('pozitif', 0)
        negatif = ozet.get('olumsuz', 0) or news_data.get('negatif', 0)
        notr = toplam - pozitif - negatif if toplam > 0 else news_data.get('notr', 0)
        sentiment = ozet.get('sentiment_score', 0) or news_data.get('sentiment_score', 0)
        trend = ozet.get('trend', 'stabil') or news_data.get('trend', 'stabil')

        trend_map = {'yukari': 'Yukselis', 'asagi': 'Dusus', 'stabil': 'Stabil', 'pozitif': 'Pozitif', 'negatif': 'Negatif'}
        trend_text = trend_map.get(trend, str(trend).title() if trend else 'Stabil')
        trend_color = {'yukari': self.SUCCESS_GREEN, 'asagi': self.DANGER_RED, 'stabil': colors.grey, 'pozitif': self.SUCCESS_GREEN, 'negatif': self.DANGER_RED}.get(trend, colors.grey)

        stats_data = [
            ["Toplam Haber", "Pozitif", "Negatif", "Notr", "Sentiment", "Trend"],
            [str(toplam), str(pozitif), str(negatif), str(notr), f"{sentiment:.2f}", trend_text]
        ]

        stats_table = Table(stats_data, colWidths=[2.5*cm, 2.5*cm, 2.5*cm, 2.5*cm, 2.5*cm, 2.5*cm])
        stats_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.KKB_BLUE),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('BACKGROUND', (1, 1), (1, 1), colors.HexColor('#dcfce7')),  # Pozitif - yesil
            ('BACKGROUND', (2, 1), (2, 1), colors.HexColor('#fee2e2')),  # Negatif - kirmizi
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(stats_table)
        elements.append(Spacer(1, 0.5*cm))

        # Kaynak dagilimi
        kaynak_dagilimi = news_data.get('kaynak_dagilimi', {})
        if kaynak_dagilimi:
            elements.append(Paragraph("<b>Kaynak Dagilimi</b>", self.styles['SubSectionTitle']))

            kaynak_rows = [["Kaynak", "Toplam", "Olumlu", "Olumsuz"]]
            for kaynak, data in kaynak_dagilimi.items():
                if isinstance(data, dict):
                    kaynak_rows.append([
                        self._sanitize_text(kaynak),
                        str(data.get('total', 0)),
                        str(data.get('olumlu', 0)),
                        str(data.get('olumsuz', 0))
                    ])

            if len(kaynak_rows) > 1:
                kaynak_table = Table(kaynak_rows, colWidths=[6*cm, 3*cm, 3*cm, 3*cm])
                kaynak_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), self.KKB_BLUE),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, self.ROW_ALT_BG]),
                    ('TOPPADDING', (0, 0), (-1, -1), 6),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ]))
                elements.append(kaynak_table)
                elements.append(Spacer(1, 0.5*cm))

        # Haberler listesi (onemli_haberler veya haberler)
        haberler = news_data.get('onemli_haberler', []) or news_data.get('haberler', [])
        if haberler:
            elements.append(Paragraph("<b>Haberler</b>", self.styles['SubSectionTitle']))

            for i, haber in enumerate(haberler[:15], 1):  # Ilk 15 haber
                baslik = self._sanitize_text(haber.get('baslik', '-'))
                kaynak = self._sanitize_text(haber.get('kaynak', '-'))
                tarih = self._sanitize_text(haber.get('tarih', '-'))
                haber_sentiment = haber.get('sentiment', 'notr')

                # Sentiment mapping (olumlu/olumsuz veya pozitif/negatif)
                sentiment_map = {'olumlu': 'pozitif', 'olumsuz': 'negatif', 'pozitif': 'pozitif', 'negatif': 'negatif'}
                normalized_sentiment = sentiment_map.get(haber_sentiment, 'notr')

                sentiment_emoji = {'pozitif': '[+]', 'negatif': '[-]', 'notr': '[o]'}.get(normalized_sentiment, '[o]')
                sentiment_color = {'pozitif': '#16a34a', 'negatif': '#dc2626', 'notr': '#64748b'}.get(normalized_sentiment, '#64748b')

                haber_text = f"<font color='{sentiment_color}'><b>{sentiment_emoji}</b></font> {baslik[:100]}{'...' if len(baslik) > 100 else ''}"
                haber_meta = f"<font color='#94a3b8' size='8'>{kaynak} - {tarih}</font>"

                elements.append(Paragraph(haber_text, self.styles['CustomBodyText']))
                elements.append(Paragraph(haber_meta, self.styles['CustomSmallText']))
                elements.append(Spacer(1, 0.2*cm))

        elements.append(Spacer(1, 0.3*cm))
        return elements

    def _create_council_section(self, report_data: dict) -> list:
        """Council degerlendirmesi bolumu"""
        elements = []

        elements.append(self._create_section_header("KOMITE DEGERLENDIRMESI"))
        elements.append(Spacer(1, 0.5*cm))

        council = report_data.get('council_decision') or report_data.get('council_data')

        if not council:
            elements.append(Paragraph(
                "<i>Komite degerlendirmesi bulunamadi.</i>",
                self.styles['CustomBodyText']
            ))
            return elements

        # Komite skorlari
        scores = council.get('scores', {})
        initial_scores = scores.get('initial', {})
        final_scores = scores.get('final', {}) or council.get('final_scores', {})

        if initial_scores or final_scores:
            elements.append(Paragraph("<b>Komite Uye Skorlari</b>", self.styles['SubSectionTitle']))

            score_rows = [["Uye", "Ilk Skor", "Final Skor", "Degisim"]]

            all_members = set(list(initial_scores.keys()) + list(final_scores.keys()))
            for member in all_members:
                member_name = self.COUNCIL_MEMBER_NAMES.get(member, member.replace('_', ' ').title())
                initial = initial_scores.get(member, '-')
                final = final_scores.get(member, '-')

                if isinstance(initial, (int, float)) and isinstance(final, (int, float)):
                    diff = final - initial
                    diff_text = f"+{diff}" if diff > 0 else str(diff)
                else:
                    diff_text = '-'

                score_rows.append([
                    self._sanitize_text(member_name),
                    str(initial) if initial != '-' else '-',
                    str(final) if final != '-' else '-',
                    diff_text
                ])

            score_table = Table(score_rows, colWidths=[5*cm, 3*cm, 3*cm, 3*cm])
            score_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), self.KKB_BLUE),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, self.ROW_ALT_BG]),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            elements.append(score_table)
            elements.append(Spacer(1, 0.5*cm))

        # Karar gerekcesi
        rationale = council.get('decision_rationale') or council.get('summary')
        if rationale:
            elements.append(Paragraph("<b>Karar Gerekcesi</b>", self.styles['SubSectionTitle']))
            elements.append(Paragraph(
                self._sanitize_text(rationale),
                self.styles['CustomBodyText']
            ))
            elements.append(Spacer(1, 0.5*cm))

        # Komite tartismasi (transcript)
        transcript = council.get('transcript', [])
        if transcript:
            elements.append(PageBreak())
            elements.append(self._create_section_header("KOMITE TARTISMASI (Tam Transkript)"))
            elements.append(Spacer(1, 0.5*cm))

            current_phase = None
            phase_titles = {
                'opening': 'Acilis',
                'presentation': 'Sunum',
                'discussion': 'Tartisma',
                'decision': 'Karar',
                # Integer phase degerleri icin
                '1': 'Acilis',
                '2': 'Sunum',
                '3': 'Tartisma',
                '4': 'Karar'
            }

            for entry in transcript:
                # Faz degisimi
                phase = entry.get('phase')
                if phase is not None and phase != current_phase:
                    current_phase = phase
                    # phase integer veya string olabilir
                    phase_key = str(phase) if isinstance(phase, int) else phase
                    phase_title = phase_titles.get(phase_key, f"Faz {phase}")
                    elements.append(Spacer(1, 0.3*cm))
                    elements.append(Paragraph(
                        f"<b>--- {phase_title} ---</b>",
                        ParagraphStyle(name='PhaseHeader', fontSize=10, alignment=TA_CENTER, textColor=colors.grey)
                    ))
                    elements.append(Spacer(1, 0.2*cm))

                # Konusmaci
                speaker_name = self._sanitize_text(entry.get('speaker_name', 'Bilinmeyen'))
                speaker_emoji = entry.get('speaker_emoji', '')
                risk_score = entry.get('risk_score')

                speaker_text = f"{speaker_emoji} <b>{speaker_name}</b>"
                if risk_score is not None:
                    speaker_text += f" <font color='#64748b'>(Skor: {risk_score})</font>"

                elements.append(Paragraph(speaker_text, self.styles['SpeakerName']))

                # Konusma icerigi
                content = self._sanitize_text(entry.get('content', ''))
                if content:
                    elements.append(Paragraph(content, self.styles['SpeechText']))

        return elements

    def _create_footer(self) -> list:
        """PDF footer olusturur"""
        elements = []

        elements.append(Spacer(1, 1*cm))

        # Ayirici cizgi
        line = Table([['']], colWidths=[15*cm])
        line.setStyle(TableStyle([
            ('LINEABOVE', (0, 0), (-1, 0), 1, colors.HexColor('#e2e8f0')),
        ]))
        elements.append(line)

        elements.append(Spacer(1, 0.3*cm))

        # Footer metni
        footer_text = Paragraph(
            "<font color='#94a3b8' size='8'>Bu rapor KKB Agentic AI sistemi tarafindan otomatik olarak olusturulmustur. "
            "Rapor icerigi yalnizca bilgilendirme amaclidir ve nihai karar icin kullanilmadan once dogrulanmalidir.</font>",
            ParagraphStyle(name='FooterText', fontSize=8, alignment=TA_CENTER)
        )
        elements.append(footer_text)

        elements.append(Spacer(1, 0.3*cm))

        footer_brand = Paragraph(
            "<font color='#64748b' size='9'><b>KKB Agentic AI Hackathon 2024</b></font>",
            ParagraphStyle(name='FooterBrand', fontSize=9, alignment=TA_CENTER)
        )
        elements.append(footer_brand)

        return elements

    def _create_section_header(self, title: str, icon: str = "") -> Table:
        """Bolum basligi olusturur - Modern tasarim"""
        # Sol tarafta mavi cizgi, beyaz arka plan
        accent_cell = Table([['']], colWidths=[0.4*cm], rowHeights=[0.8*cm])
        accent_cell.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), self.KKB_BLUE),
        ]))

        title_text = f"{icon} {title}" if icon else title
        header_para = Paragraph(
            f"<font color='#1e3a8a' size='13'><b>{title_text}</b></font>",
            ParagraphStyle(name='SectionHeader', fontSize=13, alignment=TA_LEFT)
        )

        header_table = Table([[accent_cell, header_para]], colWidths=[0.5*cm, 16.5*cm])
        header_table.setStyle(TableStyle([
            ('BACKGROUND', (1, 0), (-1, -1), colors.HexColor('#f1f5f9')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (1, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (1, 0), (-1, -1), 10),
            ('LEFTPADDING', (1, 0), (-1, -1), 12),
        ]))
        return header_table

    def _format_datetime(self, dt) -> str:
        """Datetime formatlar"""
        if not dt:
            return '-'
        if isinstance(dt, str):
            try:
                dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
            except:
                return dt
        if isinstance(dt, datetime):
            return dt.strftime('%d.%m.%Y %H:%M')
        return str(dt)

    def _format_currency(self, amount) -> str:
        """Para birimi formatlar"""
        if not amount:
            return "0"
        try:
            return "{:,.0f}".format(float(amount)).replace(",", ".")
        except:
            return str(amount)

    def generate_filename(self, company_name: str) -> str:
        """PDF dosya adi olusturur (ASCII karakterler, HTTP header uyumlu)"""
        # Turkce karakterleri ASCII'ye cevir
        for tr_char, ascii_char in self.TR_CHAR_MAP.items():
            company_name = company_name.replace(tr_char, ascii_char)

        # Sadece ASCII alfanumerik ve bosluk/tire/alt cizgi
        safe_name = "".join(c for c in company_name if c.isascii() and (c.isalnum() or c in (' ', '-', '_'))).strip()
        safe_name = safe_name.replace(' ', '_')
        date_str = datetime.now().strftime('%Y-%m-%d')
        return f"{safe_name}_Istihbarat_Raporu_{date_str}.pdf"
