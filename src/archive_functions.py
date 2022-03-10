import os
import requests
import pickle
import json
import pandas as pd
from pandas import read_csv
from datetime import datetime,timedelta


#### Functions for updating the save files

## Function to update the bag of words dataframes
def update_precompute(clean_df_set,ARCHIVEPATH):
    if 'pmid' in clean_df_set['_id'].iloc[0]:
        df_source = "litcovid"
    else:
        df_source = "preprint"
    if 'author' in list(clean_df_set.columns):
        df_type = 'auth'
    else:
        df_type = 'text'
    filename = df_type+"_"+df_source+"_set.txt"
    with open(os.path.join(ARCHIVEPATH,filename), "rb") as tmpfile:
        old_info = pickle.load(tmpfile)
    updated_info = pd.concat((old_info,clean_df_set),ignore_index=True)
    updated_info.drop_duplicates(subset='_id',keep='last',inplace=True)
    with open(os.path.join(ARCHIVEPATH,filename), "wb") as dmpfile:
        pickle.dump(updated_info, dmpfile)


## Format the results for easier updating in biothings
def convert_txt_dumps(txtdump):
    colnames = list(txtdump.columns)
    txtdump.rename(columns={'correction.identifier':'identifier','correction.url':'url','correction.correctionType':'correctionType'}, inplace=True)
    dictlist = []
    for i in range(len(txtdump)):
        if 'correction.pmid' in colnames:
            tmpdict={'_id':txtdump.iloc[i]['_id'],'correction':[{'@type':'Correction',
                                                                'identifier':txtdump.iloc[i]['identifier'],
                                                                'correctionType':txtdump.iloc[i]['correctionType'],
                                                                'url':txtdump.iloc[i]['url'],
                                                                'pmid':txtdump.iloc[i]['correction.pmid']}]}
        else:
             tmpdict={'_id':txtdump.iloc[i]['_id'],'correction':[{'@type':'Correction',
                                                                'identifier':txtdump.iloc[i]['identifier'],
                                                                'correctionType':txtdump.iloc[i]['correctionType'],
                                                                'url':txtdump.iloc[i]['url']}]}           
        dictlist.append(tmpdict)
    return(dictlist)


def generate_updates(updatedf,OUTPUTPATH):
    priorupdates = read_csv(os.path.join(OUTPUTPATH,'update_file.tsv'),delimiter="\t",header=0,index_col=0)
    correctionA = updatedf[['litcovid','preprint']].copy()
    correctionA.rename(columns={'litcovid':'_id','preprint':'correction.identifier'},inplace=True)
    correctionA['correction.@type']='outbreak:Correction'
    correctionA['correction.correctionType']='preprint'
    correctionA['baseurl']='https://doi.org/10.1101/'
    correctionA['correction.url']=correctionA['baseurl'].str.cat(correctionA['correction.identifier'])
    correctionA.drop('baseurl',axis=1,inplace=True)
    correctionB = updatedf[['litcovid','preprint']].copy()
    correctionB.rename(columns={'litcovid':'correction.identifier','preprint':'_id'},inplace=True)
    correctionB['correction.@type']='outbreak:Correction'
    correctionB['correction.correctionType']='peer-reviewed version'
    correctionB['baseurl']='https://pubmed.ncbi.nlm.nih.gov/'
    correctionB['correction.pmid'] = correctionB['correction.identifier'].astype(str).str.replace('pmid','')
    correctionB['correction.url']=correctionB['baseurl'].str.cat(correctionB['correction.pmid'])
    correctionB.drop('baseurl',axis=1,inplace=True)
    correctionB.drop('correction.pmid',axis=1,inplace=True)
    correctionupdate = pd.concat((priorupdates,correctionA,correctionB),ignore_index=True)
    correctionupdate.drop_duplicates(keep='first')
    correctionupdate.to_csv(os.path.join(OUTPUTPATH,'update_file.tsv'),sep="\t",header=True)
    corrections_added = len(correctionupdate)
    json_corrections = convert_txt_dumps(correctionupdate)
    with open(os.path.join(OUTPUTPATH,'update_file.json'), 'w', encoding='utf-8') as f:
        json.dump(json_corrections, f)
    return(corrections_added)


