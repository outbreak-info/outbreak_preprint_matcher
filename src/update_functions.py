import os
import requests
import pickle
import json
from datetime import datetime,timedelta
import pandas as pd
from pandas import read_csv
from src.cleaning_functions import *

#### Get the size of the source (to make it easy to figure out when to stop scrolling)
def fetch_src_size(source):
    pubmeta = requests.get("https://api.outbreak.info/resources/query?q=curatedBy.name:"+source+"&size=0&aggs=@type")
    pubjson = json.loads(pubmeta.text)
    pubcount = int(pubjson["facets"]["@type"]["total"])
    return(pubcount)

#### Pull ids from a json file
def get_ids_from_json(jsonfile):
    idlist = []
    for eachhit in jsonfile["hits"]:
        if eachhit["_id"] not in idlist:
            idlist.append(eachhit["_id"])
    return(idlist)

#### Ping the API and get all the ids for a specific source and scroll through the source until number of ids matches meta
def get_source_ids(source):
    source_size = fetch_src_size(source)
    r = requests.get("https://api.outbreak.info/resources/query?q=curatedBy.name:"+source+"&fields=_id&fetch_all=true")
    response = json.loads(r.text)
    idlist = get_ids_from_json(response)
    try:
        scroll_id = response["_scroll_id"]
        while len(idlist) < source_size:
            r2 = requests.get("https://api.outbreak.info/resources/query?q=curatedBy.name:"+source+"&fields=_id&fetch_all=true&scroll_id="+scroll_id)
            response2 = json.loads(r2.text)
            idlist2 = set(get_ids_from_json(response2))
            tmpset = set(idlist)
            idlist = tmpset.union(idlist2)
            try:
                scroll_id = response2["_scroll_id"]
            except:
                print("no new scroll id")
        return(idlist)
    except:
        return(idlist)

#### Pull ids from the major publication sources (litcovid, medrxiv,biorxiv)
def get_pub_ids():
    update_date = datetime.now()
    biorxiv_ids = get_source_ids("bioRxiv")
    medrxiv_ids = get_source_ids("medRxiv")
    litcovid_idlist = get_source_ids("litcovid")
    preprint_idlist = list(set(medrxiv_ids).union(set(biorxiv_ids)))
    preprint_ids={datetime.strftime(update_date,'%Y-%m-%d'):preprint_idlist}
    litcovid_ids={datetime.strftime(update_date,'%Y-%m-%d'):litcovid_idlist}
    return(preprint_ids,litcovid_ids)


def get_date(datedict):
    for eachdate in list(datedict.keys()):
        dict_date = datetime.strptime(eachdate,'%Y-%m-%d')
    return(dict_date)


#### Load the previously saved id lists, and compare the two to identify only the new ids
def remove_old_ids(preprint_dict,litcovid_dict,ARCHIVEPATH,TEMPPATH):
    preprint_run = pickle.load(open(os.path.join(ARCHIVEPATH,"all_preprint_dict.txt"), "rb"))
    litcovid_run = pickle.load(open(os.path.join(ARCHIVEPATH,"all_litcovid_dict.txt"), "rb"))
    old_preprint_date = get_date(preprint_run)
    old_litcovid_date = get_date(litcovid_run)
    all_preprint_date = get_date(preprint_dict)
    all_litcovid_date = get_date(litcovid_dict)
    old_pre_str_date = datetime.strftime(old_preprint_date,'%Y-%m-%d')
    old_lit_str_date = datetime.strftime(old_litcovid_date,'%Y-%m-%d')
    all_pre_str_date = datetime.strftime(all_preprint_date,'%Y-%m-%d')
    all_lit_str_date = datetime.strftime(all_litcovid_date,'%Y-%m-%d')
    if (all_preprint_date-old_preprint_date)> timedelta(days=1):
        new_preprint_ids = [x for x in preprint_dict[all_pre_str_date] if x not in preprint_run[old_pre_str_date]]
        new_preprint_dict = {all_pre_str_date:new_preprint_ids}
        with open(os.path.join(TEMPPATH,"new_preprint_dict.txt"),"wb") as dumpfile:
            pickle.dump(new_preprint_dict,dumpfile)
        with open(os.path.join(ARCHIVEPATH,"all_preprint_dict.txt"),"wb") as dumpfile:
            pickle.dump(preprint_dict,dumpfile)       
    if (all_litcovid_date-old_litcovid_date)> timedelta(days=1):
        new_litcovid_ids = [x for x in litcovid_dict[all_lit_str_date] if x not in litcovid_run[old_lit_str_date]]
        new_litcovid_dict = {all_lit_str_date:new_litcovid_ids}
        with open(os.path.join(TEMPPATH,"new_litcovid_dict.txt"),"wb") as dumpfile:
            pickle.dump(new_litcovid_dict,dumpfile)
        with open(os.path.join(ARCHIVEPATH,"all_litcovid_dict.txt"),"wb") as dumpfile:
            pickle.dump(litcovid_dict,dumpfile) 

            
def check_id_update_status(TEMPPATH):
    today = datetime.now()
    preprint_run = pickle.load(open(os.path.join(TEMPPATH,"new_preprint_dict.txt"), "rb"))
    old_preprint_date = get_date(preprint_run)
    litcovid_run = pickle.load(open(os.path.join(TEMPPATH,"new_litcovid_dict.txt"), "rb"))
    old_litcovid_date = get_date(litcovid_run)
    run_dict = {'preprint_updated':False,'litcovid_updated':False}
    if (today-old_preprint_date) < timedelta(days = 1):
        run_dict['preprint_updated']=True
    if (today-old_litcovid_date) < timedelta(days = 1):
        run_dict['litcovid_updated']=True
    return(run_dict)


