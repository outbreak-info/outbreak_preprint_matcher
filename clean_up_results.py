import os
import requests
import pickle
import json
import pandas as pd
from pandas import read_csv
from datetime import datetime,timedelta
import pathlib
from src.comparison_functions import *
from src.archive_functions import *


#### Set paths
scriptpath = pathlib.Path(__file__).parent.absolute()
RESULTSPATH = os.path.join(scriptpath,'results/')
ARCHIVEPATH = os.path.join(RESULTSPATH,'archives/')
TEMPPATH = os.path.join(RESULTSPATH,'temp/')
OUTPUTPATH = os.path.join(RESULTSPATH,'update dumps/')
REVIEWPATH = os.path.join(RESULTSPATH,'to review/')

thresholds = {"auth":0.45,
              "text":0.2,
              "sum_min":0.75}

## update the set after the run
runcheck_dict = check_comparison_run(TEMPPATH)
if False not in list(runcheck_dict.values()):
    update_precompute(clean_lit_text,ARCHIVEPATH)
    update_precompute(clean_lit_auth,ARCHIVEPATH)
    update_precompute(clean_rxiv_text,ARCHIVEPATH)
    update_precompute(clean_rxiv_auth,ARCHIVEPATH)
    try:
        new_text_matches = read_csv(os.path.join(TEMPPATH,'text_above_threshold.txt'),delimiter='\t',header=0,index_col=False)
        if 'Unnamed: 0' in new_text_matches.columns:
            new_text_matches.drop('Unnamed: 0',axis=1,inplace=True)
    except:
        new_text_matches = pd.DataFrame(columns=['litcovid','preprint','j_sim'])
    try:
        new_auth_matches = read_csv('results/temp/auth_above_threshold.txt',delimiter='\t',header=0,index_col=False)
        if 'Unnamed: 0' in new_auth_matches.columns:
            new_auth_matches.drop('Unnamed: 0',axis=1,inplace=True)
    except:
        new_auth_matches = pd.DataFrame(columns=['litcovid','preprint','j_sim'])

    if len(new_text_matches)<1 or len(new_auth_matches)<1:
        matchupdates = False
    else:
        matchupdates = True
        clean_matches,lowscores,manual_check = sort_matches(new_text_matches,new_auth_matches,thresholds)
    corrections_added = generate_updates(clean_matches,OUTPUTPATH)
    manual_check_update = update_results(manual_check,ARCHIVEPATH,REVIEWPATH)
    lowscores_update = update_results(lowscores,ARCHIVEPATH,REVIEWPATH)
    clean_match_update = update_results(clean_matches,ARCHIVEPATH,REVIEWPATH)
else:
    print(runcheck_dict)