
# coding: utf-8

# # atomIQ Ticketing Self Service - Clustering Module

# In[ ]:

#basic packages - found in the Anaconda release
import pandas as pd
import numpy as np
import itertools
from sklearn.externals import joblib
import logging
import logging.config
from time import time, gmtime, strftime
from datetime import datetime
import re
from scipy.sparse import vstack, hstack
import json
import sys
from PIL import Image
import os
from shutil import copyfile
import json
import traceback

from sklearn.metrics.pairwise import euclidean_distances
from sklearn.metrics.pairwise import cosine_distances


# In[ ]:

#matplotlib imports

#%matplotlib notebook 
#Magic command to view plots in Jupyter notebooks. disable when running as the application

import matplotlib
matplotlib.use('Agg') #Configures matplotlib for the application server and does not look for a GUI
import matplotlib.pyplot as plt
from matplotlib import colors


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


Output_Path="/UTSAmilyAttachments/AMILY_TO_UTS/"
ERROR_MSG_FOR_USER = "An error has occured while clustering data on atomIQ ticketing, the operation has been aborted"
LABELS_ONLY=True #True if only label data is provided by UTS, and not textual fields
GMM_COMPONENTS=120


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
    #column_dict[cols['label_field']]='label'
    
    full_df.rename(columns=column_dict,inplace=True)
    
    #Filter filed by filtered values - Unneccesary in Current UTS implementation - The data will already be filtered
    '''
    for idx, filter_field in enumerate(cols['filter_fields']):
        filter_field_column=str("_".join(['filter_field',str(idx+1)]))
        full_df=full_df.loc[full_df[filter_field_column]==cols['filter_values'][idx]]
    '''
        
    #Drop NA only after filters were done and only for the relevant columns
    column_list=[]
    for key, value in column_dict.items():
        column_list.append(value)
    #full_df.dropna(inplace=True, subset=column_list)
    full_df = full_df.drop_duplicates(subset=['ticket_id']).sort_values(by=['ticket_id']).reset_index(drop=True) 
    #print(full_df.info())
    
    return full_df[column_list]
    #Return a shuffled-row-order data frame as a preperation for the cross validation
    #return full_df.sample(frac=1)


# In[ ]:

#Archive files - copy to Archive Directory and remove from orignal directory
def archive_infile(infile_name):
    try:
        file_name=infile_name[infile_name.rfind('/')+1:]
        copyfile(infile_name, AMILY_SS_HOME+"/Archive/"+file_name)
        os.remove(infile_name)
        logging.info('Clustering training file was moved to Archive folder')
    except:
        logging.warning('Clustering training file was not moved successfully to Archive folder')
        tb = traceback.format_exc()
        current_frame_traceback(tb)


# In[ ]:

#INPUT PARAMETERS - FILE WILL BE RECEIVED FROM ITSM
try:
    if TEST_ENVIROMENT:
        infile_name = AMILY_SS_HOME+"/Unit-test/Data/Unit1--000000000000948.txt" #Internal use only - testing purposes
    else:
        infile_name = str(sys.argv[1])

    logging.info('----------------- CLUSTERING SESSION HAS STARTED-----------------')
    logging.info("File was loaded for clustering: "+infile_name)
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
label_field = "Label"
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
    train_df = read_corpus(infile_name,cols)
    
    filter_values=[train_df["filter_field_1"].unique()[0]] #Is External Yes or No - A very UTS-specific implementation
    train_df=train_df.loc[train_df["filter_field_1"]==filter_values[0]].reset_index(drop=True) #Make sure using only one filter value field
    
    send_result_request(success=True, company=account_name, request_id=request_id, Ack=True)
    logging.info("Data for clustering - %s account, %d unique tickets, Is_External=%s"%(account_name,train_df.shape[0],filter_values[0]))
    if train_df["filter_field_1"].unique().shape[0]>1:
        logging.warning('More than 1 filter field values')
