from Atoms.Atom_date_range_extractor import DateRangeParser
from datetime import datetime
import pandas as pd

def test_basic_extractor():
    line = "June 11, 2016 to July 10, 2016"
    parser = DateRangeParser(line)
    first,second = parser.parse()
    assert first=="20160611"
    assert second=="20160710"
    
#def test_noyear():
    #no year mentioned, as per line 65
#    line = "June 21-July 11"
#    parser = DateRangeParser(line)
#    first,second = parser.parse()
#    assert first=="20160621"
    

def test_partial():
    #no day mentioned, as per line 74
    line = "March to June 2016"
    parser = DateRangeParser(line)
    first,second = parser.parse()
    assert first=="20160301"
    assert second=="20160630"
    
def test_short_year():
    #from line 4
    line="10 Jun 16 - 09 Jul 16"
    parser = DateRangeParser(line)
    first,second = parser.parse()
    assert first=="20160610"
    assert second=="20160709"
    
def test_failed_case():
    line="Bill Number: Unbilled Charges Bill Period 08/13/16 - 09/12/16"
    parser = DateRangeParser(line)
    first,second = parser.parse_several()[0]
    assert first=="20160813"
    assert second=="20160912"

def test_missing_year_this():
    cur_date = pd.to_datetime(datetime.now())
    cur_month=cur_date.month
    cur_year=cur_date.year
    cur_year_str=str(cur_year)
    if cur_month > 2:
        month_2=cur_month-2
        month_1=cur_month-1
        line=''.join([str(month_2)," 1-",str(month_1), " 28"])
        parser = DateRangeParser(line)
        first,second = parser.parse()
        assert first[:4]==cur_year_str
        assert second[:4]==cur_year_str
    else:
        assert True
        
def test_missing_year_prev():
    cur_date = pd.to_datetime(datetime.now())
    cur_month=cur_date.month
    cur_year=cur_date.year
    prev_year_str=str(cur_year-1)
    if cur_month < 10:
        month_2=cur_month+2
        month_1=cur_month+1
        line=''.join([str(month_1)," 1-",str(month_2), " 28"])
        parser = DateRangeParser(line)
        first,second = parser.parse()
        assert first[:4]==prev_year_str
        assert second[:4]==prev_year_str
    else:
        assert True
        
def test_missing_year_mixed():
    cur_date = pd.to_datetime(datetime.now())
    cur_month=cur_date.month
    cur_year=cur_date.year
    prev_year_str=str(cur_year-1)
    if cur_month < 12 and cur_month > 1:
        month_2=cur_month+1
        month_1=cur_month-1
        line=''.join([str(month_1)," 1-",str(month_2), " 28"])
        parser = DateRangeParser(line)
        first,second = parser.parse()
        assert first[:4]==prev_year_str
        assert second[:4]==prev_year_str
    else:
        assert True
    
def test_missing_year():
    cur_date = pd.to_datetime(datetime.now())
    #cur_month=cur_date.month
    cur_year=cur_date.year
    prev_year_str=str(cur_year-1)
    line="June 1-August 31"
    parser = DateRangeParser(line)
    first,second = parser.parse()
    assert first=="20160601"
    assert second=="20160831"
    assert prev_year_str==first[:4]
    
def test_maria():
    line="Maria 123"
    parser = DateRangeParser(line, verbose=4)
    first,second = parser.parse()
    assert first=="error"
    assert second=="error"
    
def test_several():
    line="Account: 6543210 BILLING PERIOD : 3/18/2016-4/17/2016 4/18/2016-5/17/2016"
    parser = DateRangeParser(line)
    date_lst = parser.parse_several()
    assert 3==len(date_lst)
    first_range=date_lst[0]
    second_range=date_lst[1]
    assert ('20160318', '20160417') == first_range
    assert ('20160418', '20160517') == second_range
    
def test_issue_from_qa1():
    desc='''
    Kindly facilitate data extraction request from bill period 3/27/2017-4/26/2017 and confirm if the charges were valid or not. 
    '''
    parser = DateRangeParser(desc)
    date_lst = parser.parse_several()
    assert 2==len(date_lst)
    first_range=date_lst[0]
    assert ('20170327', '20170426') == first_range
    
def test_issue_from_qa2():
    desc='''
    following dates: 3/26/17, 4/3/17 and 4/5/17, 
    '''
    parser = DateRangeParser(desc)
    date_lst = parser.parse_several()
    assert 3==len(date_lst)
    first_range=date_lst[0]
    assert ('error', 'error') == first_range

def test_missing_mon_year():
    line="27-29 June 2017"
    parser = DateRangeParser(line)
    date_lst = parser.parse_several()
    assert 2==len(date_lst)
    first_range=date_lst[0]
    assert ('20170627', '20170629') == first_range
    
def test_missinglinebreaks():
    line = "KarlLuther Juelar:  No Title For the Description:  Requestor Name : Jonalyn Alcala Requestor’s / group email / Alternate/Supervisor Email : N/A Requestor Phone :  N/A Location(Store Name/Call Center/Etc.): TechMahindra myBSS User ID: ztcm5247  MSISDN/BAN/PTN/Equipment info/FA ID/ORDER ID /ServiceID : 9178566518 Subscriber Name: Mark Oliver Molina Transaction/Order Type: Extraction of Roaming Data Charges Exact Error : N/A - The customer is complaining that they didn't use/open their cellular data on these following dates: 3/26/17, 4/3/17 and 4/5/17, but they were charged for Roam Surf 599. Advised customer will request for extraction of data roaming charges. This was already approved by my IS and Sir Anton Bonifacio. Kindly facilitate data extraction request from bill period 3/27/2017-4/26/2017 and confirm if the charges were valid or not. Please see the screenshot of the contested charges reflected on the bill.      Issue Details: For extraction of data roaming charges from bill period 3/27/2017-4/26/2017. This was already approved by my IS and Sir Anton Bonifacio. Date of Occurrence: 3/26/17 Users Impacted: 9178566518"
    parser = DateRangeParser(line)
    date_lst = parser.parse_several()
    assert 2==len(date_lst)
    first_range=date_lst[0]
    assert ('20170627', '20170629') == first_range 