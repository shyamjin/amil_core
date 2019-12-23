This Directory holds all entity extractor atoms.
Some atoms are highly generic (Regex, Date, etc.) and some are flow-in-account-specific (Atom_globe_asmm_extractor)

-- DO NOT CHANGE FILES NAMES --

IMPORTANT:
1. File names should always start with "Atom_" followed by words seperated by an underline charcter ("_").
2. The class name of each atom should correspond to the file name in the following manner:
	2.1. File name = "Atom_this_is_the_extractor_name"
	2.2. Class name = "ThisIsTheExtrcatorName"
	Capital letters and no spaces on the class name and underline on the file name are mandatory.
3. Each Atom is required to have a "get_matches" method in it's extractor class. This method should receive a textual document and return a dictionary/tupel of parsed flow parameters.