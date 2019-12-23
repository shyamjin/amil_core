import pandas as pd

class AirtelIndiaOptimaOldInvExtractor:
    def __init__(self,
                 entity_name = 'Regex',
                 column_synonyms = {"Invoice No":None, "Date":None}):
        self.entity_name=entity_name
        self.column_synonyms=column_synonyms
        return
        
    def fetch_column_values(self,df,header):
        try:
            value_dict = {header.replace(" ","_"):df[header].tolist()} 
        except:
            value_dict = {header.replace(" ","_"):[]}
        return value_dict
        
    def get_matches(self, file_name):
        file_name = file_name["text"]
        result_list=[]
        result_dic={self.entity_name:result_list}
        try:
            exc = pd.ExcelFile(file_name)
        except Exception as exp:
            print(exp)
            return result_dic
        for s in exc.sheet_names:
            try:
                df = pd.read_excel(exc, sheet_name=s)
            except:
                continue            
            df_cols = df.columns.values.tolist()
            for key, value in self.column_synonyms.items():
                for idx, col_header in enumerate(df_cols):
                    if col_header.upper() in value:
                        df_cols[idx] = key
            new_cols = dict(zip(df.columns.values, df_cols))
            df = df.rename(columns = new_cols)
        
            if 'Invoice No' in df.columns.values:      
                invoice_no_dict=self.fetch_column_values(df,'Invoice No')
                date_dict=self.fetch_column_values(df,'Date')
                data = (invoice_no_dict,date_dict)
                df['Date']=df['Date'].dt.strftime('%d-%m-%Y')
                df[self.entity_name] = df["Invoice No"].map(str)+"_"+df["Date"].map(str) 
                result_list = df[self.entity_name].tolist()

        result_dict = {self.entity_name: result_list}

        return result_dict

def main():
    file_path = "airtel.xlsx"
    # file_path = "Airtel_India_parsing.json"  it would generate exception and return empty result
    entity_name = 'inv_dt'
    column_synonyms = {"Invoice No":["INVOICE","INV","INV_NO","INVOICE_NUMBER","INVOICE_NO","INVOICE_NUM","INV_NUM","INV NO","INVOICE NUMBER","INVOICE NO","INVOICE NUM","INV NUM"],
                       "Date":["INV_DATE","INV DATE","MONTH & YEAR","INVOICE_DATE","INVOICE DATE","DATE","INVOICE DT","INVOICE_DT","INV_DT","INV DT","DATES","INVOICE_DATES","INVOICE DATES"]
                      }
    extractor = AirtelIndiaOptimaOldInvExtractor(entity_name,column_synonyms)
    file = {"text":file_path}
    res = extractor.get_matches(file)
    print(res)

if __name__== "__main__":
    result  = main()
