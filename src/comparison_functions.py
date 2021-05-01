import os
import requests
import pickle
from datetime import datetime,timedelta
import pandas as pd
from pandas import read_csv
from cleaning_functions import *

## load the metadata for comparison
def load_new_meta(TEMPPATH):
    clean_rxiv_text = pickle.load(open(os.path.join(TEMPPATH,"clean_rxiv_text.txt"),"rb"))
    clean_rxiv_auth = pickle.load(open(os.path.join(TEMPPATH,"clean_rxiv_auth.txt"),"rb"))
    clean_lit_text = pickle.load(open(os.path.join(TEMPPATH,"clean_lit_text.txt"),"rb"))
    clean_lit_auth = pickle.load(open(os.path.join(TEMPPATH,"clean_lit_auth.txt"),"rb"))
    return(clean_rxiv_text,clean_rxiv_auth,clean_lit_text,clean_lit_auth)


def load_previous_runs(ARCHIVEPATH):
    ## Load previous run and remove successfully mapped entries
    old_rxiv_text = remove_matched_values('preprint','text',ARCHIVEPATH)
    old_rxiv_auth = remove_matched_values('preprint','auth',ARCHIVEPATH)
    old_lit_text = remove_matched_values('litcovid','text',ARCHIVEPATH)
    old_lit_auth = remove_matched_values('litcovid','auth',ARCHIVEPATH)
    return(old_rxiv_text,old_rxiv_auth,old_lit_text,old_lit_auth)

#### Check if 2/3 of the new ids are already in the old ids. If so, then there's no need to do the comparison
def check_b4_compare(newdf,olddf):
    newids = set(newdf['_id'].unique().tolist)
    oldids = set(olddf['_id'].unique().tolist)
    incommon = oldids.intersection(newids)
    if len(incommon)/len(newids)>0.67:
        newdata = False
    else:
        newdata = True
        

#### Generate id_lists by topicCategory  
def generate_comparison_dfs(topicdf,litcoviddf,preprintdf,topicCategory):
    idlist = topicdf['_id'].loc[topicdf['topicCategory']==topicCategory].unique().tolist()
    preprint_topicdf = preprintdf.loc[preprintdf['_id'].isin(idlist)]
    litcovid_topicdf = litcoviddf.loc[litcoviddf['_id'].isin(idlist)]
    return(preprint_topicdf,litcovid_topicdf)


#### Calculate jaccard similiarity and return -1 for anything that falls below threshold
def calculate_jsim(sample_set1,sample_set2,thresholds,set_type):
    j_dist = nltk.jaccard_distance(set(sample_set1),set(sample_set2))
    j_sim = 1-j_dist
    if j_sim > thresholds[set_type]:
        return(j_sim)
    else:
        return(-1)
    

## The comparison function re-written with pandas itterrows AND lambda apply in hopes of speeding it up even more
def run_comparison(preprint_set,litcovid_set,set_type,thresholds,TEMPPATH):
    matches = pd.DataFrame(columns=['litcovid','preprint','j_sim'])
    filename = set_type+"_above_threshold.txt"
    for index, row in litcovid_set.iterrows():
        litcovidwords = set(row['words'])
        preprint_subset = preprint_set.loc[preprint_set['date']<=row['date']].copy()
        if len(preprint_subset)>0:
            preprint_subset.rename(columns={'_id':'preprint'},inplace=True)
            preprint_subset['j_sim'] = preprint_subset.apply(lambda x: calculate_jsim(litcovidwords,set(x['words']),thresholds,set_type),axis=1)
            preprint_subset['litcovid']=row['_id']
            clean = preprint_subset[['litcovid','preprint','j_sim']].loc[preprint_subset['j_sim']!=-1].copy()
            if len(clean)>0:
                matches = pd.concat((matches,clean),ignore_index=True)
    matches.to_csv(os.path.join(TEMPPATH,filename),mode="a",sep='\t',header=False) 
    
    
## Merge the author and text matches that meet threshold, calculate sum score, and sort results
def sort_matches(new_text_matches,new_auth_matches,threshold):
    new_text_matches.rename(columns={'j_sim':'j_sim_text'},inplace=True)
    new_auth_matches.rename(columns={'j_sim':'j_sim_author'},inplace=True)
    preprint_matches = new_text_matches.merge(new_auth_matches,on=['litcovid','preprint'],how='inner')
    preprint_matches['sum_score'] = preprint_matches['j_sim_text']+preprint_matches['j_sim_author']
    preprint_matches['date'] = datetime.now().strftime('%Y-%m-%d')
    ## Set duplicates aside for manual checking
    dupcheckdf = preprint_matches.groupby('preprint').size().reset_index(name='preprint_count')
    dup_preprints = dupcheckdf['preprint'].loc[dupcheckdf['preprint_count']>1].tolist() ## does a preprint map to more than one pmid?
    duplitcheckdf = preprint_matches.groupby('litcovid').size().reset_index(name='litcovid_count')
    dup_pmids = duplitcheckdf['litcovid'].loc[duplitcheckdf['litcovid_count']>1].tolist() ## does a preprint map to more than one pmid?
        
    duplicates = preprint_matches.loc[(preprint_matches['litcovid'].isin(dup_pmids)) | 
                                      (preprint_matches['preprint'].isin(dup_preprints))]
    ## Set low scores aside for manual checking
    lowscores = preprint_matches.loc[preprint_matches['sum_score']<threshold['sum_min']]
    ## Save the clean matches for auto updating
    clean_matches = preprint_matches.loc[(~preprint_matches['litcovid'].isin(dup_pmids)) &
                                         (~preprint_matches['preprint'].isin(dup_preprints)) &
                                         (preprint_matches['sum_score']>=threshold['sum_min'])]

    manual_check = pd.concat((duplicates,lowscores),ignore_index=True)
    return(clean_matches,lowscores,manual_check)


def check_comparison_run(TEMPPATH):
    clean_rxiv_file = pathlib.Path(os.path.join(TEMPPATH,'clean_rxiv_text.txt'))
    clean_lit_file = pathlib.Path(os.path.join(TEMPPATH,'clean_lit_text.txt'))
    auth_matches = pathlib.Path(os.path.join(TEMPPATH,'auth_above_threshold.txt'))
    text_matches = pathlib.Path(os.path.join(TEMPPATH,'text_above_threshold.txt'))
    rxiv_mtime = datetime.fromtimestamp(clean_rxiv_file.stat().st_mtime)
    lit_mtime = datetime.fromtimestamp(clean_lit_file.stat().st_mtime)
    text_mtime = datetime.fromtimestamp(text_matches.stat().st_mtime)
    auth_mtime = datetime.fromtimestamp(auth_matches.stat().st_mtime)
    text_size = text_matches.stat().st_size/1024
    auth_size = auth_matches.stat().st_size/1024
    blank_size = 27/1024
    if (text_size > blank_size) and (auth_size > blank_size):
        size_check_success = True
    else:
        size_check_success = False
    if ((text_mtime - rxiv_mtime) < timedelta(days=3)) and ((auth_mtime - rxiv_mtime) < timedelta(days=3)):
        rxiv_check_success = True
    else:
        rxiv_check_success = False
    if ((text_mtime - lit_mtime) < timedelta(days=3)) and ((auth_mtime - lit_mtime) < timedelta(days=3)):
        lit_check_success = True
    else:
        lit_check_success = False
    runcheck_dict = {"size_check_success":size_check_success,
                     "preprint_check_success":rxiv_check_success,
                     "litcovid_check_success":lit_check_success}
    return(runcheck_dict)

