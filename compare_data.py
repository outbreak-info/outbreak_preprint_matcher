#### This code performs the actual bag of word comparisons

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
from src.comparison_functions import *

scriptpath = pathlib.Path(__file__).parent.absolute()
generalpath = pathlib.Path(__file__).parents[0]
RESULTSPATH = os.path.join(scriptpath,'results/')
ARCHIVEPATH = os.path.join(RESULTSPATH,'archives/')
TEMPPATH = os.path.join(RESULTSPATH,'temp/')
TOPICPATH = os.path.join(generalpath,'topic_classifier/results')
TOPICFILE = read_csv(os.path.join(TOPICPATH,'topicCats.tsv'),delimiter='\t',header=0,index_col=0,
                     converters={"topicCategory": lambda x: x.strip("[]").replace("'","").split(", ")})
TOPICFILE.fillna({i: [] for i in TOPICFILE.index})
topicdf = TOPICFILE.explode('topicCategory').reset_index()
topicdf.drop(columns=['index'],inplace=True)

thresholds = {"auth":0.45,
              "text":0.2,
              "sum_min":0.75}

clean_rxiv_text,clean_rxiv_auth,clean_lit_text,clean_lit_auth = load_new_meta(TEMPPATH)
old_rxiv_text,old_rxiv_auth,old_lit_text,old_lit_auth =  load_previous_runs(ARCHIVEPATH)

new_rxiv = check_b4_compare(clean_rxiv_text,old_rxiv_text)
new_litcovid = check_b4_compare(clean_rxiv_text,old_rxiv_text)

if new_rxiv==True and new_litcovid==True:
    blank_temps(TEMPPATH)
    ## run old preprints against new litcovid entries:
    if len(clean_lit_text)>0:
        for eachtopic in topicdf['topicCategory'].unique().tolist():
            preprint_topicdf,litcovid_topicdf = generate_comparison_dfs(topicdf,clean_lit_text,old_rxiv_text,eachtopic)
            if len(preprint_topicdf)+len(litcovid_topicdf)>0:
                run_comparison(preprint_topicdf,litcovid_topicdf,'text',thresholds,TEMPPATH)
    if len(clean_lit_auth)>0:
        for eachtopic in topicdf['topicCategory'].unique().tolist():
            preprint_topicdf,litcovid_topicdf = generate_comparison_dfs(topicdf,clean_lit_auth,old_rxiv_auth,eachtopic)
            if len(preprint_topicdf)+len(litcovid_topicdf)>0:
                run_comparison(preprint_topicdf,litcovid_topicdf,'auth', thresholds,TEMPPATH)
    ## run new preprints against new litcovid entries
    if len(clean_rxiv_text)>0:
        for eachtopic in topicdf['topicCategory'].unique().tolist():
            preprint_topicdf,litcovid_topicdf = generate_comparison_dfs(topicdf,clean_lit_text,clean_rxiv_text,eachtopic)
            if len(preprint_topicdf)+len(litcovid_topicdf)>0:
                run_comparison(preprint_topicdf,litcovid_topicdf,'text',thresholds)
    if len(clean_rxiv_auth)>0:
        for eachtopic in topicdf['topicCategory'].unique().tolist():
            preprint_topicdf,litcovid_topicdf = generate_comparison_dfs(topicdf,clean_lit_auth,clean_rxiv_auth,eachtopic)
            if len(preprint_topicdf)+len(litcovid_topicdf)>0:
                run_comparison(preprint_topicdf,litcovid_topicdf,'auth', thresholds)

elif new_rxiv==False and new_litcovid==True:
    ## run old preprints against new litcovid entries
    if len(clean_lit_text)>0:
        for eachtopic in topicdf['topicCategory'].unique().tolist():
            preprint_topicdf,litcovid_topicdf = generate_comparison_dfs(topicdf,clean_lit_text,old_rxiv_text,eachtopic)
            if len(preprint_topicdf)+len(litcovid_topicdf)>0:
                run_comparison(preprint_topicdf,litcovid_topicdf,'text',thresholds,TEMPPATH)
    if len(clean_lit_auth)>0:
        for eachtopic in topicdf['topicCategory'].unique().tolist():
            preprint_topicdf,litcovid_topicdf = generate_comparison_dfs(topicdf,clean_lit_auth,old_rxiv_auth,eachtopic)
            if len(preprint_topicdf)+len(litcovid_topicdf)>0:
                run_comparison(preprint_topicdf,litcovid_topicdf,'auth', thresholds,TEMPPATH)

elif new_rxiv==True and new_litcovid==False:
    print("no point in comparing new preprints to old litcovid entries)
          
else:
    print("nothing new to compare")