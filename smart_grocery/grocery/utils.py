from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
from reportlab.lib.units import inch
from io import BytesIO
from .models import Order, OrderItem


def generate_invoice(order):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)

    # Sample styles
    styles = getSampleStyleSheet()
    centered_bold = ParagraphStyle(name='CenteredBold', fontSize=12, fontName='Helvetica-Bold', alignment=1)
    centered_normal = ParagraphStyle(name='CenteredNormal', fontSize=10, fontName='Helvetica', alignment=1)

    # Create Invoice Header
    invoice_header = Paragraph('<b>Invoice</b>', centered_bold)

    # Invoice Data
    invoice_data = [
        ['Order ID:', f'{order.id if order.id is not None else "N/A"}'],
        ['Customer:', order.customer.user.get_full_name() if (order.customer and order.customer.user) else 'N/A'],
        ['Order Date:', order.ordered_at.strftime('%Y-%m-%d %H:%M:%S') if order.ordered_at else 'N/A'],
        ['Total Amount:', f"${order.total_amount:.2f}" if order.total_amount is not None else "$0.00"]
    ]

    # Create the Invoice Data Table
    invoice_table = Table(invoice_data, colWidths=[2.0*inch, 2.0*inch])
    invoice_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONT', (0, 1), (-1, -1), 'Helvetica'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('GRID', (0, 0), (-1, -1), 0.5, (0, 0, 0))
    ]))

    # Create Products Section Header
    products_header = Paragraph('<b>Products:</b>', centered_bold)

    # Product Data
    product_data = [
        ['Product Name', 'Quantity', 'Price']
    ]

    # Add product details
    order_items = OrderItem.objects.filter(order=order)
    if order_items.exists():
        for item in order_items:
            product_name = item.product.name if item.product else 'N/A'
            quantity = item.quantity if item.quantity is not None else 0
            product_price = f"${item.price:.2f}" if item.price is not None else "$0.00"
            product_data.append([product_name, quantity, product_price])
    else:
        product_data.append(['No products available', '', ''])

    # Create the Products Table
    product_table = Table(product_data, colWidths=[2.5*inch, 1.0*inch, 1.0*inch])
    product_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
        ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONT', (0, 1), (-1, -1), 'Helvetica'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('GRID', (0, 0), (-1, -1), 1, (0, 0, 0))
    ]))

    # Build PDF with the invoice and product sections
    elements = [
        invoice_header,
        Spacer(1, 12),  
        invoice_table,
        Spacer(1, 24),  
        products_header,
        Spacer(1, 12),  
        product_table
    ]
    doc.build(elements)

    buffer.seek(0)
    return buffer.getvalue()
