
# coding: utf-8

# # atomIQ Ticketing Self Service - Classification Module

# In[ ]:

#basic packages - found in the Anaconda release
import pandas as pd
from glob import glob
import numpy as np
import itertools
from sklearn.externals import joblib
import logging
import logging.config
from time import time, gmtime, strftime
import re
from scipy.sparse import vstack, hstack
import json
import sys
from PIL import Image
import os
from shutil import copyfile
import json
import pickle
import traceback


# In[ ]:

#matplotlib imports

#%matplotlib notebook 
#Magic command to view plots in Jupyter notebooks. sidable when running as the application

import matplotlib
matplotlib.use('Agg') #Configures matplotlib for the application server and does not look for a GUI
import matplotlib.pyplot as plt
from matplotlib import colors


# # Global Variables

DEFAULT_LOGS_DIRNAME = "Logs"
SS_LOG_FILENAME="self_service.log"
MINIMUM_LABELS_PER_FLOW = int(os.environ.setdefault("MINIMUM_LABELS_PER_FLOW","10"))

# Load & validate required environment variables
AMILY_SS_HOME     = os.environ.setdefault("AMILY_SS_HOME","")                           # This is a full path
AMILY_SS_LOGS_DIR = os.environ.setdefault("AMILY_SS_LOGS_DIR",AMILY_SS_HOME+"/Logs")    # This is a full path (in case you want logs on a different file system)
AMILY_FLOW_TYPES = os.environ.setdefault("AMILY_FLOW_TYPES","automation dispatch functional_category operationl_category").split(" ")

init_errors = 0     # count the number of errors we get during initialization

if len(AMILY_SS_HOME) == 0:
    print('FATAL: Environment variable "AMILY_SS_HOME" is not set')
    init_errors += 1

if len(AMILY_SS_LOGS_DIR) == 0:
    AMILY_SS_LOGS_DIR = AMILY_SS_HOME + "/" + DEFAULT_LOGS_DIRNAME
    print('INFO: Environment variable "AMILY_SS_LOGS_DIR" is not set. Will default to [' + AMILY_SS_LOGS_DIR + ']')

if init_errors > 0:
    sys.exit(1)


Output_Path="/UTSAmilyAttachments/AMILY_TO_UTS/"
ERROR_MSG_FOR_USER = "An error has occured while training data on atomIQ ticketing, the operation has been aborted"
LABELS_ONLY=True #True if only label data is provided by UTS, and not textual fields


# # Log Configurations

# In[ ]:

#Configure Self Service Log
logging.basicConfig(filename=AMILY_SS_LOGS_DIR + "/" + SS_LOG_FILENAME,
                    format='%(asctime)s.%(msecs)03d %(levelname)s %(message)s', 
                    datefmt='%Y-%m-%d,%H:%M:%S',
                    level=logging.DEBUG
                   )

#Disable DEBUG loggings from PIL library
logging.getLogger("PIL").setLevel(logging.WARNING)
logging.getLogger("requests").setLevel(logging.CRITICAL)


# # Working Enviroment Variables

# In[ ]:

#Identification of running enviroment - UAT or Prod
import socket
server=socket.gethostname()
UAT=True
if 'prd3' in server:
    UAT=False


# In[ ]:

#Unit Test indicator
TEST_ENVIROMENT=True if sys.argv[1]=='-f' else False


# In[ ]:

#Endpoints for AO integration - Load from configuration file
with open(AMILY_SS_HOME+'/Features/Configurations/ao_endpoints.json') as json_data:
    endpoints = json.load(json_data)


# In[ ]:

#Deploy Model Is a parameter passed by the shell script activating the deployment module
try:
    DEPLOY_MODEL=True if sys.argv[2]=="Deploy" else False
except:
    DEPLOY_MODEL=False


# # Logs traceback lines on the current code frame + the actual error message
def current_frame_traceback(tb):
    cur_file_name=__file__
    tb_re="".join(["\"",cur_file_name.replace("/","\/"),".+\n.+","|(Error.+)"])
    tb_pattern=re.compile(tb_re)
    index = 1
    for p in tb_pattern.finditer(tb):
        logging.error(" Traceback line %d: %s"%(index,p.group().replace('\n','  ->')))
        index+=1

# # Amily Reply REST Call to UTS-AO Function

# In[ ]:

import requests
def send_result_request(success, detailed_results_path=None, stats_report_path=None, 
                        error_message=None, company='Unknown', request_id=0, Ack=False):
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
    
    #File paths request
    if not Ack:
        #file_paths_dict = r"""{"inputParameters":[{"name":"Inputs","value":"{'XmlFields': [{'FilePath': '/tmp/test.txt'},{'Operation': 'report'}]}"}]}"""
        fp1=r"""{"inputParameters": [{"name":"Inputs","value":"{'XmlFields': [{'Field': [{'FilePath': '"""
        fp2=r"""'},{'Operation':'report'}]},{'Field': [{'FilePath':'"""
        fp3=r"""'},{'Operation':'stats'}]},{'Field': [{'Status':'"""
        fp4=r"""'},{'StatusDescription':'"""
        fp5=r"""'},{'Company':'"""
        fp6=r"""'},{'RequestID': '"""
        fp7=r"""'}]}]}"}]}"""

        if not error_message:
            error_message="Operation successful"
        status="Success" if success else "Failure"

        file_paths_dict=''.join([fp1,str(detailed_results_path),fp2,str(stats_report_path),fp3,status,fp4,str(error_message),fp5,str(comapny_name),fp6,str(request_id),fp7])
        
        result_request = requests.post(url 
                                       ,data=file_paths_dict
                                       ,headers=headers
                                       ,verify = False
                                      )

        #print(file_paths_dict)
        if result_request.status_code!=200:
            logging.error('Failed in sending file paths to AO')
        else:
            logging.info('Reply from UTS - >'+result_request.text)
            
    #Acknowledgement request
    if Ack:
        fp1=r"""{"inputParameters":[{"name":"Inputs","value":"{'Ack': [{'Field': [{'Status': 'InProgress'},{'StatusDescription': 'Operation successful'},{'Company': '"""
        fp2=r"""'},{'RequestID': '"""
        fp3=r"""'}]}]}"}]}"""
        ack_dict="".join([fp1,str(comapny_name),fp2,str(request_id),fp3])
        result_request = requests.post(url 
                                       ,data=ack_dict
                                       ,headers=headers
                                       ,verify = False
                                      )
        #print(file_paths_dict)
        if result_request.status_code!=200:
            logging.error('Failed in sending acknowledgement to AO')
        else:
            logging.info('Acknowledgement Reply from UTS - >'+result_request.text)
        
    
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
    
    if not Ack: logging.info('File paths sent successfully to UTS')
    #print('\nsuccess :-)')
    
    return


