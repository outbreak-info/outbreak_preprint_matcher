import requests
import pickle
import json
import pandas
from pandas import read_csv
import nltk
import string
from nltk.corpus import stopwords
stopwords = stopwords.words("english")
from datetime import datetime


#### Functions to get updated ids
def fetch_src_size(source):
    pubmeta = requests.get("https://api.outbreak.info/resources/query?q=curatedBy.name:"+source+"&size=0&aggs=@type")
    pubjson = json.loads(pubmeta.text)
    pubcount = int(pubjson["facets"]["@type"]["total"])
    return(pubcount)

def get_ids_from_json(jsonfile):
    idlist = []
    for eachhit in jsonfile["hits"]:
        if eachhit["_id"] not in idlist:
            idlist.append(eachhit["_id"])
    return(idlist)

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
    
def get_pub_ids():
    biorxiv_ids = get_source_ids("biorxiv")
    medrxiv_ids = get_source_ids("medrxiv")
    litcovid_ids = get_source_ids("litcovid")
    preprint_ids = list(set(medrxiv_ids).union(set(biorxiv_ids)))
    return(preprint_ids,litcovid_ids)

def remove_old_ids(allidlist):
    preprint_run = pickle.load(open("results/archives/all_preprint_ids.txt", "rb"))
    litcovid_run = pickle.load(open("results/archives/all_litcovid_ids.txt", "rb"))
    old_id_list = list(set(preprint_run).union(set(litcovid_run)))
    new_ids_only = [x for x in allidlist if x not in old_id_list]
    return(new_ids_only)

#### Functions to get the metadata for id lists
#### Note, I've tried batches of 1000, and the post request has failed, so this uses a batch size that's less likely to fail
def batch_fetch_meta(idlist):
    runs = round((len(idlist))/100,0)
    i=0 
    separator = ','
    textdf = pandas.DataFrame(columns = ['_id','abstract','name'])
    authdf = pandas.DataFrame(columns = ['_id','author'])
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
        r = requests.post("https://api.outbreak.info/resources/query/", params = {'q': sample_ids, 'scopes': '_id', 'fields': 'name,abstract'})
        if r.status_code == 200:
            rawresult = pandas.read_json(r.text)
            cleanresult = rawresult[['_id','name','abstract']].loc[rawresult['_score']==1].copy()
            cleanresult.drop_duplicates(subset='_id',keep="first", inplace=True)
            textdf = pandas.concat((textdf,cleanresult))
            
        a = requests.post("https://api.outbreak.info/resources/query/", params = {'q': sample_ids, 'scopes': '_id', 'fields': 'author'})
        if a.status_code == 200:
            rawresult = pandas.read_json(a.text)
            cleanresult = rawresult[['_id','author']].loc[rawresult['_score']==1].copy()
            cleanresult.drop_duplicates(subset='_id',keep="first", inplace=True)
            authdf = pandas.concat((authdf,cleanresult))
        i=i+1
    return(textdf,authdf)
    
#### Functions for cleaning up metadata for new entries prior to running comparisons
def text2word_tokens(section_text):
    sample_text = section_text.lower().translate(str.maketrans('','',string.punctuation))
    sample_set = [x for x in nltk.tokenize.word_tokenize(sample_text) if x not in stopwords]
    return(sample_set)

def get_ids_from_df(rawdf_set):
    rawdf_ids = rawdf_set['_id'].unique().tolist()
    return(rawdf_ids)
    
def remove_text_na(rawdf):
    rawdf['text'] = rawdf['name'].str.cat(rawdf['abstract'], sep=" | ")
    rawdf_set = rawdf.loc[~rawdf['abstract'].isna() & ~rawdf['text'].isna()].copy()
    rawdf_set['words'] = rawdf_set.apply(lambda x: text2word_tokens(x['text']), axis=1)
    return(rawdf_set)
    
def remove_auth_na(rawdf,textset_ids):
    rawdf_set = rawdf.loc[~rawdf['author'].isna() & rawdf['_id'].isin(textset_ids)].copy()
    rawdf_set['author'] = rawdf_set['author'].astype(str)
    rawdf_set['words'] = rawdf_set.apply(lambda x: text2word_tokens(x['author']), axis=1)
    return(rawdf_set)

def clean_source_data(textdf,authdf,source):
    textdf_set = remove_text_na(textdf)
    textdf_ids = get_ids_from_df(textdf_set)
    authdf_set = remove_auth_na(authdf,textdf_ids)
    authdf_ids = get_ids_from_df(authdf_set)
    return(textdf_set,authdf_set)    
    
