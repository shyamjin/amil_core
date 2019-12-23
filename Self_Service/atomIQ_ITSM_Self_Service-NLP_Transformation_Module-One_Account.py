
# coding: utf-8

# # atomIQ Ticketing Self Service - NLP Transformation Module

# **NOTE - MULTIPROCESSING WORKS ONLY ON LINUX ENVIROMENT, THIS CODE WILL FREEZE ON WINDOWS**
# 
# Implements one transformation pickle

# In[ ]:

#basic packages - found in the Anaconda release
import pandas as pd
from glob import glob
import numpy as np
import itertools
from sklearn.externals import joblib
import logging
from time import time, strftime
import re
from scipy.sparse import vstack, hstack
import json
import multiprocessing as mp
import pickle
import sys
from shutil import copyfile
import os
import json
import traceback


# # Global Variables

# In[ ]:

#UAT=True #UAT indicator, Assign to False when deploying in prod

#Identification of running enviroment
import socket
server=socket.gethostname()
UAT=True
if 'prd3' in server:
    UAT=False


# # Global Variables
DEFAULT_LOGS_DIRNAME = "Logs"
SS_LOG_FILENAME="self_service.log"

# Load & validate required environment variables
AMILY_SS_HOME     = os.environ.setdefault("AMILY_SS_HOME","")                           # This is a full path
AMILY_SS_LOGS_DIR = os.environ.setdefault("AMILY_SS_LOGS_DIR",AMILY_SS_HOME+"/Logs")    # This is a full path (in case you want logs on a different file system)

init_errors = 0     # count the number of errors we get during initialization

if len(AMILY_SS_HOME) == 0:
    print('FATAL: Environment variable "AMILY_SS_HOME" is not set')
    init_errors += 1

if len(AMILY_SS_LOGS_DIR) == 0:
    AMILY_SS_LOGS_DIR = AMILY_SS_HOME + "/" + DEFAULT_LOGS_DIRNAME
    print('INFO: Environment variable "AMILY_SS_LOGS_DIR" is not set. Will default to [' + AMILY_SS_LOGS_DIR + ']')

if init_errors > 0:
    sys.exit(1)



TEST_ENVIROMENT=True if sys.argv[1]=='-f' else False #Unit Test indicator


# In[ ]:

#Endpoints for AO integration - Load from configuration file
with open(AMILY_SS_HOME+'/Features/Configurations/ao_endpoints.json') as json_data:
    endpoints = json.load(json_data)


# # Log Configuration

# In[ ]:

logging.basicConfig(filename=AMILY_SS_LOGS_DIR + "/" + SS_LOG_FILENAME,
                    format='%(asctime)s.%(msecs)03d %(levelname)s %(message)s', 
                    datefmt='%Y-%m-%d,%H:%M:%S',
                    level=logging.DEBUG
                   )
logging.getLogger("requests").setLevel(logging.CRITICAL)

# # Logs traceback lines on the current code frame + the actual error message
def current_frame_traceback(tb):
    cur_file_name=__file__
    tb_re="".join(["\"",cur_file_name.replace("/","\/"),".+\n.+","|(Error.+)"])
    tb_pattern=re.compile(tb_re)
    index = 1
    for p in tb_pattern.finditer(tb):
        logging.error(" Traceback line %d: %s"%(index,p.group().replace('\n','  ->')))
        index+=1

# In[ ]:

import requests
def send_result_request(status, company='Unknown', request_id=0):
    if TEST_ENVIROMENT:
        return
    
    comapny_name=company.replace("_"," ")
    
    #Login request
    #if UAT:
    #    url = 'https://gssuts-uat-ao2:48443/baocdp/rest/login'
    #else:
    #    url = 'https://gssuts-ao2:28443/baocdp/rest/login'
    url=endpoints[server]['login']
    headers = {'Content-Type' : 'application/json'}
    body=str('{"username":"Amily",\n"password":"12345678"}')
    login_request = requests.post(url
                                  ,data=body
                                  ,headers=headers
                                  ,verify = False
                                 )
    try:
        token=login_request.headers['Authentication-Token']
    except:
        logging.error('Failed to fetch AO Token for REST Service')
        return

    
    #if UAT:
    #    url = 'https://gssuts-uat-ao2:48443/baocdp/rest/process/:Amdocs_Amily_Integration_Interface:Self_Service_Amily_To_UTS/execute?mode=sync'
    #else:
    #    url = 'https://gssuts-ao2:28443/baocdp/rest/process/:Amdocs_Amily_Integration_Interface:Self_Service_Amily_To_UTS/execute?mode=sync'
    url=endpoints[server]['ack']
    headers = {'Content-Type' : 'application/json' ,'Authentication-Token': token}
            
    #Status update request
    fp1=r"""{"inputParameters":[{"name":"Inputs","value":"{'Ack': [{'Field': [{'Status': '"""
    fp2=r"""'},{'StatusDescription': 'Operation successful'},{'Company': '"""
    fp3=r"""'},{'RequestID': '"""
    fp4=r"""'}]}]}"}]}"""
    ack_dict="".join([fp1,str(status), fp2, str(comapny_name),fp3,str(request_id),fp4])
    result_request = requests.post(url 
                                   ,data=ack_dict
                                   ,headers=headers
                                   ,verify = False
                                  )
    #print(file_paths_dict)
    if result_request.status_code!=200:
        logging.error('Failed in sending status to AO for NLP Transformation')
    else:
        logging.info('Acknowledgement Reply from UTS for NLP Transformation - >'+result_request.text)
        
    
    #Logout request
    #if UAT:
    #    url = 'https://gssuts-uat-ao2:48443/baocdp/rest/logout'
    #else:
    #    url = 'https://gssuts-ao2:28443/baocdp/rest/logout'
    url=endpoints[server]['logout']
    headers = {'Content-Type' : 'application/json','Authentication-Token': token}
    logout_request = requests.post(url
                                   ,headers=headers
                                   ,verify = False
                                  )
    if logout_request.status_code!=200:
        logging.error('Failed logging out from AO')
        return
    else:
        logging.info('Successfully logged out from AO')
    
    return


