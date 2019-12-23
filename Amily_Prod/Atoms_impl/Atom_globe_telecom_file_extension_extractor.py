"""Capture extension type of an attachment.

User supplies:
  - entity name

"""

import os

DEBUG = False  # Used for debugging the code ONLY!


class GlobeTelecomFileExtensionExtractor:
    def __init__(self, entity_name):
        self.entity_name = entity_name

    def get_matches(self, file_name):
        file_name = file_name["text"]
        result_list = []
        result_dict = {self.entity_name: result_list}

        try:
        
            ext2 = os.path.splitext(file_name)[1]
            ext = ext2.rpartition('.')[-1]
            output = ext
            result_list.append(output)
                        
        except Exception as exp:
            print(exp)

        result_dict = {self.entity_name: result_list}

        return result_dict


def main():
    file_path = "C:/Users/neilangr/Documents/Yashika/Data Labelling/entity-extraction-KT/SR00072152_Approval.docx"
    file_path = "C:/Users/sumitsah/sumit/atomIQ-NLP-Training/GLOBE/Somesh/neil-20-12-18/test.test.xlsx"
    # file_path = "C:/Users/sumitsah/sumit/atomIQ-NLP-Training/GLOBE/Somesh/neil-20-12-18/test_test.txt"
    # file_path = "C:/Users/sumitsah/sumit/atomIQ-NLP-Training/GLOBE/Somesh/neil-20-12-18/test_doc.docx"
    file_path = "C:/Users/sumitsah/sumit/atomIQ-NLP-Training/GLOBE/Somesh/neil-20-12-18/test.pdf"
    file_path = "C:/Users/sumitsah/sumit/atomIQ-NLP-Training/GLOBE/Somesh/neil-20-12-18/test.csv"
    extractor = GlobeTelecomFileExtensionExtractor( entity_name="Attachment_Type")
    data = {"text": file_path}
    res = extractor.get_matches(data)
    print(res)

if __name__== "__main__":
    result  = main()

