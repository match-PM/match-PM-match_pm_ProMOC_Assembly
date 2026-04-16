"""Sanity checks for the reduced promoc_core.logging module."""

from __future__ import annotations

from promoc_core.logging import LogTags, TaggedLogger


class _FakeLogger:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def debug(self, msg: str, *args, **kwargs) -> None:
        self.calls.append(("debug", msg))

    def info(self, msg: str, *args, **kwargs) -> None:
        self.calls.append(("info", msg))

    def warning(self, msg: str, *args, **kwargs) -> None:
        self.calls.append(("warning", msg))

    def error(self, msg: str, *args, **kwargs) -> None:
        self.calls.append(("error", msg))

    def fatal(self, msg: str, *args, **kwargs) -> None:
        self.calls.append(("fatal", msg))


def test_tagged_logger_prefixes_messages() -> None:
    logger = _FakeLogger()
    tagged = TaggedLogger(logger, LogTags.CAM_AF)

    tagged.info("Focus started")
    tagged.warning("Low contrast")

    assert logger.calls == [
        ("info", "[CAM:AF] Focus started"),
        ("warning", "[CAM:AF] Low contrast"),
    ]