#### save the results to different files
def generate_split_updates(updatedf,OUTPUTPATH):
    priorlitcovidupdates = read_csv(os.path.join(OUTPUTPATH,'litcovid_update_file.tsv'),delimiter="\t",header=0,index_col=0)
    correctionA = updatedf[['litcovid','preprint']].copy()
    correctionA.rename(columns={'litcovid':'_id','preprint':'correction.identifier'},inplace=True)
    correctionA['correction.@type']='outbreak:Correction'
    correctionA['correction.correctionType']='preprint'
    correctionA['baseurl']='https://doi.org/10.1101/'
    correctionA['correction.url']=correctionA['baseurl'].str.cat(correctionA['correction.identifier'])
    correctionA.drop('baseurl',axis=1,inplace=True)
    correctionAupdate = pd.concat((priorlitcovidupdates,correctionA),ignore_index=True)
    correctionAupdate.drop_duplicates(keep='first')
    correctionAupdate.to_csv(os.path.join(OUTPUTPATH,'litcovid_update_file.tsv'),sep="\t",header=True)
    json_correctionsA = convert_txt_dumps(correctionAupdate)
    with open(os.path.join(OUTPUTPATH,'litcovid_update_file.json'), 'w', encoding='utf-8') as f:
        json.dump(json_correctionsA, f)
    priorpreprintupdates = read_csv(os.path.join(OUTPUTPATH,'preprint_update_file.tsv'),delimiter="\t",header=0,index_col=0,converters = {'correction.pmid': str})
    correctionB = updatedf[['litcovid','preprint']].copy()
    correctionB.rename(columns={'litcovid':'correction.identifier','preprint':'_id'},inplace=True)
    correctionB['correction.@type']='outbreak:Correction'
    correctionB['correction.correctionType']='peer-reviewed version'
    correctionB['baseurl']='https://pubmed.ncbi.nlm.nih.gov/'
    correctionB['correction.pmid'] = correctionB['correction.identifier'].astype(str).str.replace('pmid','')
    correctionB['correction.url']=correctionB['baseurl'].str.cat(correctionB['correction.pmid'])
    correctionB.drop('baseurl',axis=1,inplace=True)
    correctionBupdate = pd.concat((priorpreprintupdates,correctionB),ignore_index=True)
    correctionBupdate.drop_duplicates(keep='first')
    correctionBupdate.to_csv(os.path.join(OUTPUTPATH,'preprint_update_file.tsv'),sep="\t",header=True)
    json_correctionsB = convert_txt_dumps(correctionBupdate)
    with open(os.path.join(OUTPUTPATH,'preprint_update_file.json'), 'w', encoding='utf-8') as f:
        json.dump(json_correctionsB, f)
    corrections_added = len(correctionBupdate)+len(correctionAupdate)
    return(corrections_added)


## Function to update the save files for manual review or further processing (formatting for biothings)        
def update_results(result_df,ARCHIVEPATH,REVIEWPATH):
    update_dict = {}
    dupcheck = result_df.groupby('litcovid').size().reset_index(name='counts')
    dupcheck2 = result_df.groupby('preprint').size().reset_index(name='counts')
    if len(dupcheck.loc[dupcheck['counts']>1]) or len(dupcheck2.loc[dupcheck2['counts']>1]):
        old_manual_check = read_csv(os.path.join(REVIEWPATH,'manual_check.txt'),delimiter='\t',header=0,index_col=0)
        update_dict['previous matches for manual checking']=len(old_manual_check)
        update_dict['current matches for manual checking'] =len(result_df)
        total_manual_check = pd.concat((old_manual_check,result_df),ignore_index=True)
        total_manual_check.drop_duplicates(subset=['litcovid','preprint'],keep='first',inplace=True)
        total_manual_check.to_csv(os.path.join(REVIEWPATH,'manual_check.txt'),sep='\t',header=True)
    elif result_df['sum_score'].max() < 0.75:
        old_low_scores = read_csv(os.path.join(REVIEWPATH,'low_scores.txt'),delimiter='\t',header=0,index_col=0)
        update_dict['previous matches with low scores']=len(old_low_scores)
        update_dict['current matches with low scores'] =len(result_df)
        old_low_scores = pd.concat((old_low_scores,result_df),ignore_index=True)
        old_low_scores.drop_duplicates(subset=['litcovid','preprint'],keep='first',inplace=True)
        old_low_scores.to_csv(os.path.join(REVIEWPATH,'low_scores.txt'),sep='\t',header=True)
    elif (len(dupcheck) == len(result_df)) and (len(dupcheck2)==len(result_df)):
        old_clean_results = read_csv(os.path.join(ARCHIVEPATH,'clean_results.txt'),delimiter='\t',header=0,index_col=0)
        update_dict['previous matches for updating']=len(old_clean_results)
        update_dict['current matches for updating'] =len(result_df)
        old_clean_results = pd.concat((old_clean_results,result_df),ignore_index=True)
        old_clean_results.drop_duplicates(subset=['litcovid','preprint'],keep='first',inplace=True)
        old_clean_results.to_csv(os.path.join(ARCHIVEPATH,'clean_results.txt'),sep='\t',header=True)
    return(update_dict)   