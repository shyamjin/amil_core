# # Amily Web Service for Amily Phase2 - 2017.09.07

# Added:
#     1. Dispatch logic
#     2. Missing information in ticket logic
#     3. Flow probability archiving
#     4. Additional security modifications
#     5. Mutiple fields to be parsed modifications

# # Amily Web Service for Amily Phase3 - 2017.12.13 (#2 Loaded to production on 2017.01.07)
# Added:
#     1. Subflow Logic
#     2. New response payload

# # Amily Web Service for Amily Phase4 - 2017.12.18
# Added:
#     1. Ignore base64 tickets logic

# # Amily Web Service for Amily BugFix - 2017.12.19 (Updated in 2018.01.30)
# Added:
#     1. Disabled automatic logic for setting unique values in parsing parameters - causes sorting issues

# # Amily Web Service for Amily BugFix - 2017.01.10
# Added:
#     1. Fixed cumulative value bug that occures where we have multiple parsers for same parameter 

# # Amily Web Service for Amily Hotfix - 2017.01.16
# Added:
#     1. Added parsing paramter value limitation (defaul - 500)

# # Amily Web Service for Amily Hotfix - 2017.02.14 (Loaded to production on 2017.02.27)
# Added:
#     1. Fixed unique values for each parsed parameter list 
#     2. Added a logic where a "null" value appears in a parsed paramter list Amily returns empty list for that parameter

# # Amily Web Service for Amily Hotfix - 2017.02.19 (Loaded to production on 2017.02.27)
# Added:
#     1. Read NLTK Processor for Spanish
#     2. Tef Argentina

import os
import socket
import logging
import json
import tornado.ioloop
import tornado.web
import pandas as pd
import re
#import parsedatetime
from datetime import datetime
import time
import importlib
import sys
import pickle
import numpy as np
import zipfile
import signal
import base64
import hashlib
import copy
import traceback

#FIXME - install and use bcrypt
#import bcrypt


# # Logs traceback lines on the current code frame + the actual error message
def current_frame_traceback(tb):
    cur_file_name=__file__
    tb_re="".join(["\"",cur_file_name.replace("/","\/"),".+\n.+","|(Error.+)"])
    tb_pattern=re.compile(tb_re)
    index = 1
    for p in tb_pattern.finditer(tb):
        logging.error(" Traceback line %d: %s"%(index,p.group().replace('\n','  ->')))
        index+=1

#Global constants
MAX_WAIT_SECONDS_BEFORE_SHUTDOWN = 3
AMILY_WS_LOG_FILENAME = "amily.log"
HOSTNAME = socket.gethostname()

DEFAULT_LOGS_DIRNAME = "Logs"
DEFAULT_PASSWD_FILENAME = ".htpasswd"

#Load & validate required environment variables
AMILY_WS_HOME     = os.environ.setdefault("AMILY_WS_HOME","")                           # This is a full path
AMILY_WS_LOGS_DIR = os.environ.setdefault("AMILY_WS_LOGS_DIR","")                       # This is a full path (in case you want logs on a different file system)
AMILY_WS_PASSWD_FILENAME = os.environ.setdefault("AMILY_WS_PASSWD_FILENAME","")         # This is just the file name, not including the directory path
AMILY_WS_CERT_FILENAME   = os.environ.setdefault("AMILY_WS_CERT_FILENAME","")           # This is just the file name, not including the directory path
AMILY_WS_CERT_PRIVATEKEY_FILENAME = os.environ.setdefault("AMILY_WS_CERT_PRIVATEKEY_FILENAME","")       # This is just the file name, not including the directory path
AMILY_WS_HTTPS_LISTEN_PORT = os.environ.setdefault("AMILY_WS_HTTPS_LISTEN_PORT","")                     # Port number
AMILY_FLOW_TYPES = set(os.environ.setdefault("AMILY_FLOW_TYPES", "").split())                                # This is supported flow types list (split on whitespace)
AMILY_WS_ACCOUNTS = list(set(os.environ.setdefault("AMILY_WS_ACCOUNTS1", "").split()))                              # This is account_name:flowtypes list (split on whitespace) example: XL_Axiata:automation,dispatch Globe:automation,functional_category
AMILY_WS_REGEX_TICKET_ID = os.environ.setdefault("AMILY_WS_REGEX_TICKET_ID", "")                        # ticket_id
AMILY_WS_REGEX_ATTACHMENT_LINK = os.environ.setdefault("AMILY_WS_REGEX_ATTACHMENT_LINK", "")            # attachment link
AMILY_AUTOMATION_FLOW_NAME = os.environ.setdefault("AMILY_AUTOMATION_FLOW_NAME", "automation")          #Automation flow name to be ignored while parsing other flows


init_errors = 0     # count the number of errors we get during initialization
if len(AMILY_WS_HOME) == 0:
    logging.info('Environment variable "AMILY_WS_HOME" is not set')
    init_errors += 1
if len(AMILY_WS_LOGS_DIR) == 0:
    AMILY_WS_LOGS_DIR = AMILY_WS_HOME + "/" + DEFAULT_LOGS_DIRNAME
    logging.info('Environment variable "AMILY_WS_LOGS_DIR" is not set. Will default to [' + AMILY_WS_LOGS_DIR + ']')
if len(AMILY_WS_PASSWD_FILENAME) == 0:
    AMILY_WS_PASSWD_FILENAME = DEFAULT_PASSWD_FILENAME
    logging.info('Environment variable "AMILY_WS_PASSWD_FILENAME" is not set. Will default to [' + AMILY_WS_PASSWD_FILENAME + ']')
if len(AMILY_WS_CERT_FILENAME) == 0:
    logging.error('Environment variable "AMILY_WS_CERT_FILENAME" is not set')
    init_errors += 1
if len(AMILY_WS_CERT_PRIVATEKEY_FILENAME) == 0:
    logging.error('Environment variable "AMILY_WS_CERT_PRIVATEKEY_FILENAME" is not set')
    init_errors += 1
if len(AMILY_WS_HTTPS_LISTEN_PORT) == 0:
    logging.error('Environment variable "AMILY_WS_HTTPS_LISTEN_PORT" is not set')
    init_errors += 1
if len(AMILY_WS_ACCOUNTS) == 0:
    logging.error('Environment variable "AMILY_WS_ACCOUNTS" is not set')
    init_errors += 1
if len(AMILY_FLOW_TYPES) == 0:
    logging.error('Environment variable "AMILY_FLOW_TYPES" is not set')
    init_errors += 1
