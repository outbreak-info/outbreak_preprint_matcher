import os
import requests
import pickle
import json
import pandas as pd
from pandas import read_csv
import nltk
import string
from nltk.corpus import stopwords
stopwords = stopwords.words("english")
from datetime import datetime,timedelta
import pathlib
from src.update_functions import *
from src.cleaning_functions import *

scriptpath = pathlib.Path(__file__).parent.absolute()
RESULTSPATH = os.path.join(scriptpath,'results/')
ARCHIVEPATH = os.path.join(RESULTSPATH,'archives/')
TEMPPATH = os.path.join(RESULTSPATH,'temp/')

update_meta(ARCHIVEPATH,TEMPPATH)