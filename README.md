# Outbreak resource litcovid and preprint matcher

This code pings the outbreak.info api to pull an updated list of ids, compares the ids with files containing previously run ids and identifies the newly updated ids. For the newly updated ids, it pings the api to pull the relevant metadata so that a similarity test can be run for the new ids.

**Requirements**
This code was written in python 3.6 and uses the following libraries:
* requests
* pandas
* nltk
* pickle
* json
* string
* datetime
* pathlib

Additionally, you will need a few libraries from nltk which must be downloaded using the nltk downloader including:
* stopwords
* punkt

To get these, run this once:
`import nltk

nltk download stopwords

nltk download punkt`


**Limitations**
This code does not account for publications hosted in Zenodo, Dataverse, Figshare, or any other general repository, as the relationship between publications hosted on those sites and litcovid publications cannot be automatically determined.  This code is only for linking preprints in biorxiv and medrxiv to litcovid. Note that it currently does not accommodate preprint rxivs outside of biorxiv and medrxiv as the parsers for those preprints have yet to be written.

**Assumptions**
In order to minimize manual review, the threshholds have been set pretty high so precision is expected to be high, but sensitivity is expected to be low. An initial run was already performed and all the relevant data was already saved.  This data is included in the repo as detailed below

**Code documentation**
Please refer to the jupyter notebook for more commented code

**File structure**
Previous results are 'cached' (ie-saved and updated), so that recalculations are not required, and time isn't wasted re-running
Files may be named by type of meta compared (either 'text' or 'auth' (author)), and source (either 'litcovid' or 'preprint')

**file paths**:
* 'results/archives/' - stores precomputed files from previous runs and lists of identifiers in previous runs
* 'temp/' - temporarily stores the type-specific successful matches in a run
* 'to review/' - stores the results of the matching that require manual review
* 'update dumps/' - stores the dataframe of updates to make based on sorted matches in this run

**Pre-existing files**
* 'results/archives/all_`source`_ids.txt' - a pickled list of identifiers that has already been run (where `source` is either litcovid or preprints
* 'results/archives/`compare_type`_`source`_set.txt' - a pickled pandas dataframe containing preprocessed text for comparison. The `source` is again either litcovid or preprints, while the `compare_type` is either auth (author), or text (title and abstract)
* 'temp/`compare_type`_above_threshold.txt - a tab-delimited text file containing all matches based on the `compare_type` (either auth or text) where the similarity was found to be above the minimum threshhold. These files are merged to identify match candidates
* 'results/to review/low_scores.txt' - a tab-delimited pandas dump for matches where the sum score was below the threshhold for acceptance
* 'results/to review/manual_check.txt' - a tab-delimited pandas dump for matches where a litcovid item matched with more than one preprint or vice versa
* 'results/archives/clean_results.txt' - a tab-delimited pandas dump for matches which do not need further screening. This file is processed for creating the update dump
* 'results/update dumps/update_file.txt' - a tab-delimited pandas dump for matches which do not need further screening and have been formatted with the appropriate fields for importing into outbreak.info resource metadata
* As of May 2021, an additional split export has been included for ease of merging into the database
* Note that some files may be compressed to meet github upload requirements. Uncompress in same directory for script run

### Similarity calculations
This script currently uses a basic bag of words comparison and calculated jaccard similarity index. 
Based on a test run, from when litcovid had only 30k entries and there were only slightly less than 7K preprints, text similarities >0.2 and author similarities >0.45 make a reasonable cutoff. The author and text metafields were compared individually as this would allow for the identification and use of a more tailored threshold. 

Although there were initial plans to check other comparison methods (TF-IDF with cosine similarity), these plans were dropped as this method seems sufficient for the given task and using more complicated methods may extend the runtime.


