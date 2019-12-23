
# coding: utf-8

# In[ ]:

import pandas as pd
import numpy as np
import glob
import logging
import os
import time


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


# In[ ]:

#Configure Self Service Log
logging.basicConfig(filename=AMILY_SS_HOME + "/" + SS_LOG_FILENAME,
                    format='%(asctime)s.%(msecs)03d %(levelname)s %(message)s', 
                    datefmt='%Y-%m-%d,%H:%M:%S',
                    level=logging.DEBUG
                   )


# In[ ]:

def read_data(account, request_id):
    read_success=False
    
    try:
        infile_name="".join([AMILY_SS_HOME,'/Archive/Classification/',account,'--',str(request_id),'.txt']) #default path
        #print(infile_name)
        
        account_archive_files=glob.glob(AMILY_SS_HOME+'/Archive/Classification/'+'*'+account+'*.txt')
        for path in account_archive_files:
            path_req_id=int(path[path.rfind('--')+2:path.rfind('.')])
            #print(path_req_id,'--->',int(request_id),'\t',path_req_id==int(request_id))
            if path_req_id==int(request_id):
                infile_name=path
                #print('F--->',infile_name)

        eval_flow_matrix=pd.read_csv(infile_name)
    except:
        print(infile_name,' Was not found')
        return None, None, None, read_success 
    
    cou=1
    flow_str = ""
    flow_dict={}
    for flow_name in eval_flow_matrix.columns.values.tolist():
        if (flow_name!="Other" and flow_name!='label'):
            flow_str= flow_str+str(cou)+'. '+str(flow_name)+'\n'
            flow_dict[cou]=flow_name
            cou+=1
    flow_str=flow_str+str(cou)+'. '+'Other'+'\n'
    flow_dict[cou]=flow_name
    print('File loaded for %s account: %s'%(account.replace("_"," "),infile_name[infile_name.rfind('/')+1:]))
    #print('Avilable Flows for thresholds sensitivity analysis:\n%s'%flow_str)
    read_success=True
    return eval_flow_matrix,flow_str,flow_dict,read_success


# In[ ]:

def th_analysis(eval_flow_matrix, eval_flow, lower_threshold, upper_threshold):

    fully_automated_tp = eval_flow_matrix.loc[(eval_flow_matrix[eval_flow]>=upper_threshold) & 
                                              (eval_flow_matrix["label"]==eval_flow)].shape[0]

    fully_automated_fn = eval_flow_matrix.loc[(eval_flow_matrix[eval_flow]<upper_threshold) & 
                                              (eval_flow_matrix["label"]==eval_flow)].shape[0]

    fully_automated_fp = eval_flow_matrix.loc[(eval_flow_matrix[eval_flow]>=upper_threshold) & 
                                              (eval_flow_matrix["label"]!=eval_flow)].shape[0]


    semi_automated_tp = eval_flow_matrix.loc[(eval_flow_matrix[eval_flow]>=lower_threshold) & 
                                             (eval_flow_matrix[eval_flow]<upper_threshold) &
                                             (eval_flow_matrix["label"]==eval_flow)].shape[0]

    semi_automated_fn = eval_flow_matrix.loc[(eval_flow_matrix[eval_flow]<lower_threshold) & 
                                             (eval_flow_matrix["label"]==eval_flow)].shape[0]

    semi_automated_fp = eval_flow_matrix.loc[(eval_flow_matrix[eval_flow]>=lower_threshold) & 
                                             (eval_flow_matrix[eval_flow]<upper_threshold) &
                                             (eval_flow_matrix["label"]!=eval_flow)].shape[0]


    print("\n~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
    print("THRESHOLD SENSITIVITY ANALYSIS FOR %s\nLower TH-%1.2f; Upper TH-%1.2f"%(eval_flow.upper(), lower_threshold, upper_threshold))
    print("----------------------------------------------------------------------")
    overall_tickets=eval_flow_matrix.loc[eval_flow_matrix["label"]==eval_flow].shape[0]
    if overall_tickets==0:
        return
    print("Overall %s tickets in labeled data\t %d (%1.1f%% of all tickets)\n"% (eval_flow, overall_tickets,100*overall_tickets/eval_flow_matrix.shape[0]))
    correct_reco=int(fully_automated_tp+semi_automated_tp)
    print("TICKETS IDENTIFIED BY atomIQ Ticketing MACHINE LEARNING\t %d/%d (%1.1f%% of %d):"% 
          (correct_reco,overall_tickets,100*correct_reco/overall_tickets,overall_tickets))
    
    #print("CORRECT RECOMMENDATIONS BY atomIQ TICKETING ON TRAINING DATA:")
    print("Tickets identified and routed to full automation\t %d (%1.1f%% of %d)"% 
          (fully_automated_tp,100*fully_automated_tp/overall_tickets,overall_tickets))
    print("Tickets identified but routed to manual validation\t %d (%1.1f%% of %d)\n"% 
          (semi_automated_tp,100*semi_automated_tp/overall_tickets,overall_tickets))
     
    print("TICKETS MISCLASSIFIED BY atomIQ TICKETING MACHINE LEARNING:")
    if (fully_automated_tp+fully_automated_fp)>0:
        print("Tickets misclassified and routed to full automation\t %d (%1.1f%% of %d+%d)"% 
              (fully_automated_fp,100*fully_automated_fp/(fully_automated_fp+fully_automated_tp),fully_automated_fp,fully_automated_tp))
    else:
        print("Tickets misclassified and routed to full automation\t %d (%1.1f%% of %d+%d)"% 
              (fully_automated_fp,0.0,fully_automated_fp,fully_automated_tp))
        
    if (semi_automated_tp+semi_automated_fp)>0:
        print("Tickets misclassified but routed to manual validation\t %d (%1.1f%% of %d+%d)\n"% 
              (semi_automated_fp,100*semi_automated_fp/(semi_automated_fp+semi_automated_tp),semi_automated_fp,semi_automated_tp))
    else:
        print("Tickets misclassified but routed to manual validation\t %d (%1.1f%% of %d+%d)\n"% 
              (semi_automated_fp,0.0,semi_automated_fp,semi_automated_tp))
    #print("Fully automated false negatives = %d\n"% fully_automated_fn)
    
    #print("%s Tickets that were not labeled as %s by atomIQ Ticketing = %d\n"% (eval_flow,eval_flow,semi_automated_fn))
    #print("Uncorrect recommendation - false negatives = %d"% int(semi_automated_fn))
    print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")


# In[ ]:

def get_input(input_text,input_type,error_msg,accepted_value_list=None):
    success=True
    try:
        user_input=input(input_text)
        casting=str(input_type+'(user_input)')
        user_input=eval(casting)
        if accepted_value_list:
            if user_input not in accepted_value_list:
                print(error_msg)
                return None, False
        return user_input, success
    except:
        print(error_msg)
        return None, False


# In[ ]:

def analyze_flow(eval_flow):
    continue_sa=True
    while continue_sa:

        lower_threshold, success=get_input('Enter lower threshold: ','float','Please enter a number between 0 and 1')
        if success:
            while (lower_threshold<0 or lower_threshold>1):
                print('Please enter a number between 0 and 1')
                lower_threshold, success=get_input('Enter lower threshold: ','float','Please enter a number between 0 and 1')
        else:
            continue

        upper_threshold, success=get_input('Enter upper threshold: ','float','Please enter a number between 0 and 1')
        if success:
            while (upper_threshold<0 or upper_threshold>1):
                print('Please enter a number between 0 and 1')
                upper_threshold, success=get_input('Enter upper threshold: ','float','Please enter a number between 0 and 1')
        else:
            continue

        th_analysis(eval_flow_matrix, eval_flow, lower_threshold, upper_threshold)
        
        success=False
        while not success:
            continue_sa, success=get_input('\nAnalyze another set of thresholds? (Y/N):','str','Please enter Y or N',['Y','N','y','n'])
        #continue_sa=get_input(input_text,input_type,error_msg)
        if continue_sa.upper()=="N": continue_sa=False


# ## Main Program

# In[ ]:

#Fetch all active accounts from current configuration folder
def active_accounts():
    TH_files = glob.glob(AMILY_SS_HOME+'/Archive/Classification/*.txt')
    account_list=[]
    account_dict={}
    for file in TH_files:
        account_list.append(file[file.rfind('/')+1:file.rfind('-')-1])
    account_list=sorted(list(set(account_list)))
    for i, account in enumerate(account_list):
        account_dict[str(i+1)]=account
    return account_dict


# In[ ]:

#Prints every request that was sent to the Self-Service in the past weeks
def fetch_recent_account_files(account, weeks=2):
    print('The following requests were received in the past %d weeks for %s:'%(weeks,account))
    account_archive_files=glob.glob(AMILY_SS_HOME+'/Archive/Classification/'+'*'+account+'*.txt')
    new_requests=0
    for path in account_archive_files:
        timestamp=os.path.getmtime(path)
        if (time.time()-timestamp)<=(60*60*24*7*weeks):
            print(time.strftime('%Y-%m-%d %H:%M', time.localtime(timestamp)),'\t',path[path.rfind('/')+1:])
            new_requests+=1
    if new_requests==0:
        print('No requests were received')


# In[ ]:

print('*********************WELCOME TO atomIQ TICKETING FLOW THRESHOLD SENSITIVITY ANALYSIS********************* ')
#account="Sprint Nextel Corporation"
#request_id='000000000000209'
chosen_account=False
print('Avilable accounts for analysis:')
account_dict=active_accounts()
for key, value in account_dict.items():
    print("".join([key,". ",value]))
while not chosen_account:
    account, chosen_account=get_input(''.join(['Please choose account number [1-',str(len(account_dict)),']: ']),
                               'int',''.join(['Please enter a number between 1 and ',str(len(account_dict))])
                                ,np.arange(len(account_dict)+1).tolist())
account=account_dict[str(account)]
print('Chosen account:',account)
    
read_success=False
while not read_success:
    #account=input('Enter account: ')
    fetch_recent_account_files(account)
    request_id=input('Enter training session request ID: ')
    eval_flow_matrix,flow_str,flow_dict,read_success=read_data(account, request_id)
    
    if not read_success:
        continue_feedback_success=False
        while not continue_feedback_success:
            continue_feedback,continue_feedback_success=get_input('\nDo you wish to continue? (Y/N):','str','Please enter Y or N',['Y','N','y','n']) 
        if continue_feedback.upper()=='N': break
            
if read_success:
    
    flow_count=len(flow_dict)
    evaluate_flow=True

    while evaluate_flow:
        print("".join(['\nFlows avilable for analysis:\n',flow_str]))
        success=False
        while not success:
            eval_flow_ind, success=get_input(''.join(['Please choose flow number [1-',str(flow_count),']: ']),
                               'int',''.join(['Please enter a number between 1 and ',str(flow_count)])
                                ,(np.arange(flow_count)+1).tolist())
            if success:
                eval_flow=flow_dict[eval_flow_ind]
                print('\nChosen flow: ',eval_flow)

        analyze_flow(eval_flow)

        success_sa=False
        while not success_sa:
            continue_sa, success_sa=get_input('\nAnalyze another flow? (Y/N):','str'
                                              ,'Please enter Y or N',['Y','N','y','n'])
        if continue_sa.upper()=="N": evaluate_flow=False
    
print('****************************************THANK YOU AND GOODBYE :-)**************************************** ')

