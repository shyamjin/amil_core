#Returns True if a valid attachment is found
class UsCellularCorporationPrepaidRegistrationExtractor:
    def __init__(self,
                 entity_name="Attachment",
                 attachment_dir = "UTSAmilyAttachments"):
        self.entity_name = entity_name
        self.attachment_dir = attachment_dir
        
    def get_matches(self, file_path):
        if str(self.attachment_dir) in file_path['text']:
            return_dict = {self.entity_name:[None]}
        else:
            return_dict = {self.entity_name:[False]} 
        return return_dict


def main():  
    file_path = "C:/Users/YanivAvr/Desktop/CL9MASSTRX_20171120_TRY.zip"
    
    extractor = UsCellularCorporationPrepaidRegistrationExtractor()
    data = {"text":file_path}
    res = extractor.get_matches(data)
    print(res)

if __name__== "__main__":
    result  = main()

