import asyncio
import logging
from collections.abc import Callable
from email.message import Message
from email.parser import BytesParser
from email.policy import default as default_policy
from typing import Any, Coroutine

from aioimaplib import aioimaplib

from .exceptions import IMAPAuthError, IMAPConnectionError, IMAPIDLEError


class IMAPIdleListener:
    """
    Monitors an IMAP mailbox for new emails using the IDLE command.

    Connects to an IMAP server, listens for new emails in real-time,
    and processes them using custom functions or coroutines.

    Attributes:
        host (str): IMAP server hostname.
        port (int): IMAP server port.
        username (str): Email address for authentication.
        password (str): Password for authentication.
        mailbox (str): Mailbox to monitor (default: "INBOX").
        idle_timeout (int): Timeout for IDLE mode in seconds (default: 15 minutes).
        email_processors (list): List of functions or coroutines to process emails.

    """

    def __init__(
        self,
        host,
        port,
        username,
        password,
        mailbox="INBOX",
        idle_timeout=15 * 60,
        email_processors=None,
    ):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.mailbox = mailbox
        self.idle_timeout = idle_timeout
        self.client: aioimaplib.IMAP4_SSL | None = None
        self._stop_event = asyncio.Event()
        self.logger = logging.getLogger(__name__)
        self.email_processors = email_processors if email_processors is not None else []

    async def connect(self) -> bool:
        try:
            self.client = aioimaplib.IMAP4_SSL(host=self.host, port=self.port)
            await self.client.wait_hello_from_server()

            self.logger.info(f"Logging in to {self.username}")
            response = await self.client.login(self.username, self.password)
            if response.result != "OK":
                raise IMAPAuthError(f"Login failed: {response.result}")

            self.logger.info(f"Selecting mailbox {self.mailbox}")
            response = await self.client.select(self.mailbox)
            if response.result != "OK":
                raise IMAPConnectionError(
                    f"Failed to select mailbox: {response.result}"
                )

            return True
        except Exception as e:
            self.logger.error(f"Connection error: {e}", exc_info=True)
            raise IMAPConnectionError(f"Connection failed: {e}")

    async def fetch_new_emails(self) -> None:
        assert self.client is not None, "Client is not connected"
        self.logger.info("Checking for new emails...")
        response = await self.client.search("UNSEEN")
        if response.result == "OK":
            email_ids = response.lines[0].split()
            if email_ids:
                self.logger.info(f"Found {len(email_ids)} new email(s)")
                for email_id in email_ids:
                    await self.process_email(email_id.decode())
            else:
                self.logger.debug("No new emails found")

    async def process_email(self, email_id: str) -> None:
        assert self.client is not None, "Client is not connected"
        try:
            response = await self.client.fetch(email_id, "(BODY[])")
            if response.result != "OK":
                self.logger.error(f"Failed to fetch email {email_id}")
                return

            raw_email = response.lines[1]
            email_message = BytesParser(policy=default_policy).parsebytes(raw_email)  # type: ignore
            self.logger.info(
                f"Processing email {email_id} - Subject: {email_message['subject']}"
            )

            for processor in self.email_processors:
                if asyncio.iscoroutinefunction(processor):
                    await processor(email_message, self)
                else:
                    processor(email_message, self)

        except Exception as e:
            self.logger.error(f"Error processing email {email_id}: {e}", exc_info=True)

    def add_email_processor(
        self,
        processor: Callable[[Message, "IMAPIdleListener"], None]
        | Callable[[Message, "IMAPIdleListener"], Coroutine[Any, Any, None]],
    ) -> None:
        """
        Add a custom email processor.

        Args:
            processor: A function or coroutine to process emails.
        """
        self.email_processors.append(processor)

    async def start_idle(self) -> None:
        assert self.client is not None, "Client is not connected"

        self.logger.info("Starting IDLE mode")
        try:
            while not self._stop_event.is_set():
                await self.fetch_new_emails()

                self.logger.debug("Entering IDLE mode")
                idle_task = await self.client.idle_start()

                try:
                    await self.client.wait_server_push(timeout=self.idle_timeout)
                except asyncio.TimeoutError:
                    self.logger.debug("IDLE timeout, checking for new emails")
                finally:
                    self.client.idle_done()
                    await asyncio.wait_for(idle_task, timeout=10)

        except Exception as e:
            self.logger.error(f"Error in IDLE mode: {e}", exc_info=True)
            raise IMAPIDLEError(f"IDLE mode failed: {e}")

    async def stop(self) -> None:
        assert self.client is not None, "Client is not connected"
        self.logger.info("Stopping IDLE listener")
        self._stop_event.set()
        if self.client:
            try:
                await self.client.logout()
            except Exception as e:
                self.logger.error(f"Error during logout: {e}", exc_info=True)
            finally:
                self.client = None
