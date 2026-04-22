import smtplib, os, datetime
from email.message import EmailMessage
from fpdf import FPDF, XPos, YPos
from duckduckgo_search import DDGS
from semantic_kernel.functions import kernel_function


from pypdf import PdfReader
from semantic_kernel.functions import kernel_function
# import uuid

class InsuranceMathPlugin:
    @kernel_function(
        description="Calculates health insurance premiums based on 2026 tax laws and risk factors.",
        name="CalculatePremium"
    )
    def calculate_premium(
        self, 
        base_rate: float, 
        age: int, 
        is_smoker: bool = False, 
        has_ped: bool = False, 
        ncb_years: int = 0
    ) -> str:
        # 1. Age-Based Loading (Standard industry logic)
        age_factor = 1.0
        if age > 40: age_factor = 1.2  # 20% increase
        if age > 55: age_factor = 1.5  # 50% increase
        
        current_premium = base_rate * age_factor
        
        # 2. Tobacco/Smoking Loading (Usually +20% to +30%)
        tobacco_loading = 0
        if is_smoker:
            tobacco_loading = current_premium * 0.25
            current_premium += tobacco_loading
            
        # 3. Pre-Existing Disease (PED) Loading
        ped_loading = 0
        if has_ped:
            ped_loading = current_premium * 0.20
            current_premium += ped_loading
            
        # 4. No Claim Bonus (NCB) Discount (Accumulated over years)
        ncb_discount = 0
        if ncb_years > 0:
            # Typically 10% per year, capped at 50%
            ncb_rate = min(ncb_years * 0.10, 0.50)
            ncb_discount = current_premium * ncb_rate
            current_premium -= ncb_discount
            
        # 5. 2026 GST Logic: Individual Health Insurance is 0%
        # Group/Corporate is still 18%, but we'll assume Individual for this agent.
        gst = 0.0 
        total_payable = current_premium + gst
        
        return (
            f"--- Premium Breakdown ---\n"
            f"Base Rate: Rs. {base_rate:,.2f}\n"
            f"Age Loading: x{age_factor}\n"
            f"Tobacco Loading: +Rs. {tobacco_loading:,.2f}\n"
            f"PED Loading: +Rs. {ped_loading:,.2f}\n"
            f"NCB Discount: -Rs. {ncb_discount:,.2f}\n"
            f"GST (2026 Individual Rate): Rs. {gst:,.2f}\n"
            f"Total Annual Payable: Rs. {total_payable:,.2f}"
        )
    
class DynamicPDF(FPDF):
    def __init__(self, style):
        super().__init__()
        self.style = style
        # 1. Register a Unicode-friendly font
        # If you don't have this .ttf file, you can download 'DejaVuSans.ttf' 
        # or use any Arial/Roboto .ttf from your Windows/Fonts folder.
        try:
            # Attempt to use a standard system font that supports Unicode
            self.add_font("DejaVu", "", "DejaVuSans.ttf") 
            self.unicode_font = "DejaVu"
        except:
            # Fallback to Helvetica if font file isn't found (will still error on ₹)
            self.unicode_font = "helvetica"

    def header(self):
        bg_color = self.style.get("header_bg", (36, 44, 52))
        self.set_fill_color(*bg_color)
        self.rect(0, 0, 210, 25, "F") 
        self.set_text_color(255, 255, 255)
        # Use the unicode font here too
        self.set_font(self.unicode_font, "B", 16) 
        self.set_y(5)
        self.cell(0, 15, self.style.get("title", "Insurance Report").upper(), align="C")
        self.ln(20)

@kernel_function(
    description="Generates a professional PDF report.",
    name="CreateCustomPDF"
)
def create_custom_pdf(self, content: str, filename: str = "Insurance_Report") -> str:
    # 1. Define the filename clearly first
    safe_filename = filename.replace(' ', '_')
    
    # 2. Now use it in the config
    style_config = {
        "title": "Insurance Analysis",
        "header_bg": (36, 44, 52),
        "accent_color": (0, 51, 102),
        "filename": safe_filename
    }
    
    content = content.replace("₹", "Rs. ")
    pdf = DynamicPDF(style_config)
    pdf.add_page()
    accent = style_config.get("accent_color", (0, 51, 102))

    if "|" in content and "---" in content:
        self._render_table(pdf, content, accent)
    else:
        self._render_text(pdf, content, accent)
    
    full_path = f"{safe_filename}.pdf"
    pdf.output(full_path)
    return full_path

    def _render_table(self, pdf, content, accent):
        # Professional Table Logic
        pdf.set_font("helvetica", "B", 12)
        pdf.set_text_color(*accent)
        pdf.cell(0, 10, "Comparison Table", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(2)

        lines = content.strip().split("\n")
        pdf.set_font("helvetica", size=9)
        pdf.set_text_color(0, 0, 0)
        
        # Simple auto-table using fpdf2's built-in table feature
        with pdf.table(borders_layout="HORIZONTAL_LINES", 
                      cell_fill_color=(245, 245, 245),
                      cell_fill_mode="ROWS",
                      line_height=8) as table:
            for line in lines:
                if "|" in line and "---" not in line:
                    row = [cell.strip() for cell in line.split("|") if cell.strip()]
                    if row:
                        table.row(row)

    def _render_text(self, pdf, content, accent):
        # Professional Text Logic
        pdf.set_left_margin(15)
        pdf.set_draw_color(*accent)
        pdf.set_line_width(0.5)
        # Decorative accent line on the left
        pdf.line(12, 35, 12, 280) 
        
        pdf.set_font("helvetica", "B", 13)
        pdf.set_text_color(*accent)
        pdf.cell(0, 10, "Detailed Analysis", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        
        pdf.ln(3)
        pdf.set_font("helvetica", size=11)
        pdf.set_text_color(40, 40, 40)
        pdf.multi_cell(0, 7, content)
    @kernel_function(
        description="Sends an email with a PDF attachment.",
        name="SendEmail"
    )
    def send_email(self, recipient_email: str, file_path: str) -> str:
        sender_email = os.getenv("SENDER_EMAIL") 
        app_password = os.getenv("GMAIL_APP_PASSWORD") # Must be 16-digit App Password
        
        if not sender_email or not app_password:
            return "Error: Email credentials not found in .env"

        msg = EmailMessage()
        msg['Subject'] = 'Your Insurance AI Report'
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg.set_content("Attached is your personalized insurance analysis report.")
        
        try:
            # We strip in case the LLM adds "Path: " to the string
            clean_path = file_path.replace("Path: ", "").strip()
            
            with open(clean_path, 'rb') as f:
                file_data = f.read()
                msg.add_attachment(
                    file_data,
                    maintype='application',
                    subtype='pdf',
                    filename=os.path.basename(clean_path)
                )

            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
                smtp.login(sender_email, app_password)
                smtp.send_message(msg)
            
            return f"Success! PDF sent to {recipient_email}."
        except Exception as e:
            return f"Failed to send email: {str(e)}"

class WebSearchPlugin:
    @kernel_function(
        # Be very specific here
        description="Fetch real-time insurance quotes, PolicyBazaar listings, and premium rates for 2026.",
        name="search"
    )    
    def search(self, query: str) -> str:
        with DDGS() as ddgs:
            results = [r for r in ddgs.text(query, max_results=3)]
            return "\n".join([f"Title: {r['title']}\nSnippet: {r['body']}\nSource: {r['href']}\n" for r in results])