except:
    logging.error("Unable to load file. OPERATION ABORTED")
    tb = traceback.format_exc()
    current_frame_traceback(tb)
    #send_result_request(success=False, error_message=ERROR_MSG_FOR_USER, company=account_name)
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


# # Clustering Algorithm

# Dimensionality Reduction

# In[ ]:

'''Dimensionality Reduction using TruncatedSVD'''
def svd_dim_reduction(train_feat, components, verbose=False):
    from sklearn.decomposition import TruncatedSVD
    start=time()
    if verbose:
        print('Dimensionality redcuction started at ',end ='')
        print(datetime.now().strftime('%H:%M:%S'))
    svd = TruncatedSVD(n_components=components)
    svd.fit(train_feat)
    train_feat_SVD = svd.fit_transform(train_feat,y=None)
    if verbose:
        print('Dimensionality redcuction concluded successfully at ',end ='')
        print(datetime.now().strftime('%H:%M:%S'))
    logging.info('Dimensionality reduction of data completed succesfully. Time to complete - %1.2f[min.]'%((time()-start)/60))
    return train_feat_SVD


# GMM Clustering

# In[ ]:

def gmm_clustering(train_db,num_components,verbose=False):
    from sklearn import mixture
    
    if verbose:
        print('GMM Clustering started at ',end ='')
        print(datetime.now().strftime('%H:%M:%S'))
    
    clf = mixture.GaussianMixture(n_components=num_components, covariance_type='full')
    clf.fit(train_db)
    db=clf.predict(train_db)
    
    if verbose:
        print('GMM Clustering concluded successfully at ',end ='')
        print(datetime.now().strftime('%H:%M:%S'))
    return db


# DBSCAN Clustering

# In[ ]:

def dbscan_clustering (train_db, epsilon, minimum_cluster_size, verbose=False):
    from sklearn.cluster import DBSCAN
    
    if verbose:
        print('DBSCAN Clustering started at ',end ='')
        print(datetime.now().strftime('%H:%M:%S'))
    
    #train_df normalization for cosine metric
    Xnorm = np.linalg.norm(train_db,axis = 1)
    np.seterr(divide='ignore', invalid='ignore')
    Xnormed = np.divide(train_db,Xnorm.reshape(Xnorm.shape[0],1))
    Xnormed = np.nan_to_num(Xnormed)
    
    db = DBSCAN(eps = epsilon, min_samples = minimum_cluster_size, metric = 'euclidean', n_jobs=-1).fit_predict(Xnormed)
    
    if verbose:
        print('DBSCAN Clustering concluded successfully at ',end ='')
        print(datetime.now().strftime('%H:%M:%S'))
    return db


# In[ ]:

# Generate Clusters
def generate_clusters(svd_components=50, dbscan_eps=0.6, dbscan_min_cluster_size=10, two_phase_dbscan = False,
                     num_components=GMM_COMPONENTS):
    verbose=True if TEST_ENVIROMENT else False
    start=time()
    try:
        train_feat_dim_reduced = svd_dim_reduction(train_feat_trans, svd_components, verbose=verbose)
        #train_df['cluster'] = dbscan_clustering(train_feat_dim_reduced, dbscan_eps, dbscan_min_cluster_size, verbose=verbose)
        train_df['cluster']=gmm_clustering(train_feat_dim_reduced,num_components,verbose=verbose)

        clustered_df = pd.DataFrame(train_feat_dim_reduced)
        clustered_df['ticket_id'] = train_df['ticket_id']
        clustered_df['cluster'] = train_df['cluster']

        clustered_df['cluster'] = clustered_df['cluster']+1
    
        logging.info('Clustering completed succesfully. Time to complete - %1.2f[min.]'%((time()-start)/60))
        return clustered_df
    except:
        logging.error('Could not complete clustering process. OPERATION ABORTED')
        tb = traceback.format_exc()
        current_frame_traceback(tb)
        send_result_request(success=False, error_message=ERROR_MSG_FOR_USER, company=account_name, request_id=request_id)
        return

