import platform
import asyncio
import signal
import json
import smtplib
import logging
from aiosmtpd.controller import Controller
from aiosmtpd.smtp import Envelope, Session, SMTP
import argparse

if platform.system() == "Windows":
  asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

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
  def __init__(self):
    self.relay_rules = {}
    self.load_relay_rules()

  def load_relay_rules(self):
    try:
      with open('relayers.json', 'r', encoding='utf-8') as f:
        self.relay_rules = json.load(f)
      return True
    except FileNotFoundError:
      print("Error: 'relayers.json' file not found.")
      return False
    except json.JSONDecodeError:
      print("Error: Failed to parse 'relayers.json'. Ensure it is valid JSON.")
      return False

  def get_relay_server(self, sender_domain):
    logger.debug(f"Looking up relay for domain: {sender_domain}")
    if not self.load_relay_rules():
      return '550 Failed to load relay rules'
    return self.relay_rules.get(sender_domain)

  async def handle_DATA(self, server, session, envelope):
    try:
      refused = self._deliver(envelope)
    except smtplib.SMTPRecipientsRefused as e:
      logging.info('Got SMTPRecipientsRefused: %s', e)
      return "553 Recipients refused"
    except smtplib.SMTPResponseException as e:
      return "{} {}".format(e.smtp_code, e.smtp_error)
    else:
      if refused:
        logging.info('Recipients refused: %s', refused)
      return '250 OK'

  def _deliver(self, envelope: Envelope):
    logger.debug("handle_DATA method invoked")
    sender_domain = envelope.mail_from.split('@')[-1]
    relay_server = self.get_relay_server(sender_domain)

    logger.debug("=== SMTP DATA RECEIVED ===")
    logger.debug(f"MAIL FROM: {envelope.mail_from}")
    logger.debug(f"RCPT TO: {envelope.rcpt_tos}")
    logger.debug(f"Message size: {len(envelope.content)} bytes")
    logger.debug("Raw message:")
    logger.debug(envelope.content.decode(errors='ignore'))

    if not relay_server:
      logger.debug("No relay rule found for sender domain")
      return '554 No relay rule for this sender'

    host = relay_server.get("host")
    port = relay_server.get("port", 25)
    use_ssl = relay_server.get("ssl", False)
    use_tls = relay_server.get("tls", False)

    if not host or host.startswith("."):
      logger.error(f"Invalid relay server host: {host}")
      return '554 Invalid relay server host'

    try:
      s = smtplib.SMTP_SSL(host, port) if use_ssl else smtplib.SMTP(host, port)
      s.set_debuglevel(1)

      if use_tls:
        s.starttls()

      if "helo_hostname" in relay_server:
        helo = relay_server["helo_hostname"]
        s.helo(helo)
        s.ehlo(helo)
      else:
        s.ehlo()

      if "username" in relay_server and "password" in relay_server:
        s.login(relay_server["username"], relay_server["password"])

      try:
        s.sendmail(envelope.mail_from, envelope.rcpt_tos, envelope.content)
        logger.debug("Message successfully relayed")
        return '250 Message accepted for delivery'
      finally:
        s.quit()

    except (OSError, smtplib.SMTPException) as e:
      logging.exception('got %s', e.__class__)
      errcode = getattr(e, 'smtp_code', 554)
      errmsg = getattr(e, 'smtp_error', e.__class__)
      raise smtplib.SMTPResponseException(errcode, str(errmsg))

# WIP
class AuthHandler(SMTP):
  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.authenticated = False

  async def handle_AUTH(self, arg):
    logger.debug(f"AUTH command received with arg: {arg}")

async def main():
  print("Starting SMTP server...")
  handler = CustomHandler()
  # auth_handler = AuthHandler(handler)

  if public:
    controller = Controller(handler, hostname='0.0.0.0', port=port)
    print(f"SMTP server started (public) on port {port}...")
  else:
    controller = Controller(handler, hostname='localhost', port=port)
    print(f"SMTP server started on port {port}...")

  controller.start()

  # Setup graceful shutdown
  stop_event = asyncio.Event()

  def shutdown():
    print("Shutting down...")
    stop_event.set()

  loop = asyncio.get_running_loop()

  if platform.system() == "Windows":
    # Windows: Handle KeyboardInterrupt for graceful shutdown
    print("Running on Windows: Press Ctrl+C to stop the server.")
    try:
      while not stop_event.is_set():
        await asyncio.sleep(1)  # Keep the loop running
    except KeyboardInterrupt:
      shutdown()
  else:
    # Non-Windows: Use signal handlers
    loop.add_signal_handler(signal.SIGTERM, shutdown)
    loop.add_signal_handler(signal.SIGINT, shutdown)
    await stop_event.wait()

  controller.stop()

if __name__ == '__main__':
  asyncio.run(main())