#### Functions for removing successful matches from old metadata prior to running comparisons
def remove_matched_values(source,dftype):
    clean_matches = read_csv('results/archives/clean_results.txt',delimiter='\t',header=0,index_col=0)
    matched_ids = clean_matches[source].unique().tolist()
    with open("results/archives/"+dftype+"_"+source+"_set.txt", "rb") as openfile:
        old_source = pickle.load(openfile)
    clean_source = old_source.loc[~old_source['_id'].isin(matched_ids)]
    return(clean_source)    

#### Functions for comparing metadata
def blank_temps():
    tmppath='results/temp/'
    tmpfiles = ['auth_above_threshold.txt','text_above_threshold.txt']
    for eachfile in tmpfiles:
        with open(tmppath+eachfile,'w') as outwrite:
            outwrite.write('litcovid\tpreprint\tj_sim\n')

def run_comparison(preprint_set,litcovid_set,set_type, thresholds):
    i=0
    while i < len(litcovid_set):
        litcovid_id = litcovid_set.iloc[i]['_id']
        sample_set1 = litcovid_set.iloc[i]['words']
        j=0
        while j < len(preprint_set):
            preprint_id = preprint_set.iloc[j]['_id']
            sample_set2 = preprint_set.iloc[j]['words']
            j_dist = nltk.jaccard_distance(set(sample_set1), set(sample_set2))
            j_sim = 1-j_dist
            if j_sim > thresholds[set_type]:
                with open("results/temp/"+set_type+"_above_threshold.txt","a") as dump:
                    dump.write(litcovid_id+'\t'+preprint_id+'\t'+str(j_sim)+'\n')
            j=j+1
        i=i+1    
    
def sort_matches(new_text_matches,new_auth_matches,threshold):
    new_text_matches.rename(columns={'j_sim':'j_sim_text'},inplace=True)
    new_auth_matches.rename(columns={'j_sim':'j_sim_author'},inplace=True)
    preprint_matches = new_text_matches.merge(new_auth_matches,on=['litcovid','preprint'],how='inner')
    preprint_matches['sum_score'] = preprint_matches['j_sim_text']+preprint_matches['j_sim_author']
    preprint_matches['date'] = datetime.now().strftime('%Y-%m-%d')
    dupcheckdf = preprint_matches.groupby('preprint').size().reset_index(name='preprint_count')
    dup_preprints = dupcheckdf['preprint'].loc[dupcheckdf['preprint_count']>1].tolist()
    duplitcheckdf = preprint_matches.groupby('litcovid').size().reset_index(name='litcovid_count')
    dup_pmids = duplitcheckdf['litcovid'].loc[duplitcheckdf['litcovid_count']>1].tolist() 
        
    duplicates = preprint_matches.loc[(preprint_matches['litcovid'].isin(dup_pmids)) | 
                                      (preprint_matches['preprint'].isin(dup_preprints))]
    lowscores = preprint_matches.loc[preprint_matches['sum_score']<threshold['sum_min']]

    clean_matches = preprint_matches.loc[(~preprint_matches['litcovid'].isin(dup_pmids)) &
                                         (~preprint_matches['preprint'].isin(dup_preprints)) &
                                         (preprint_matches['sum_score']>=threshold['sum_min'])]

    manual_check = pandas.concat((duplicates,lowscores),ignore_index=True)
    return(clean_matches,lowscores,manual_check)    
    
#### Functions for cleaning up the results
def convert_txt_dumps(txtdump):
    txtdump.rename(columns={'correction.identifier':'identifier','correction.url':'url','correction.type':'type'}, inplace=True)
    dictlist = []
    for i in range(len(txtdump)):
        tmpdict={'_id':txtdump.iloc[i]['_id'],'correction':[{'@type':'Correction',
                                                            'identifier':txtdump.iloc[i]['identifier'],
                                                            'correctionType':txtdump.iloc[i]['type'],
                                                            'url':txtdump.iloc[i]['url']}]}
        dictlist.append(tmpdict)
    return(dictlist)


