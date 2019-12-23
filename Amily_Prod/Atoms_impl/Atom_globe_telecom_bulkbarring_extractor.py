import pandas as pd
import zipfile
import re

class GlobeTelecomBulkbarringExtractor:
    def __init__(self,
                 file_entity_name = "FILE",
                 data_entity_name = "DATA",
                 file_name_format = r"""(^|/)CL9MASSTRX""",
                 file_format = ""
                ):
        self.file_entity_name = file_entity_name
        self.data_entity_name = data_entity_name
        self.file_name_format = file_name_format
        
    def get_file_name(self, path):
        path = path.replace('/','\\')
        
        extract_file_name_regex = r"""[ \w-]+\.(.+)"""
        search_pattern = re.compile(extract_file_name_regex)

        for p in search_pattern.finditer(path):
            file_name = p.group() 
        return file_name
    
    def validate_file_name_format(self, file_name):
        file_format_search_pattern = re.compile(self.file_name_format)
        if file_format_search_pattern.search(file_name):
            return True
        return False
    
    def bytes_to_string (self, doc):
        if type(doc) is bytes:
            doc = doc.decode('utf-8')
        return(doc)

    def get_matches(self, file_path):
        file_path = file_path["text"]
        file_dict = {self.file_entity_name:[]} 
        data_dict = {self.data_entity_name:[]}
        
        try:
            zipped_file = zipfile.ZipFile(file_path)
        except:
            pass
            
        try:
            zipped_file = zipfile.ZipFile(file_path)   
            for file in zipped_file.namelist():
                file_obj = zipped_file.open(file)
                file_name = file_obj.name
                file_name = self.get_file_name(file_name)
                if self.validate_file_name_format(file_name):
                    file_data = file_obj.read()
                    file_data = self.bytes_to_string(file_data)
                    file_dict[self.file_entity_name].append(file_name)
                    data_dict[self.data_entity_name].append(file_data)
        except:
            try:
                exc = open(file_path,'r')
                file_name = self.get_file_name(file_path)
                if not self.validate_file_name_format(file_name):
                    return file_dict, data_dict
                file_data = exc.read()
                file_data = self.bytes_to_string(file_data) 
                file_dict = {self.file_entity_name:[file_name]}
                data_dict = {self.data_entity_name:[file_data]}
            except:
                return file_dict, data_dict 
         
        return file_dict, data_dict


def main():  
    #file_path = "C:/Users/YanivAvr/Desktop/CL9MASSTRX_20171226_100001.zip"
    #file_path = "C:/Users/YanivAvr/Desktop/CL9MASSTRX_20171120_1430.input"
    file_path = "C:/Users/YanivAvr/Desktop/CL9MASSTRX_20171120_TRY.zip"
    
    extractor = GlobeTelecomBulkbarringExtractor()
    data = {"text":file_path}
    res = extractor.get_matches(data)
    print(res)

if __name__== "__main__":
    result  = main()

