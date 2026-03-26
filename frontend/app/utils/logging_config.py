import logging


def configure_logging(level_name: str = "INFO") -> None:
    root_logger = logging.getLogger()
    if getattr(configure_logging, "_configured", False):
        root_logger.setLevel(_resolve_level(level_name))
        return

    logging.basicConfig(
        level=_resolve_level(level_name),
        format="%(asctime)s %(levelname)s %(message)s",
    )
    configure_logging._configured = True


def _resolve_level(level_name: str) -> int:
    return getattr(logging, str(level_name or "INFO").upper(), logging.INFO)
