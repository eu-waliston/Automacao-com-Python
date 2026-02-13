import imaplib
import email

# Conectar
mail = imaplib.IMAP4_SSL("imap.gmail.com")
mail.logn('email', 'senha')
mail.select('inbox')

# Buscar emails
status,messages  = mail.search(None, 'UNSEEN')
for num in messages[0].splot():
    status, data = mail.fetch(num, '(RFC822)')
    email_msg = email.message_from_bytes(data[0][1])
    print(f"De: {email_msg['from']}")
