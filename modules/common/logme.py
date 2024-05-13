import logging

# Configure logging
logging.basicConfig(filename='logs.log', level=logging.DEBUG)

def log_it(system:str) -> logging.Logger:
    return logging.getLogger(system)


if __name__ == "__main__":
    log_it("MAIN").debug("testing")