# # Data Read

# In[ ]:

# DB read
def read_corpus(path, cols):
    
    full_df = pd.read_csv(path, delimiter='\t', encoding="utf8")
    
    #Set column names to predefined values
    column_dict = {}
    column_dict[cols['ticket_id']]='ticket_id'
    for idx, textual_field in enumerate(cols['textual_fields']):
        col_name=str("_".join(['textual_field',str(idx+1)]))
        column_dict[textual_field]=col_name
    for idx, filter_field in enumerate(cols['filter_fields']):
        col_name=str("_".join(['filter_field',str(idx+1)]))
        column_dict[filter_field]=col_name
    #column_dict[cols['company_field']]='company'
    
    #print('size ->',full_df.shape)
    #print(column_dict)
    full_df.rename(columns=column_dict,inplace=True)
        
    #Drop NA only after filters were done and only for the relevant columns
    column_list=[]
    for key, value in column_dict.items():
        column_list.append(value)
    full_df=full_df[column_list]
    
    #full_df.dropna(inplace=True, subset=column_list)
    for idx, textual_field in enumerate(cols['textual_fields']):
        col_name=str("_".join(['textual_field',str(idx+1)]))
        full_df[col_name]=full_df[col_name].fillna(" ")
    
    full_df = full_df.drop_duplicates(subset=['ticket_id']).sort_values(by=['ticket_id']).reset_index(drop=True) 
    #print(full_df.info())
    
    return full_df


# In[ ]:

#INPUT PARAMETERS - FILE WILL BE RECEIVED FROM ITSM
if TEST_ENVIROMENT:
    infile_name = "./Unit-test/Data/Deploy Test--007.txt"
else:
    infile_name = str(sys.argv[1])


# In[ ]:

#Archive files - copy to Archive Directory and remove from orignal directory
def archive_infile(infile_name):
    try:
        file_name=infile_name[infile_name.rfind('/')+1:]
        copyfile(infile_name, AMILY_SS_HOME+"/Archive/Transformations/"+file_name)
        os.remove(infile_name)
        logging.info('Transformation file was moved to Archive folder')
    except:
        logging.warning('Transformation file was not moved successfully to Archive folder')
        tb = traceback.format_exc()
        current_frame_traceback(tb)


# # Text Preprocessing

# In[ ]:

import pandas as pd
from glob import glob
import numpy as np
import itertools
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.pipeline import Pipeline, FeatureUnion
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer

import string

from nltk.corpus import stopwords as sw
from nltk.corpus import wordnet as wn
from nltk import wordpunct_tokenize
from nltk import WordNetLemmatizer
from nltk import sent_tokenize
from nltk import pos_tag

''' Workaround for the pos_tag error in NLTK 3.2 '''
from nltk.tag import PerceptronTagger
from nltk.data import find
PICKLE = "averaged_perceptron_tagger.pickle"
AP_MODEL_LOC = 'file:'+str(find('taggers/averaged_perceptron_tagger/'+PICKLE))
tagger = PerceptronTagger(load=False)
tagger.load(AP_MODEL_LOC)
pos_tag = tagger.tag

from sklearn.base import BaseEstimator, TransformerMixin


# In[ ]:

class NLTKPreprocessor(BaseEstimator, TransformerMixin):

    def __init__(self, stopwords=None, punct=None,
                 lower=True, strip=True):
        self.count=0
        self.lower      = lower
        self.strip      = strip
        self.stopwords  = stopwords or set(sw.words('english'))
        self.punct      = punct or set(string.punctuation)
        self.lemmatizer = WordNetLemmatizer()
        self.start_pat=re.compile(r"base64,")
        self.end_pat=re.compile(r"&gt;")

    def fit(self, X, y=None):
        return self

    def inverse_transform(self, X):
        return [" ".join(doc) for doc in X]

    def transform(self, X):
        workers = mp.Pool()
        return workers.map(self.transform_doc,X)
    
    def transform_doc(self, doc):
        return list(self.tokenize(doc))

    def tokenize(self, document):
        self.count+=1 
        
        #print(self.count)
        cleaned=self.zap_base64(document)
        #print("length of cleaned is %d"%(len(cleaned)))
        # Break the document into sentences
        for sent in sent_tokenize(cleaned):
            # Break the sentence into part of speech tagged tokens
            #sent=sent.replace('*', ' ')
            for token, tag in pos_tag(wordpunct_tokenize(sent)):
                # Apply preprocessing to the token
                token = token.lower() if self.lower else token
                token = token.strip() if self.strip else token
                token = token.strip('_') if self.strip else token
                token = token.strip('*') if self.strip else token

                # If stopword, ignore token and continue
                if token in self.stopwords:
                    continue

                # If punctuation, ignore token and continue
                if all(char in self.punct for char in token):
                    continue
                
                # Transform all numbers to generic _NUMBER token
                if token.isdigit():
                    token = "_NUMBER"

                # Lemmatize the token and yield
                lemma = self.lemmatize(token, tag)
                #lemma = token
                yield lemma

    def lemmatize(self, token, tag):
        tag = {
            'N': wn.NOUN,
            'V': wn.VERB,
            'R': wn.ADV,
            'J': wn.ADJ
        }.get(tag[0], wn.NOUN)

        return self.lemmatizer.lemmatize(token, tag)
    
    def zap_base64(self, s):
        #find start and end labels
        start_matches=[m.start() for m in re.finditer(self.start_pat, s)]
        if not start_matches:
            return s
        #print("=====")
        end_matches=[m.start() for m in re.finditer(self.end_pat, s)]
        if len(end_matches)!=len(start_matches): #In case where the end char of the base64 encoding is not found
            return s[:start_matches[0]]
        try:
            end_matches_ser=pd.Series(end_matches)
            pair_list=[]
            for st in start_matches:
                end_loc=end_matches_ser.searchsorted(st)[0]
                pair_list.append((st, end_matches_ser.loc[end_loc]))
            #print(pair_list)
            start_list=[0]
            end_list=[]
            for st, en in pair_list:
                start_list.append(en+4)
                end_list.append(st)
            l=len(s)
            end_list.append(l)
            #for sp, ep in zip(start_list, end_list):
                #print(sp, ep)
            res=' '.join(s[sp:ep] for sp, ep in zip(start_list, end_list))
        except:
            logging.error("Base64 removal error")
            tb = traceback.format_exc()
            current_frame_traceback(tb)
            return s
        return res


# In[ ]:

def identity(arg):
    """
    Simple identity function works as a passthrough.
    """
    return arg
    
class ItemSelector(BaseEstimator, TransformerMixin):
    def __init__(self, key):
        self.key = key

    def fit(self, x, y=None):
        return self

    def transform(self, data_dict):
        return data_dict[self.key]


# # Feature Transformation

# In[ ]:

#Pipeline for preproccesing of the text - tokenization, lemmatziation and vectorization
def vectorizer_fit_transform(X):
    transformed_textual_lengths = {}
    
    transformer_list=[]
    transformer_weights={}
    
    for i in range(len(cols['textual_fields'])):
        field_name="_".join(['textual_field',str(i+1)])
        
        textual_field_transformer = Pipeline([
                ('selector', ItemSelector(key=field_name)),
                ('preprocessor', NLTKPreprocessor()),
                ('vectorizer', TfidfVectorizer(
                tokenizer=identity, preprocessor=None, 
                lowercase=False, ngram_range=(1,2)
                )),
            ])
        transformer_list.append((field_name,textual_field_transformer))
        transformer_weights[field_name]=1
        
        
    transformer=Pipeline([
        ('union', FeatureUnion(transformer_list=transformer_list, transformer_weights=transformer_weights)
        )])
    train_feat=transformer.fit_transform(X)
    
    #Calculate textual fields features lengths
    for t in transformer.named_steps['union'].transformer_list:
        transformed_textual_lengths[t[0]]=len(t[1].named_steps['vectorizer'].get_feature_names())
        
    #return textual_field_transformers, transformed_textual_lengths, train_feat
    return transformer, transformed_textual_lengths, train_feat


# # Transform Features for Account

# In[ ]:

