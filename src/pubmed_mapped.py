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

def parse_preprints(recordList):
    results = []
    for PMID in recordList:
        handle = Entrez.efetch(db="pubmed", id=PMID, rettype="medline", retmode="text")
        records = Medline.parse(handle) ##parses pubmed entry for that ID 
        for record in records:
            rec_dict = {
                'preprintPMID':record['PMID'],
                'preprint_citation':record['SO'],
                'publicationType':record['PT']
            }
            try:
                rec_dict['updatedInfo']=record['UIN']
                results.append(rec_dict)
            except:
                rec_dict['updatedInfo']='could not parse'
                results.append(rec_dict)
            
            time.sleep(0.5)
    resultdf = pd.DataFrame(results)
    return(resultdf)

def parse_pmid(entry):
    tmp = entry[0].split(':')
    pmid = tmp[-1].strip()
    return(pmid)

def parse_doi(entry):
    tmp = entry.split(":")
    doi = tmp[-1].strip()
    return(doi)

def parse_journal(entry):
    tmp = entry.split(":")
    tmp2 = tmp[0].split(".")
    journal = tmp2[0]
    return(journal)    

def fetch_pubmed_preprints(email_address):
    Entrez.email=email_address
    handle = Entrez.esearch(db="pubmed", RetMax=5000, term="preprint[Publication Type]")
    records = Entrez.read(handle)
    handle.close()
    recordList = records['IdList']
    return(recordList)

def load_litcovid_ids(ARCHIVEPATH):
    with open(os.path.join(ARCHIVEPATH,'all_litcovid_dict.txt'),'rb') as infile:
        all_litcovid_dict = pickle.load(infile)
    key = list(all_litcovid_dict.keys())
    all_litcovid_ids = all_litcovid_dict[key[0]]
    return(all_litcovid_ids)

def doi_to_id(entry):
    no_end_period = entry.rstrip('.')
    no_versions = re.sub(r"\/v\d","",no_end_period)
    split_out_slashes = no_versions.split('/')
    the_id = split_out_slashes[-1]
    return(the_id)

def parse_records(recordList,ARCHIVEPATH):
    resultdf = parse_preprints(recordList)
    has_update = resultdf.loc[resultdf['updatedInfo']!='could not parse'].copy()
    has_update['updatedPMID'] = has_update.apply(lambda row: parse_pmid(row['updatedInfo']),axis=1)
    all_litcovid_ids = load_litcovid_ids(ARCHIVEPATH)
    has_update['outbreak_update_pmids']=['pmid'+str(x) for x in has_update['updatedPMID']]
    has_litcovid = has_update.loc[has_update['updatedPMID'].isin(all_litcovid_ids)].copy()
    has_litcovid['doi'] = has_litcovid.apply(lambda row: parse_doi(row['preprint_citation']),axis=1)
    has_litcovid['preprint journal'] = has_litcovid.apply(lambda row: parse_journal(row['preprint_citation']),axis=1)
    has_litcovid['outbreak_preprint_id'] = has_litcovid.apply(lambda row:doi_to_id(row['doi']),axis=1)
    return(has_update)

def transform_results(has_litcovid):
    from_rxiv = has_litcovid.loc[has_litcovid['preprint journal'].astype(str).str.contains('Rxiv')]
    updatedf = from_rxiv[['outbreak_update_pmids','outbreak_preprint_id']].copy()
    updatedf.rename(columns={'outbreak_update_pmids':'litcovid','outbreak_preprint_id':'preprint'},inplace=True)
    return(updatedf)

def pull_updates_from_pubmed(email_address,ARCHIVEPATH,OUTPUTPATH):
    recordList = fetch_pubmed_preprints(email_address)
    has_litcovid = parse_records(recordList,ARCHIVEPATH)
    updatedf = transform_results(has_litcovid)
    generate_updates(updatedf,OUTPUTPATH)
    generate_split_updates(updatedf,OUTPUTPATH)