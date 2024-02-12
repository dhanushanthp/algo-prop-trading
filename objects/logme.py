import logging

# Configure logging
logging.basicConfig(filename='logs.log', level=logging.DEBUG)

# Create a logger object
logger = logging.getLogger('snipper_reloaded')


if __name__ == "__main__":
    logger.info("testing")
    logger.debug("testing")
    logger.error("testing")