def generate_updates(updatedf):
    priorupdates = read_csv('results/update dumps/update_file.tsv',delimiter="\t",header=0,index_col=0)
    correctionA = updatedf[['litcovid','preprint']].copy()
    correctionA.rename(columns={'litcovid':'_id','preprint':'correction.identifier'},inplace=True)
    correctionA['correction.type']='preprint'
    correctionA['baseurl']='https://doi.org/10.1101/'
    correctionA['correction.url']=correctionA['baseurl'].str.cat(correctionA['correction.identifier'])
    correctionA.drop('baseurl',axis=1,inplace=True)
    correctionB = updatedf[['litcovid','preprint']].copy()
    correctionB.rename(columns={'litcovid':'correction.identifier','preprint':'_id'},inplace=True)
    correctionB['correction.type']='peer-reviewed version'
    correctionB['baseurl']='https://pubmed.ncbi.nlm.nih.gov/'
    correctionB['correction.url']=correctionB['baseurl'].str.cat(correctionB['correction.identifier'])
    correctionB.drop('baseurl',axis=1,inplace=True)
    correctionupdate = pandas.concat((priorupdates,correctionA,correctionB),ignore_index=True)
    correctionupdate.drop_duplicates(keep='first')
    correctionupdate.to_csv('results/update dumps/update_file.tsv',sep="\t",header=True)
    corrections_added = len(correctionupdate)
    json_corrections = convert_txt_dumps(correctionupdate)
    with open('results/update dumps/update_file.json', 'w', encoding='utf-8') as f:
        json.dump(json_corrections, f)
    return(corrections_added)
    
#### Functions for updating the save files
def update_archives(all_ids):
    if 'pmid' in list(all_ids)[0]:
        filename = 'all_litcovid_ids'
    else:
        filename = 'all_preprint_ids'
    with open('results/archives/'+filename+'.txt', 'wb') as dmpfile:
        pickle.dump(all_ids, dmpfile)

def update_precompute(clean_df_set):
    if 'pmid' in clean_df_set['_id'].iloc[0]:
        df_source = "litcovid"
    else:
        df_source = "preprint"
    if 'author' in list(clean_df_set.columns):
        df_type = 'auth'
    else:
        df_type = 'text'
    old_info = pickle.load(open("results/archives/"+df_type+"_"+df_source+"_set.txt", "rb"))
    updated_info = pandas.concat((old_info,clean_df_set),ignore_index=True)
    with open("results/archives/"+df_type+"_"+df_source+"_set.txt", "wb") as dmpfile:
        pickle.dump(updated_info, dmpfile)

def update_results(result_df):
    update_dict = {}
    dupcheck = result_df.groupby('litcovid').size().reset_index(name='counts')
    dupcheck2 = result_df.groupby('preprint').size().reset_index(name='counts')
    if len(dupcheck.loc[dupcheck['counts']>1]) or len(dupcheck2.loc[dupcheck2['counts']>1]):
        old_manual_check = read_csv('results/to review/manual_check.txt',delimiter='\t',header=0,index_col=0)
        update_dict['previous matches for manual checking']=len(old_manual_check)
        update_dict['current matches for manual checking'] =len(result_df)
        total_manual_check = pandas.concat((old_manual_check,result_df),ignore_index=True)
        total_manual_check.drop_duplicates(subset='_id',keep='first',inplace=True)
        total_manual_check.to_csv('results/to review/manual_check.txt',sep='\t',header=True)
    elif result_df['sum_score'].max() < 0.75:
        old_low_scores = read_csv('results/to review/low_scores.txt',delimiter='\t',header=0,index_col=0)
        update_dict['previous matches with low scores']=len(old_low_scores)
        update_dict['current matches with low scores'] =len(result_df)
        old_low_scores = pandas.concat((old_low_scores,result_df),ignore_index=True)
        old_low_scores.drop_duplicates(subset='_id',keep='first',inplace=True)
        old_low_scores.to_csv('results/to review/low_scores.txt',sep='\t',header=True)
    elif (len(dupcheck) == len(result_df)) and (len(dupcheck2)==len(result_df)):
        old_clean_results = read_csv('results/archives/clean_results.txt',delimiter='\t',header=0,index_col=0)
        update_dict['previous matches for updating']=len(old_clean_results)
        update_dict['current matches for updating'] =len(result_df)
        old_clean_results = pandas.concat((old_clean_results,result_df),ignore_index=True)
        old_clean_results.drop_duplicates(subset='_id',keep='first',inplace=True)
        old_clean_results.to_csv('results/archives/clean_results.txt',sep='\t',header=True)
    return(update_dict)       


    
#### Main function
thresholds = {"auth":0.45,
              "text":0.2,
              "sum_min":0.75}

changeinfo = {'run start':datetime.now()}

## pull ids
all_preprint_ids,all_litcovid_ids = get_pub_ids()
preprint_ids = remove_old_ids(all_preprint_ids)
litcovid_ids = remove_old_ids(all_litcovid_ids)

