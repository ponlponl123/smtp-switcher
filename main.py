import asyncio
import ssl
from aiosmtpd.controller import Controller

class PlainSMTPHandler:
  async def handle_DATA(self, server, session, envelope):
    print(f'Received mail from: {envelope.mail_from}')
    print(f'Recipients: {envelope.rcpt_tos}')
    print(f'Message: {envelope.content.decode("utf8", errors="replace")}')
    return '250 Message accepted for delivery'

class STARTTLSHandler:
  async def handle_DATA(self, server, session, envelope):
    print(f'Received mail from: {envelope.mail_from}')
    print(f'Recipients: {envelope.rcpt_tos}')
    print(f'Message: {envelope.content.decode("utf8", errors="replace")}')
    return '250 Message accepted for delivery'

# SSL Context for STARTTLS
context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
context.load_cert_chain(certfile="cert.pem", keyfile="key.pem")

async def start_smtp_servers():
  loop = asyncio.get_event_loop()
  
  # Create a plain SMTP controller
  controller_plain = Controller(PlainSMTPHandler(), hostname='0.0.0.0', port=25, ready_timeout=30)
  # Create an SMTP with STARTTLS controller
  controller_starttls = Controller(STARTTLSHandler(), hostname='0.0.0.0', port=587, ready_timeout=30, ssl_context=context)
  
  controller_plain.start()
  controller_starttls.start()
  
  print("SMTP server started on ports 25 (Plain) and 587 (STARTTLS)...")
  
  await asyncio.Event().wait()

if __name__ == '__main__':
  asyncio.run(start_smtp_servers())
