"""
Workflow processor

Functions
    parse_data_file
"""

import os
import pandas as pd

import lib_platefunctions as pf

#####    ####   #####    #####  ######    ######  ##  ##      ######
##  ##  ##  ##  ##  ##  ##      ##        ##      ##  ##      ##
#####   ######  #####    ####   ####      ####    ##  ##      ####
##      ##  ##  ##  ##      ##  ##        ##      ##  ##      ##
##      ##  ##  ##  ##  #####   ######    ##      ##  ######  ######

def parese_data_file(data_rules, str_FilePath):
    """
    Takes raw data file parsing rules (as pandas dataframe) and file path of raw data file to parse (as string)
    and builds a data frame.

    Arguments:
        data_rules
        str_FilePath
    
    Returns pandas dataframe "dfr_RawData" and boolean value for success of parsing.
    """

    # Make it easy on yourself, read out rules into shorter to write variables ######################################################################
    # Data File Parsing
    str_Extension = data_rules["Extension"]
    str_FileType = data_rules["FileType"]
    str_Engine = data_rules["Engine"]
    str_Worksheet = data_rules["Worksheet"]
    # File verification
    bool_Verification = data_rules["UseVerificationKeyword"]
    if bool_Verification == True:
        str_VerificationKeyword = data_rules["Verification"]["Keyword"]
        int_VerificationAxis = int(data_rules["Verification"]["Axis"]) 
        int_VerificationRow = int(data_rules["Verification"]["Row"])
        int_VerificationColumn = int(data_rules["Verification"]["Column"])
        bool_ExactVerificationKeyword = data_rules["Verification"]["Exact"]

    # Get the first read ############################################################################################################################
    if str_FileType == "csv" or str_FileType == "txt":
        print("Trying to parse CSV or TXT file.")
        try:
            dfr_ParsedDataFile = pd.read_csv(str_FilePath, sep=None, header=None, index_col=False, engine=str_Engine)
        except:
            # Couldn't parse, return empty dataframe and no success
            return pd.DataFrame(), False
        print("Successfully parsed a CSV or TXT file.")
    elif str_FileType[0:3] == "xls":
        print("Trying to parse XLS or XLSX file.")
        try:
            dfr_ParsedDataFile = pd.read_excel(str_FilePath, sheet_name=str_Worksheet, header=None, index_col=None, engine=str_Engine)
        except:
            # Couldn't parse, return empty dataframe and no success
            return pd.DataFrame(), False
        print("Successfully parsed a XLS or XLSX file")
    print("Shape: " + str(dfr_ParsedDataFile.shape[0]) + " by " + str(dfr_ParsedDataFile.shape[1]))

    # Verify whether we're dealing with a valid data file ###########################################################################################
    if bool_Verification == True:
        bool_Verified = False
        # Trawl file for specified keyword in specified column
        if int_VerificationAxis == 0:
            for idx in dfr_ParsedDataFile.index:
                # Make sure we actually only look at strings:
                var_Cell = str(dfr_ParsedDataFile.loc[idx, int_VerificationColumn])
                bool_Verified = Verification(var_Cell, str_VerificationKeyword, bool_ExactVerificationKeyword)
                if bool_Verified == True:
                    break
        elif int_VerificationAxis == 1:
            for col in dfr_ParsedDataFile.columns:
                # Make sure we actually only look at strings:
                var_Cell = dfr_ParsedDataFile.loc[int_VerificationRow, col]
                bool_Verified = Verification(var_Cell, str_VerificationKeyword, bool_ExactVerificationKeyword)
                if bool_Verified == True:
                    break
        # If keyword is NOT found:
        if bool_Verified == False:
            print("could not verify file")
            # Couldn't parse, return empty dataframe and no success
            return pd.DataFrame(), False

    # Continue writing rules to variables ###########################################################################################################
    # 
    str_PlateOrSample = data_rules["PlateOrSample"]
    if str_PlateOrSample == "Plate":
        int_Wells = data_rules["AssayPlateFormat"]
    
    str_GridOrTable = data_rules["GridOrTable"]

    # First dataset
    bool_DatasetKeyword = data_rules["UseDatasetKeyword"]
    bool_ExactDatasetKeyword = data_rules["ExactDatasetKeyword"]
    str_DatasetKeyword = data_rules["DatasetKeyword"]
    int_DatasetKeywordRow = data_rules["DatasetKeywordRow"]
    int_DatasetKeywordColumn = data_rules["DatasetKeywordColumn"]
    tpl_DatasetKeywordOffset = data_rules["DatasetKeywordOffset"]
    tpl_DatasetCoordinates = data_rules["DatasetCoordinates"]
    
    # Multiple datasets
    bool_MultipleDatasets = data_rules["MultipleDatasets"]
    int_DatasetAxis = int(data_rules["DatasetAxis"])
    int_Datasets = int(data_rules["NumberMultipleDatasets"])
    str_NewDatasetSeparator = data_rules["NewDatasetSeparator"]
    if str_NewDatasetSeparator == "SameAsMain":
        str_NewDatasetKeyword = str_DatasetKeyword
        bool_ExactNewDatasetKeyword = bool_ExactDatasetKeyword
        int_NewDatasetKeywordColumn = int_DatasetKeywordColumn
        tpl_NewDatasetKeywordOffset = tpl_DatasetKeywordOffset
    elif str_NewDatasetSeparator == "Keyword":
        str_NewDatasetKeyword = data_rules["NewDatasetKeyword"]
        bool_ExactNewDatasetKeyword = bool_ExactDatasetKeyword
        int_NewDatasetKeywordColumn = data_rules["NewDatasetKeywordColumn"]
        tpl_NewDatasetKeywordOffset = data_rules["NewDatasetKeywordOffset"]
    elif str_NewDatasetSeparator == "SetDistance":
        tpl_NewDatasetOffset = data_rules["NewDatasetOffset"]

    # Sub-Datasets
    bool_SubDatasets = data_rules["UseSubDatasets"]
    int_SubDatasets = int(data_rules["NumberSubDatasets"])
    int_SubDatasetAxis = int(data_rules["SubDatasetAxis"])
    str_SubDatasetSeparator = data_rules["SubDatasetSeparator"]
    if str_SubDatasetSeparator == "SameAsMain":
        if bool_DatasetKeyword == True:
            str_SubDatasetKeyword = data_rules["DatasetKeyword"]


    # Start looking at files ########################################################################################################################
    dfr_DatasetCoordinates = pd.DataFrame(index=[0],columns=[0])
    # First step: Identify datasets and sub-datasets
    print("Dataset axis: " + str(int_DatasetAxis))
    lst_Coordinates = []
    # Find index of first dataset
    # First case: Keywords
    if bool_DatasetKeyword == True:
        if int_DatasetAxis == 0:
            lst_Coordinates.append(FindKeywordVertically(dfr_ParsedDataFile, 0, int_DatasetKeywordColumn, str_DatasetKeyword,
                                bool_ExactDatasetKeyword))
        elif int_DatasetAxis == 1:
            lst_Coordinates.append(FindKeywordHorizontally(dfr_ParsedDataFile, 0, int_DatasetKeywordRow, str_DatasetKeyword,
                                bool_ExactDatasetKeyword))
    # Continue if we have multiple datasets:
    if bool_MultipleDatasets == True:
        print("Multiple datasets")
        # Branch for different separators:
        if str_NewDatasetSeparator == "Keyword" or (str_NewDatasetSeparator == "SameAsMain" and bool_DatasetKeyword == True):
            print("First dataset: by keyword")
            if int_DatasetAxis == 0:
                lst_Coordinates += FindKeywordsVertically(dfr_ParsedDataFile, dfr_DatasetCoordinates.iloc[0,0]+1, int_DatasetKeywordColumn,
                                                    str_NewDatasetKeyword, bool_ExactDatasetKeyword,dfr_ParsedDataFile.shape[int_DatasetAxis]-1)
            elif int_DatasetAxis == 1:
                lst_Coordinates += FindKeywordsHorizontally(dfr_ParsedDataFile, dfr_DatasetCoordinates.iloc[0,0]+1, int_DatasetKeywordRow,
                                                    str_NewDatasetKeyword, bool_ExactDatasetKeyword,dfr_ParsedDataFile.shape[int_DatasetAxis]-1)
        elif str_NewDatasetSeparator == "SetDistance":
            print("Further dataset: by fixed offset")
            # For this one, we create a completely new dataframe instead of merging with the old one.
            if int_DatasetAxis == 0:
                int_NewRow = lst_Coordinates[0] + tpl_NewDatasetOffset[int_DatasetAxis]
                while int_NewRow < dfr_ParsedDataFile.shape[int_DatasetAxis]:                    
                    print(int_NewRow)
                    lst_Coordinates.append(int_NewRow)
                    int_NewRow += tpl_NewDatasetOffset[0]
            elif int_DatasetAxis == 1:
                int_NewCol = lst_Coordinates[0] + tpl_NewDatasetOffset[int_DatasetAxis]
                while int_NewCol < dfr_ParsedDataFile.shape[int_DatasetAxis]:                    
                    print(int_NewCol)
                    lst_Coordinates.append(int_NewCol)
                    int_NewCol += tpl_NewDatasetOffset[int_DatasetAxis]
    dfr_DatasetCoordinates = pd.DataFrame(index=range(len(lst_Coordinates)),columns=[0],data=lst_Coordinates)
    
    # Do we have sub-datasets?
    if bool_SubDatasets == True:
        print("Sub-datasets")
        print("Sub-dataset axis: " + str(int_SubDatasetAxis))
        dfr_SubDatasetCoordinates = pd.DataFrame(index=dfr_DatasetCoordinates.index)
        # Branch for different separators:
        # Keyword separator
        print("Sub-dataset separator: " + str_SubDatasetSeparator)
        if str_SubDatasetSeparator == "Keyword" or (str_SubDatasetSeparator == "SameAsMain" and bool_DatasetKeyword == True):
            print("Sub-dataset keyword: " + str_SubDatasetKeyword )
            # Branch for axis:
            if int_SubDatasetAxis == 0:
                for idx in dfr_DatasetCoordinates.index:
                    lst_SubDatasetCoordinates = []
                    int_StartRow = dfr_DatasetCoordinates.loc[idx,0] + 1
                    lst_SubDatasetCoordinates += FindKeywordsVertically(dfr_ParsedDataFile, int_StartRow,
                                                                        int_DatasetKeywordColumn, str_SubDatasetKeyword,
                                                                        bool_ExactDatasetKeyword, dfr_DatasetCoordinates.loc[idx,0]-1)
                    # Enlarge dataframe if necessary:
                    if len(lst_SubDatasetCoordinates) > dfr_SubDatasetCoordinates.shape[1]:
                        dfr_SubDatasetCoordinates = dfr_SubDatasetCoordinates.reindex(columns=range(len(lst_SubDatasetCoordinates)))
                    dfr_SubDatasetCoordinates.loc[idx] = lst_SubDatasetCoordinates
            elif int_SubDatasetAxis == 1:
                for idx in dfr_DatasetCoordinates.index:
                    lst_SubDatasetCoordinates = []
                    int_StartCol = dfr_DatasetCoordinates.loc[idx,0] + 1
                    lst_SubDatasetCoordinates += FindKeywordsHorizontally(dfr_ParsedDataFile, int_StartCol,
                                                                        int_DatasetKeywordRow, str_SubDatasetKeyword,
                                                                        bool_ExactDatasetKeyword, dfr_DatasetCoordinates.loc[idx,0]-1)
                    # Enlarge dataframe if necessary:
                    if len(lst_SubDatasetCoordinates) > dfr_SubDatasetCoordinates.shape[1]:
                        dfr_SubDatasetCoordinates = dfr_SubDatasetCoordinates.reindex(columns=range(len(lst_SubDatasetCoordinates)))
                    dfr_SubDatasetCoordinates.loc[idx] = lst_SubDatasetCoordinates
        # Offset separator
        elif str_SubDatasetSeparator == "SetDistance":
            print("Sub-dataset separator: keyword.")
            int_NewRow = lst_SubDatasetCoordinates[0]
            while int_NewRow in dfr_ParsedDataFile.index:
                print(int_NewRow)
                lst_SubDatasetCoordinates.append(int_NewRow)
                int_NewRow += tpl_NewDatasetOffset[int_SubDatasetAxis]
        # Create dataframe to merge
        print(dfr_SubDatasetCoordinates)
        dfr_DatasetCoordinates = pd.concat([dfr_DatasetCoordinates, dfr_SubDatasetCoordinates], axis=1, join="inner")
        dfr_DatasetCoordinates.columns = range(len(dfr_DatasetCoordinates.columns))
        # Convert all values to integers:
        for col in dfr_DatasetCoordinates.columns:
            dfr_DatasetCoordinates[col] = dfr_DatasetCoordinates[col].astype(int)
        print(dfr_DatasetCoordinates)

    # Print info for sanity check
    print("Datasets: " + str(dfr_DatasetCoordinates.shape[0]))
    print(u"Dataset start rows: \n" + str(dfr_DatasetCoordinates.iloc[:,0]))

    # Branching: Plate or samples?
    if str_PlateOrSample == "Plate":
        print("We have a plate")
        # Brancking: Table or Grid?
        if str_GridOrTable == "Grid":
            # Create dataframe -> assuming one dataset for now
            dfr_RawData = pd.DataFrame(index=dfr_DatasetCoordinates.index,columns=dfr_DatasetCoordinates.columns)
            int_PlateRows = pf.plate_rows(int_Wells)
            int_PlateCols = pf.plate_columns(int_Wells)
            lst_RowLetters = pf.plate_rows_letters(int_Wells)
            lst_ColumnNumbers = pf.plate_columns_numbers(int_Wells)
            for dfrrow in range(dfr_RawData.shape[0]):
                print("Dataframe row: " + str(dfrrow))
                for dfrcol in range(dfr_RawData.shape[1]):
                    print("Dataframe column: " + str(dfrcol))
                    # remember dataframes are indexed from zero!
                    startrow = dfr_DatasetCoordinates.iloc[dfrrow,dfrcol] + tpl_DatasetKeywordOffset[0]
                    print("Startrow: " + str(startrow))
                    startcol = int_DatasetKeywordColumn + tpl_DatasetKeywordOffset[1]
                    print("Startcol: " + str(startcol))
                    dfr_RawData.iloc[dfrrow,dfrcol] = dfr_ParsedDataFile.iloc[startrow:startrow+int_PlateRows,
                                                                            startcol:startcol+int_PlateCols]
                    # Rename rows and columns:
                    dfr_RawData.iloc[dfrrow,dfrcol] = dfr_RawData.iloc[dfrrow,dfrcol].set_axis(lst_RowLetters, axis=0)
                    dfr_RawData.iloc[dfrrow,dfrcol] = dfr_RawData.iloc[dfrrow,dfrcol].set_axis(lst_ColumnNumbers, axis=1)
                    print(dfr_RawData.iloc[dfrrow,dfrcol])

    #print(dfr_RawData)

    #print(dfr_ParsedDataFile)

    return dfr_RawData, True


