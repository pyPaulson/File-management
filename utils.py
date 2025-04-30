import smtplib
from email.message import EmailMessage

def send_email_verification(to_email: str, token: str):
    verify_link = f"http://127.0.0.1:8000/verify-email?token={token}"

    email = EmailMessage()
    email["Subject"] = "Verify your email"
    email["From"] = "noreply@example.com"
    email["To"] = to_email
    email.set_content(f"Click the link to verify your email: {verify_link}")

    # ✏️ Use your Mailtrap SMTP credentials here:
    smtp_server = "sandbox.smtp.mailtrap.io"
    smtp_port = 587
    sender_username = "6328bee4dffc7a"
    sender_password = "4e0a64b92cc561"

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as smtp:
            smtp.starttls()
            smtp.login(sender_username, sender_password)
            smtp.send_message(email)
            print("✅ Verification email sent to Mailtrap!")
    except Exception as e:
        print("❌ Failed to send email:", e)