# # Data Read

# In[ ]:

# DB read
def read_corpus(path, cols):
    
    full_df = pd.read_csv(path, delimiter='\t', encoding="utf8")
    label_type = full_df.columns.values.tolist()[-2]
    
    #Set column names to predefined values
    column_dict = {}
    column_dict[cols['ticket_id']]='ticket_id'
    if not LABELS_ONLY:
        for idx, textual_field in enumerate(cols['textual_fields']):
            col_name=str("_".join(['textual_field',str(idx+1)]))
            column_dict[textual_field]=col_name
    for idx, filter_field in enumerate(cols['filter_fields']):
        col_name=str("_".join(['filter_field',str(idx+1)]))
        column_dict[filter_field]=col_name
    column_dict[label_type]='label'
    
    full_df.rename(columns=column_dict,inplace=True)
    
    #Filter filed by filtered values - Unneccesary in Current UTS implementation - The data will already be filtered
    '''
    for idx, filter_field in enumerate(cols['filter_fields']):
        filter_field_column=str("_".join(['filter_field',str(idx+1)]))
        full_df=full_df.loc[full_df[filter_field_column]==cols['filter_values'][idx]]
    '''
    
    #Fill blank labels with value "Other"
    full_df['label']=full_df['label'].fillna("Other")

    #Remove labels for flows with less than minimum required
    try:
        vc = full_df['label'].value_counts()
        removed_labels = vc.loc[vc < MINIMUM_LABELS_PER_FLOW].index.tolist()
        full_df.loc[full_df['label'].isin(removed_labels), 'label'] = 'Other'
        if removed_labels:
            logging.info('Removed labels with less than %d occurrences - %s'%(MINIMUM_LABELS_PER_FLOW, removed_labels))
    except:
        logging.error('Unable to remove labels with less than minimum required')
        tb = traceback.format_exc()
        current_frame_traceback(tb)
        
    #Drop NA only after filters were done and only for the relevant columns
    column_list=[]
    for key, value in column_dict.items():
        column_list.append(value)
    #full_df.dropna(inplace=True, subset=column_list)
    full_df = full_df.drop_duplicates(subset=['ticket_id']).sort_values(by=['ticket_id']).reset_index(drop=True) 
    #print(full_df.info())
    
    return full_df, label_type
    #Return a shuffled-row-order data frame as a preperation for the cross validation
    #return full_df.sample(frac=1)


# In[ ]:

#Archive files - copy to Archive Directory and remove from orignal directory
def archive_infile(infile_name):
    try:
        file_name=infile_name[infile_name.rfind('/')+1:]
        copyfile(infile_name, AMILY_SS_HOME+"/Archive/"+file_name)
        os.remove(infile_name)
        logging.info('Training file was moved to Archive folder')
    except:
        logging.warning('Training file was not moved successfully to Archive folder')
        tb = traceback.format_exc()
        current_frame_traceback(tb)


# In[ ]:

#INPUT PARAMETERS - FILE WILL BE RECEIVED FROM ITSM
try:
    if TEST_ENVIROMENT:
        infile_name = AMILY_SS_HOME+"/Unit-test/Data/Globe Telecom--000000000004006.txt" #Internal use only - testing purposes
    else:
        infile_name = str(sys.argv[1])
    QUICK_TRAINING=True
    if infile_name.find('Full')>0:
        QUICK_TRAINING=False

    logging.info('-----------------%s TRAINING SESSION HAS STARTED-----------------'%('QUICK' if QUICK_TRAINING else 'FULL'))
    logging.info("File was loaded for classification: "+infile_name)
except:
    logging.error("Could not open file. OPERATION ABORTED")
    tb = traceback.format_exc()
    current_frame_traceback(tb)
    send_result_request(success=False, error_message='atomIQ ticketing could not read the file sent by UTS. Operation Aborted')
    if not TEST_ENVIROMENT: archive_infile(infile_name)
    exit()


# In[ ]:

#INPUT PARAMETERS - DEFAULT PARAMETERS FOR UTS
account_name=infile_name[infile_name.rfind('/')+1:infile_name.rfind("--")]
request_id=infile_name[infile_name.rfind("--")+2:infile_name.rfind(".")]
ticket_id_field = "Incident Number"
textual_fields=["DESCRIPTION","DETAILED_DECRIPTION"]
filter_fields=["Origin Type"]
#filter_values=["Yes"]
#label_field = "Label"
generate_pickles=False


# In[ ]:

# Read Data
if LABELS_ONLY:
    cols = {"ticket_id":ticket_id_field
           ,"filter_fields":filter_fields
           #,"filter_values":filter_values
           #,"label_field":label_field
           }
else:
    cols = {"ticket_id":ticket_id_field
           ,"textual_fields":textual_fields
           ,"filter_fields":filter_fields
           #,"filter_values":filter_values
           #,"label_field":label_field
           }

