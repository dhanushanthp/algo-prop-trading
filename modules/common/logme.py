import logging
from modules import config

# Configure logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", filename=f'logs/{config.local_ip}.log', level=logging.DEBUG)

def log_it(system:str) -> logging.Logger:
    return logging.getLogger(system)


if __name__ == "__main__":
    log_it("MAIN").debug("testing")