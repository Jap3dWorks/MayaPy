import logging
logging.basicConfig()
lHandler = logging.Handler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
lHandler.setFormatter(formatter)
logger = logging.getLogger('Spline Distribute UI')
logger.setLevel(logging.DEBUG)
logger.addHandler(lHandler)
