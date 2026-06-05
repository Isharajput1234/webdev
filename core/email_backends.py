from __future__ import annotations

import traceback
from typing import Iterable

from django.core.mail.backends.smtp import EmailBackend as DjangoSMTPEmailBackend


class DebugSMTPEmailBackend(DjangoSMTPEmailBackend):
    """
    SMTP backend that logs safe, high-signal diagnostics.

    It avoids printing credentials or raw SMTP traffic.
    """

    def open(self) -> bool:
        opened = super().open()
        try:
            if self.connection is not None:
                code, msg = self.connection.noop()
                safe_msg = msg.decode(errors="replace") if isinstance(msg, (bytes, bytearray)) else str(msg)
                print(
                    "[email-debug] connected",
                    f"host={self.host}",
                    f"port={self.port}",
                    f"use_tls={self.use_tls}",
                    f"use_ssl={self.use_ssl}",
                    f"noop={code} {safe_msg}",
                )
        except Exception:
            print("[email-debug] connection NOOP failed")
            print(traceback.format_exc())
        return opened

    def send_messages(self, email_messages: Iterable) -> int:
        msgs = list(email_messages or [])
        try:
            print(
                "[email-debug] sending batch",
                f"host={self.host}",
                f"port={self.port}",
                f"use_tls={self.use_tls}",
                f"use_ssl={self.use_ssl}",
                f"count={len(msgs)}",
            )
            for i, m in enumerate(msgs, start=1):
                to = ",".join(getattr(m, "to", []) or [])
                cc = ",".join(getattr(m, "cc", []) or [])
                bcc = ",".join(getattr(m, "bcc", []) or [])
                print(
                    f"[email-debug] msg#{i}",
                    f"from={getattr(m, 'from_email', '')}",
                    f"to={to}",
                    f"cc={cc}",
                    f"bcc={bcc}",
                    f"subject={getattr(m, 'subject', '')}",
                )

            sent = super().send_messages(msgs)
            print("[email-debug] sent", f"count={sent}")
            return sent
        except Exception:
            print("[email-debug] send failed")
            print(traceback.format_exc())
            raise

