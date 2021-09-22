import os
import requests
import pandas as pd
from pandas import read_csv
import json
from Bio import Entrez
from Bio import Medline
import time
import pickle
import re
from src.archive_functions import generate_updates
from src.archive_functions import generate_split_updates
from src.pubmed_mapped import *

scriptpath = pathlib.Path(__file__).parent.absolute()
RESULTSPATH = os.path.join(scriptpath,'results/')
ARCHIVEPATH = os.path.join(RESULTSPATH,'archives/')
OUTPUTPATH = os.path.join(RESULTSPATH,'update dumps/')

pull_updates_from_pubmed(email_address,ARCHIVEPATH,OUTPUTPATH