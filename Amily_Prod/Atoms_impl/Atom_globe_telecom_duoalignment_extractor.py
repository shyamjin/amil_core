"""
EXTRACTOR FOR GLOBE'S DUO ALIGNMENT FLOW

i.e.: 123~4567~A89

"""

import re

class GlobeTelecomDuoalignmentExtractor:
    def __init__(self,
                 entity_name = 'MSISDN',
                 ):
        
        self.entity_name = entity_name        


    def parse_flow_entities(self, string, full_list, msisdn_list, duo_list):
        full_list.append(string)
            
        parsed_entity_list = string.split(",")
        msisdn = parsed_entity_list[0][2:]
        msisdn_list.append(str(msisdn))
        duo_number = parsed_entity_list[1][2:]
        duo_list.append(str(duo_number))
        
        return full_list, msisdn_list, duo_list
        
    def seperate_items_by_semicolon(self, res_list):
        activate_res_semi_colon = ""
        if res_list:
            for i in res_list:
                activate_res_semi_colon = activate_res_semi_colon+";"+i
            activate_res_semi_colon = [activate_res_semi_colon[1:]]
        return activate_res_semi_colon 
        
    def get_matches(self, doc):
        doc = doc["text"]        
        Deactivate_res = []
        Deactivate_msisdn_res = []
        Deactivate_duo_res = []
        Activate_res = []
        Activate_msisdn_res = []
        Activate_duo_res = []
        
        de_activate_regex = "639\d{9}\s{0,5},\s{0,5}63\d{7,11}\s{0,5},\s{0,5}[A-z]{1,15}\s{1,15}de.?activate"
        de_activatesearch_pattern = re.compile(de_activate_regex, re.MULTILINE|re.IGNORECASE)
        
        for p in de_activatesearch_pattern.finditer(doc):
            parsed_entity = re.sub("\s","",re.sub("(d|D)e.?(a|A)ctivate","",p.group()))
            Deactivate_res, Deactivate_msisdn_res,  Deactivate_duo_res = self.parse_flow_entities(parsed_entity, Deactivate_res, Deactivate_msisdn_res,  Deactivate_duo_res)
        
        activate_regex = "639\d{9}\s{0,5},\s{0,5}63\d{7,11}\s{0,5},\s{0,5}[A-z]{1,15}\s{1,15}activate"
        activatesearch_pattern = re.compile(activate_regex, re.MULTILINE|re.IGNORECASE)
        
        for p in activatesearch_pattern.finditer(doc):
            parsed_entity = re.sub("\s","",re.sub("(a|A)ctivate","",p.group()))
            Activate_res, Activate_msisdn_res,  Activate_duo_res = self.parse_flow_entities(parsed_entity, Activate_res, Activate_msisdn_res,  Activate_duo_res)
            
        
                      
        #Filter to only unique entities in the extraction list 
        
        Activate_res_semi_colon = self.seperate_items_by_semicolon(Activate_res)
        Deactivate_res_semi_colon = self.seperate_items_by_semicolon(Deactivate_res)
        
        Deactivate_dict = {"Deactivate":Deactivate_res_semi_colon}
        Activate_dict = {"Activate":Activate_res_semi_colon}
        Deactivate_msisdn_dict = {"MSISDN_Deactivation":Deactivate_msisdn_res}
        Deactivate_duo_dict = {"DUO_Deactivation":Deactivate_duo_res}
        Activate_msisdn_dict = {"MSISDN_Activation":Activate_msisdn_res}
        Activate_duo_dict = {"DUO_Activation":Activate_duo_res}
        
        return Deactivate_dict, Activate_dict, Deactivate_msisdn_dict, Deactivate_duo_dict, Activate_msisdn_dict, Activate_duo_dict    
    
#Script Tester
def main(argv):
    line = argv[0]
    extractor = GlobeTelecomDuoalignmentExtractor()
    res = extractor.get_matches(line)
    print(res)

if __name__== "__main__":   
   
    #sample = r"""please extract DM14O2186144;        1;1 hi please"""

    sample = r""""Alignment in AAM


639178360121,6322165229,NCR	Activate
639178909198,6322165229,NCR	Deactivate
	
639175707485,6325005772,NCR	Activate

639178380388,6325776341,NCR  Activate
    
    """
  
    doc = {"text":sample}      
    
    main([doc])
    