if len(AMILY_WS_REGEX_TICKET_ID) == 0:
    logging.warning('Environment variable "AMILY_WS_REGEX_TICKET_ID" is not set')
if len(AMILY_WS_REGEX_ATTACHMENT_LINK) == 0:
    logging.warning('Environment variable "AMILY_WS_REGEX_ATTACHMENT_LINK" is not set')
if init_errors > 0:
    sys.exit(1)

'''
Sample Imput :
AMILY_FLOW_TYPES automation dispatch functional_category operationl_category
AMILY_WS_ACCOUNTS Globe_Telecom:automation Sprint_Nextel_Corporation:automation,dispatch US_Cellular_Corporation:automation,dispatch,functional_category

Logic: We will iterate over AMILY_WS_ACCOUNTS and check if provided flow types are valid. If not we will not load the account

'''
accounts_with_flows_list={}
if len(AMILY_WS_ACCOUNTS) > 0:
    for account_entity in AMILY_WS_ACCOUNTS:
        account_name = account_entity.split(":")[0]
        flow_types = set(account_entity.split(":")[1].split(","))
        # If intersection of account flow types and all supported flow types is not equal to length of list of account flow types , then skip account
        if not len(list(flow_types & AMILY_FLOW_TYPES)) == len(flow_types):
            print("Account: "+account_name+" has invalid provided flow_types: '"+ (", ").join(flow_types-AMILY_FLOW_TYPES)+\
                              "' valid values are: "+(", ").join(list(AMILY_FLOW_TYPES)))
            print ("***Account: "+account_name+ " will not be loaded ****")
        else:
            # Load all flow types per account in this list
            accounts_with_flows_list[account_name]=flow_types
        
#Define the path of the Amily production directory
amily_prod_path = os.environ["AMILY_WS_HOME"]

#Define the application log
wfh = logging.handlers.WatchedFileHandler(filename=AMILY_WS_LOGS_DIR + '/' + AMILY_WS_LOG_FILENAME)
wfh.setLevel(logging.DEBUG)
logging.basicConfig(
                    format='%(asctime)s.%(msecs)03d [' + HOSTNAME + '] %(levelname)s %(message)s',
                    datefmt='%Y-%m-%d,%H:%M:%S',
                    level=logging.DEBUG,
                    handlers=[wfh]
                   )

#Define all file paths
sys.path.append(amily_prod_path)
sys.path.append(amily_prod_path+'/Pickles')
sys.path.append(amily_prod_path+'/Classification')
sys.path.append(amily_prod_path+'/Atoms_core')      # NOTE: the core Atoms must appear before the impl Atoms directory
sys.path.append(amily_prod_path+'/Atoms_impl')      # .. in order that core should always override impl if there is attempted override by impl
sys.path.append(amily_prod_path+'/Configurations')


# In[ ]:

logging.info("*******  AMILY SERVICE HAS BEEN ACTIVATED  *******")
'''Load the basic NLTK preprocessor, that is used for every classification task, to memory'''
try:
    from NLTK_Processor import NLTKPreprocessor
except Exception as err:
    logging.error('Unable to load NLTK Processor module')
    logging.error("Error {0}".format(err))
try:
    from NLTK_Processor_Spanish import NLTKSpanishPreprocessor
except Exception as err:
    logging.error('Unable to load Spanish NLTK Processor module')
    logging.error("Error {0}".format(err))
try:
    from Item_Selector import ItemSelector, identity
except:
    logging.error('Unable to load Item Selector module')
try:
    from FeatureWeighting import FeatureWeighting
except:
    logging.error('Unable to load Feature Weighting module')


# Security Definitions - Authentication, input validation

# In[ ]:


'''Authentication Configuration Functions'''
def require_basic_auth(handler_class):
    def wrap_execute(handler_execute):
        def require_basic_auth(handler, kwargs):
            auth_header = handler.request.headers.get('Authorization')
            #print(auth_header)
            if auth_header is None or not auth_header.startswith('Basic '):
                #logging.error("Username and Password Authentication Failed")
                handler.set_status(401)
                handler.set_header('WWW-Authenticate', 'Basic realm=Restricted')
                handler._transforms = []
                handler.finish()
                return False
            #auth_decoded = base64.b64decode(auth_header)
            #logging.debug("auth_header=%s"%(auth_header))
            #print(auth_header)
            auth_decoded = str(base64.decodebytes(str.encode(auth_header[6:])), "utf-8")
            #print(auth_decoded)
            #logging.debug("auth_decoded=%s"%(auth_decoded))
            kwargs['basicauth_user'], kwargs['basicauth_pass'] = auth_decoded.split(':', 2)
            return True
        def _execute(self, transforms, *args, **kwargs):
            if not require_basic_auth(self, kwargs):
                return False
            return handler_execute(self, transforms, *args, **kwargs)
        return _execute
    handler_class._execute = wrap_execute(handler_class._execute)
    return handler_class

def read_passwd_file(passwdfile='/'.join([amily_prod_path, "SSL", AMILY_WS_PASSWD_FILENAME])):
    with open(passwdfile, "r") as fh:
        content = fh.readlines()
    for item in content:
        item.strip()
    passwords = {}
    for line in content:
        if ":" in line: 
            username, password = line.split(":")
            passwords[username] = password
    return passwords

def verify_password(passwords, username, password):
    salt = '12344321'
    m = hashlib.md5()
    m.update((salt + password).encode('utf-8')) 
    hashed = m.hexdigest()
    
    #hashed = bcrypt.hashpw(password, bcrypt.gensalt(12))
    try:
        stored_hash = passwords[username].strip("\n")
    except:
        stored_hash = ""
    
    if stored_hash == hashed:
        return True
    else:
        return False


# In[ ]:

#Input Validation - Ticket ID
def validate_ticket_ID(ticket_id):#INC000012345
    tid_regex = AMILY_WS_REGEX_TICKET_ID
    search_pattern = re.compile(tid_regex,re.VERBOSE)
    return search_pattern.search(ticket_id) is not None

def validate_attachment_link(link):
    link_regex = AMILY_WS_REGEX_ATTACHMENT_LINK
    search_pattern = re.compile(link_regex,re.VERBOSE)
    return search_pattern.search(link) is not None


# Initiate Application - load all files to memory upon service re/activation

# In[ ]:

'''Load All configuration and pickle files to memory - occures every time the service is activated/reactivated'''
class AmilyApplication(tornado.web.Application):
    def __init__(self, handlers=None, default_host=None, transforms=None, **settings):
        super().__init__(handlers, default_host, transforms, **settings)
       
        #Define the label of the "non-automation" flow - make sure that it is exactly the same as in the training files
        self.other_name = "Other"
        #Define names of all accounts configured - the exact names as in UTS and configuration files
        accounts = list(accounts_with_flows_list.keys()) # Get list of accounts
        #Define the directory path where pickle files are found
        pickels_directory_path = amily_prod_path+'/Pickles/'
        # Path to configurations json
        json_path_base_path = os.path.join(amily_prod_path,"Configurations")
        
        # types applicable for all
        types=['ext','int']

        for account in accounts:
            for flow_name in accounts_with_flows_list[account]:
                
                
                #Automation flow is a special flow. We need to set 'is_automation_flow_ind' as True to handle this special cases
                is_automation_flow_ind = True if AMILY_AUTOMATION_FLOW_NAME.lower() ==  flow_name.lower() else False
                
                # Load all dynamic variables for loading in memory
                # Define the suffix of all pickle files
                # Path for NLP_Preprocessor pkl files
                dynamic_NLP_path = self.remove_automation_flow_name('_NLP_Preprocessor_{}.pkl'.format(flow_name.lower()),AMILY_AUTOMATION_FLOW_NAME)
                # Path for Classification models
                dynamic_Model_path = self.remove_automation_flow_name('_Classification_model_{}.pkl'.format(flow_name.lower()),AMILY_AUTOMATION_FLOW_NAME)
                # load NLP type
                dynamic_NLP_type=self.remove_automation_flow_name("{}_NLP_model".format("_"+flow_name.lower()),AMILY_AUTOMATION_FLOW_NAME)
                # load classification type
                dynamic_Model_type=self.remove_automation_flow_name("{}_Classification_model".format("_"+flow_name.lower()),AMILY_AUTOMATION_FLOW_NAME)
                # load the _thresholds json
                dynamic_thresholds_json=self.remove_automation_flow_name(account+"_thresholds_{}.json".format(flow_name.lower()),AMILY_AUTOMATION_FLOW_NAME)
                #  load parsing json
                dynamic_parsing_json=self.remove_automation_flow_name(account+"{}_parsing.json".format("_"+flow_name.lower()),AMILY_AUTOMATION_FLOW_NAME)
                # Define the path for the parsing configuration file of account
                parse_parsing_json_path = os.path.normpath(os.path.join(json_path_base_path, dynamic_parsing_json))
                # Define the path for the classification threshold configuration file of account
                parse_thresholds_json_path = os.path.join(json_path_base_path,dynamic_thresholds_json)
                
                # The below is applicable for automation flow_type
                if  is_automation_flow_ind:
                    subflows_attr_name=account + "_subflows"
                    # TODO 'automation' flow needs speciaal handling .thresholds and not threshold 
                    dynamic_attr_name=self.remove_automation_flow_name(account+"_flow{}_thresholds".format("_"+flow_name.lower()),AMILY_AUTOMATION_FLOW_NAME)
                else:
                    subflows_attr_name = None
                    dynamic_attr_name=self.remove_automation_flow_name(account+"_flow{}_threshold".format("_"+flow_name.lower()),AMILY_AUTOMATION_FLOW_NAME)
                
                # ticket_type = 'ext','int' for automation else it will be "".
                #COndition to handle "" is written in method load_account_flows
                for ticket_type in types: 
                    self.load_to_memory(pickels_directory_path,account,dynamic_NLP_path,dynamic_NLP_type,ticket_type)
                    self.load_to_memory(pickels_directory_path,account,dynamic_Model_path,dynamic_Model_type,ticket_type)
                
                #parsing configuration file of account is only applicable for automation flow
                if  is_automation_flow_ind:    
                    # Load to memory Parsing Configuration Files
                    try:
                        self.load_account_flows(parse_parsing_json_path, account + "_flows")
                    except:
                        logging.warning("Unable to load/parse " + account + " parsing configuration file")
                        tb = traceback.format_exc()
                        current_frame_traceback(tb)
                        
                #Load to memory dispatch thresholds configuration files
                try:
                    self.load_account_flows(parse_thresholds_json_path,dynamic_attr_name,subflows_attr_name)#
                except:
                    logging.warning("Unable to load/parse " + account + " classification thresholds configuration file")
                    tb = traceback.format_exc()
                    current_frame_traceback(tb)
    
        logging.info("Finished initializing web service")
        logging.info("Listening for inbound requests on port "+AMILY_WS_HTTPS_LISTEN_PORT)

     
    def remove_automation_flow_name(self,entity_name,to_remove_substring):
        '''
        #TODO:There is an issue where dynamic_NLP_path,dynamic_Model_path needs camel case and rest of them need lower case
        Another issue is that the '$AMILY_AUTOMATION_FLOW_NAME' has explicit use case . This is the automation part
         of the script which should always remain  
        '''
        #if "automation" dn replace --> required for dynamic_Model_type.etc
        if "_"+to_remove_substring.lower() in entity_name:
            entity_name = entity_name.replace("_"+to_remove_substring.lower(),"")
        #if "Automation" dn replace --> required for     dynamic_NLP_path,dynamic_Model_path
        if "_"+to_remove_substring.title() in entity_name:
            entity_name = entity_name.replace("_"+to_remove_substring.title(),"")
        return entity_name            

    def load_account_flows(self, parse_path, attr_name ,subflows_attr_name = None):
        # Parse the configuration file, which comes in a json file
        config_obs=self.parse_config(parse_path)
        setattr(self,attr_name,{})
        #check if subflows are present in classification threshold configuration file of account
        if subflows_attr_name : setattr(self,subflows_attr_name,{})
        for flow_conf in config_obs:
            cur_flow=flow_conf["flow"]
            #TODO as thresholds are for automation and threshold are for dispatch they will not be in same file
            # load the flow parsing configurations to the attribute, the configurations are hold in a dictionary
            if not flow_conf.get("thresholds",flow_conf.get("threshold",None)):
                getattr(self,attr_name)[cur_flow]=self.init_flow(flow_conf)
                    #load the boolean requires_attachment value to the attribute
                getattr(self,attr_name)[cur_flow+"_requires_attachment"]=flow_conf["requires_attachment"]
            else:
                #load the flow's thresholds to the attribute, the values are hold in a dictionary
                cur_flow_threshold=flow_conf.get("thresholds",flow_conf.get("threshold"))
                getattr(self,attr_name)[cur_flow]=cur_flow_threshold
                #load the flow's subflows configuration - only if exists
                if flow_conf.get("subflows",None):
                    cur_flow_subflows=flow_conf["subflows"]
                    getattr(self,subflows_attr_name)[cur_flow]=cur_flow_subflows

    #Load to memory pickle of .py files
    def load_to_memory(self, directory, account_name,path,file_type,ticket_type_name=""):
        try:
            #Load file for the specific account and type (internal/external)
            if ticket_type_name!="":
                full_path =str(directory+account_name+"_"+ticket_type_name+path)
                #logging.debug("trying to load %s"%(full_path))
                with open(full_path, 'rb') as fid:
                    setattr(self,account_name+"_"+ticket_type_name+file_type,pickle.load(fid))
            else:
                full_path =str(directory+account_name+path)
                #logging.debug("trying to load %s"%(full_path))
                with open(full_path, 'rb') as fid:
                    setattr(self,account_name+file_type,pickle.load(fid))
        except:
            #An error meassage to the log in case where the file could not be loaded
            logging.warning("Unable to load "+account_name+"_"+ticket_type_name+file_type)
            tb = traceback.format_exc()
            current_frame_traceback(tb)
            
    #Parses a json file
    def parse_config(self, config_path):
        infile=open(config_path,"r")
        flow_map=json.load(infile)
        return flow_map
    
    #Converts the name of the atom class to the name of the atom file name
    #Will always be in a constant format. for example: 
    #RegexExtractor is the name of the class and Atom_regex_extractor is the (py) file name
    def convert(self, name):
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        name_low= re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
        return '_'.join(['Atom', name_low]) 
    
    #Loads all flow atom configurations found in the configuration file and converts them to python modules
    def init_flow(self, flow_conf):
        atom_list = []
        for atom in flow_conf["atoms"]:
            atom_ent=list(atom.keys())[0]
            atom_module=self.convert(atom_ent)
            atom_list.append(self.init_atom(atom_module, atom[atom_ent], atom_ent))
        return atom_list
    
    #Uses the atom name, atom file name and atom parameters to load a a atom parsing configurations and convert to a python module
    def init_atom(self, atom_module, atom_dict, atom_name):
        my_module = importlib.import_module(atom_module)
        my_class=getattr(my_module,atom_name)
        atom=my_class(**atom_dict)
        return atom


