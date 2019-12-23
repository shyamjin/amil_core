import pandas as pd
import zipfile

class AirtelIndiaP2pIdCreationExtractor:
    def __init__(self):
        self.column_synonyms = {"OLMS/HRMS ID":["OLMS ID","User ID"],
                                "USER_NAME":["NAME","First Name","User Name"],
                                "USER_MOBILE":["MOBILE NO","Mobile Number","USER MOBILE"],
                                "USER_EMAIL":["EMAIL ID","E Mail ID","USER EMAIL"],
                                "CIRCLE_NAME":["CIRCLE NAME"],
                                "USER_ROLE":["USER ROLE"],
                                "Temporary ( Yes / No)":["Temporary"],
                                "Start Date (If Yes)":["Start Date"],
                                "End Date (If Yes)":["End Date"],
                                }
        return
        
    def fetch_column_values(self,df,header):
        try:
            value_dict = {header.replace(" ","_"):df[header].tolist()} 
        except:
            value_dict = {header.replace(" ","_"):[]}
        return value_dict
        
    def get_matches(self, file_name):
        file_name = file_name["text"]
        parsing_tuple=()
        
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
                return parsing_tuple              
        
        #exc = pd.ExcelFile(self.file_name) #To be used when reading an excel file and not a zip file
        
        for s in exc.sheet_names:
        #Assuming that the data is found in ONLY one of the worksheets
            try:
            #Having issues with colums that have dates in them, they are not correctly parsed. For now - being ignored
                df = pd.read_excel(exc, 
                                   sheetname=s
                                   )
            except:
                continue
            
            
            #Allign Column headers names as expected in format - seacrh for synonyms
            df_cols = df.columns.values.tolist()
            for key, value in self.column_synonyms.items():
                for idx, col_header in enumerate(df_cols):
                    if col_header in value:
                        df_cols[idx] = key

            new_cols = dict(zip(df.columns.values, df_cols))
            df = df.rename(columns = new_cols)
            
            if 'USER_NAME' in df.columns.values:      
                #OLMS/HRMS_ID, USER_NAME, USER_MOBILE, USER_EMAIL,CIRCLE_NAME, USER_ROLE, Temporary, Start_Date, End_Date
                OLMS_HRMS_ID_dict=self.fetch_column_values(df,'OLMS/HRMS ID')
                USER_NAME_dict=self.fetch_column_values(df,'USER_NAME')
                USER_MOBILE_dict=self.fetch_column_values(df,'USER_MOBILE')
                USER_EMAIL_dict=self.fetch_column_values(df,'USER_EMAIL')
                CIRCLE_NAME_dict=self.fetch_column_values(df,'CIRCLE_NAME')
                USER_ROLE_dict=self.fetch_column_values(df,'USER_ROLE')
                Temporary_dict=self.fetch_column_values(df,'Temporary ( Yes / No)')
                Start_Date_dict=self.fetch_column_values(df,'Start Date (If Yes)')
                End_Date_dict=self.fetch_column_values(df,'End Date (If Yes)')
           
                parsing_tuple = (OLMS_HRMS_ID_dict,
                                 USER_NAME_dict,
                                 USER_MOBILE_dict,
                                 USER_EMAIL_dict,
                                 CIRCLE_NAME_dict,
                                 USER_ROLE_dict,
                                 Temporary_dict,
                                 Start_Date_dict,
                                 End_Date_dict)
                
            
        return parsing_tuple


def main():
    #file_path = "vim cmilinutsaosiuat1:/UTSAmilyAttachments/UnProcessed/ASMM VS TC Aug 1, 2016.zip"
    file_path = "../Attachments/P2P ID Creation/P2P_ID_Creation2_INC000002135004.xls.xlsx"
    #file_path ="./P2P_ID_Creation4_INC000002189689.xls.xlsx"
    
    extractor = AirtelIndiaP2pIdCreationExtractor()
    data = {"text":file_path}
    res = extractor.get_matches(data)
    print(res)

if __name__== "__main__":
    result  = main()

