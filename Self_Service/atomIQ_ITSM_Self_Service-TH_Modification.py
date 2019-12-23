# coding: utf-8

# In[ ]:

import pandas as pd
import numpy as np
import json
import logging
import glob
import os
import copy


# # Global Variables
DEFAULT_LOGS_DIRNAME = "Logs"
SS_LOG_FILENAME="deployment_self_service.log"

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
logging.basicConfig(filename=AMILY_SS_LOGS_DIR + "/" + SS_LOG_FILENAME,
                    format='%(asctime)s.%(msecs)03d %(levelname)s %(message)s', 
                    datefmt='%Y-%m-%d,%H:%M:%S',
                    level=logging.DEBUG
                   )


# In[ ]:

#Fetch all active accounts from current configuration folder
def active_accounts():
    TH_files = glob.glob(AMILY_SS_HOME+'/Incoming_File_Transfer/'+'*_thresholds*.json')
    account_list=[]
    account_dict={}
    for file in TH_files:
        #account_list.append(file[file.rfind('/')+1:file.rfind('.')].replace('_thresholds',""))
        account_list.append(file[file.rfind('/')+1:file.rfind('.')])
    account_list=sorted(list(set(account_list)))
    for i, account in enumerate(account_list):
        account_dict[str(i+1)]=account
    return account_dict


# In[ ]:

#Prints a dictionary nicely alligned
class TablePrinter(object):
    "Print a list of dicts as a table"
    def __init__(self, fmt, sep=' ', ul=None):
        """        
        @param fmt: list of tuple(heading, key, width)
                        heading: str, column label
                        key: dictionary key to value to print
                        width: int, column width in chars
        @param sep: string, separation between columns
        @param ul: string, character to underline column label, or None for no underlining
        """
        super(TablePrinter,self).__init__()
        self.fmt   = str(sep).join('{lb}{0}:{1}{rb}'.format(key, width, lb='{', rb='}') for heading,key,width in fmt)
        self.head  = {key:heading for heading,key,width in fmt}
        self.ul    = {key:str(ul)*width for heading,key,width in fmt} if ul else None
        self.width = {key:width for heading,key,width in fmt}

    def row(self, data):
        return self.fmt.format(**{ k:str(data.get(k,''))[:w] for k,w in self.width.items() })

    def __call__(self, dataList):
        _r = self.row
        res = [_r(data) for data in dataList]
        res.insert(0, _r(self.head))
        if self.ul:
            res.insert(1, _r(self.ul))
        return '\n'.join(res)

def print_thresholds(json_file):
    ls=[]
    for i, flow in enumerate(json_file):
        ls.append({'#':str(i+1),'flow':flow['flow'],'lower':flow[type_dict[automation_indicator]]['lower'],
                   'upper':flow[type_dict[automation_indicator]]['upper']})
    fmt = [
        ('#','#',3),
        ('Flow','flow',50),
        ('Lower TH','lower',10),
        ('Upper TH','upper',10),
    ]
    
    print(TablePrinter(fmt, ul='=')(ls))


# In[ ]:

#Read current configuration file and prints the contents
def read_current(account):
    read_success=False
    infile_name="".join([AMILY_SS_HOME,'/Incoming_File_Transfer/',account
                         #,'_thresholds'
                        ,'.json']
                       )
    try:
        th_config = json.load(open(infile_name))
        #print('Current threshold configurations for %s:'%account.replace("_"," "))
        #print_thresholds(th_config)
        #available_flows=[]
        #for flow in th_config:
        #    available_flows.append(flow['flow'])
        flow_type=account[account.find('')]
        automation_flow = account.find('thresholds_') == -1
        read_success=True
    except:
        print(infile_name,' Was not found or Could not be parsed')
        return None, None,read_success
    return th_config , automation_flow, read_success


# In[ ]:

#Indexing and printing values in a dictionary
def print_dict(dict_to_print):
    for key, value in dict_to_print.items():
        print("".join([key,". ",value.replace("_thresholds","").replace("_"," ")]))


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

