import signal
import asyncio
import json
import smtplib
import logging
from aiosmtpd.controller import Controller
from aiosmtpd.smtp import Envelope, Session, SMTP
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("-p", "--port", help="port number", type=int)
parser.add_argument("-a", "--public", help="public", action='store_true')
args = parser.parse_args()
port = args.port or 25
public = args.public or False

logging.basicConfig(
  level=logging.DEBUG,
  format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("smtp-gateway")

class CustomHandler:
  def __init__(self, relay_rules):
    self.relay_rules = relay_rules

  def get_relay_server(self, sender_domain):
    logger.debug(f"Looking up relay for domain: {sender_domain}")
    return self.relay_rules.get(sender_domain)

  async def handle_DATA(self, server, session: Session, envelope: Envelope):
    sender_domain = envelope.mail_from.split('@')[-1]
    relay_server = self.get_relay_server(sender_domain)

    logger.debug("=== SMTP DATA RECEIVED ===")
    logger.debug(f"MAIL FROM: {envelope.mail_from}")
    logger.debug(f"RCPT TO: {envelope.rcpt_tos}")
    logger.debug(f"Client IP: {session.peer}")
    logger.debug(f"Message size: {len(envelope.content)} bytes")
    logger.debug("Raw message:")
    logger.debug(envelope.content.decode(errors='ignore'))

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
        return '250 Message accepted for delivery'
      except smtplib.SMTPException as e:
        print(f"Failed to connect to relay server: {e}")
        return '554 Relay server error (SMTP exception)'
      except ConnectionRefusedError:
        print(f"Failed to connect to relay server: Connection refused")
        return '554 Relay server error (Connection refused)'
      except TimeoutError:
        print(f"Failed to connect to relay server: Timeout")
        return '554 Relay server error (Timeout)'
      except smtplib.SMTPServerDisconnected:
        print(f"Failed to connect to relay server: Server disconnected")
        return '554 Relay server error (Server disconnected)'
      except smtplib.SMTPAuthenticationError:
        print(f"Failed to authenticate to relay server")
        return '554 Relay server error (Authentication failed)'
      except smtplib.SMTPSenderRefused:
        print(f"Failed to send mail from {envelope.mail_from}")
        return '554 Relay server error (Sender refused)'
      except smtplib.SMTPRecipientsRefused:
        print(f"Failed to send mail to {envelope.rcpt_tos}")
        return '554 Relay server error (Recipient refused)'
      except smtplib.SMTPDataError:
        print(f"Failed to send mail data")
        return '554 Relay server error (Data error)'
      except Exception as e:
        print(f"Failed to relay mail from {envelope.mail_from} to {relay_server['host']}: {e}")
        return '554 Relay server error (Unknown)'
    else:
      print(f"No relay server found for domain {sender_domain}")
      return '550 No relay server found'

  async def handle_MAIL(self, server, session, envelope, address, mail_options):
    logger.debug(f"MAIL FROM: {address}")
    envelope.mail_from = address
    return '250 OK'

  async def handle_RCPT(self, server, session, envelope, address, rcpt_options):
      logger.debug(f"RCPT TO: {address}")
      envelope.rcpt_tos.append(address)
      return '250 OK'

class AuthHandler(SMTP):
  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.authenticated = False

  async def handle_AUTH(self, arg):
    logger.debug(f"AUTH command received with arg: {arg}")

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