# Amily handler - classification and parsing upon ticket arrival

# In[ ]:

'''Recieves a ticket data - stored in a dataframe, classifies and parses the ticket and returns the answer to client'''

@require_basic_auth
class AmilyHandler(tornado.web.RequestHandler):
    '''----------------------GET METHOD----------------------'''
    #Mandatory method - NOT IN USE
    def get(self):
        name=self.get_argument("name", None, True )
        self.write("Hello from Amily, %s!"%(name))
        
    '''----------------------GENERAL CLASSIFICATION METHODS----------------------'''
    def text_to_features(self, doc, nlp_model):
        #Open the relevant NLP model (stored in an attribute) and tranform text
        #currently the transoframtion is done only on the summary and description fields
        try:
            features = getattr(self.application,nlp_model).transform(doc)
            return True, features
        except:
            return False, ""
    
    def classifications_probabilities(self, features, classification_model):
        #Open the relevant classification model (stored in an attribute) and fetch flow probabilities (to a list form)
        #for each configured flow in the account
        try:
            probabilities = getattr(self.application,classification_model).predict_proba(features).tolist()[0]
            return True, probabilities
        except:
            return False, []
            
    def predicted_instance (self, probabilities_list, classification_model):
        #Locate maximum likelihood flow that is not "Other" 
        other_indicator = list(getattr(self.application,classification_model).labels_.classes_).index(self.application.other_name)
        predicted_flow_ind = other_indicator
        predicted_flow_prob = 0 
       
        #Iterate through all flow probabilities and record the highest that is not "Other"
        for i in range(len(probabilities_list)):
            if (float(probabilities_list[i])>predicted_flow_prob) and (i!=other_indicator):
                predicted_flow_prob=probabilities_list[i]
                predicted_flow_ind = i 
                
        #use the inverse tranform method of the classification model to locate the maximun likelihood flow name from it's indicator
        predicted_flow_name = getattr(self.application,classification_model).labels_.inverse_transform(int(predicted_flow_ind))
        return predicted_flow_prob, predicted_flow_name
    
    def fetch_threshold (self, account,flow,th_type):
        account_flow_threshold_attr = str(account)+"_flow_thresholds"
        type_threshold=getattr(self.application,account_flow_threshold_attr)[flow][th_type]
        return type_threshold
        
    def search_token_for_subflow (self, document, token):
        for idx, row in document.iterrows():
            text = " ".join([row.summary, row.description])
        search_pattern = re.compile(token, re.MULTILINE|re.IGNORECASE)
        if search_pattern.search(text):
            return True
        else:
            return False

    '''----------------------WORKFLOW CLASSIFICATION METHOD----------------------'''
    def classify_ticket_to_flow(self, doc, ticket_account, is_external):
        
        #Set the default value for the classification success indicator - unsuccessfult until defined otherwise
        classification_success = False
        #Configure to open attributes that holds the current NLP and classification models
        if is_external:
            ext_ind='ext'
        else:
            ext_ind='int'
        cur_NLP_model = str(ticket_account)+"_"+str(ext_ind)+'_NLP_model'
        #logging.debug("cur_NLP_model=%s"%(cur_NLP_model))
        cur_classification_model = str(ticket_account)+"_"+str(ext_ind)+'_Classification_model'
        #logging.debug("cur_classification_model=%s"%(cur_classification_model))
        
        #Transorm text to features
        text_to_feature_success, ticket_features = self.text_to_features(doc, cur_NLP_model)
        if not text_to_feature_success:
            logging.error(ticket_account+" NLP preprocessor not found")
            tb = traceback.format_exc()
            current_frame_traceback(tb)
            #If no NLP transformer is found return "Other" as recomended flow with a classification_success in status fail
            return self.application.other_name, False, classification_success, 1, []
       
        #Predict flow probabilities
        probabilities_success, predicted_flow_prob_list = self.classifications_probabilities(ticket_features, cur_classification_model) 
        if not probabilities_success:
            logging.error(ticket_account+" classification model not found")
            #If no classification model is found return "Other" as recomended flow with a classification_success in status fail
            tb = traceback.format_exc()
            current_frame_traceback(tb)
            return self.application.other_name, False, classification_success, 1, []
        predicted_flow_prob, predicted_flow_name = self.predicted_instance(predicted_flow_prob_list, cur_classification_model)
        
        #print(predicted_flow_prob, predicted_flow_name)
        #Threshold logic for workflow classification
        try:
            #Fetch upper and lower bounds for predicted flows
            account_flow_threshold_attr = str(ticket_account)+"_flow_thresholds"
            predicted_flow_upper_threshold=getattr(self.application,account_flow_threshold_attr)[predicted_flow_name]['upper']
            predicted_flow_lower_threshold=getattr(self.application,account_flow_threshold_attr)[predicted_flow_name]['lower']
            
            full_automation = False
            #in case where the flow's probability is higher than the upper bound the recommendation will be full automation
            if predicted_flow_prob>=predicted_flow_upper_threshold: full_automation = True
            
            #in case where the flow's probability is lower than the lower bound the projected flow will be "Other" 
            if predicted_flow_prob<predicted_flow_lower_threshold:
                predicted_flow_ind = list(getattr(self.application,cur_classification_model).labels_.classes_).index(self.application.other_name)
                predicted_flow_name = getattr(self.application,cur_classification_model).labels_.inverse_transform(int(predicted_flow_ind))
                predicted_flow_prob = 1 - predicted_flow_prob
                full_automation = False           
        except:
            #In case where no bounds were found for the projected flow (or in case of "Other") 
            #the recommendation will be semi automation and the flow is "Other"  
            full_automation = False
            #A case where a flow was found that is not "Other" and there's an issue loading the thresolds
            if predicted_flow_name != self.application.other_name:
                logging.error(ticket_account+" threshold configuration error")
                predicted_flow_name = self.application.other_name
                predicted_flow_prob = 1 - predicted_flow_prob
                return predicted_flow_name, full_automation, classification_success, predicted_flow_prob, []
        
        #Fetch selected flow id - DISABLED FOR PHASE1
        '''
        try:
            account_flow_id_attr = str(ticket_account)+"_flow_ids"
            predicted_flow_id = getattr(self.application,account_flow_id_attr)[predicted_flow_name]
        except:
            predicted_flow_id = 0
        '''
        
        #Subflows logic
        if predicted_flow_name in getattr(self.application,str(ticket_account)+"_subflows"):
            try:
                predicted_subflows = {}

                account_flow_subflows_attr = str(ticket_account)+"_subflows"
                predicted_flow_subflows = getattr(self.application,account_flow_subflows_attr)[predicted_flow_name]
                
                #Iterate trhough all defined subflows and seacrh for koens defining/nullifying them in the ticket's text
                for subflow in predicted_flow_subflows:
                    # Search for a token defining a subflow
                    subflow_inclusion_indicator = False
                    if "inclusion_list" in subflow:
                        for inclusion_token in subflow['inclusion_list']:
                            if self.search_token_for_subflow(doc, inclusion_token):
                                subflow_inclusion_indicator = True

                    # Seacrh for a token nullifying a flow
                    subflow_exclusion_indicator = False
                    if "exclusion_list" in subflow:
                        for exclusion_token in subflow['exclusion_list']:
                            if self.search_token_for_subflow(doc, exclusion_token):
                                subflow_exclusion_indicator = True

                    # Add subflow to potential selected subflows list if a token is found
                    if subflow_inclusion_indicator and not subflow_exclusion_indicator:
                        predicted_subflows[subflow['order']] = subflow['subflow']        
                    if subflow_exclusion_indicator:
                        predicted_subflows[0] = self.application.other_name #"Other" flow will always get ordering = 0
                        

                # Select subflow if potentials exist
                if predicted_subflows:
                    selected_subflow_key = min(predicted_subflows.keys()) #Choose the subflow with the lowest ordering
                    #Assign probabilities to selected subflow
                    if selected_subflow_key == 0:
                        predicted_flow_prob = 1  #Other flow probability
                    else:
                        if len(predicted_subflows)> 1: 
                            #In case where there are several non "Other" potential subflows the probability assigned is the flow's lower threshold
                            predicted_flow_prob = self.fetch_threshold(ticket_account,predicted_flow_name,'lower')
                    #Assign flow name to selected subflow
                    predicted_flow_name = predicted_subflows[selected_subflow_key]
                else:
                    #If no potentials exist choose the flow with the highest ordering
                    min_order = 100
                    temp_subflow_name = self.application.other_name
                    for subflow in predicted_flow_subflows:
                        if int(subflow['order'])<min_order:
                            min_order = int(subflow['order'])
                            temp_subflow_name = subflow['subflow']
                    predicted_flow_name = temp_subflow_name
            except:
                logging.error(ticket_account+" threshold configuration error on flow's", predicted_flow_name," subflows")
                tb = traceback.format_exc()
                current_frame_traceback(tb)
                pass

        # Documentation logic for automation flows - return all flows probabilities and thresholds
        #TODO - Add same logic to the "classify_ticket_to_dispatch" method
        #TODO - Varify no exceptions
        #TODO - Conctenate results of "classify_ticket_to_flow" and "classify_ticket_to_dispatch" on "post" method

        # Fetch probabilities assigned for each flow in the current ticket
        documentation_probs = zip(list(getattr(self.application, cur_classification_model).labels_.classes_),
                                  predicted_flow_prob_list)
        documentation_probs = [{'flow_name': n, 'prob': p} for (n, p) in documentation_probs]

        # Fetch thresholds configured for each flow, in case where no thresholds are configured, returns -1 for both upper and lower
        account_flow_threshold_attr = str(ticket_account) + "_flow_thresholds"
        for d in documentation_probs:
            try:
                d['upper_thresh'] = getattr(self.application, account_flow_threshold_attr)[d['flow_name']][
                    'upper']
                d['lower_thresh'] = getattr(self.application, account_flow_threshold_attr)[d['flow_name']][
                    'lower']
            except:
                d['upper_thresh'] = -1
                d['lower_thresh'] = -1

        #If arrived to this point the classification process was a success
        classification_success = True
        if predicted_flow_prob ==0:
            predicted_flow_prob = 1
            full_automation = False
        return predicted_flow_name, full_automation, classification_success, predicted_flow_prob, documentation_probs
    
    '''----------------------DISPATCH CLASSIFICATION METHOD----------------------'''
    def classify_ticket_to_dispatch(self, doc, ticket_account ,dynamic_flow, is_external):
        
        #Set the default value for the classification success indicator - unsuccessfult until defined otherwise
        classification_success = False
        #Configure to open attributes that holds the current NLP and classification models
        if is_external:
            flow_ext_ind='ext'
        else:
            flow_ext_ind='int'
        flow_dynamic_NLP_type = str(ticket_account)+"{}_{}_NLP_model".format("_"+flow_ext_ind,dynamic_flow.lower())
        #dispatch_classification_model = str(ticket_account)+'_dispatch_Classification_model'
        flow_dynamic_Model_type = str(ticket_account) + "{}_{}_Classification_model".format("_"+flow_ext_ind,dynamic_flow.lower())
        
        #Transorm text to features
        text_to_feature_success, ticket_features = self.text_to_features(doc, flow_dynamic_NLP_type)
        if not text_to_feature_success:
            #logging.error(ticket_account+" Dispatch NLP preprocessor not found")
            #If no NLP transformer is found return "Other" as recomended flow with a classification_success in status fail
            return self.application.other_name,False, classification_success, 1,[]
       
        #Predict flow probabilities
        probabilities_success, predicted_group_prob_list = self.classifications_probabilities(ticket_features, flow_dynamic_Model_type)
        if not probabilities_success:
            #logging.error(ticket_account+" Dispatch classification model not found")
            #If no classification model is found return "Other" as recomended flow with a classification_success in status fail
            return self.application.other_name,False, classification_success, 1,[]
        #toDo: can have threshold value for dispatch as well
        predicted_group_prob, predicted_group_name = self.predicted_instance(predicted_group_prob_list, flow_dynamic_Model_type)

        #Threshold logic for dispatch classification
        try:
            #Fetch upper and lower bounds for predicted flows
            account_group_threshold_attr = ticket_account + "_flow{}_threshold".format("_" + dynamic_flow.lower())
            predicted_group_upper_threshold=getattr(self.application,account_group_threshold_attr)[predicted_group_name]['upper']
            predicted_group_lower_threshold=getattr(self.application,account_group_threshold_attr)[predicted_group_name]['lower']

            full_group_flow = False
            if predicted_group_prob>=predicted_group_upper_threshold: full_group_flow = True

            #in case where the group's probability is lower than the threshold the recommendation will be "Other"
            if predicted_group_prob<predicted_group_lower_threshold:
                predicted_group_prob = 1- predicted_group_prob
                predicted_group_name = self.application.other_name
                full_group_flow = False
        except:
            #In case where no bounds were found for the projected group (or in case of "Other")
            #the recommendation will be "Other"
            #A case where a flow was found that is not "Other" and there's an issue loading the thresolds
            full_group_flow = False
            if predicted_group_name != self.application.other_name:
                logging.error(ticket_account+ "{} threshold configuration error".format("_" + dynamic_flow.lower()))
                tb = traceback.format_exc()
                current_frame_traceback(tb)
                predicted_group_prob = 1- predicted_group_prob
                predicted_group_name = self.application.other_name
                return predicted_group_name,full_group_flow, classification_success, predicted_group_prob,[]

        # Documentation logic for automation flows - return all flows probabilities and thresholds
        dynamic_documentation_probs = zip(list(getattr(self.application, flow_dynamic_Model_type).labels_.classes_),
                                  predicted_group_prob_list)
        dynamic_documentation_probs = [{'flow_name': n, 'prob': p} for (n, p) in dynamic_documentation_probs]

        # Fetch thresholds configured for each flow, in case where no thresholds are configured, returns -1 for both upper and lower
        dynamic_account_flow_threshold_attr = ticket_account + "_flow{}_threshold".format("_" + dynamic_flow.lower())
        for d in dynamic_documentation_probs:
            try:
                d['upper_thresh'] = getattr(self.application, dynamic_account_flow_threshold_attr)[d['flow_name']][
                    'upper']
                d['lower_thresh'] = getattr(self.application, dynamic_account_flow_threshold_attr)[d['flow_name']][
                    'lower']
            except:
                d['upper_thresh'] = -1
                d['lower_thresh'] = -1
        #If arrived to this point the classification process was a success
        classification_success = True
        if predicted_group_prob ==0:
            predicted_group_prob = 1
            full_group_flow = False
        return predicted_group_name,full_group_flow, classification_success, predicted_group_prob,dynamic_documentation_probs


    '''----------------------PARSING METHOD----------------------'''
    #parse a dictionary to lists of keys and values
    def parse_list(self, parsed_entity):
        key = list(parsed_entity.keys())[0]
        value = list(parsed_entity.values())[0]
        return key, value

    #Extract all parameters for the ticket's flow
    def extract_parts(self,flow, account, desc):
        #Initialize a dictionary that would contain all parsed entitites in key-value form
        #Key -> paramater name, value -> parsed values, in a form of list
        parse_dict={}
        try:
            #Iterates through all entities that should be parsed and trigger the configured atoms for parsing
            for atom in getattr(self.application,account+'_flows')[flow]:
                #The get_matches method should appear in each and every Atom we're using.
                #This action triggers the configured atom and receives back a dictionary holding the parameter name (key)
                #and values (value)
                cur_parse = atom.get_matches(desc)
                
                #The atom can return a simple dictionary or a tuple containing several dictionaries for multiple entitites
                if type(cur_parse) is dict:
                    #parse the dictionary returned by the atom
                    key, value = self.parse_list(cur_parse)
                    #append the values to the parse_dict dictionary
                    if key not in parse_dict:
                        parse_dict[key]=value
                    else:
                        #In case where the entity already exists add new values found
                        temp_dict = parse_dict[key].copy()
                        temp_dict.extend(value)
                        parse_dict[key] = temp_dict
                if type(cur_parse) is tuple:
                    for dict_instance in cur_parse:
                        key, value = self.parse_list(dict_instance)  
                        if key not in parse_dict:
                            parse_dict[key]=value
                        else:
                            #In case where the entity already exists add new values found
                            temp_dict = parse_dict[key].copy()
                            temp_dict.extend(value)
                            parse_dict[key] = temp_dict
                            #parse_dict[key].extend(value)
            success = True
            
        except:
            logging.error("Unable to parse entitities of flow "+flow+" from account "+account)
            tb = traceback.format_exc()
            current_frame_traceback(tb)
            success = False

        #return the full parsed dictionary and an indicator of parsing success (true/false)
        return parse_dict, success
        
    '''----------------------POST----------------------'''
    def get(self):
        name=self.get_argument("name", None, True )
        self.write("Wassap, %s!"%(name))
 
    def search_base64(self, desc):
        found_base64 = False
        if re.search('base64,',desc):
            found_base64 = True
        return found_base64
        
    def post(self, basicauth_user, basicauth_pass):
        
        #Authentication
        passwords = read_passwd_file()
        if not verify_password(passwords, basicauth_user, basicauth_pass):
            logging.error('User name/Password Authentication Failed')
            res_dict = {"ERROR":"User name/Password Authentication Failed"}
            self.write(res_dict)
            return
        
        #"body" holds the ticket data as recieved from UTS, in a json format
        body = self.request.body
        #Removes the name of the server from the reply header - security request
        self.set_header('Server', '')
        
        #logging.info('POST "%s" "%s" %d bytes',
        #             filename, content_type, len(body))
        #logging.debug(body)

        #Open and parse incoming ticket file
        
        try:
            cur_df=pd.read_json(body, typ="series")            

            ticket_id = cur_df["ticket_id"]
            ticket_account = cur_df["header"]["account"].replace(" ","_")
            is_external = cur_df["header"]["is_external"]
            ticket_create_date = time.strftime('%Y-%m-%d-%H-%M-%S', time.localtime(cur_df["body"]["create_date"]))
            description = cur_df["body"]["description"]
            summary = cur_df["body"]["summary"]
            #Ignore ticket that have base64 coding within it's description text 
            if self.search_base64(description):
                description = ""
                summary = ""
        except:
            logging.error("Unable to parse incoming file")
            tb = traceback.format_exc()
            current_frame_traceback(tb)
            res_dict = {"ERROR":"Could not parse incoming json file, please check file structure"}
            #self.write(json.dumps(res_dict))
            self.write(res_dict)
            return
        
        #INPUT VALIDATION
        if not validate_ticket_ID(ticket_id):
            logging.error("Input validation error - Ticket ID")
            res_dict = {"ERROR":"Could not parse incoming json file, please check file structure"}
            self.write(res_dict)
            return
        
        '''
        try:
            for attachment in cur_df["body"]["attachments"]
                if not validate_attachment_link(attachment["url"]):
                    logging.error("Input validation error - Attachment link")
                    res_dict = {"ERROR":"Could not parse incoming json file, please check file structure"}
                    self.write(res_dict)
                    return
        except:
            pass
        '''
        logging.info("Succesfully parsed ticket " + ticket_id)

        #WORKFLOW CLASSIFICATION
        #first define a datframe that holds all necessary data for classification
        ticket_df = pd.DataFrame(columns=['is_external','summary','description'])
        ticket_df.loc[0]= [is_external,summary,description]
        #Trigger the workflow classification method
        flow_name, full_automation, classification_success, classification_prob, documentation_probs = self.classify_ticket_to_flow(ticket_df, ticket_account, is_external)
        #classification_dict={"flow_id":flow_id,"flow_name":flow_name,"full_automation":full_automation}
        
        #Try fetching flow name from previous classifications
        try:
            prev_flow=cur_df["header"]["uts_flow_name"]
            if (prev_flow is not None) and (prev_flow != flow_name):
                flow_name = prev_flow
                full_automation = False
        except:
            pass
        
        #Define a dictionary holding the classification result and success indicator
        classification_dict={"flow_name":flow_name,"full_automation":full_automation}
        
        #DISPACTH CLASSIFICATION
        dynamic_classification_dict =[]
        flow_types_list = copy.deepcopy(accounts_with_flows_list[ticket_account])
        # remove the automation flow from the list because it is already handled
        if AMILY_AUTOMATION_FLOW_NAME in flow_types_list : flow_types_list.remove(AMILY_AUTOMATION_FLOW_NAME)
        # iterate for each flow_type
        for dynamic_flow in flow_types_list:
            dynamic_flow_name,dynamic_group_full_automation, dynamic_classification_success, dynamic_classification_prob,dynamic_documentation_probs = self.classify_ticket_to_dispatch(ticket_df, ticket_account ,dynamic_flow, is_external)
            #toDo:here we are passing order as 1 always confirm
            if len(dynamic_documentation_probs)>1:
                documentation_probs.extend(dynamic_documentation_probs)

            if(dynamic_flow_name!='Other'):
                dynamic_classification_dict.append({"flow_name":dynamic_flow_name,"full_automation":dynamic_group_full_automation,"probability":dynamic_classification_prob,"order":1})
        # toDo: if we don't have any flow then return
        if len(flow_types_list) < 1:
            dynamic_classification_dict = []

        #PARSING
        parse_success = True
        #Defines the variable that holds all the data for parsing, that does not come within an attachment
        ticket_text = summary +'\nDescription:'+ description
        data_for_parsing = {"text":ticket_text,"create_date":ticket_create_date}
        
        #Parse only if the classification was a success and the recommended flow is not "Other"
        if classification_success and flow_name!=self.application.other_name:
            parsing_dict, parse_success = self.extract_parts(flow_name, ticket_account, data_for_parsing)
            #res_json = json.dumps(self.extract_parts(flow_name, description, ticket_id))
        else:
            parsing_dict = {}
        
        #Parsing of attachments if neccesary
        attach_parse_success = True
        try:
            #First check if the ticket requires an attachment parse
            if getattr(self.application,ticket_account+"_flows")[flow_name+"_requires_attachment"]:
                try:
                    #Loop through all attachments found in the ticket data
                    for attachment in cur_df["body"]["attachments"]:
                        try:
                            #the url will contain the server name, which is unneccesary and will be removed
                            file_name_for_parsing = attachment["url"][attachment["url"].index(':')+1:]
                        except:
                            file_name_for_parsing = attachment["url"]
                        data_for_parsing = {"text":file_name_for_parsing}
                        #logging.info(data_for_parsing)
                        attach_parsing_dict, attach_parse_success = self.extract_parts(flow_name, ticket_account, data_for_parsing) 
                        #Append found attachment data to the parsing_dict
                        for key ,value in attach_parsing_dict.items():
                            temp_dict = parsing_dict[key].copy()
                            try:
                                #Make sure only unique values are inserted
                                for v in value:
                                    if v not in temp_dict:
                                        temp_dict.extend([v])
                            except:
                                temp_dict.extend(value)
                            parsing_dict[key] = temp_dict
                            #parsing_dict[key].extend(value)
                except:
                    logging.error("Unable to parse attachment data for ticket",ticket_id)
                    tb = traceback.format_exc()
                    current_frame_traceback(tb)
        except:
            pass
        
        
        #Assign Unique Values to each parameter value list - keeps original order!
        try:
            for key, value in parsing_dict.items():
                #parsing_dict[key]=list(set(value)) -> CAUSES SORTING ISSUES, DO NOT ACTIVATE
                if type(value) is list:
                    temp_list = []
                    for v in value:
                        if v not in temp_list:
                            temp_list.append(v)
                    parsing_dict[key]=temp_list
        except:
            pass
        
            
        #if not parse_success or not attach_parse_success:
        parsing_success = parse_success and attach_parse_success 
        
        
        #Limit number of parsed values being passed to UTS in order to avoid memory issues or Appilcation crashes
        #Return empty list for a parameter where the parsers have returned at leat one null value
        VALUE_LIMITATION = 500
        try:
            for key, value in parsing_dict.items():
                if type(value) is list:
                    if None in parsing_dict[key]:
                        parsing_dict[key]=[]
                    if len(value)>VALUE_LIMITATION:
                        parsing_dict[key] = []
                        classification_dict["full_automation"]=False
                        logging.info('ATTENTION - Value limitation in parsed list exceeded')
        except:
            pass
        
        #consolidate results to a json file - OLD version
        '''
        res_dict = {"ticket_id":ticket_id,
                    "success":classification_success,
                    "classification":classification_dict, 
                    "parsing":parsing_dict,
                    "probability": classification_prob,
                    "dispatch_support_group":dispatch_flow_name}
        #res_json = json.dumps(res_dict)

        #Report results to the Amily log
        logging.info({"ticket_id":ticket_id,
                      "create_date":ticket_create_date,
                      "classification success":classification_success,
                      "parsing success": parsing_success,
                      "classification":classification_dict, 
                      "parsing":parsing_dict,
                      "probability":classification_prob,
                      "dispatch":dynamic_classification_dict
                     })
        
        '''
        #consolidate results to a json file - New version
        
        classification_dict['order'] = 1
        classification_dict['probability'] = classification_prob
        classification_dict['parameters'] = parsing_dict 
        
        '''
        # FOR TESTING PUPROSES
        classification_dict_syn = {"flow_name": "Rated Events Extraction",
                                   "full_automation": full_automation,
                                   "order": 2,
                                   "probability": classification_prob,
                                   "parameters": parsing_dict
                                  }
                                   
        
        
        dynamic_classification_dict['order'] = 2
        dynamic_classification_dict['probability'] = dynamic_classification_prob
        
        dynamic_classification_dict = {"flow_name":"Rejects",
                                           "order": 3,
                                           "probability": dynamic_classification_prob} 
        
        '''
        
        res_dict = {"ticket_id":ticket_id,
                    "success":classification_success,
                    "recommendations":{"automation_flow":[classification_dict],"dispatch_flow":dynamic_classification_dict},
                    "other_recommendations": documentation_probs
                    }
        
        #Report results to the Amily log
        logging.info({"account":ticket_account,
                      "ticket_id":ticket_id,
                      "create_date":ticket_create_date,
                      "classification success":classification_success,
                      "parsing success": parsing_success,
                      "classification":classification_dict, 
                      "parsing":parsing_dict,
                      "probability":classification_prob,
                      "dispatch":dynamic_classification_dict
                     })
        
        
        #Return the result to client
        #self.write(res_json)
        self.write(res_dict)


