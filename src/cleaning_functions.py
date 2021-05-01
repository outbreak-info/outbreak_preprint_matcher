import os
import requests
import pickle
from datetime import datetime,timedelta
import pandas as pd
from pandas import read_csv
import nltk
import string
from nltk.corpus import stopwords
stopwords = stopwords.words("english")

## reduce camelcase differences by lower casing everything, deal with punctuation oddities, remove stopwords and tokenize
def text2word_tokens(section_text):
    sample_text = section_text.lower().translate(str.maketrans('','',string.punctuation))
    sample_set = [x for x in nltk.tokenize.word_tokenize(sample_text) if x not in stopwords]
    return(sample_set)

## Pull the ids from a dataframe
def get_ids_from_df(rawdf_set):
    rawdf_ids = rawdf_set['_id'].unique().tolist()
    return(rawdf_ids)

## merge title and abstract and create bag of words, remove entries missing abstract (can't be compared)
def remove_text_na(rawdf):
    rawdf['text'] = rawdf['name'].str.cat(rawdf['abstract'], sep=" | ")
    rawdf_set = rawdf.loc[~rawdf['abstract'].isna() & ~rawdf['text'].isna()].copy()
    rawdf_set['words'] = rawdf_set.apply(lambda x: text2word_tokens(x['text']), axis=1)
    return(rawdf_set)

## create bag of words from author and remove entries missing authors (can't be compared)
def remove_auth_na(rawdf,textset_ids):
    rawdf_set = rawdf.loc[~rawdf['author'].isna() & rawdf['_id'].isin(textset_ids)].copy()
    rawdf_set['author'] = rawdf_set['author'].astype(str)
    rawdf_set['words'] = rawdf_set.apply(lambda x: text2word_tokens(x['author']), axis=1)
    return(rawdf_set)

## run the cleaning functions above on a given text dataframe, author dataframe, and source (preprint or litcovid)
def clean_source_data(textdf,authdf,source):
    textdf_set = remove_text_na(textdf)
    textdf_ids = get_ids_from_df(textdf_set)
    authdf_set = remove_auth_na(authdf,textdf_ids)
    authdf_ids = get_ids_from_df(authdf_set)
    return(textdf_set,authdf_set)

## Remove previous successful matches from old metadata prior to running comparisons
def remove_matched_values(source,dftype,ARCHIVEPATH):
    clean_matches = read_csv(os.path.join(ARCHIVEPATH,'clean_results.txt'),delimiter='\t',header=0,index_col=0)
    matched_ids = clean_matches[source].unique().tolist()
    filename = dftype+"_"+source+"_set.txt"
    with open(os.path.join(ARCHIVEPATH,filename), "rb") as openfile:
        old_source = pickle.load(openfile)
    clean_source = old_source.loc[~old_source['_id'].isin(matched_ids)]
    return(clean_source)


## Blank out the previous temp files 
def blank_temps(TEMPPATH):
    tmpfiles = ['auth_above_threshold.txt','text_above_threshold.txt']
    for eachfile in tmpfiles:
        with open(os.path.join(TEMPPATH,eachfile),'w') as outwrite:
            outwrite.write('\tlitcovid\tpreprint\tj_sim\n')