if len(preprint_ids) > 0:
    update_archives(all_preprint_ids) ##update the archive file only if there are new ids
    preprint_textdf,preprint_authdf = batch_fetch_meta(preprint_ids) ## get meta for new ids
if len(litcovid_ids) > 0:
    update_archives(all_litcovid_ids) ##update the archive file only if there are new ids
    litcovid_textdf,litcovid_authdf = batch_fetch_meta(litcovid_ids) ## get meta for new ids
    
## log changes
changeinfo['total litcovid ids']=len(all_litcovid_ids)
changeinfo['total preprint ids']=len(all_preprint_ids)
changeinfo['new litcovid ids']=len(litcovid_ids)
changeinfo['new preprint ids']=len(preprint_ids)    
    
## Prep for comparison
clean_lit_text,clean_lit_auth = clean_source_data(litcovid_textdf,litcovid_authdf,'litcovid')
clean_rxiv_text,clean_rxiv_auth = clean_source_data(preprint_textdf,preprint_authdf,'preprint')

## Load previous run and remove successfully mapped entries
old_litcovid_text = remove_matched_values('litcovid','text')
old_litcovid_auth = remove_matched_values('litcovid','auth')

old_rxiv_text = remove_matched_values('preprint','auth')
old_rxiv_auth = remove_matched_values('preprint','auth')

## Clean up the temp files prior to the comparison run
blank_temps()

#### THIS IS THE SLOW PART OF THE SCRIPT ####
## run new preprints against new litcovid entries:
if len(clean_rxiv_auth)>0 and len(clean_lit_auth)>0:
    run_comparison(clean_rxiv_auth,clean_lit_auth,'auth', thresholds)        
if len(clean_rxiv_text)>0 and len(clean_lit_text)>0:
    run_comparison(clean_rxiv_text,clean_lit_text,'text', thresholds)

## run new litcovid entries against previous preprints
if len(clean_lit_text)>0:
    run_comparison(old_rxiv_text,clean_lit_text,'text', thresholds)
if len(clean_lit_auth)>0:
    run_comparison(old_rxiv_auth,clean_lit_auth,'auth', thresholds)

## run new preprints against previously litcovid entries:
if len(clean_rxiv_text)>0:
    run_comparison(clean_rxiv_text,old_litcovid_text,'text', thresholds)
if len(clean_rxiv_auth)>0:
    run_comparison(clean_rxiv_auth,old_litcovid_auth,'auth', thresholds)    
#### THIS WAS THE SLOW PART OF THE SCRIPT ####
    
## update the set after the run
update_precompute(clean_lit_text)
update_precompute(clean_lit_auth)
update_precompute(clean_rxiv_text)
update_precompute(clean_rxiv_auth)

try:
    new_text_matches = read_csv('results/temp/text_above_threshold.txt',delimiter='\t',header=0)
except:
    new_text_matches = pandas.DataFrame(columns=['litcovid','preprint','j_sim'])
try:
    new_auth_matches = read_csv('results/temp/auth_above_threshold.txt',delimiter='\t',header=0)
except:
    new_auth_matches = pandas.DataFrame(columns=['litcovid','preprint','j_sim'])    
    
if len(new_text_matches)<1 or len(new_auth_matches)<1:
    matchupdates = False
else:
    matchupdates = True
    clean_matches,lowscores,manual_check = sort_matches(new_text_matches,new_auth_matches,thresholds)    
    
corrections_added = generate_updates(clean_matches)
changeinfo['new matches found']=len(clean_matches)
changeinfo['new matches to review']=len(manual_check)
changeinfo['new low scoring matches']=len(lowscores)
changeinfo['new updates to make']=corrections_added    
    
manual_check_update = update_results(manual_check)
changeinfo.update(manual_check_update)
lowscores_update = update_results(lowscores)
changeinfo.update(lowscores_update)
clean_match_update = update_results(clean_matches)
changeinfo.update(clean_match_update)
changeinfo['run complete'] = datetime.now()
with open('results/temp/run_log.txt','wb') as dmpfile:
    pickle.dump(changeinfo, dmpfile)    
    
init_dmp = read_csv('results/update dumps/update_file.tsv', delimiter='\t', header=0, index_col=0)
dictlist = convert_txt_dumps(init_dmp)
with open('results/update dumps/update_file.json', 'w', encoding='utf-8') as f:
    json.dump(dictlist, f)    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    