try:
    train_df, label_type = read_corpus(infile_name,cols)
    
    filter_values=[train_df["filter_field_1"].unique()[0]] #Is External Yes or No - A very UTS-specific implementation
    train_df=train_df.loc[train_df["filter_field_1"]==filter_values[0]].reset_index(drop=True) #Make sure using only one filter value field
    
    send_result_request(success=True, company=account_name, request_id=request_id, Ack=True)
    logging.info("Data for training - %s type, %s account, %d unique tickets, Is_External=%s"%(label_type,account_name,train_df.shape[0],filter_values[0]))
    if train_df["filter_field_1"].unique().shape[0]>1:
        logging.warning('More than 1 filter field values')
except:
    logging.error("Unable to load file. OPERATION ABORTED")
    tb = traceback.format_exc()
    current_frame_traceback(tb)
    send_result_request(success=False, error_message=ERROR_MSG_FOR_USER, company=account_name, request_id=request_id)
    if not TEST_ENVIROMENT: archive_infile(infile_name)
    exit()


# # Text Preprocessing - Load From File

# Load Sparse Matrix from disk

# In[ ]:

try:
    file_prefix = "_".join([account_name.replace(" ","_"),str(filter_fields[0])+'-'+str(filter_values[0])]) 
    file_name=".".join([file_prefix,'npz'])

    #A workaround for the following command as scipy save_npz does not work on scipy 0.18.1 version -> train_feat_loaded = load_npz('./Features/'+file_name)
    loaded_npz = np.load(AMILY_SS_HOME+'/Features/'+file_name)
    train_feat_loaded = loaded_npz[loaded_npz.keys()[0]].item()
    del(loaded_npz)
    logging.info('%s was succesfully uploaded from disk'%file_name)
except:
    logging.error('%s failed to load from disk. OPERATION ABORTED'%file_name)
    tb = traceback.format_exc()
    current_frame_traceback(tb)
    send_result_request(success=False, error_message=ERROR_MSG_FOR_USER, company=account_name, request_id=request_id)
    if not TEST_ENVIROMENT: archive_infile(infile_name)
    exit()


# Load Account Configuration file containing mapping of ticket IDs and textual fields feature lengths

# In[ ]:

try:
    file_prefix = "_".join([account_name.replace(" ","_"),str(filter_fields[0])+'-'+str(filter_values[0])]) 
    file_name=".".join([file_prefix,'json'])
    account_dict = json.load(open(AMILY_SS_HOME+'/Features/'+file_name))
    transformed_textual_lengths_loaded=account_dict['text_limits']
    transformed_ticket_ids=account_dict['ticket_ids']
    logging.info('%s textual configuration file succesfully uploaded from disk'%account_name)
except:
    logging.error('%s textual configuration file failed to load from disk. OPERATION ABORTED'%account_name)
    tb = traceback.format_exc()
    current_frame_traceback(tb)
    send_result_request(success=False, error_message=ERROR_MSG_FOR_USER, company=account_name, request_id=request_id)
    if not TEST_ENVIROMENT: archive_infile(infile_name)
    exit()


# Merge Loaded Data to existing tickets for training

# In[ ]:

#The assumption is that both data sources - transformed features and train data from user - are SORTED by ticket ID
#This is enforced by the algorithm
try:
    transformed_ticket_ids_df=pd.DataFrame(transformed_ticket_ids, columns=['ticket_id_trans'])
    train_ticket_ids_df=pd.DataFrame(train_df['ticket_id'].tolist(), columns=['ticket_id_train'])
    #Left join all tickets ids that are transformed with all ticket ids received by the user
    comparison_df=pd.merge(transformed_ticket_ids_df, train_ticket_ids_df, how='left', 
                           left_on=['ticket_id_trans'],right_on=['ticket_id_train'])

    missing_tickets = train_df['ticket_id'].shape[0]- comparison_df['ticket_id_train'].count()
    #print('Number of tickets in train set with transformations found - ',comparison_df['ticket_id_train'].count())
    if missing_tickets>0:
        logging.info('Number of tickets in train set with features transformations not found - %d'%missing_tickets)
        #Extract a list of tickets passed by the user and were not found in feature trnasformation matrix
        missing_df = pd.merge(train_ticket_ids_df, comparison_df, how='left', 
        left_on=['ticket_id_train'],right_on=['ticket_id_train'])
        removed_tickets_from_train=missing_df.loc[missing_df['ticket_id_trans'].isnull()][['ticket_id_train']]['ticket_id_train'].tolist()
        #print(removed_tickets_from_train) #for debugging purposes
        #Remove unfound tickets from training data frame
        train_df=train_df[~train_df['ticket_id'].isin(removed_tickets_from_train)].reset_index(drop=True)

    indices = np.where(comparison_df['ticket_id_trans']==comparison_df['ticket_id_train'])[0]
    train_feat_trans = train_feat_loaded[indices,:]
    logging.info('Merge of loaded textual features and data in file completed succesfully')
except:
    logging.error('Merge of loaded textual features and data in file failed. OPERATION ABORTED')
    tb = traceback.format_exc()
    current_frame_traceback(tb)
    send_result_request(success=False, error_message=ERROR_MSG_FOR_USER, company=account_name, request_id=request_id)
    if not TEST_ENVIROMENT: archive_infile(infile_name)
    exit()


# # Shuffle Data as a Prep. for Cross Validation

# In[ ]:

try:
    index = np.arange(np.shape(train_feat_trans)[0])
    np.random.shuffle(index)
    train_feat_trans_shuffled=train_feat_trans[index, :] #Features Shuffled
    label_series=train_df.label[index] #Labels Shuffled
except:
    logging.error('shuffling of train data as a prep. for CV has failed. OPERATION ABORTED')
    tb = traceback.format_exc()
    current_frame_traceback(tb)
    send_result_request(success=False, error_message=ERROR_MSG_FOR_USER, company=account_name, request_id=request_id)
    if not TEST_ENVIROMENT: archive_infile(infile_name)
    exit()


# # Textual fields Feature Weightings

# In[ ]:

#A transformer which assigns weights to textual fields features

