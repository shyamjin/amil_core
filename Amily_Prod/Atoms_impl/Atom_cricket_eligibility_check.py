"""
EXTRACT A 10 DIGIT PHONE NUMBERS FROM TEXT WITH CONDITIONS

Returnes a list of unique telephone numbers (TNs) from the found in the text.
In case where no TNs were extracted, an empty list is returned.
    
"""

import re

class CricketEligibilityCheck:
    def __init__(self,
                 entity_name = 'CTN'
                 ):
        self.entity_name = entity_name
        self.added_digits = 0
        self.phone_re = r"""(^|\D)(0?\d{3})-?(\d{3})-?(\d{1})-?(\d{3})-?(\d{,"""+str(self.added_digits)+"""})?(?=\D|$)""" 
        self.search_re=r"""(CTN|TN|Line|Phone\snumber)((:|\s|-|\d|,)*)"""
        
        self.phone_pattern = re.compile(self.phone_re,
                                        re.VERBOSE|re.MULTILINE|re.IGNORECASE)
        self.search_pattern = re.compile(self.search_re,
                                        re.VERBOSE|re.MULTILINE|re.IGNORECASE)
        

    def get_matches(self, doc):
        '''
        Input: doc - string containing description text
        Returns: list of strings, each one is a valid phone number
        '''
        doc = doc["text"]
        doc = re.sub("~|\*|%","",doc)
        res = []
        
        #In Summary search for all 10 digit numbers
        search_summary = doc[:doc.find("Description:")]
        for p in self.phone_pattern.finditer(search_summary):
            res.append(re.sub("[^0-9]", "",p.group()))
        
        #In Description search only 10 digit numbers that appears after CTN/TN/Line/Phone number phrases
        search_description = doc[doc.find("Description:"):]
        for k in self.search_pattern.finditer(search_description):
            text_to_search = k.group()
            for p in self.phone_pattern.finditer(text_to_search):
                res.append(re.sub("[^0-9]", "",p.group()))

        #Filter to only unique entities in the extraction list 
        res_uniq = list(set(res))
        #"Cleans" the phone number formats
        res_uniq = [s.replace('-',"") for s in res_uniq]      
           
        
        dict = {self.entity_name: res_uniq}
        return dict
    
#Script Tester
def main(argv):
    line = argv[0]
    extractor = CricketEligibilityCheck()                                     
    res = extractor.get_matches(line)
    print(res)

if __name__== "__main__":
    sample=r"""CTN : 1234567890         

Description:
                                                AMDOC can you please cancel eligibility check error for CTN : 4432619044, 123456789, 
andy
80010113 / kaz201
port 4432619041
By Belal Abou-Khraybe on 12/29/2017 1:10 PM
Notes: cancel elligibility check error

Customer First Name: 
Customer Last Name: 
CTN: 
BAN:443261904
4432619045
{CMI: MCID192757}"""
    #sample = "MSISDN: 6287876295318"
    doc = {"text":sample}      
    
    main([doc])
