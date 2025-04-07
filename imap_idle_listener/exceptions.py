class IMAPListenerError(Exception):
    """Base exception for IMAP listener errors"""

    pass


class IMAPAuthError(IMAPListenerError):
    """Authentication failed"""

    pass


class IMAPConnectionError(IMAPListenerError):
    """Connection to IMAP server failed"""

    pass


class IMAPIDLEError(IMAPListenerError):
    """IDLE command failed"""

    pass
