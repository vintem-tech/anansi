import logzero
from logzero import logger

logzero.logfile("anansi.log", loglevel=logzero.ERROR, maxBytes=1e6, backupCount=3)