import pandas as pd
import zipfile
import re

class AirtelIndiaPendingForActivationExtractor:
    def __init__(self,
                 entity_name = 'Mobile_No',
                 #var_name="File Identifier",  #The relevant column headers,
                 regex = r'''(^|\D)(7|8|9)\d{9}(\D|$)'''
                 ):
        self.entity_name = entity_name
        #self.var_name=var_name
        self.regex = regex
        self.regex_pat=re.compile(self.regex)
        
        #self.identity=lambda v:v
        #self.converters={self.var_name:self.identity}


    def get_matches(self, file_name):
        file_name = file_name["text"]
        result_list = []
        result_dict={self.entity_name:result_list}
        
        try:
            exc = pd.ExcelFile(file_name)
        except:
            return result_dict
              
        for s in exc.sheet_names:
            try:
                df = pd.read_excel(exc, 
                                   sheetname=s, 
                                   #skiprows=self.num_skip_rows,
                                   #converters=self.converters,
                                   #parse_dates=False
                                   )
                cur_columns = df.columns
                for col in cur_columns:
                    values_in_col=df[col].tolist()
                    for value in values_in_col:
                        if self.regex_pat.search(str(value)):
                            result_list.append(value)
            except:
                continue
            
        result_dict={self.entity_name:result_list}
            
        return result_dict


def main():
    #file_path = "vim cmilinutsaosiuat1:/UTSAmilyAttachments/UnProcessed/ASMM VS TC Aug 1, 2016.zip"
    file_path = "C:/Users/YanivAvr/Desktop/Book3.xlsx"
    
    extractor = AirtelIndiaPendingForActivationExtractor()
    data = {"text":file_path}
    res = extractor.get_matches(data)
    print(res)

if __name__== "__main__":
    result  = main()

