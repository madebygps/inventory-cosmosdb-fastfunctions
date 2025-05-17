import logging

logger = logging.getLogger("inventory_api") 

if not logger.handlers:
    logger.setLevel(logging.ERROR) 

    ch = logging.StreamHandler()
    ch.setLevel(logging.ERROR) 

    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Add formatter to ch
    ch.setFormatter(formatter)

    # Add ch to logger
    logger.addHandler(ch)
