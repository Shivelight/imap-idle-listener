import asyncio
import logging
import os

from dotenv import load_dotenv

from imap_idle_listener import IMAPIdleListener

load_dotenv()

IMAP_SERVER = os.getenv("IMAP_SERVER", "imap.example.com")
IMAP_PORT = int(os.getenv("IMAP_PORT", 993))
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
MAILBOX = os.getenv("MAILBOX", "INBOX")
CHECK_FREQUENCY = int(os.getenv("CHECK_FREQUENCY", 29))  # Minutes (IDLE timeout)
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
FONNTE_TOKEN = os.getenv("FONNTE_TOKEN")

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

    try:
        logging.info("Starting IMAP IDLE listener")
        await listener.start_idle()
    except Exception as e:
        logging.error(f"Error in main: {e}", exc_info=True)
        await listener.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Keyboard interrupt received, exiting...")
    except Exception as e:
        logging.error(f"Unexpected error: {e}", exc_info=True)
    finally:
        logging.info("IMAP IDLE listener stopped")
