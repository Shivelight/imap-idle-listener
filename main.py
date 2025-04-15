import asyncio
import logging
import os
import re
from email.message import Message

import httpx
from dotenv import load_dotenv

from imap_idle_listener import IMAPIdleListener

load_dotenv()

IMAP_SERVER = os.getenv("IMAP_SERVER", "imap.example.com")
IMAP_PORT = int(os.getenv("IMAP_PORT", 993))
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
MAILBOX = os.getenv("MAILBOX", "INBOX")
CHECK_FREQUENCY = int(os.getenv("CHECK_FREQUENCY", 29))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


async def main():
    listener = IMAPIdleListener(
        host=IMAP_SERVER,
        port=IMAP_PORT,
        username=EMAIL_ADDRESS,
        password=EMAIL_PASSWORD,
        mailbox=MAILBOX,
        idle_timeout=CHECK_FREQUENCY * 60,
    )

    listener.add_email_processor(extract_verification_code)

    try:
        logging.info("Starting IMAP IDLE listener")
        await listener.connect()
        await listener.start_idle()
    except Exception as e:
        logging.error(f"Error in main: {e}", exc_info=True)
        await listener.stop()


async def extract_verification_code(email_message: Message, client: IMAPIdleListener):
    verification_code = None
    for part in email_message.walk():
        content_type = part.get_content_type()

        if content_type == "text/html":
            payload = part.get_payload(decode=True)
            if payload and isinstance(payload, bytes):
                html_content = payload.decode("utf-8")
                code_match = re.search(
                    r'<p style="font-size:20px;margin-top:15px;">(\d+)</p>',
                    html_content,
                )
                if code_match:
                    verification_code = code_match.group(1)

    if verification_code:
        async with httpx.AsyncClient() as http:
            await http.post(
                os.environ["GREEN_API_SENDMESSAGE_URL"],
                json={
                    "chatId": os.environ["GREEN_API_SENDMESSAGE_TARGET"],
                    "message": f"{verification_code}",
                },
            )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Keyboard interrupt received, exiting...")
    except Exception as e:
        logging.error(f"Unexpected error: {e}", exc_info=True)
    finally:
        logging.info("IMAP IDLE listener stopped")