from sklearn.base import BaseEstimator, TransformerMixin
class FeatureWeighting(BaseEstimator, TransformerMixin):
    def __init__(self,  transformer_weights,transformed_textual_lengths):
        self.transformer_weights = transformer_weights
        self.transformed_textual_lengths = transformed_textual_lengths

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        start=0
        end=0
        for i in range(len(self.transformer_weights)):
            field_name="_".join(['textual_field',str(i+1)])
            start=end
            end=end+self.transformed_textual_lengths[field_name]
            added_matrix=X[:,start:end]*self.transformer_weights[field_name]
            if i==0:
                #print(start,end)
                train_feat_stacked = added_matrix
            else:
                #print(start,end)
                train_feat_stacked =hstack([train_feat_stacked, added_matrix] ,format='csr')
                return train_feat_stacked


# # Flow Classifier

# In[ ]:

# Classifier Pipeline
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder
from sklearn.linear_model import SGDClassifier
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.svm import SVC
from sklearn.metrics import classification_report as clsr
from sklearn.metrics import confusion_matrix
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cross_validation import train_test_split as tts
from sklearn.feature_selection import SelectPercentile, chi2, f_classif
from sklearn.model_selection import GridSearchCV
from sklearn.model_selection import train_test_split as tts
#from tqdm import tqdm

def build_classification_model(X_train, y_train, transformed_textual_lengths, 
                               CV=True,
                               Full_model=False, #True if all instances should be trained, regardless of cross validation
                               Quick_training=False, #True if quick training should be applied - default parameters
                               outpath=None, 
                               verbose=False, 
                               inner_CV=False #CV when training the CV folds
                              ):

    def default_account_parameter_values():
    #Load default parameters for account and filter values for quick training
        found = False
        file_name = "default_classification_parameters.json" 
        param_dicts = json.load(open(AMILY_SS_HOME+'/Features/Configurations/'+file_name))
        filter_value_dict={1:"ext",0:"int"}
        for param_dict in param_dicts:
            if param_dict['account']==account_name.replace(" ","_"):
                param_dict_filter="_".join(["default_parameters",filter_value_dict[filter_values[0]]])
                param_dict_default=param_dict[param_dict_filter]
                found = True
                break
        return param_dict_default, found

    def build(classification_model, X, y=None, param_dict_default=None):
        """
        Inner build function that builds a single model.
        """
        
        #Define a modelling pipeline with SelectPercentile as feature selector
        w_dict = {"textual_field_1":0.5,"textual_field_2":0.5}
        classifier = Pipeline([("union", FeatureWeighting(transformer_weights=w_dict,
                                                          transformed_textual_lengths=transformed_textual_lengths)),
                               ("selector", SelectPercentile(score_func=chi2))])
        percentile_range = [20]
        textual_weights_range=[
                              #{"textual_field_1":0,"textual_field_2":1},
                              {"textual_field_1":0.25,"textual_field_2":0.75}
                              ,{"textual_field_1":0.5,"textual_field_2":0.5}
                              ,{"textual_field_1":0.75,"textual_field_2":0.25}
                              #,{"textual_field_1":1,"textual_field_2":0}
                            ]
        param_dict = {'selector__percentile': percentile_range
                     ,'union__transformer_weights': textual_weights_range
                     }
        
        #print(classifier.get_params().keys())
        
        #Model Option 1 - Random Forest
        if classification_model == "rf":
            classifier.steps.append(["randforest", RandomForestClassifier(class_weight="balanced",n_jobs=-1)])
            param_range=[100,200,500]
            #param_range=[200]
            param_dict['randforest__n_estimators']=param_range
            if Quick_training:
                param_dict=param_dict_default
            model = GridSearchCV(estimator = classifier, param_grid=[param_dict], n_jobs=1,verbose=0)
        
        #Model Option 2 - SVM
        '''
        if classification_model == "svm":
            classifier.steps.append(["svm", SVC(probability=True, random_state=1)])
            #print(classifier.get_params().keys())
            param_range = [0.0001, 0.001, 0.01, 0.01, 1.0, 10.0, 100.0, 1000.0]
            param_grid = [{'selector__percentile': percentile_range,'svm__C': param_range,'svm__kernel':['linear']}
                          ,
                         {'selector__percentile': percentile_range,'svm__C': param_range,'svm__gamma': param_range,'svm__kernel':['rbf']}
                         ]
            model = GridSearchCV(estimator = classifier, param_grid=param_grid, n_jobs=-1, verbose=0)
        '''
        
        #number of CV folds within outer folds
        if inner_CV:
            model.cv = 5
        else:
            model.cv = [(slice(None),slice(None))]
        
        model.fit(X, y)
        return model

    cross_validation = 5
    test_results=[]
    labels = LabelEncoder().fit(y_train)
    num_classes=len(labels.classes_.tolist())
    
    if Quick_training:
        param_dict_default, found_default_for_account=default_account_parameter_values()
        if not found_default_for_account:
            logging.error("Could not find default training parameters for account %s. OPERATION ABORTED"%account_name)
            exit()
    else:
        param_dict_default=None
    
    if CV:
        step = train_df.shape[0]//cross_validation
        last_step_addition = train_df.shape[0]%cross_validation
        prob_df_success = True
        for i in range(cross_validation):
            X_test_cv={}
            X_train_cv={}
        
            #Split train and test uniformly so all tickets would be a part of a test set and evaluated. Data was was already shuffled
            if i == (cross_validation-1):
                X_test_cv=X_train[i*step:((i+1)*step+last_step_addition)]
                X_train_cv=X_train[:i*step]
                y_test_cv=y_train[i*step:((i+1)*step+last_step_addition)]
                y_train_cv=y_train[:i*step]   
            else:
                X_test_cv=X_train[i*step:(i+1)*step]
                y_test_cv=y_train[i*step:(i+1)*step]
                if i==0:
                    X_train_cv=X_train[(i+1)*step:]
                    y_train_cv=y_train[(i+1)*step:]
                else:
                    X_train_cv=vstack([X_train[:i*step],X_train[(i+1)*step:]])
                    y_train_cv=y_train.loc[~y_train.index.isin(y_test_cv.index)]
            
                
            #labels = LabelEncoder()
            y_test_cv_encoded = labels.transform(y_test_cv)
            y_train_cv_encoded = labels.transform(y_train_cv)

            if verbose: print("Building for evaluation - Fold %d/%d" %(i+1,cross_validation))

            model = build("rf", X_train_cv, y_train_cv_encoded,param_dict_default)
            model.labels_=labels

            y_pred = model.predict(X_test_cv)
            test_pred_prob = model.predict_proba(X_test_cv)

            #Add to predcited flow (+prob) of test matrix - will be used for the user feedback
            test_results.append(list(zip(y_test_cv.index,labels.inverse_transform(y_pred),np.max(test_pred_prob, axis=1))))
            
            #Add to full probabilities of test matrix - will be used for the thresholds sensitivity analysis
            try:
                if np.unique(y_train_cv_encoded).shape[0]==num_classes:
                    try:
                        #Concatenate if already exists
                        #print(i,'--->',np.unique(y_train_cv_encoded).shape[0])
                        full_test_results_prob=np.vstack([full_test_results_prob,test_pred_prob])
                    except:
                        #Create a new probabilities matrix
                        full_test_results_prob=test_pred_prob
            except:
                prob_df_success = False
            
            if verbose:
                print(model.best_params_)
                
        #Generate the full predicted probabilities dataframe - will be used for the thresholds sensitivity analysis
        if prob_df_success:
            try:
                prob_df = pd.DataFrame(full_test_results_prob,
                                       columns=labels.inverse_transform(np.arange(full_test_results_prob.shape[1])))
                prob_df['label']=y_train.reset_index(drop=True)
            except:
                prob_df=None
        else:
            prob_df=None
    
    if Full_model:
        if verbose: print("Building model over all training data")
        y_train_encoded = labels.transform(y_train)
        model = build("rf", X_train, y_train_encoded,param_dict_default)
        prob_df=None
    
    model.labels_=labels
    return model, test_results, prob_df


