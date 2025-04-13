import asyncio
import logging
import os
import re
from email.parser import BytesParser
from email.policy import default as default_policy

import httpx
from aioimaplib import aioimaplib

from .exceptions import IMAPAuthError, IMAPConnectionError, IMAPIDLEError


class IMAPIdleListener:
    def __init__(
        self, host, port, username, password, mailbox="INBOX", idle_timeout=29 * 60
    ):
        """
        Initialize the IMAP IDLE listener

        Args:
            host: IMAP server host
            port: IMAP server port
            username: Email address
            password: Email password
            mailbox: Mailbox to monitor (default: INBOX)
            idle_timeout: Timeout for IDLE mode in seconds (default: 29 minutes)
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.mailbox = mailbox
        self.idle_timeout = idle_timeout
        self.client = None
        self._stop_event = asyncio.Event()
        self.logger = logging.getLogger(__name__)

    async def connect(self):
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
            self.logger.error(f"Connection error: {str(e)}")
            raise IMAPConnectionError(f"Connection failed: {str(e)}")

    async def fetch_new_emails(self):
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

    async def process_email(self, email_id):
        try:
            response = await self.client.fetch(email_id, "(BODY[])")
            if response.result != "OK":
                self.logger.error(f"Failed to fetch email {email_id}")
                return

            raw_email = response.lines[1]
            email_message = BytesParser(policy=default_policy).parsebytes(raw_email)  # type: ignore
            verification_code = None
            for part in email_message.walk():
                content_type = part.get_content_type()

                if content_type == "text/html":
                    payload = part.get_payload(decode=True)
                    if payload:
                        html_content = payload.decode("utf-8")
                        # plain_text = html2text(html_content)
                        code_match = re.search(
                            r'<p style="font-size:20px;margin-top:15px;">(\d+)</p>',
                            html_content,
                        )
                        if code_match:
                            verification_code = code_match.group(1)

            self.logger.info(f"Processing email - Subject: {email_message['subject']}")

            if verification_code:
                async with httpx.AsyncClient() as client:
                    await client.post(
                        "https://api.fonnte.com/send",
                        headers={"Authorization": os.environ["FONNTE_TOKEN"]},
                        data={
                            "target": os.environ["FONNTE_TARGET"],
                            "message": verification_code,
                        },
                    )

        except Exception as e:
            self.logger.error(f"Error processing email {email_id}: {str(e)}")

    async def start_idle(self):
        if not self.client:
            await self.connect()

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

    async def stop(self):
        self.logger.info("Stopping IDLE listener")
        self._stop_event.set()
        if self.client:
            try:
                await self.client.logout()
            except Exception as e:
                self.logger.error(f"Error during logout: {e}", exc_info=True)
            finally:
                self.client = None
