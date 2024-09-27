from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet

def generate_invoice(order):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []

    # Define styles
    styles = getSampleStyleSheet()
    title_style = styles['Title']
    heading_style = styles['Heading2']
    normal_style = styles['BodyText']

    # Title
    elements.append(Paragraph("Invoice", title_style))

    # Order details
    order_info = [
        ["Order ID", str(order.id)],
        ["Customer", order.customer.name],
        ["Payment Date", str(order.payment_date)],
        ["Total Amount", f"${order.total_amount}"]
    ]

    # Add order details as a table
    order_table = Table(order_info, colWidths=[150, 300])
    order_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), '#f0f0f0'),
        ('TEXTCOLOR', (0, 0), (-1, 0), (0, 0, 0)),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('BACKGROUND', (0, 1), (-1, -1), '#ffffff'),
        ('GRID', (0, 0), (-1, -1), 1, (0, 0, 0)),
    ]))
    elements.append(order_table)
    elements.append(Paragraph("<br/>", normal_style))

    # Table for products
    product_headers = ["Product Name", "Quantity", "Price"]
    product_data = [[item.product.name, str(item.quantity), f"${item.price}"] for item in order.items.all()]
    product_data.insert(0, product_headers)

    product_table = Table(product_data, colWidths=[200, 100, 100])
    product_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), '#d0d0d0'),
        ('TEXTCOLOR', (0, 0), (-1, 0), (0, 0, 0)),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('BACKGROUND', (0, 1), (-1, -1), '#ffffff'),
        ('GRID', (0, 0), (-1, -1), 1, (0, 0, 0)),
    ]))
    elements.append(Paragraph("Products:", heading_style))
    elements.append(product_table)

    # Build the PDF
    doc.build(elements)

    pdf_value = buffer.getvalue()
    buffer.close()

    return pdf_value