# Main Program

# In[ ]:

'''2 Test classes - Not in use in production'''
class SimpleHandler(tornado.web.RequestHandler):
    def get(self):
        name=self.get_argument("name", None, True )
        self.write("Hello from Amily, %s!"%(name))

    def post(self):
        logging.debug(self.request.headers)
        logging.debug(self.request.body)

#Graceful shutdown of the service        
def killhandle(sig, frame):
    io_loop = tornado.ioloop.IOLoop.instance()

    def stop_loop(deadline):
        now = time.time()
        if now < deadline and (io_loop._callbacks or io_loop._timeouts):
            #Open services are open and the service will not yet be closed
            logging.info('Waiting for next tick before Amily service deactivation')
            io_loop.add_timeout(now + 1, stop_loop, deadline)
        else:
            io_loop.stop()
            logging.info('*******  AMILY SERVICE HAS BEEN DEACTIVATED  *******')

    def shutdown():
        #logging.info('Will deactivate Amily in %s seconds ...',
        #             MAX_WAIT_SECONDS_BEFORE_SHUTDOWN)
        stop_loop(time.time() + MAX_WAIT_SECONDS_BEFORE_SHUTDOWN)

    io_loop.add_callback_from_signal(shutdown)
    
class MainHandler(tornado.web.RequestHandler):
    def post(self):
        #name=self.get_argument("name", None, True )
        self.write("ERROR - Invalid post request, expecting an 'amily' post")

