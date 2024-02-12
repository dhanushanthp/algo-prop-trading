import logging

# Configure logging
logging.basicConfig(filename='logs.log', level=logging.INFO)

# Create a logger object
logger = logging.getLogger('snipper_reloaded')


if __name__ == "__main__":
    logger.info("testing")