#INPUT PARAMETERS - DEFAULT PARAMETERS FOR UTS

ticket_id_field = "Incident Number"
textual_fields=["Description","Detailed Decription"]
#filter_fields=["z1D TicketTypeExternal?"]
filter_fields=["Origin Type"]

filter_dict={filter_fields[0]:"Origin Type"} #A UTS configuration, as the name of the field may be different between the NLP transformation file and the file received by the user


# In[ ]:

# Read Data
cols = {"ticket_id":ticket_id_field
       ,"textual_fields":textual_fields
       ,"filter_fields":filter_fields
        #,"company_field":company_field
       }
try:
    file_name = infile_name[infile_name.rfind("/")+1:]
    company = file_name[:file_name.find("-")].replace(" ","_")
    request_id = file_name[file_name.find("-")+2:file_name.rfind(".")]
    transformation_df = read_corpus(infile_name,cols)
    if not TEST_ENVIROMENT:
        logging.info('-----------------NLP TRANSFORMATION SESSION FOR ACCOUNT %s HAS STARTED-----------------'%company)
    else:
        print(transformation_df.head())
    send_result_request(status="InProgress", company=company, request_id=request_id)
except:
    logging.error('Unable to load file %s for NLP Transformation'%infile_name)
    tb = traceback.format_exc()
    current_frame_traceback(tb)
    try:
        send_result_request(status="Failure", company=company, request_id=request_id)
    except:
        send_result_request(status="Failure")
    #if not TEST_ENVIROMENT: archive_infile(infile_name)
    exit()


# In[ ]:

#Specific implementation for the current UTS-driven Amily web service
def align_pickle_to_uts(transformer):
    textual_fields_in_web_service=["summary","description"]
    for i, t in enumerate(transformer.named_steps['union'].transformer_list):
        t[1].named_steps['selector'].key=textual_fields_in_web_service[i]
    transformer.named_steps['union'].transformer_weights={'summary':1,'description':1}
    return transformer


# In[ ]:

#Generate NLP features for filter field value
try:
    for i in range(len(filter_fields)):
        filter_field="_".join(["filter_field",str(i+1)])
        for filter_value in transformation_df[filter_field].unique().tolist():
            start_time=time()
            train_df=transformation_df.loc[transformation_df[filter_field]==filter_value]

            verbose=True if TEST_ENVIROMENT else False
            if verbose: print("fitting and transforming records for %s-%s"%(str(filter_dict[filter_fields[i]]),filter_value))
                
            textual_field_transformer, transformed_textual_lengths, train_feat = vectorizer_fit_transform(train_df)
            message = str("Finished transforming %d tickets of %s with %s-%s in %1.2f [min.]"%(train_df.shape[0],company,str(filter_dict[filter_fields[i]]),filter_value,(time()-start_time)/60))
            if not TEST_ENVIROMENT:
                logging.info(message)
            else:
                print(message)

            #Save compressed feature array to disk
            file_prefix = "_".join([company.replace(" ","_"),str(filter_dict[filter_fields[i]])+'-'+str(filter_value)]) 
            output_file_name=".".join([file_prefix,'npz'])
            np.savez_compressed(AMILY_SS_HOME+'/Features/'+output_file_name, train_feat)

            #Save transformed textual field limits and ticket ids to disk - configuration file
            account_dict={"text_limits":transformed_textual_lengths, "ticket_ids":train_df['ticket_id'].tolist()}
            output_file_name=".".join([file_prefix,'json'])
            with open(AMILY_SS_HOME+'/Features/'+output_file_name, 'w') as outfile:
                json.dump(account_dict, outfile)
            
            #Save NLP Transformarion Pickle
            textual_field_transformer=align_pickle_to_uts(textual_field_transformer) #SPECIFIC UTS IMPLEMENTATION
            
            filter_value_dict={1:"ext",0:"int"}
            filter_value_for_file_name=filter_value_dict[filter_value]
            Text_Preprocessor_file_name = "".join([company,'_',filter_value_for_file_name,
                                                   '_NLP_Preprocessor.pkl'])
            
            with open(AMILY_SS_HOME+'/Generated_Pickles/'+Text_Preprocessor_file_name, 'wb') as NLP_pkl:
                pickle.dump(textual_field_transformer, NLP_pkl)
            
    send_result_request(status="Success", company=company, request_id=request_id)
except:
    send_result_request(status="Failure", company=company, request_id=request_id)
    logging.error('Could not complete NLP transformation process for %s'%company)
    tb = traceback.format_exc()
    current_frame_traceback(tb)


# In[ ]:

try:
    #if not TEST_ENVIROMENT: archive_infile(infile_name)
    logging.info('-----------------SUCCESSFULLY FINIHED NLP TRANSFORMATION PROCESS FOR %s-----------------'%company)
except:
    pass