# In[ ]:

# Build Classification Model
try:
    start=time()
    Quick_training=(QUICK_TRAINING and not DEPLOY_MODEL)
    verbose=True if TEST_ENVIROMENT else False
    
    model, test_results, prob_df = build_classification_model(train_feat_trans_shuffled
                                                     ,label_series
                                                     ,transformed_textual_lengths_loaded
                                                     ,CV=not DEPLOY_MODEL
                                                     ,Full_model=DEPLOY_MODEL
                                                     ,Quick_training=Quick_training
                                                     ,verbose=verbose
                                                    )
    logging.info('Training of data completed succesfully. Time to complete training - %1.2f[min.]'%((time()-start)/60))
    #Log best parameters if not Quick Training
    if not Quick_training: 
        BP = ""
        for key, value in model.best_params_.items():
            BP += str(', %s: %s'%(key,value))
        logging.info('Best Parameters in training:'+BP[1:])
except:
    logging.error('Training of data failed. OPERATION ABORTED')
    tb = traceback.format_exc()
    current_frame_traceback(tb)
    send_result_request(success=False, error_message=ERROR_MSG_FOR_USER, company=account_name, request_id=request_id)
    if not TEST_ENVIROMENT: archive_infile(infile_name)
    exit()


# # Generate User Feedback

# In[ ]:

#produce precision and recall statistics + user labels-atomIQ labels mismathces dataframe
from sklearn.metrics import classification_report as clsr
def generate_user_feedback(test_results,feedback_threshold = 0.3, filter_mismatches=False):
    #Flatten Result list as the basis for the feedback to the user
    test_results_flattened = [item for sublist in test_results for item in sublist]
    #Convert list of test results to pandas data frame
    feedback_df = pd.DataFrame(test_results_flattened, columns=['index','label-atomIQ','prob']).sort_values(by=['index'])
    #Join ticket ID and user label with model results
    feedback_df = pd.merge(train_df[['ticket_id','label']].reset_index(), feedback_df, how='left', on=['index'])
    feedback_df=feedback_df.sort_values(by=['index'])
    
    #Produce precision and recall stats
    stat_df = feedback_df.dropna().drop_duplicates(subset=['index','label','label-atomIQ'])
    statistical_results = clsr(stat_df['label'], stat_df['label-atomIQ'])
    
    
    #Filter results where model and user label mismatch
    filtered_df = feedback_df.loc[(feedback_df['label-atomIQ']!=feedback_df['label'])].dropna()
    #Filter data where probability is above feedback threshold 
    filtered_df = filtered_df.loc[((filtered_df['prob']>feedback_threshold) & (filtered_df['label-atomIQ']!="Other"))
               | ((filtered_df['prob']>1-feedback_threshold) & (filtered_df['label-atomIQ']=="Other"))]
    #In case of duplicate indeces keep the lowest probability (favors FNs)
    filtered_df=filtered_df.sort_values(by=['index','prob']).drop_duplicates(subset=['index']
                                                                             #,keep='last'
                                                                            )
    if filter_mismatches:
        return statistical_results, filtered_df
    else:
        return statistical_results, feedback_df


# In[ ]:

try:
    if not DEPLOY_MODEL:
        stats, feedback_df = generate_user_feedback(test_results,
                                                    #filter_mismatches=True
                                                   )
        logging.info('User feedback was generated succesfully')
except:
    logging.error('User feedback was not generated succesfully. OPERATION ABORTED')
    tb = traceback.format_exc()
    current_frame_traceback(tb)
    send_result_request(success=False, error_message=ERROR_MSG_FOR_USER, company=account_name, request_id=request_id)
    if not TEST_ENVIROMENT: archive_infile(infile_name)
    exit()


# # Export the detailed ticket feedback to a textual file

# In[ ]:

try:
    if not DEPLOY_MODEL:
        if not TEST_ENVIROMENT:
            detailed_report_path=Output_Path+account_name+'--'+request_id+".txt"
        else:
            detailed_report_path = AMILY_SS_HOME+"/Unit-test/Output/"+account_name+'--'+request_id+".txt"
        
        feedback_df['cluster']=None #UTS implementation - for a unified file format regardless of model (classification/clustering)
        feedback_df = feedback_df.rename(columns={'ticket_id': 'Incident_Number', 'label-atomIQ': 'Recommended_Label',
                                              'prob':'Probability','cluster':'Cluster'})
        
        #detailed_report_df=feedback_df.loc[feedback_df['Recommended_Label']!="Other"] #Do not export "Other" results to UTS
        #detailed_report_df[['Incident_Number','Recommended_Label','Probability','Cluster']].to_csv(detailed_report_path,index=None,sep=",")
        
        feedback_df[['Incident_Number','Recommended_Label','Probability','Cluster']].to_csv(detailed_report_path,index=None,sep=",")
        
        logging.info('%s was created succesfully'%detailed_report_path)
        #del(detailed_report_df)
except:
    logging.error('%s was not created succesfully. OPERATION ABORTED'%detailed_report_path)
    tb = traceback.format_exc()
    current_frame_traceback(tb)
    send_result_request(success=False, error_message=ERROR_MSG_FOR_USER, company=account_name, request_id=request_id)
    if not TEST_ENVIROMENT: archive_infile(infile_name)
    exit()


# ## Export the full probabilities matrix for future thresholds sensitivity analysis

# In[ ]:

if not DEPLOY_MODEL:
    try:
        prob_df.to_csv(AMILY_SS_HOME+'/Archive/Classification/'+account_name+'--'+request_id+".txt",index=None,sep=",")
        logging.info('Full classification probabilities matrix for threshold sensitiviy analysis was archived succesfully')
    except:
        logging.warning('Full classification probabilities matrix for threshold sensitiviy analysis was not archived succesfully')
        tb = traceback.format_exc()
        current_frame_traceback(tb)


# # Export the classification report to PNG file

# Plot confusion matrix

# In[ ]:

#Generate a Confusion Matrix Plot
def plot_confusion_matrix(cm_masked, cm, classes
                          ):
    """
    This function prints and plots the confusion matrix.
    Normalization can be applied by setting `normalize=True`.
    """
    #fig,axs=plt.subplots(2,1)
    
    max_length_of_label_text=len(max(classes, key=len)) #cm.shape[0]*0.6
    fig = plt.figure(frameon=False, figsize=(9,9)) #adaptive figure size causes errors
    plt.imshow(cm, interpolation='nearest', cmap=colors.ListedColormap(['#c6efce']),)

    cmap = colors.ListedColormap(['#fffef9','#fffddd', '#f2e8ff'])
    bounds=[0,1,max(int(0.1*np.max(cm_masked)),5),max(np.max(cm_masked),10)]
    norm = colors.BoundaryNorm(bounds, cmap.N)
    plt.imshow(cm_masked, interpolation='nearest', cmap=cmap,norm=norm)
    
    filter_value_dict={1:"External",0:"Internal"}
    plt.suptitle(account_name.replace("_"," ")+" - "+filter_value_dict[filter_values[0]]+" Tickets - Type:"+label_type+"\natomIQ Ticketing Auto Labeling Results - "+strftime("%Y-%m-%d %H:%M")+" (CMI TZ)"
                 , y=0.99, fontsize=14,fontweight='bold')
    plt.title('\n\n\n\nAuto labeling compared to my original labeling',fontsize=10,fontweight='bold')
    
    
    tick_marks = np.arange(len(classes))
    plt.xticks(tick_marks, classes, rotation=90)
    plt.yticks(tick_marks, classes)
    
    for i, j in itertools.product(range(cm.shape[0]), range(cm.shape[1])):
        plt.text(j, i, cm[i, j],
                 horizontalalignment="center",
                 color="#d3d3d3" if cm[i,j]==0 else "black",fontsize=120/cm.shape[0])
    
    plt.ylabel('My label'
               ,color='#686e77'
               ,fontweight='bold')
    plt.xlabel('\nPredicted label by atomIQ ticketing'
               ,color='#686e77'
               ,fontweight='bold')
    #plt.figtext(.0, .05, "IMPORTANT NOTE:\nA ticket is assigned\nto a flow if the predicted\nproability is above 0.5.\nThreshold modification may\noffset misclassfications")
    #plt.colorbar(shrink=0.5,fontsize=5)
    
    #ColorBar
    cb = plt.colorbar(shrink=0.5)
    cb.ax.set_yticklabels(cb.ax.get_yticklabels(), fontsize=8)
    
    plt.tight_layout()

    return plt


# In[ ]:

#Excepts a 2D array representing the confusion matrix and returns a 2D array where "Other" is pushed to the end 
#+ the ordered list of flow names for plotting
def move_Other_to_end_of_confusion_mat(feedback_df):
    cm_ord = confusion_matrix(feedback_df['label'], feedback_df['Recommended_Label'])
    cls = model.labels_.inverse_transform(np.arange(len(label_series.unique().tolist()))).tolist()
    Other_index = cls.index("Other")
    df_ord = pd.DataFrame(cm_ord,columns=cls)
    df_ord["-Other-"]=df_ord["Other"]
    df_ord = df_ord.drop('Other', 1)
    cm_ord = df_ord.values.T
    df_ord = pd.DataFrame(cm_ord,columns=cls)
    df_ord["-Other-"]=df_ord["Other"]
    df_ord = df_ord.drop('Other', 1)
    cm_ord = df_ord.values.T
    cls = df_ord.columns.values
    return cm_ord, cls


# In[ ]:

#Export Confusion Matrix to a .jpg file
cm_plot_success=True
try:
    if not DEPLOY_MODEL:
        plt.clf()
        try:
            #Try shifting Other to the end, if not - continue as printed from training model
            cm, cls = move_Other_to_end_of_confusion_mat(feedback_df)
        except:    
            cm = confusion_matrix(feedback_df['label'], feedback_df['Recommended_Label'])
            cls=model.labels_.inverse_transform(np.arange(len(label_series.unique().tolist())))
        cm =np.ma.masked_where(np.diag(np.ones(cm.shape[0]))==1, cm) #The diaginal is masked in order to show it in green
        try:
            cm_plot = plot_confusion_matrix(cm, cm.data,classes=cls)
        except:
            #In case where ther's only one column in confudion matrix
            cm_plot = plot_confusion_matrix(cm.data, cm.data,classes=cls)
        
        cm_plot.savefig(AMILY_SS_HOME+"/Images/confusion_mat.jpg")