#Function to read new threshold value
def fetch_th_value(th_type,lower_th=-10000000):
    th_value_success=False
    while not th_value_success:
        try:
            th_value=float(input('Write a new %s threshold:'%th_type))
        except:
            print('Invalid Type. Please write a number between 0 and 1')
            continue

        if th_value<0 or th_value>1.2:
            print('The threshold value must be between 0 and 1.2')
        elif th_value<lower_th:
            print('The upper threshold must be higher than the lower threshold')
        else:
            th_value_success=True
    return th_value


# In[ ]:

def update_active_flow(th):
    
    #Show user avilable flows for update and prompt selection of a flow
    chosen_flow_success=False
    print('\nFLOWS:')
    for i, flow in enumerate(th):
        print("".join([str(i+1),". ",flow['flow']]))
    while not chosen_flow_success:
        updated_flow,chosen_flow_success=get_input(''.join(['Please choose flow number to update [1-',str(len(th)),']: ']),
                                       'int',''.join(['Please enter a number between 1 and ',str(len(th))])
                                        ,np.arange(len(th)+1).tolist())
    updated_flow=th[updated_flow-1]['flow']
    
    for i, flow in enumerate(th):
        if flow['flow']==updated_flow:
            print('\nCurrent TH for %s - [%1.2f,%1.2f]'%(updated_flow,flow[type_dict[automation_indicator]]['lower'],
                                                         flow[type_dict[automation_indicator]]['upper']))
            flow_index=i
            
    #User selects an action
    update_options={"1":"Update Flow Name",
                    "2":"Update Flow Thresholds"}
    print('\nActions:')
    print_dict(update_options)
    action_read_success = False
    while not action_read_success:
        user_action, action_read_success=get_input('Enter desired action ID: ','int','Please choose a number [1-2]',
                                                    np.arange(len(update_options)+1).tolist())
    
    #Update Flow Name
    if user_action==1:
        update_name=True
        while update_name:
            new_flow_name=input('Write a new flow name for %s: '%updated_flow)
            confirm_feedback=False
            while not confirm_feedback:
                confirm,confirm_feedback=get_input('New flow name for %s -> %s. please confirm (Y/N)'%(updated_flow,new_flow_name),
                                                   'str','Please enter Y or N',['Y','N','y','n'])
            if confirm.upper()=='N':
                continue_feedback_success=False
                while not continue_feedback_success:
                    continue_feedback,continue_feedback_success=get_input('\nDo you wish to provide an alternative flow name? (Y/N):',
                                                                          'str','Please enter Y or N',['Y','N','y','n']) 
                if continue_feedback.upper()=='N': update_name=False
            else:
                th[flow_index]['flow']=new_flow_name
                update_name=False
        
    #Update Flow thresholds
    if user_action==2:
        update_th=True
        while update_th:
            lower_th=fetch_th_value('lower')
            upper_th=fetch_th_value('upper',lower_th)
            
            confirm_feedback=False
            while not confirm_feedback:
                confirm,confirm_feedback=get_input('New TH for %s -> (%1.2f,%1.2f). please confirm (Y/N)'%(updated_flow,lower_th,upper_th),
                                                   'str','Please enter Y or N',['Y','N','y','n'])
            if confirm.upper()=='N':
                continue_feedback_success=False
                while not continue_feedback_success:
                    continue_feedback,continue_feedback_success=get_input('\nDo you wish to provide an alternative thresholds? (Y/N):',
                                                                          'str','Please enter Y or N',['Y','N','y','n']) 
                if continue_feedback.upper()=='N': update_th=False
            else:
                th[flow_index][type_dict[automation_indicator]]['lower']=lower_th
                th[flow_index][type_dict[automation_indicator]]['upper']=upper_th
                update_th=False
            
    return th


# In[ ]:

def add_new_flow(th):
    new_flow_dict={}

    #New Flow Name
    update_name=True
    while update_name:
        new_flow_name=input('Write a new flow name:')
        confirm_feedback=False
        while not confirm_feedback:
            confirm,confirm_feedback=get_input('New flow -> %s. please confirm (Y/N)'%(new_flow_name),
                                               'str','Please enter Y or N',['Y','N','y','n'])
        if confirm.upper()=='N':
            continue_feedback_success=False
            while not continue_feedback_success:
                continue_feedback,continue_feedback_success=get_input('\nDo you wish to provide an alternative new flow name? (Y/N):',
                                                                      'str','Please enter Y or N',['Y','N','y','n']) 
            if continue_feedback.upper()=='N':
                return th
        else:
            new_flow_dict['flow']=new_flow_name
            update_name=False
            
    update_th=True
    while update_th:
        lower_th=fetch_th_value('lower')
        upper_th=fetch_th_value('upper',lower_th)

        confirm_feedback=False
        while not confirm_feedback:
            confirm,confirm_feedback=get_input('TH for %s -> (%1.2f,%1.2f). please confirm (Y/N)'%(new_flow_name,lower_th,upper_th),
                                               'str','Please enter Y or N',['Y','N','y','n'])
        if confirm.upper()=='N':
            continue_feedback_success=False
            while not continue_feedback_success:
                continue_feedback,continue_feedback_success=get_input('\nDo you wish to provide an alternative thresholds? (Y/N):',
                                                                      'str','Please enter Y or N',['Y','N','y','n']) 
            if continue_feedback.upper()=='N':
                return th
        else:
            new_flow_dict[type_dict[automation_indicator]]={}
            new_flow_dict[type_dict[automation_indicator]]['lower']=lower_th
            new_flow_dict[type_dict[automation_indicator]]['upper']=upper_th
            update_th=False
    
    th.append(new_flow_dict)
    return th


# In[ ]:

def remove_active_flow(th):
    #Show user avilable flows for update and prompt selection of a flow
    chosen_flow_success=False
    print('\nFLOWS:')
    for i, flow in enumerate(th):
        print("".join([str(i+1),". ",flow['flow']]))
        
    confirm_feedback=False
    while not confirm_feedback:
    
        while not chosen_flow_success:
            updated_flow,chosen_flow_success=get_input(''.join(['Please choose flow number to remove [1-',str(len(th)),']: ']),
                                           'int',''.join(['Please enter a number between 1 and ',str(len(th))])
                                            ,np.arange(len(th)+1).tolist())
        updated_flow=th[updated_flow-1]['flow']
        confirm,confirm_feedback=get_input('Are you sure you want to remove flow %s? (Y/N)'%(updated_flow),
                                                   'str','Please enter Y or N',['Y','N','y','n'])
        
        if confirm.upper()=='N':
            return th
        else:
            confirm_feedback=True
    
    #Remove selected flow
    for i, flow in enumerate(th):
        if flow['flow']==updated_flow:
            th.pop(i)
            print('%s was removed successfully'%updated_flow)

    return th


# In[ ]:

def update_configuration_file(account,new_config):
    file_name="".join([AMILY_SS_HOME,'/Outbound_File_Transfer/',account,".json"])
    with open(file_name, 'w') as fp:
        json.dump(new_config, fp, indent=4)
    print('%s threshold configuration file updtaed successfully!'%account)
    return


# ## Main Program

# In[ ]:

import copy
print('*********************WELCOME TO atomIQ TICKETING FLOW THRESHOLD MODIFICATION MODULE********************* ')

#Read the Current Configuration File
try:
    print('Avilable accounts for analysis:')
    account_dict=active_accounts()
    print_dict(account_dict)
    chosen_account=False
    while not chosen_account:
        account, chosen_account=get_input(''.join(['Please choose account number [1-',str(len(account_dict)),']: ']),
                                   'int',''.join(['Please enter a number between 1 and ',str(len(account_dict))])
                                    ,np.arange(len(account_dict)+1).tolist())
        account=account_dict[str(account)]
        print('\nChosen account:',account)