clustered_df=generate_clusters()
if not isinstance(clustered_df, pd.DataFrame):
    if not TEST_ENVIROMENT: 
        archive_infile(infile_name)
    exit()


# # Generate User Feedback

# In[ ]:

try:
    ticket_id_field="Incident Number"
    
    if not TEST_ENVIROMENT:
        detailed_report_path=Output_Path+account_name+'--'+request_id+".txt"
    else:
        detailed_report_path = AMILY_SS_HOME+"/Unit-test/Output/"+account_name+'--'+request_id+".txt"

    feedback_df = pd.DataFrame(clustered_df['ticket_id'])
    #feedback_df['Recommended_Label']=np.NaN
    #feedback_df['Probability']=np.NaN
    feedback_df['Cluster']=clustered_df['cluster']
    
    feedback_df=feedback_df.rename(columns={"ticket_id": ticket_id_field})
    
    if missing_tickets>0:
        tickets_with_no_transformation_df = pd.DataFrame(removed_tickets_from_train, columns=[ticket_id_field])
        tickets_with_no_transformation_df['Cluster']=np.nan
        feedback_df = feedback_df.append(tickets_with_no_transformation_df, ignore_index=True)
    feedback_df['Cluster'] = feedback_df['Cluster'].dropna().apply(lambda x: str(int(x)))
    
    feedback_df.to_csv(detailed_report_path,index=None,sep=",")
    logging.info('%s was created succesfully'%detailed_report_path)
    #del(feedback_df)
except:
    logging.error('%s was not created succesfully. OPERATION ABORTED'%detailed_report_path)
    tb = traceback.format_exc()
    current_frame_traceback(tb)
    send_result_request(success=False, error_message=ERROR_MSG_FOR_USER, company=account_name, request_id=request_id)
    if not TEST_ENVIROMENT: archive_infile(infile_name)
    #exit()


# # Generate User Report

# In[ ]:

#For each cluster fetch one representative example 
def fetch_cluster_example_recommendation(clustered_df, cluster_ind, two_phase_dbscan = False):
    filtered_df = clustered_df.loc[clustered_df.cluster == cluster_ind, :].reset_index(drop=True)
    size_of_cluster = filtered_df.shape[0] 
    
    #2 phase DBSCAN - Currently Disabled
    if two_phase_dbscan:
        mean_distance_between_pairs = filtered_df.iloc[:,:-5].mean().mean(axis = 0) 
        filtered_df['cluster_minor'] = dbscan_clustering(filtered_df.iloc[:,:-4], abs(mean_distance_between_pairs*10), int(filtered_df.shape[0]/4))
        largest_cluster_ind = np.argmax(filtered_df.cluster_minor.value_counts()) 
        filtered_df = filtered_df.loc[filtered_df.cluster_minor == largest_cluster_ind, :].reset_index(drop=True)
        #print(filtered_df)

    #Compute pairwise distance matrix
    distance_matrix = pd.DataFrame(euclidean_distances(filtered_df.iloc[:,:-5],filtered_df.iloc[:,:-5]))
    distance_matrix['average'] = distance_matrix.mean(axis = 0)
    index_min = distance_matrix.average.idxmin(axis = 1)

    ticket_id = filtered_df.ticket_id.iloc[index_min]
    size_of_cluster_print = '{:d} ({:.2f}% of training data)'.format(size_of_cluster,100*(size_of_cluster/clustered_df.shape[0]))
    return [cluster_ind, size_of_cluster_print, ticket_id]


# # Generate Clustering Summary Image

# In[ ]:

