import logging

logger = logging.Logger(__name__)
log_handler = logging.StreamHandler()
log_handler.setLevel(logging.NOTSET)
logger.setLevel(logging.NOTSET)
logger.addHandler(log_handler)
