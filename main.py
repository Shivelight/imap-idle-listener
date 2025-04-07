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


async def shutdown(signal, loop, listener):
    """Cleanup tasks tied to the service's shutdown."""
    logging.info(f"Received exit signal {signal.name}...")
    await listener.stop()
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    [task.cancel() for task in tasks]
    logging.info("Cancelling outstanding tasks")
    await asyncio.gather(*tasks, return_exceptions=True)
    loop.stop()


async def main():
    """Main function to run the IMAP IDLE listener"""
    # Initialize listener
    listener = IMAPIdleListener(
        host=IMAP_SERVER,
        port=IMAP_PORT,
        username=EMAIL_ADDRESS,
        password=EMAIL_PASSWORD,
        mailbox=MAILBOX,
        idle_timeout=CHECK_FREQUENCY * 60,
    )

    loop = asyncio.get_running_loop()
    # signals = [signal.SIGTERM, signal.SIGINT]
    # for s in signals:
    #     loop.add_signal_handler(
    #         s, lambda s=s: asyncio.create_task(shutdown(s, loop, listener))
    #     )

    try:
        logging.info("Starting IMAP IDLE listener")
        await listener.start_idle()
    except Exception as e:
        logging.error(f"Error in main: {str(e)}")
        await listener.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Keyboard interrupt received, exiting...")
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
    finally:
        logging.info("IMAP IDLE listener stopped")
