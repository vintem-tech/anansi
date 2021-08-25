import json
from typing import List, Union
from src.utils import schemas
from src.utils.databases.sql.models import SingleTickerMonitoring
from pony.orm import db_session, select