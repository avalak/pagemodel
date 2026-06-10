import logging

__all__ = ("logger",)

logger = logging.getLogger("pagemodel")
# logger.addHandler(logging.StreamHandler())
logger.addHandler(logging.NullHandler())
