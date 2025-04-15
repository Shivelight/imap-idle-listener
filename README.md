# imap-idle-listener

A Python-based IMAP IDLE listener that monitors an email inbox in real-time and processes new emails using custom handlers.

## Requirements

*   Python 3.11 or higher
*   Dependencies:
    *   `aioimaplib`

## Example Email Processor

```python
from email.message import Message
from imap_idle_listener import IMAPIdleListener

async def extract_verification_code(email_message: Message, client: IMAPIdleListener):
    print(f"Processing email: {email_message['subject']}")
```


## Full Example

You can find a full example in [`main.py`](main.py).

1.  Clone the repository:

    ```bash
    git clone https://github.com/Shivelight/imap-idle-listener
    cd imap-idle-listener
    ```

2.  Install dependencies using `uv`:

    ```bash
    uv sync --extra example
    ```

3.  Create a `.env` file based on `.env.example`.

4.  Set the following environment variables:

    *   `IMAP_SERVER`: IMAP server hostname (e.g., `imap.example.com`).
    *   `IMAP_PORT`: IMAP server port (e.g., `993`).
    *   `EMAIL_ADDRESS`: Email address for authentication.
    *   `EMAIL_PASSWORD`: Password for authentication.
    *   `MAILBOX`: Mailbox to monitor (default: `INBOX`).
    *   `CHECK_FREQUENCY`: IDLE timeout in minutes (default: `15`).
    *   `LOG_LEVEL`: Logging level (e.g., `INFO`, `DEBUG`).

5. Run the example:

    ```bash
    uv run main.py
    ```