def plot_clustering_summary(recommendation_df):
    from pandas.tools.plotting import table
    fig, ax = plt.subplots(figsize=(10, recommendation_df.shape[0]*0.4)) # set size frame

    ax.xaxis.set_visible(False)  # hide the x axis
    ax.yaxis.set_visible(False)  # hide the y axis
    ax.set_frame_on(False)  # no visible frame, uncomment if size is ok
    #tabla = table(ax, stat, loc='upper right', colWidths=[0.12,0.12,0.18])  # where df is your data frame

    tabla = table(ax, recommendation_df, loc='upper left',colWidths=[0.1,0.35,0.2])  # where df is your data frame

    tabla.auto_set_font_size(False) # Activate set fontsize manually
    tabla.set_fontsize(11) # if ++fontsize is necessary ++colWidths
    tabla.scale(1.2, 1.2)

    filter_value_dict={1:"External",0:"Internal"}
    plt.figtext(0.24, 0.95, account_name.replace("_"," ")+" - "+filter_value_dict[filter_values[0]]+" Tickets"
                     ,fontsize=14,fontweight='bold')
    plt.figtext(0.12, 0.9,"atomIQ Ticketing Clustering Results - "+strftime("%Y-%m-%d %H:%M")+" (CMI TZ)"
                     ,fontsize=12,fontweight='bold')
    return plt


# In[ ]:

#Create report and exoprt the report to file
summary_plot_success=True
try:
    recommendation_list = []
    for i in range (np.max(clustered_df['cluster'])):
        try:
            reco = fetch_cluster_example_recommendation(clustered_df, i+1)
            recommendation_list.append(reco)
        except:
            pass
    recommendation_df=pd.DataFrame(recommendation_list,columns=['Cluster #','Cluster Size','Sample Ticket ID'])
    #recommendation_df['Cluster #']=recommendation_df['Cluster #']+1
    summary_plt = plot_clustering_summary(recommendation_df)
    summary_plt.savefig(AMILY_SS_HOME+'/Images/clustering_report.jpg')
except:
    logging.error('Clustering summary report .jpg file was not created successfully')
    tb = traceback.format_exc()
    current_frame_traceback(tb)
    summary_plot_success=False


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
try:
    list_im=[AMILY_SS_HOME+"/Images/Fixed/atomiq_logo.png"]
    if summary_plot_success:
        list_im.append(AMILY_SS_HOME+"/Images/clustering_report.jpg")
    else:
        list_im.append(AMILY_SS_HOME+"/Images/Fixed/CM-Error.PNG")

    imgs = [Image.open(i) for i in list_im]
    im = pil_grid(imgs,1)
    if not TEST_ENVIROMENT:
        saved_path=Output_Path+account_name+'--'+request_id+'.png'
        im.save(saved_path)
    else:
        saved_path=AMILY_SS_HOME+'/Unit-test/Output/Training_Report_'+account_name+'--'+request_id+'.png'
        im.save(saved_path)
    logging.info('User clustering feedback report was generated successfully')
except:
    logging.error('User clustering feedback report was not generated successfully')
    try:
        #Send a textual file containing an error message
        if not TEST_ENVIROMENT:
            saved_path=Output_Path+'Training_Report_'+account_name+'--'+request_id+'.txt'
        else:
            saved_path=AMILY_SS_HOME+'/Unit-test/Output/Training_Report_'+account_name+'--'+request_id+'.txt'
        with open(saved_path, 'w') as error_msg_file:
            error_msg_file.write('An error occurred while generating the Auto labeling statistics report for '+account_name+' ['+strftime("%Y-%m-%d %H:%M", gmtime())+']')
    except:
        pass

try:
    os.remove(AMILY_SS_HOME+'/Images/clustering_report.jpg')
except:
    pass


# # Export the detailed ticket feedback to a textual file

# In[ ]:

send_result_request(success=True, detailed_results_path=detailed_report_path, 
                    stats_report_path=saved_path, company=account_name, request_id=request_id)


# # Delete training file from directory upon training completion

# In[ ]:

if not TEST_ENVIROMENT:
    try:
        archive_infile(infile_name)
        logging.info('-----------------SUCCESSFULLY FINISHED CLUSTERING PROCESS FOR %s-----------------'%account_name)
    except:
        logging.error('Could not delete training file after completion of training')
else:
    logging.info('-----------------SUCCESSFULLY FINISHED CLUSTERING PROCESS FOR %s-----------------'%account_name)