def FindKeywordVertically(dfr, startrow, col, keyword, exact):
    for idx in dfr.index[startrow:]:
        cell = dfr.loc[idx,col]
        if not pd.isna(cell) == True:
            if keyword in cell:
                if exact == True:
                    if cell == keyword:
                        return idx
                else:
                    return idx

def FindKeywordsVertically(dfr, startrow, column, keyword, exact, stoprow):
    """
    Takes a pandas dataframe (dfr) and looks through specified column from startrow until stoprow is reached.
    If keyword is found, the corresponding row is added to the return list
    """
    lst_Return = []
    for idx in dfr.index[startrow:]:
        cell = dfr.loc[idx,column]
        if not pd.isna(cell) == True:
            if keyword in cell:
                if exact == True:
                    if cell == keyword:
                        lst_Return.append(idx)
                else:
                    lst_Return.append(idx)
        if idx == stoprow:
            break
    return lst_Return

def FindKeywordHorizontally(dfr, startcol, idx, keyword, exact):
    for col in dfr.columns[startcol:]:
        cell = dfr.loc[idx,col]
        if not pd.isna(cell) == True:
            if keyword in cell:
                if exact == True:
                    if cell == keyword:
                        return col
                else:
                    return col

def FindKeywordsHorizontally(dfr, startcolumn, row, keyword, exact, stopcol):
    """
    Takes a pandas dataframe (dfr) and looks through specified column starting at startcolumn until stopcolumn is reached.
    If keyword is found, the corresponding row is added to the return list
    """
    lst_Return = []
    for column in dfr.columns[startcolumn:]:
        cell = dfr.loc[row,column]
        if not pd.isna(cell) == True:
            if keyword in cell:
                if exact == True:
                    if cell == keyword:
                        lst_Return.append(column)
                else:
                    lst_Return.append(column)
        if column == stopcol:
            break
    return lst_Return

def Verification(str_Test, str_Keyword, bool_Exact):
    if bool_Exact == True and str_Keyword == str_Test:
        return True
    elif str_Keyword in str_Test:
        return True
    else:
        return False