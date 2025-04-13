import logging
from rich.logging import RichHandler

def setup_logger():
    logging.basicConfig(
        level=logging.CRITICAL,  # Faqat juda muhim xabarlar
        format="%(message)s",
        handlers=[RichHandler(
            show_path=False,
            show_time=False,
            show_level=False,
            rich_tracebacks=False
        )]
    )
    logger = logging.getLogger("icloud")
    logger.propagate = False  # Boshqa loggerlarga yubormaslik
    return logger

logger = setup_logger()