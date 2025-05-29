import smtplib
from email.message import EmailMessage
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import io
from django.conf import settings

def generate_ticket_pdf(booking, seat, concert, payment_id):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    p.setFont("Helvetica", 16)
    p.drawString(100, 800, f"Электронный билет на концерт: {concert.name}")
    p.setFont("Helvetica", 12)
    p.drawString(100, 770, f"Дата и время: {concert.date.strftime('%d.%m.%Y %H:%M')}")
    p.drawString(100, 750, f"Место: Ряд {seat.row}, Место {seat.seat_number}")
    p.drawString(100, 730, f"ФИО: {booking.full_name}")
    p.drawString(100, 710, f"Email: {booking.email}")
    p.drawString(100, 690, f"Телефон: {booking.phone}")
    p.drawString(100, 670, f"Номер платежа: {payment_id}")
    p.drawString(100, 650, f"Стоимость: {'VIP' if seat.is_vip else ''} {concert.vip_price if seat.is_vip else concert.price} ₽")
    p.drawString(100, 630, "Спасибо за покупку! Приятного посещения концерта!")
    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer.read()

def send_ticket_email(to_email, booking, seat, concert, payment_id):
    # Генерируем PDF билет
    pdf_data = generate_ticket_pdf(booking, seat, concert, payment_id)
    # Формируем письмо
    msg = EmailMessage()
    msg['Subject'] = f'Ваш электронный билет на концерт: {concert.name}'
    msg['From'] = settings.EMAIL_HOST_USER
    msg['To'] = to_email
    msg.set_content(f"Здравствуйте, {booking.full_name}!\n\nВаш билет на концерт '{concert.name}' успешно оплачен. Билет во вложении (PDF).\n\nНомер платежа: {payment_id}\n\nСпасибо за покупку!")
    msg.add_attachment(pdf_data, maintype='application', subtype='pdf', filename='ticket.pdf')
    # Отправляем письмо
    with smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT) as server:
        server.starttls()
        server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
        server.send_message(msg) 