def run_id_update(ARCHIVEPATH,TEMPPATH):
    run_dict = check_id_update_status(TEMPPATH)
    if False in list(run_dict.values()):
        all_preprint_ids,all_litcovid_ids = get_pub_ids()
        remove_old_ids(all_preprint_ids,all_litcovid_ids,ARCHIVEPATH,TEMPPATH)
        run_dict = check_id_update_status(TEMPPATH)
        return(run_dict)
    else:
        return(run_dict)

    
#### Get the metadata for each list
#### Note, I've tried batches of 1000, and the post request has failed, so this uses a batch size that's less likely to fail
def batch_fetch_meta(idlist):
    ## Break the list of ids into smaller chunks so the API doesn't fail the post request
    runs = round((len(idlist))/100,0)
    i=0 
    separator = ','
    ## Create dummy dataframe to store the meta data
    textdf = pd.DataFrame(columns = ['_id','abstract','name','date'])
    authdf = pd.DataFrame(columns = ['_id','author','date'])
    while i < runs+1:
        if len(idlist)<100:
            sample = idlist
        elif i == 0:
            sample = idlist[i:(i+1)*100]
        elif i == runs:
            sample = idlist[i*100:len(idlist)]
        else:
            sample = idlist[i*100:(i+1)*100]
        sample_ids = separator.join(sample)
        ## Get the text-based metadata (abstract, title) and save it
        r = requests.post("https://api.outbreak.info/resources/query/", params = {'q': sample_ids, 'scopes': '_id', 'fields': 'name,abstract,date'})
        if r.status_code == 200:
            rawresult = pd.read_json(r.text)
            cleanresult = rawresult[['_id','name','abstract','date']].loc[rawresult['_score']==1].copy()
            cleanresult.drop_duplicates(subset='_id',keep="first", inplace=True)
            textdf = pd.concat((textdf,cleanresult),ignore_index=True)
        ## Get the author metadata and save it    
        a = requests.post("https://api.outbreak.info/resources/query/", params = {'q': sample_ids, 'scopes': '_id', 'fields': 'author,date'})
        if a.status_code == 200:
            rawresult = pd.read_json(a.text)
            cleanresult = rawresult[['_id','author','date']].loc[rawresult['_score']==1].copy()
            cleanresult.drop_duplicates(subset='_id',keep="first", inplace=True)
            authdf = pd.concat((authdf,cleanresult),ignore_index=True)
        i=i+1
    return(textdf,authdf)


def load_new_ids(TEMPPATH):
    new_preprint_dict = pickle.load(open(os.path.join(TEMPPATH,"new_preprint_dict.txt"), "rb"))
    preprintdatekey = list(new_preprint_dict.keys())[0]
    new_preprint_ids = new_preprint_dict[preprintdatekey]
    new_litcovid_dict = pickle.load(open(os.path.join(TEMPPATH,"new_litcovid_dict.txt"), "rb"))
    litcoviddatekey = list(new_litcovid_dict.keys())[0]
    new_litcovid_ids = new_litcovid_dict[litcoviddatekey]
    return(new_preprint_ids,new_litcovid_ids)



def update_meta(ARCHIVEPATH,TEMPPATH):
    run_dict = run_id_update(ARCHIVEPATH,TEMPPATH)
    if False not in list(run_dict.values()):
        new_preprint_ids,new_litcovid_ids = load_new_ids(TEMPPATH)

        clean_rxiv_text = pickle.load(open(os.path.join(TEMPPATH,"clean_rxiv_text.txt"), "rb"))
        clean_rxiv_ids = get_ids_from_df(clean_rxiv_text)
        if (len(set(new_preprint_ids).intersection(set(clean_rxiv_ids)))/len(new_preprint_ids))<0.75:
            new_preprint_textdf,new_preprint_authdf = batch_fetch_meta(new_preprint_ids)
            clean_rxiv_text,clean_rxiv_auth = clean_source_data(new_preprint_textdf,new_preprint_authdf,'preprint')
            with open(os.path.join(TEMPPATH,"clean_rxiv_text.txt"), "wb") as dmpfile:
                pickle.dump(clean_rxiv_text, dmpfile)
            with open(os.path.join(TEMPPATH,"clean_rxiv_auth.txt"), "wb") as dmpfile:
                pickle.dump(clean_rxiv_auth, dmpfile)

        clean_litcovid_text = pickle.load(open(os.path.join(TEMPPATH,"clean_lit_text.txt"), "rb"))
        clean_litcovid_ids = get_ids_from_df(clean_litcovid_text)
        if (len(set(new_litcovid_ids).intersection(set(clean_litcovid_ids)))/len(new_litcovid_ids))<0.75:
            new_litcovid_textdf,new_litcovid_authdf = batch_fetch_meta(new_litcovid_ids)
            clean_lit_text,clean_lit_auth = clean_source_data(new_litcovid_textdf,new_litcovid_authdf,'litcovid')
            with open(os.path.join(TEMPPATH,"clean_lit_text.txt"), "wb") as dmpfile:
                pickle.dump(clean_lit_text, dmpfile)
            with open(os.path.join(TEMPPATH,"clean_lit_auth.txt"), "wb") as dmpfile:
                pickle.dump(clean_lit_auth, dmpfile)