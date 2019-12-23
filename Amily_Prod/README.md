This Directory holds all files and directories required for the Amily web service to run and function properly on the production servers.
Please review the Amily architecture on the "Amily Project Control Workbook.xlsx" file ("Amily Code Architecture" worksheet).
-- DO NOT CHANGE FILES OR DIRECTORIES NAMES --

1. Amily_web_service.py - The Amily tornado-based web service file. This is the file that is being run once the amily service is activated on the production servers.
2. Amily_web_service.ipynb - The Amily web service notebook file, for dev. and testing purposes.
3. Atoms Directory - Holds entity extrator atoms.
4. Classification Directory - Holds the basic NLTK-based text preprocessor and Item selector classes, required for any text preprocessing as a preliminary stage for ticket classification.
5. Configuration Directory - Holds parsing and thresholds configuration files for each Amily-active account.
6. Logs Directory - Holds the amily log file. could be empty.
7. Pickles Directory - Holds trained classification models in the form of .pkl files for each Amily-active account and ticket type(internal/external).
8. SSL Directory - Holds secuirty configuration files - certificate and key for SSL protocl and password file for authrization mechanism.