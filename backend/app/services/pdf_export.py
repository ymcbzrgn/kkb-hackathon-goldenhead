"""
PDF Export Service
Rapor PDF dışa aktarma
"""
from typing import Optional
from io import BytesIO
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT


class PDFExportService:
    """PDF export servis sınıfı"""

    # Risk renk kodları
    RISK_COLORS = {
        "dusuk": colors.green,
        "orta_dusuk": colors.lightgreen,
        "orta": colors.yellow,
        "orta_yuksek": colors.orange,
        "yuksek": colors.red
    }

    # Karar renk kodları
    DECISION_COLORS = {
        "onay": colors.green,
        "sartli_onay": colors.orange,
        "red": colors.red,
        "inceleme_gerek": colors.blue
    }

    # Risk ve karar çeviri
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

    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._create_custom_styles()

    def _create_custom_styles(self):
        """Özel PDF stilleri oluştur"""
        # Başlık stili
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#1e3a8a'),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))

        # Alt başlık stili
        self.styles.add(ParagraphStyle(
            name='CustomHeading',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#1e3a8a'),
            spaceAfter=12,
            spaceBefore=12,
            fontName='Helvetica-Bold'
        ))

        # Normal metin
        self.styles.add(ParagraphStyle(
            name='CustomBody',
            parent=self.styles['BodyText'],
            fontSize=10,
            spaceAfter=6
        ))

    def generate_report_pdf(self, report_data: dict) -> BytesIO:
        """
        Rapor verilerinden PDF oluşturur.

        Args:
            report_data: Rapor verileri dict olarak

        Returns:
            BytesIO: PDF dosyası binary stream olarak
        """
        pdf_buffer = BytesIO()
        doc = SimpleDocTemplate(
            pdf_buffer,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )

        # PDF içeriği
        story = []

        # 1. Başlık bölümü
        story.extend(self._create_header(report_data))

        # 2. Özet bölümü
        story.extend(self._create_summary(report_data))

        # 3. Agent sonuçları
        story.extend(self._create_agent_results(report_data))

        # 4. Council kararı
        if report_data.get('council_decision'):
            story.extend(self._create_council_decision(report_data))

        # 5. Footer
        story.extend(self._create_footer())

        # PDF oluştur
        doc.build(story)
        pdf_buffer.seek(0)

        return pdf_buffer

    def _create_header(self, report_data: dict) -> list:
        """PDF başlığını oluşturur"""
        elements = []

        # Ana başlık
        title = Paragraph(
            "FIRMA ISTIHBARAT RAPORU",
            self.styles['CustomTitle']
        )
        elements.append(title)
        elements.append(Spacer(1, 0.3*cm))

        # Firma bilgileri tablosu
        company_data = [
            ["Firma Adi:", report_data.get('company_name', 'Bilinmiyor')],
            ["Vergi No:", report_data.get('company_tax_no', '-')],
            ["Rapor Tarihi:", self._format_datetime(report_data.get('created_at'))],
        ]

        if report_data.get('completed_at'):
            company_data.append([
                "Tamamlanma Tarihi:",
                self._format_datetime(report_data.get('completed_at'))
            ])

        company_table = Table(company_data, colWidths=[4*cm, 12*cm])
        company_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))

        elements.append(company_table)
        elements.append(Spacer(1, 0.5*cm))

        # Ayırıcı çizgi
        elements.append(self._create_line())

        return elements

    def _create_summary(self, report_data: dict) -> list:
        """Özet bölümünü oluşturur"""
        elements = []

        # Başlık
        elements.append(Paragraph("OZET", self.styles['CustomHeading']))
        elements.append(Spacer(1, 0.3*cm))

        # Skor ve karar tablosu
        final_score = report_data.get('final_score')
        risk_level = report_data.get('risk_level', '')
        decision = report_data.get('decision', '')

        summary_data = []

        # Risk skoru
        if final_score is not None:
            summary_data.append([
                "Risk Skoru:",
                f"{final_score}/100"
            ])

        # Risk seviyesi
        if risk_level:
            risk_label = self.RISK_LABELS.get(risk_level, risk_level.upper())
            summary_data.append([
                "Risk Seviyesi:",
                risk_label
            ])

        # Karar
        if decision:
            decision_label = self.DECISION_LABELS.get(decision, decision.upper())
            summary_data.append([
                "Final Karar:",
                decision_label
            ])

        # Konsensüs (eğer council decision varsa)
        council = report_data.get('council_decision')
        if council and council.get('consensus') is not None:
            consensus_pct = int(council.get('consensus') * 100)
            summary_data.append([
                "Konsensus:",
                f"%{consensus_pct}"
            ])

        if summary_data:
            summary_table = Table(summary_data, colWidths=[4*cm, 12*cm])
            summary_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 11),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f3f4f6')),
                ('BOX', (0, 0), (-1, -1), 1, colors.grey),
            ]))
            elements.append(summary_table)

        # Karar özeti (eğer varsa)
        if report_data.get('decision_summary'):
            elements.append(Spacer(1, 0.3*cm))
            summary_text = Paragraph(
                f"<b>Karar Ozeti:</b> {report_data.get('decision_summary')}",
                self.styles['CustomBody']
            )
            elements.append(summary_text)

        elements.append(Spacer(1, 0.5*cm))
        elements.append(self._create_line())

        return elements

    def _create_agent_results(self, report_data: dict) -> list:
        """Agent sonuçlarını oluşturur"""
        elements = []
        agent_results = report_data.get('agent_results', {})

        if not agent_results:
            return elements

        # Başlık
        elements.append(Paragraph("AGENT SONUCLARI", self.styles['CustomHeading']))
        elements.append(Spacer(1, 0.3*cm))

        # TSG Agent
        if 'tsg_agent' in agent_results:
            elements.extend(self._create_tsg_section(agent_results['tsg_agent']))

        # İhale Agent
        if 'ihale_agent' in agent_results:
            elements.extend(self._create_ihale_section(agent_results['ihale_agent']))

        # News Agent
        if 'news_agent' in agent_results:
            elements.extend(self._create_news_section(agent_results['news_agent']))

        elements.append(self._create_line())

        return elements

    def _create_tsg_section(self, tsg_data: dict) -> list:
        """TSG Agent bölümünü oluşturur"""
        elements = []

        elements.append(Paragraph("<b>TSG Agent:</b>", self.styles['CustomBody']))
        elements.append(Spacer(1, 0.2*cm))

        # Özet
        if tsg_data.get('summary'):
            elements.append(Paragraph(tsg_data['summary'], self.styles['CustomBody']))
            elements.append(Spacer(1, 0.2*cm))

        # Önemli bulgular
        if tsg_data.get('key_findings'):
            findings = tsg_data['key_findings']
            if isinstance(findings, list) and findings:
                for finding in findings[:5]:  # İlk 5 bulgu
                    elements.append(Paragraph(f"• {finding}", self.styles['CustomBody']))

        elements.append(Spacer(1, 0.3*cm))
        return elements

    def _create_ihale_section(self, ihale_data: dict) -> list:
        """İhale Agent bölümünü oluşturur"""
        elements = []

        elements.append(Paragraph("<b>Ihale Agent:</b>", self.styles['CustomBody']))
        elements.append(Spacer(1, 0.2*cm))

        # Özet
        if ihale_data.get('summary'):
            elements.append(Paragraph(ihale_data['summary'], self.styles['CustomBody']))
            elements.append(Spacer(1, 0.2*cm))

        # Uyarı bayrakları
        if ihale_data.get('warning_flags'):
            warnings = ihale_data['warning_flags']
            if isinstance(warnings, list) and warnings:
                for warning in warnings:
                    warning_para = Paragraph(
                        f"<font color='red'>⚠ {warning}</font>",
                        self.styles['CustomBody']
                    )
                    elements.append(warning_para)

        elements.append(Spacer(1, 0.3*cm))
        return elements

    def _create_news_section(self, news_data: dict) -> list:
        """News Agent bölümünü oluşturur"""
        elements = []

        elements.append(Paragraph("<b>News Agent:</b>", self.styles['CustomBody']))
        elements.append(Spacer(1, 0.2*cm))

        # Özet
        if news_data.get('summary'):
            elements.append(Paragraph(news_data['summary'], self.styles['CustomBody']))
            elements.append(Spacer(1, 0.2*cm))

        # Önemli haberler
        if news_data.get('key_findings'):
            findings = news_data['key_findings']
            if isinstance(findings, list) and findings:
                for finding in findings[:3]:  # İlk 3 haber
                    elements.append(Paragraph(f"• {finding}", self.styles['CustomBody']))

        elements.append(Spacer(1, 0.3*cm))
        return elements

    def _create_council_decision(self, report_data: dict) -> list:
        """Council karar bölümünü oluşturur"""
        elements = []
        council = report_data.get('council_decision')

        if not council:
            return elements

        # Başlık
        elements.append(Paragraph("COUNCIL KARARI", self.styles['CustomHeading']))
        elements.append(Spacer(1, 0.3*cm))

        # Final skorlar tablosu
        final_scores = council.get('final_scores', {})
        if final_scores:
            score_data = [["Uye", "Skor"]]
            for member, score in final_scores.items():
                score_data.append([member.replace('_', ' ').title(), str(score)])

            score_table = Table(score_data, colWidths=[8*cm, 8*cm])
            score_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3a8a')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ]))
            elements.append(score_table)
            elements.append(Spacer(1, 0.3*cm))

        # Karar gerekçesi
        if council.get('decision_rationale'):
            elements.append(Paragraph(
                f"<b>Karar Gerekcesi:</b>",
                self.styles['CustomBody']
            ))
            elements.append(Paragraph(
                council['decision_rationale'],
                self.styles['CustomBody']
            ))
            elements.append(Spacer(1, 0.3*cm))

        # Şartlar (eğer varsa)
        conditions = council.get('conditions', [])
        if conditions and isinstance(conditions, list):
            elements.append(Paragraph("<b>Sartlar:</b>", self.styles['CustomBody']))
            for condition in conditions:
                elements.append(Paragraph(f"• {condition}", self.styles['CustomBody']))
            elements.append(Spacer(1, 0.3*cm))

        # Muhalefet notu (eğer varsa)
        if council.get('dissent_note'):
            elements.append(Paragraph(
                f"<b>Muhalefet Notu:</b> {council['dissent_note']}",
                self.styles['CustomBody']
            ))

        elements.append(Spacer(1, 0.5*cm))
        return elements

    def _create_footer(self) -> list:
        """PDF footer oluşturur"""
        elements = []

        elements.append(Spacer(1, 1*cm))
        footer_text = Paragraph(
            "<i>KKB Agentic AI Hackathon 2024</i>",
            self.styles['CustomBody']
        )
        elements.append(footer_text)

        return elements

    def _create_line(self):
        """Ayırıcı çizgi oluşturur"""
        line_table = Table([['']], colWidths=[16*cm])
        line_table.setStyle(TableStyle([
            ('LINEABOVE', (0, 0), (-1, 0), 1, colors.grey),
        ]))
        return line_table

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

    def generate_filename(self, company_name: str) -> str:
        """PDF dosya adı oluşturur"""
        safe_name = "".join(c for c in company_name if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_name = safe_name.replace(' ', '_')
        date_str = datetime.now().strftime('%Y-%m-%d')
        return f"{safe_name}_Rapor_{date_str}.pdf"
