import signal
import asyncio
import json
import smtplib
from aiosmtpd.controller import Controller
from aiosmtpd.smtp import Envelope, Session, SMTP
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("-p", "--port", help="port number", type=int)
parser.add_argument("-a", "--public", help="public", action='store_true')
args = parser.parse_args()
port = args.port or 25
public = args.public or False

class CustomHandler:
  def __init__(self, relay_rules):
    self.relay_rules = relay_rules

  def get_relay_server(self, sender_domain):
    return self.relay_rules.get(sender_domain)

  async def handle_DATA(self, server, session: Session, envelope: Envelope):
    sender_domain = envelope.mail_from.split('@')[-1]
    relay_server = self.get_relay_server(sender_domain)

    if relay_server:
      try:
        with smtplib.SMTP(relay_server["host"], relay_server["port"]) as relay:
          if "helo_hostname" in relay_server:
            relay.helo(relay_server["helo_hostname"])
            relay.ehlo(relay_server["helo_hostname"])
          if relay_server.get("tls", False):
            relay.starttls()
          if "username" in relay_server and "password" in relay_server:
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
    if arg == "username password":  # Replace with actual credentials or logic
      self.authenticated = True
      return '235 Authentication successful'
    else:
      return '535 Authentication credentials invalid'

async def main():
  print("Starting SMTP server...")
  try:
    with open('relayers.json', 'r', encoding='utf-8') as f:
      relay_rules = json.load(f)
  except FileNotFoundError:
    print("Error: 'relayers.json' file not found.")
    return
  except json.JSONDecodeError:
    print("Error: Failed to parse 'relayers.json'. Ensure it is valid JSON.")
    return

  handler = CustomHandler(relay_rules)
  auth_handler = AuthHandler(handler)

  if public:
    controller = Controller(auth_handler, hostname='0.0.0.0', port=port)
    print(f"SMTP server started (public) on port {port}...")
  else:
    controller = Controller(auth_handler, hostname='localhost', port=port)
    print(f"SMTP server started on port {port}...")

  controller.start()

  # Setup graceful shutdown
  loop = asyncio.get_running_loop()
  stop_event = asyncio.Event()

  def shutdown():
    print("Shutting down...")
    stop_event.set()

  loop.add_signal_handler(signal.SIGINT, shutdown)
  loop.add_signal_handler(signal.SIGTERM, shutdown)

  await stop_event.wait()
  controller.stop()

if __name__ == '__main__':
  asyncio.run(main())