import pandas as pd
import numpy as np
import copy

class GlobeTelecomSrmExtractionExtractor:
    def __init__(self):
        self.parameter_names = {"Request Type":"Request_Type",
                                "Resource Type":"Resource_Type",
                                "Resource":"Resource",
                                "Status":"Status",
                                "Category":"Category",
                                "Area Name":"Area_Name",
                                "Post / Pre":"Post_Pre",
                                "Date From":"Date_From",
                                "Date To:":"Date_To"
                                }
        return

    def append_values_to_parameter(self,result_list,parameter,value):
        extend_paramter_dict = False
        '''
        if result_list:
            for idx, parameter_dict in enumerate(result_list):
                if parameter in parameter_dict:
                    extend_paramter_dict=True
                    temp_dict = copy.deepcopy(parameter_dict)
                    temp_dict[parameter].extend([value])
                    result_list[idx]=temp_dict
        '''
        if not extend_paramter_dict:
            result_list.append({parameter:[value]})
        return result_list
        
    def get_matches(self, file_name):
        file_name = file_name["text"]
         
        result_list= []
        
        try:
            exc = pd.ExcelFile(file_name)
        except:
            return tuple(result_list)
              
        for s in exc.sheet_names:
            try:
                df = pd.read_excel(exc, sheetname=s)
                
                parameter_values = ["Request Type", "Resource Type", "Resource", "Status", "Category"
                          ,"Area Name", "Post / Pre", "Date From", "Date To:"]
                
                for parsed_value in parameter_values:
                    for idx, row in enumerate(df.values):
                        try:
                            if parsed_value in row:
                                index = np.where(row==parsed_value)[0][0]                                
                                result_list = self.append_values_to_parameter(result_list,self.parameter_names[parsed_value],
                                                                              row[index+1]) 
                        except:
                            pass                    
            except:
                continue
          
        result = tuple(result_list)
            
        return result


def main():
    #file_path = "vim cmilinutsaosiuat1:/UTSAmilyAttachments/UnProcessed/ASMM VS TC Aug 1, 2016.zip"
    file_path = "SRM Template - Copy.xlsx"
    
    extractor = GlobeTelecomSrmExtractionExtractor()
    data = {"text":file_path}
    res = extractor.get_matches(data)
    print(res)

if __name__== "__main__":
    result  = main()

