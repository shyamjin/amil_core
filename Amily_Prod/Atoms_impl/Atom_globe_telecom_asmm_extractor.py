import pandas as pd
import zipfile


class GlobeTelecomAsmmExtractor:
    def __init__(self,
                 entity_name = 'File_Indentifier',
                 var_name="File Identifier",  #The relevant column headers
                 num_skip_rows=5):
        self.entity_name = entity_name
        #self.file_name = file_name
        self.var_name=var_name
        self.num_skip_rows=5 #Skips the first 5 rows on each worksheet (in the relevant sheet we saw that it should be skipped)
        self.identity=lambda v:v
        self.converters={self.var_name:self.identity}
        
    def get_ids_from_dataframe(self, df):
        return [''+str(val)+'' for val in df[self.var_name].tolist() if pd.notnull(val)]

    def get_matches(self, file_name):
        file_name = file_name["text"]
        
        try:
            zipped_file = zipfile.ZipFile(file_name)
        except:
            pass
            
        try:
            zipped_file = zipfile.ZipFile(file_name)    
            file_obj = zipped_file.open(zipped_file.namelist()[0])
            exc = pd.ExcelFile(file_obj)
        except:
            try:
                exc = pd.ExcelFile(file_name)
            except:
                return {self.entity_name:[]}                
        
        #exc = pd.ExcelFile(self.file_name) #To be used when reading an excel file and not a zip file
        
        for s in exc.sheet_names:
            try:
            #Having issues with colums that have dates in them, they are not correctly parsed. For now - being ignored
                df = pd.read_excel(exc, 
                                   sheetname=s, 
                                   skiprows=self.num_skip_rows,
                                   converters=self.converters,
                                   parse_dates=False)
            except:
                continue
            
            cur_columns = df.columns
            if self.var_name in cur_columns:
                dict = {self.entity_name:self.get_ids_from_dataframe(df)}
                return dict
        
        dict = {self.entity_name:[]}
        return dict


def main():
    #file_path = "vim cmilinutsaosiuat1:/UTSAmilyAttachments/UnProcessed/ASMM VS TC Aug 1, 2016.zip"
    file_path = "/prjvl01/Amily_Train/Attachments/ASMM VS TC Aug 1, 2016.zip"
    
    extractor = GlobeTelecomAsmmExtractor()
    data = {"text":file_path}
    res = extractor.get_matches(data)
    print(res)

if __name__== "__main__":
    result  = main()