except:
    logging.error('Confusion Matrix .PNG file was not created successfully')
    tb = traceback.format_exc()
    current_frame_traceback(tb)
    cm_plot_success=False


# Plot Precision/Recall Report

# In[ ]:

#Generate a data frame from the prescosion/recall report
def report_to_df(report):
    #This inner function was taken from a blog - not sure it's the most efficient
    def report_to_table(report):
        report = report.splitlines()
        #print(report)
        res = []
        res.append(['']+report[0].split())
        for row in report[2:-2]:
            res.append(row.split())
        lr = report[-1].split()
        #print(lr)
        #print([' '.join(lr[:3])]+lr[3:])
        #res.append([' '.join(lr[:3])]+lr[3:])
        res.append(lr)
        return np.array(res)
    table_arr=report_to_table(re.sub("(?<=\S) (?=\S)","_",report).replace("avg_/_total","AVERAGE/SUMMARY"))
    #print(report)
    stat_list=[]
    for l in table_arr:
        stat_list.append(l)
    stat_list[0][0]='label'
    #print(stat_list)
    stats_df=pd.DataFrame(stat_list[1:], 
             columns=stat_list[0]
            )
    stats_df['label']=stats_df['label'].str.replace('_',' ')
    return stats_df


# In[ ]:

#Generate a Precision-Recall Report
def precision_recall_report(stats):
    stat = report_to_df(stats)[['label','precision','recall','support']].set_index('label')
    stat = stat.rename(columns={'support': '#Labeled Tickets', 'precision': 'Precision','recall':'Recall'})
    
    #Try removing "Other" to end of report
    def move_label_to_end_of_report(report,label):
        report_transposed = report.T
        report_transposed['-'+label+"-"]=report_transposed[label]
        report_transposed = report_transposed.drop(label, 1)
        report_ordered = report_transposed.T
        return report_ordered
    try:
        stat = move_label_to_end_of_report(stat,'Other')
        stat = move_label_to_end_of_report(stat,'AVERAGE/SUMMARY')
    except:
        pass

    stat['Precision'] = 1-stat['Precision'].astype(np.float)
    stat['Recall'] = 1-stat['Recall'].astype(np.float)
    stat['Precision']=stat['Precision'].apply('{:.0%}'.format)
    stat['Recall']=stat['Recall'].apply('{:.0%}'.format)
    stat = stat.rename(columns={'Precision': 'Error', 'Recall': 'Missed'})

    plt.clf()
    from pandas.tools.plotting import table
    max_length_of_label = len(max(stat.index.tolist(), key=len))
    #fig, ax = plt.subplots(figsize=(8.5, stat.shape[0]*0.32)) # set size frame
    
    fig, ax = plt.subplots(figsize=(8.5, stat.shape[0]*0.5)) # set size frame
    
    ax.xaxis.set_visible(False)  # hide the x axis
    ax.yaxis.set_visible(False)  # hide the y axis
    ax.set_frame_on(False)  # no visible frame, uncomment if size is ok
    #tabla = table(ax, stat, loc='upper right', colWidths=[0.12,0.12,0.18])  # where df is your data frame
    
    tabla = table(ax, stat, loc='upper right', colWidths=[0.12,0.12,0.18])  # where df is your data frame
    
    tabla.auto_set_font_size(False) # Activate set fontsize manually
    tabla.set_fontsize(11) # if ++fontsize is necessary ++colWidths
    tabla.scale(1.2, 1.2) # change size table

    plt.figtext(.47, 0.9, "Statistical Summary", fontsize=10,fontweight='bold')
    #plt.title('asdasdasd')
    plt.figtext(0.01, 0.03, "Error - % of tickets classified as the flow icorrectly by atomIQ Ticketing\nMissed - % of tickets labeld by the user to the flow and were not classified as the flow by atomIQ Ticketing", fontsize=9)
    plt.figtext(0.85,0.01,str(request_id), fontsize=8, color='#ccbbbb')
    
    training_type={True:'Quick Training',False:'Full Training'}
    plt.figtext(0.85,0.03,training_type[QUICK_TRAINING],fontsize=8,color='#ccbbbb')
    
    #plt.tight_layout()
    return plt


# In[ ]:

#Export Precision-Recall report to a .jpg file
pr_plot_success=True
try:
    if not DEPLOY_MODEL:
        pr_plot = precision_recall_report(stats)
        pr_plot.savefig(AMILY_SS_HOME+'/Images/pre_recall_report.jpg')
except:
    logging.error('Precision-Recall report .jpg file was not created successfully')
    tb = traceback.format_exc()
    current_frame_traceback(tb)
    pr_plot_success=False


# Append Images to one image

# In[ ]:

#Appends images to one image
def pil_grid(images, max_horiz=np.iinfo(int).max):
    n_images = len(images)
    n_horiz = min(n_images, max_horiz)
    h_sizes, v_sizes = [0] * n_horiz, [0] * (n_images // n_horiz)
    for i, im in enumerate(images):
        h, v = i % n_horiz, i // n_horiz
        h_sizes[h] = max(h_sizes[h], im.size[0])
        v_sizes[v] = max(v_sizes[v], im.size[1])
    h_sizes, v_sizes = np.cumsum([0] + h_sizes), np.cumsum([0] + v_sizes)
    im_grid = Image.new('RGB', (h_sizes[-1], v_sizes[-1]), color='white')
    for i, im in enumerate(images):
        im_grid.paste(im, (h_sizes[i % n_horiz], v_sizes[i // n_horiz]))
    return im_grid


# In[ ]:

#Add pictures to user feedback report, append them to one image and export to directory
if not DEPLOY_MODEL:
    try:
        list_im=[AMILY_SS_HOME+"/Images/Fixed/atomiq_logo.png"]
        if cm_plot_success:
            list_im.append(AMILY_SS_HOME+"/Images/confusion_mat.jpg")
        else:
            list_im.append(AMILY_SS_HOME+"/Images/Fixed/CM-Error.PNG")

        if pr_plot_success:
            list_im.append(AMILY_SS_HOME+"/Images/pre_recall_report.jpg")
        else:
            list_im.append(AMILY_SS_HOME+"/Images/Fixed/PR-Error.PNG")

        imgs = [Image.open(i) for i in list_im]
        im = pil_grid(imgs,1)
        if not TEST_ENVIROMENT:
            saved_path=Output_Path+account_name+'--'+request_id+'.png'
            im.save(saved_path)
        else:
            saved_path=AMILY_SS_HOME+'/Unit-test/Output/Training_Report_'+account_name+'--'+request_id+'.png'
            im.save(saved_path)
        logging.info('User feedback report was generated successfully')
    except:
        logging.error('User feedback report was not generated successfully')
        tb = traceback.format_exc()
        current_frame_traceback(tb)
        try:
            #Send a textual file containing an error message
            if not TEST_ENVIROMENT:
                saved_path=Output_Path+'Training_Report_'+account_name+'--'+request_id+'.txt'
            else:
                saved_path=AMILY_SS_HOME+'/Unit-test/Output/Training_Report_'+account_name+'--'+request_id+'.txt'
            with open(saved_path, 'w') as error_msg_file:
                error_msg_file.write('An error occurred while generating the Auto labeling statistics report for '+account_name+' ['+strftime("%Y-%m-%d %H:%M")+']')
        except:
            pass

    try:
        os.remove(AMILY_SS_HOME+'/Images/confusion_mat.jpg')
        os.remove(AMILY_SS_HOME+'/Images/pre_recall_report.jpg')
    except:
        pass


# In[ ]:

#Exports Preicision-Recall Report to Excel File - Disabled
'''
try:
    output_path = AMILY_SS_HOME+"/Output/"+account_name+"_statistics.xlsx"
    report_to_df(stats).to_excel(output_path,index=None)
    logging.info('%s was created succesfully'%output_path)
    logging.info('-----------------SUCCSEFULLY FINIHED TRAINING PROCESS FOR %s-----------------'%account_name)
except:
    logging.info('%s was not created succesfully. OPERATION ABORTED'%output_path)
'''
pass


# # View Ticket - For Internal Use Only

# In[ ]:

'''
def review_row(train_df, ticket_id, textual_field):
    for idx, row in train_df.loc[train_df['ticket_id']==ticket_id].iterrows():
        print(row[textual_field])
        
tid = 'INC000002294732'
review_row(train_df, ticket_id=tid, textual_field='textual_field_2')
'''
pass


# # Save model and NLP feature extractor to a pickle file

# In[ ]:

def save_ml_model_file(path, model):
    filter_value_dict={1:"ext",0:"int"}
    filter_value=filter_value_dict[filter_values[0]]
    
    if label_type.lower() not in AMILY_FLOW_TYPES:
        logging.warning('%s is not an identified flow type!'%label_type)
    if label_type.lower()=='automation' or label_type.lower()=='label':
        classification_type=''
    else:
        classification_type=''.join(['_',label_type.lower()])

    Classification_model_file_name = account_name.replace(" ","_")+"_"+filter_value+'_Classification_model'+classification_type+'.pkl'
    
    #Globe_Telecom_Dispatch_Classification_model
    
    with open(path+Classification_model_file_name, 'wb') as class_pkl:
        pickle.dump(model, class_pkl)


# In[ ]:

import glob
def save_nlp_model_file(path):
    filter_value_dict={1:"ext",0:"int"}
    filter_value=filter_value_dict[filter_values[0]]
    
    acc=account_name.replace(' ','_')

    source_nlp_model_file = glob.glob(''.join([AMILY_SS_HOME,'/Generated_Pickles/','*',acc,'*',filter_value,'*.pkl']))[0]
    dest_nlp_model_file=path+source_nlp_model_file[source_nlp_model_file.rfind('/')+1:]
    

    try:
        if label_type.lower()=='automation' or label_type.lower()=='label':
            classification_type=''
        else:
            classification_type=''.join(['_',label_type.lower()])
    except Exception as exp:
        logging.error(exp)
        tb = traceback.format_exc()
        current_frame_traceback(tb)
    
    dest_nlp_model_file=dest_nlp_model_file[:dest_nlp_model_file.rfind('.')]+classification_type+'.pkl'

    copyfile(source_nlp_model_file, dest_nlp_model_file)


# In[ ]:

if DEPLOY_MODEL:
    path = AMILY_SS_HOME+"/Outbound_File_Transfer/"
    try:     
        save_ml_model_file(path, model)
        logging.info('ML Model pickle was generated successfully')
    except:
        logging.error('ML Model pickle was not generated successfully')
    
    try:     
        save_nlp_model_file(path)
        logging.info('NLP Model pickle was copied successfully')
    except:
        logging.error('NLP Model pickle was not copied successfully')


# # Send Reply to UTS

# In[ ]:

if not DEPLOY_MODEL:
    send_result_request(success=True, detailed_results_path=detailed_report_path, 
                    stats_report_path=saved_path, company=account_name, request_id=request_id)


# # Delete training file from directory upon training completion

# In[ ]:

if not TEST_ENVIROMENT:
    try:
        archive_infile(infile_name)
        logging.info('-----------------SUCCESSFULLY FINISHED TRAINING PROCESS FOR %s-----------------'%account_name)
    except:
        logging.error('Could not delete training file after completion of training')
else:
    logging.info('-----------------SUCCESSFULLY FINISHED TRAINING PROCESS FOR %s-----------------'%account_name)

