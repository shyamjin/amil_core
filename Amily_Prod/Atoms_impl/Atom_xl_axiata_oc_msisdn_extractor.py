"""
EXTRACT A AN MSISN NUMBER WITH DIGITS EMBEDDED IN IT

i.e.: 123~4567~A89

"""

import re

class XlAxiataOcMsisdnExtractor:
    def __init__(self,
                 entity_name = 'MSISDN',
                 base_extraction_regex = "([A-z]|(\s|\*|~|%|$|#|-){0,3})?",
                 exclusion_list = [],
                 exclusion_offset = 40, 
                 inclusion_offset = 40,
                 inclusion_list = []
                 ):
        
        self.entity_name = entity_name        
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

    def find_linebreak(self, document):
        '''
        Locates the last position of a line break within a document
        '''
        lb = re.compile("\n", re.MULTILINE|re.IGNORECASE)
        index = 0
        for p in lb.finditer(document):
            index = p.span()[1]
        return index
        
    def get_matches(self, doc):
        '''
        Input: doc - string containing description text
        Returns: Order Id and 2 digits seperated by ";"
        '''
        doc = doc["text"]        
        res = []
        
        for p in self.search_pattern.finditer(re.sub("\n"," ",doc)):
            start_pos, end_pos = p.span()
            found_exc = False
            found_inc = False
            
            #Seacrh through all exclusion list items and tag True if found in at least one of them
            for exc_pat in self.exclusion_pats:
                #The search space is offset 
                offset_potential = doc[max(start_pos-self.exclusion_offset,0):start_pos]
                exclusion_offset = self.exclusion_offset - self.find_linebreak(offset_potential)
                
                if exc_pat.search(doc[max(start_pos-exclusion_offset,0):start_pos]):      
                    found_exc = True

            #Seacrh through all inclusion list items and tag True if found in at least one of them
            if not self.inclusion_list:
                found_inc = True    
            else:
                for inc_pat in self.inclusion_pats:
                    offset_potential = doc[max(start_pos-self.inclusion_offset,0):start_pos]
                    inclusion_offset = self.inclusion_offset - self.find_linebreak(offset_potential)
                    if inc_pat.search(doc[max(start_pos-inclusion_offset,0):start_pos]):      
                        found_inc = True

            if (not found_exc) and found_inc:
                msisdn = p.group()
                if (msisdn[-2:-1] == " ") and (not msisdn[-1:].isnumeric()):
                    msisdn = msisdn[:-2]
                res.append(re.sub(" ","",msisdn))
                      
        #Filter to only unique entities in the extraction list 
        res_uniq = list(set(res))       
        dict = {self.entity_name:res_uniq}
        return dict
    
#Script Tester
def main(argv):
    line = argv[0]
    extractor = XlAxiataOcMsisdnExtractor(inclusion_list= ["MSISDN", "ms"],
                                     inclusion_offset= 100,
                                     exclusion_list= ["acd"],
                                     exclusion_offset= 50)
    res = extractor.get_matches(line)
    print(res)

if __name__== "__main__":   
   
    #sample = r"""please extract DM14O2186144;        1;1 hi please"""
    #sample = "Description:Order Number: DM14O19186101                                	         1	           MSISDN: 62-8787629531k"
    #sample = "Description:out cust berikut nama	: Renee Doenggio MSISDN	: 62817169988 Cancelled	: 4/3/201 MSISDN: 62817 0101 234"   
   
    
    sample = r"""
    Description: Complaint : Voice : OC Insufficient Balance

*** PHONE LOG 5/12/2017 10:13:31 AM lidaVADS1337 Action Type: Incoming call

dear team, please help this cust



nama: ibu prisila / bp rudy

acd: 62818939280

msisdn: 62818939258, 62818939259 ,62718939258, 62818925158

ms acd: 62818939250

ask/compl: 


    """
    

    doc = {"text":sample}      
    
    main([doc])
    