"""
EXTRACT A AN MSISN NUMBER WITH DIGITS EMBEDDED IN IT

i.e.: 123~4567~A89

multiple_values = true if you want to extract all numbers and false if you want to extract just the first one
"""

import re

class XlAxiataMsisdnExtractor:
    def __init__(self,
                 entity_name = 'MSISDN',
                 base_extraction_regex = "([A-z]|(\s|\*|~|%|$|#|-){0,3})?",
                 exclusion_list = [],
                 exclusion_offset = 40, 
                 inclusion_offset = 40,
                 inclusion_list = [],
                 multiple_values=True
                 ):
        
        self.entity_name = entity_name
        self.multiple_values = multiple_values
        self.base_extraction_regex = base_extraction_regex
        self.extraction_regex = r"""\b0?0?0?62"""+self.base_extraction_regex
        
        for i in range(5):
            self.extraction_regex+= r"""\d"""+self.base_extraction_regex 
        
        for i in range(5):
            self.extraction_regex+= r"""\d?"""+self.base_extraction_regex 
        
        #self.extraction_regex+=r"""\b"""
        self.extraction_regex+=r"""\d?"""
        
        self.search_pattern = re.compile(self.extraction_regex, re.MULTILINE|re.IGNORECASE)
        
        self.exclusion_offset=exclusion_offset
        self.exclusion_list=exclusion_list        
        self.exclusion_pats = []
        for exc in self.exclusion_list:
            self.exclusion_pats.append(re.compile(exc, re.IGNORECASE))        
        
        self.inclusion_list=inclusion_list
        self.inclusion_offset=inclusion_offset  
        self.inclusion_pats = []
        for exc in self.inclusion_list:
            self.inclusion_pats.append(re.compile(exc, re.IGNORECASE))       

    def get_matches(self, doc):
        '''
        Input: doc - string containing description text
        Returns: MSISDN number, only the first one
        '''
        doc = doc["text"]        
        res = []
        
        for p in self.search_pattern.finditer(re.sub("\n","@",doc)):
            start_pos, end_pos = p.span()
            found_exc = False
            found_inc = False
            
            #Seacrh through all exclusion list items and tag True if found in at least one of them
            for exc_pat in self.exclusion_pats:
                if exc_pat.search(doc[max(start_pos-self.exclusion_offset,0):start_pos]):      
                    found_exc = True
                    
            #Seacrh through all inclusion list items and tag True if found in at least one of them
            if not self.inclusion_list:
                found_inc = True    
            else:
                for inc_pat in self.inclusion_pats:
                    if inc_pat.search(doc[max(start_pos-self.inclusion_offset,0):start_pos]):      
                        found_inc = True
            
            if (not found_exc) and found_inc:
                msisdn = p.group()
                if (msisdn[-2:-1] == " ") and (not msisdn[-1:].isnumeric()):
                    msisdn = msisdn[:-2]
                res.append(str(re.sub(" ","",msisdn)))
        #print("res=", res)
        
        for index,number in enumerate(res):
            res[index] = res[index].replace("-","")
    
        #print("res_uniq,self.multiple_values,res_uniq[0],res_uniq[1], len(res_uniq) = \n",res_uniq,", ",self.multiple_values,", ",res_uniq[0],", ",res_uniq[1],", ",len(res_uniq))
        #returns the first MSISDN number found in the text, (needed because the list is in reversed order)
        if (not res):
            
            dict = {self.entity_name:[]}
        elif (self.multiple_values == True):
            #Filter to only unique entities in the extraction list, pay attention that 'set' returns an unordered list, with a new random order
            res_uniq = list(set(res)) 
            #print("res_uniq=", res_uniq)
            dict = {self.entity_name:res_uniq}
        elif self.multiple_values == False:
            #dict = {self.entity_name:res_uniq[0]}
            dict = {self.entity_name:res[0]}
            
        
        return dict
    
    #parameter - multiple values - true/false
    
#Script Tester
def main(argv):
    #Maya 4.1.18 - Previously there was "Description:" in the inclusion list, I removed it
    line = argv[0]
    extractor = XlAxiataMsisdnExtractor(inclusion_list=["msdn","msisdn","nomor","User Name"],
                                    inclusion_offset=40,
                                    multiple_values=False
                                    #exclusion_list = ["msisdn"]
                                    )
    res = extractor.get_matches(line)
    print(res)

if __name__== "__main__":   
   
    #sample = r"""please extract DM14O2186144;        1;1 hi please"""
    #sample = "Description:Order Number: DM14O19186101                                	         1	           MSISDN: 62-8787629531k"
    #sample = "Description:out cust berikut nama	: Renee Doenggio MSISDN	: 62817169988 Cancelled	: 4/3/201 MSISDN: 62817 0101 234"   
   
    #sample = "MSISDN : 8170125000"
    r"""
    Description: Complaint : Data Service : Quota Not Update
*** PHONE LOG 15/12/2017 09:55:08 Fir1335 Action Type: Incoming call
nama : edi 
nomor : 6200000000003 6200000000005 6200000000002 6200000000001 6200000000000
soc_cd : 513804354

3. Type HP : Xiaomi Redmi 4A
6287854626669
4. Time frame = 2-Jan-2018

8. Lampirkan call detail :
Party Number    Call Date/Time    Event Type    Service Type    Units    Unit Rounded    Rated Amount    Bal. Monetary    Bal. SMS    Free Units    Discount Amt.    Cell ID    Country    Discount Val.    
081238383951    2017-12-15 06:32:21    Voice Outgoing    N    240    0    447.00    1653.00    0.00    0.00    0.00    510.11.35538.54163    INDONESIA    0    

MSISDN    Product Name    Product ID    Registration Date     Bucket Type    Bucket ID    Bucket Description    Total Quota    Used Quota    Remaining Quota    
6283870462627    BRONET 24Jam 3GB 60hr    513786874    2017-11-08T11:51:37+07:00    INTERNET                        
    """
    #sample = "User Name : +62 878-3511-1122"
    doc = {"text":sample}      
    
    main([doc])
    
