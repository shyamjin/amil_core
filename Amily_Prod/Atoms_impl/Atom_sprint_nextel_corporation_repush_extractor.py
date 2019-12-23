"""
EXTRACT A AN ORDER ID AND 2 DIGITS SEPERATED BY ";"

i.e.: dm14O32769941,6,5 will be extracted as dm14O32769941;6;5
order id and digits could be seperated by tab, comma and/or spaces
Order ID format is defined in the regex.

"""

import re

class SprintNextelCorporationRepushExtractor:
    def __init__(self,
                 entity_name = 'Order_ID',
                 extraction_regex = "((COM\d)|(DM\d{2}))-?O-?\d{6}\d?\d?\D(|;|\t|,|)((\s){0,50}?)\d(;|\t|,|)((\s){0,50}?)\d",
                 remove_char = "(-|(;|\t|,|)((\s){0,10}))",
                 upper_case = False
                 ):
        
        self.entity_name = entity_name        
        self.extraction_regex = extraction_regex
        self.search_pattern = re.compile(self.extraction_regex,
                                        re.VERBOSE|re.MULTILINE|re.IGNORECASE)
                                        
        self.remove_char = remove_char
        self.upper_case = upper_case


    def get_matches(self, doc):
        '''
        Input: doc - string containing description text
        Returns: Order Id and 2 digits seperated by ";"
        '''
        
        doc = doc["text"]
       
        res = []
        
        for p in self.search_pattern.finditer(doc):
            extract = re.sub(self.remove_char,"",p.group().upper())
            extract = extract[:-2]+";"+extract[-2:-1]+";"+extract[-1:]
            res.append(extract)
                      
        #Filter to only unique entities in the extraction list 
        res_uniq = list(set(res))       
        dict = {self.entity_name:res_uniq}
        return dict
    
#Script Tester
def main(argv):
    line = argv[0]
    extractor = SprintNextelCorporationRepushExtractor()
    res = extractor.get_matches(line)
    print(res)

if __name__== "__main__":   
    
    '''
    sample = r"""
    VALID - DM14O32769940   1,  1 dm14O32769941,6,5 ; DM14O32769943,1,1
NOT VALID - DM14O32769950, DM14O32769951, 1, 1
"""
    '''
    #sample = r"""please extract DM14O2186144;        1;1 hi please"""
    sample = "Order Number: DM14O19186101                                	         1	           1"
    doc = {"text":sample}      
    
    main([doc])
    