except:
    print('Threshold configuration file was not loaded succesfully. OPERATION ABORTED')
    logging.error('Could fecth directory with current configuration files')
    exit()

new_configuration=None
update_configuration = True
update_options={"1":"Update Active Flow",
       "2":"Add New Flow",
       "3":"Remove Active Flow"}
type_dict = {True:'thresholds',False:'threshold'}

#Update Account's thresholds
while update_configuration:
    chosen_account=False
    read_success=False

    #Read the Current Account's threshold
    if not new_configuration:
        while not read_success:
            current_configuration, automation_indicator, read_success = read_current(account)

            if not read_success:
                continue_feedback_success=False
                while not continue_feedback_success:
                    continue_feedback,continue_feedback_success=get_input('\nDo you wish to continue? (Y/N):',
                                                                          'str','Please enter Y or N',['Y','N','y','n']) 
                if continue_feedback.upper()=='N': break
            else:
                print('Current threshold configurations for %s:'%account.replace("_"," "))
                print_thresholds(current_configuration)
        
        new_configuration=copy.deepcopy(current_configuration)
        
    else:
        print_thresholds(new_configuration)
        

    #Choose an action
    print('\nActions:')
    print_dict(update_options)
    action_read_success = False
    while not action_read_success:
        user_action, action_read_success=get_input('Enter desired action ID: ','int','Please choose a number [1-3]',
                                                    np.arange(len(update_options)+1).tolist())
    
    #PERFORM DESIRED ACTIONS
    
    #Update Active Flow
    if user_action==1:
        continue_updating_flows=True
        while continue_updating_flows:
            new_configuration=update_active_flow(new_configuration)
            continue_feedback_success=False
            while not continue_feedback_success:
                continue_feedback,continue_feedback_success=get_input('\nDo you wish to continue updating flows for %s? (Y/N):'%account,
                                                                      'str','Please enter Y or N',['Y','N','y','n'])
            if continue_feedback.upper()=='N':
                continue_updating_flows=False
    
    #Add New Flow
    if user_action==2:
        continue_adding_flows=True
        while continue_adding_flows:
            new_configuration=add_new_flow(new_configuration)
            continue_feedback_success=False
            while not continue_feedback_success:
                continue_feedback,continue_feedback_success=get_input('\nDo you wish to continue adding flows for %s? (Y/N):'%account,
                                                                      'str','Please enter Y or N',['Y','N','y','n'])
            if continue_feedback.upper()=='N':
                continue_adding_flows=False
    
    #Remove Flows
    if user_action==3:
        continue_removing_flows=True
        while continue_removing_flows:
            new_configuration=remove_active_flow(new_configuration)
            continue_feedback_success=False
            while not continue_feedback_success:
                continue_feedback,continue_feedback_success=get_input('\nDo you wish to continue removing flows for %s? (Y/N):'%account,
                                                                      'str','Please enter Y or N',['Y','N','y','n'])
            if continue_feedback.upper()=='N':
                continue_removing_flows=False
    
    print('TH for %s after modifications:'%account)
    print_thresholds(new_configuration) 
    
    #Continue updating flows?
    continue_feedback_success=False
    while not continue_feedback_success:
        continue_feedback,continue_feedback_success=get_input('\nDo you wish to continue updating/adding/removing flows for %s? (Y/N):'%account,
                                                                  'str','Please enter Y or N',['Y','N','y','n'])
        if continue_feedback.upper()=='N':
            update_configuration=False
            
    #Update the account's configuration file if any changes were made
    if (current_configuration!=new_configuration):
        update_configuration_file(account.replace(" ","_"),new_configuration)
        logging.info('Thresholds for %s were modified by user - %s'%(account,os.getlogin()))
        
print('****************************************THANK YOU AND GOODBYE :-)**************************************** ')

