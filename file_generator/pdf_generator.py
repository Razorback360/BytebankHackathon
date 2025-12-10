import os
from datetime import datetime
from io import BytesIO
import requests
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import yfinance as yf
from agents.stock_analyzer import StockAnalyzer, StockMarket
from io import BytesIO

# Import your models to type hint correctly (optional but good practice)
# from stock_analyzer import StockAnalysisResult 

class PDFReportGenerator:
    def __init__(self, analysis_result):
        self.data = analysis_result
        self.filename = f"{self.data.ticker}_Analysis_Report.pdf"
        self.styles = getSampleStyleSheet()
        self.width, self.height = A4

    def _get_logo_image(self, website_url):
        """
        Attempts to fetch a logo from Clearbit using the company's domain.
        Returns a ReportLab Image object or None.
        """
        if not website_url:
            return None
            
        try:
            # Extract domain from URL (e.g., https://www.apple.com -> apple.com)
            domain = website_url.replace("https://", "").replace("http://", "").split('/')[0]
            if "www." in domain:
                domain = domain.replace("www.", "")
            
            logo_url = f"https://logo.clearbit.com/{domain}"
            response = requests.get(logo_url)
            
            if response.status_code == 200:
                img_data = BytesIO(response.content)
                img = Image(img_data, width=0.8*inch, height=0.8*inch)
                img.hAlign = 'LEFT'
                return img
        except Exception as e:
            print(f"Could not fetch logo: {e}")
        return None

    def _create_header(self, website):
        """Creates the header with Logo (left) and Title (right)."""
        logo = self._get_logo_image(website)
        
        title_style = ParagraphStyle(
            'HeaderTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            alignment=TA_LEFT,
            spaceAfter=0
        )
        
        sub_title_style = ParagraphStyle(
            'HeaderSub',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=colors.gray
        )

        title_text = Paragraph(f"{self.data.stock_name} ({self.data.ticker})", title_style)
        date_text = Paragraph(f"Report Generated: {datetime.now().strftime('%Y-%m-%d')}", sub_title_style)
        
        # Table to align Logo and Text side-by-side
        if logo:
            header_data = [[logo, [title_text, date_text]]]
            col_widths = [1*inch, 5*inch]
        else:
            header_data = [[title_text], [date_text]]
            col_widths = [6*inch]
            
        t = Table(header_data, colWidths=col_widths)
        t.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
        ]))
        return t

    def _create_score_gauge(self):
        """Creates a visual text representation of the score."""
        score = self.data.score
        
        # Determine color based on score
        if score >= 80: color = colors.green
        elif score >= 50: color = colors.orange
        else: color = colors.red
        
        score_style = ParagraphStyle(
            'Score',
            parent=self.styles['Heading2'],
            fontSize=20,
            alignment=TA_CENTER,
            textColor=color,
            borderWidth=1,
            borderColor=color,
            borderPadding=10,
            borderRadius=5
        )
        return Paragraph(f"AI Conviction Score: {score}/100", score_style)

    def _create_financial_table(self):
        """Creates a formatted table for key financials."""
        f = self.data.key_financials
        
        # Format large numbers
        def fmt_num(n):
            if n > 1_000_000_000_000: return f"${n/1_000_000_000_000:.2f}T"
            if n > 1_000_000_000: return f"${n/1_000_000_000:.2f}B"
            return f"{n:.2f}"

        data = [
            ["Metric", "Value", "Metric", "Value"], # Header
            ["Market Cap", fmt_num(f.market_cap), "P/E Ratio", f"{f.p_e_ratio:.2f}"],
            ["Beta", f"{f.beta:.2f}", "Debt/Equity", f"{f.debt_to_equity:.2f}%"],
            ["Rev Growth (YoY)", f"{f.revenue_yoy_growth:.1%}", "Profit Growth", f"{f.net_income_yoy_growth:.1%}"]
        ]
        
        t = Table(data, colWidths=[1.5*inch, 1.5*inch, 1.5*inch, 1.5*inch])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#003366')), # Dark Blue Header
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0,0), (-1,0), 12),
            ('BACKGROUND', (0,1), (-1,-1), colors.beige),
            ('GRID', (0,0), (-1,-1), 1, colors.black),
        ]))
        return t

    def _create_swot_section(self):
        """Formats SWOT analysis into a nice grid."""
        swot = self.data.swot_analysis
        
        # Helper to make a bulleted list paragraph
        def make_list(items):
            return [Paragraph(f"• {item}", self.styles['Normal']) for item in items]

        # 2x2 Grid
        data = [
            [Paragraph("<b>STRENGTHS</b>", self.styles['Heading4']), Paragraph("<b>WEAKNESSES</b>", self.styles['Heading4'])],
            [make_list(swot.strengths), make_list(swot.weaknesses)],
            [Paragraph("<b>OPPORTUNITIES</b>", self.styles['Heading4']), Paragraph("<b>THREATS</b>", self.styles['Heading4'])],
            [make_list(swot.opportunities), make_list(swot.threats)]
        ]
        
        t = Table(data, colWidths=[3.2*inch, 3.2*inch])
        t.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('BOX', (0,0), (0,1), 1, colors.green), # Green box for positive
            ('BOX', (1,0), (1,1), 1, colors.red),   # Red box for negative
            ('BOX', (0,2), (0,3), 1, colors.blue),  # Blue for Opps
            ('BOX', (1,2), (1,3), 1, colors.orange),# Orange for Threats
            ('LEFTPADDING', (0,0), (-1,-1), 10),
            ('RIGHTPADDING', (0,0), (-1,-1), 10),
            ('TOPPADDING', (0,0), (-1,-1), 10),
            ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ]))
        return t

    def create_pdf(self, website_url=None):
        buffer = BytesIO()
        story = []
        
        # 1. Header & Logo
        story.append(self._create_header(website_url))
        story.append(Spacer(1, 20))
        story.append(HRFlowable(width="100%", thickness=2, color=colors.black))
        story.append(Spacer(1, 20))
        
        # 2. Executive Summary & Score
        story.append(self._create_score_gauge())
        story.append(Spacer(1, 15))
        story.append(Paragraph("<b>Executive Summary:</b>", self.styles['Heading3']))
        story.append(Paragraph(self.data.summary, self.styles['Normal']))
        story.append(Spacer(1, 20))

        # 3. Financials Table
        story.append(Paragraph("<b>Key Financial Metrics:</b>", self.styles['Heading3']))
        story.append(Spacer(1, 5))
        story.append(self._create_financial_table())
        story.append(Spacer(1, 20))
        
        # 4. Outlooks
        story.append(Paragraph(f"<b>Short Term Outlook:</b> {self.data.short_term_outlook}", self.styles['Normal']))
        story.append(Spacer(1, 10))
        story.append(Paragraph(f"<b>Long Term Outlook:</b> {self.data.long_term_outlook}", self.styles['Normal']))
        story.append(Spacer(1, 20))
        
        # 5. SWOT Analysis
        story.append(Paragraph("<b>SWOT Analysis:</b>", self.styles['Heading3']))
        story.append(Spacer(1, 5))
        story.append(self._create_swot_section())

        # Build PDF
        doc = SimpleDocTemplate(buffer, pagesize=A4,
                                rightMargin=40, leftMargin=40,
                                topMargin=40, bottomMargin=40)
        doc = doc = SimpleDocTemplate(self.filename, pagesize=A4,
                                rightMargin=40, leftMargin=40,
                                topMargin=40, bottomMargin=40)
        doc.build(story)
        print(f"PDF generated successfully: {self.filename}")
        buffer.seek(0)
        return buffer

if __name__ == "__main__":
    ticker = "2222"
    market = StockMarket.SA
    # 1. Run the AI Analysis
    print(f"--- Starting Analysis for {ticker} ---")
    analyzer = StockAnalyzer()
    result = analyzer.analyze_stock(ticker, market=market)
    
    # 2. Get the website URL for the logo (quick fetch)
    print("--- Fetching meta-data for PDF ---")
    if market == StockMarket.SA:
        ticker = f"{ticker}.{market.value}"
    print(ticker)
    stock_info = yf.Ticker(ticker).info
    website = stock_info.get('website', '') # e.g., https://www.nvidia.com
    
    # 3. Generate the PDF
    print("--- Generating PDF Report ---")
    pdf_gen = PDFReportGenerator(result)
    buffer = pdf_gen.create_pdf(website_url=website)
    
    print("Done!")