'''Creates the tornado app'''
def make_app():
    return AmilyApplication([
        #(r"/simple",SimpleHandler),
        (r"/amily",AmilyHandler),
        (r"/", MainHandler),
        # The health_check path will be polled by the load balancer to see if the web service is up. It just needs to return a HTTP 200 response.
        (r"/health_check()$", tornado.web.StaticFileHandler, {'path': amily_prod_path+'/Health_Check/alive'}),
    ],
    {"par"})

from functools import partial
import tornado.httpserver

'''MAIN'''
def main():
    app = make_app()
    
    ssl_dict = {
        "certfile": amily_prod_path+'/SSL/' + AMILY_WS_CERT_FILENAME,
        "keyfile": amily_prod_path+'/SSL/' + AMILY_WS_CERT_PRIVATEKEY_FILENAME
    }
    
    #app.listen(AMILY_WS_HTTPS_LISTEN_PORT, ssl_options = ssl_dict)
    app.listen(1007)
    signal.signal(signal.SIGTERM, partial(killhandle))
    #signal.signal(signal.SIGHUP, partial(killhandle))
    signal.signal(signal.SIGINT, partial(killhandle))
    #tornado.ioloop.IOLoop.current().start()    
    tornado.ioloop.IOLoop.instance().start()  

if __name__ == "__main__":
    main()
