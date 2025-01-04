import asyncio
import json
import smtplib
from aiosmtpd.controller import Controller
from aiosmtpd.smtp import Envelope, Session, SMTP

class CustomHandler:
  def __init__(self, relay_rules):
    self.relay_rules = relay_rules

  def get_relay_server(self, sender_domain):
    return self.relay_rules.get(sender_domain, None)

  async def handle_DATA(self, server, session: Session, envelope: Envelope):
    sender_domain = envelope.mail_from.split('@')[-1]
    relay_server = self.get_relay_server(sender_domain)

    if relay_server:
      try:
        with smtplib.SMTP(relay_server["host"], relay_server["port"]) as relay:
          relay.starttls()
          relay.login(relay_server["username"], relay_server["password"])
          relay.sendmail(envelope.mail_from, envelope.rcpt_tos, envelope.content)
        print(f"Relayed mail from {envelope.mail_from} to {relay_server['host']}")
      except Exception as e:
        print(f"Failed to relay mail from {envelope.mail_from} to {relay_server['host']}: {e}")
    else:
      print(f"No relay server found for domain {sender_domain}")
      
    return '250 Message accepted for delivery'

class AuthHandler(SMTP):
  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.authenticated = False

  async def handle_AUTH(self, arg):
    if arg == "username password":
      self.authenticated = True
      return '235 Authentication successful'
    else:
      return '535 Authentication credentials invalid'

async def main():
  with open('relayers.json', 'r') as f:
    relay_rules = json.load(f)

  loop = asyncio.get_event_loop()

  handler = CustomHandler(relay_rules)
  auth_handler = AuthHandler(handler)

  controller = Controller(auth_handler, hostname='0.0.0.0', port=25, ready_timeout=30)

  controller.start()

  print("SMTP server started on port 25 with domain-based relaying and authentication...")

  await asyncio.Event().wait()

if __name__ == '__main__':
  asyncio.run(main())
