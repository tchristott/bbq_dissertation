
"""
Workflow processor

Functions
    transfer_to_layout
"""

import pandas as pd
import lib_platefunctions as pf

def transfer_to_layout(transfer_rules, str_FilePath):
    """
    Takes transfer file parsing rules (as pandas dataframe) and file path of transfer file to parse (as string) and builds a data frame that
    captures the layout of each plate in the transfer file.
    
    Returns pandas dataframe "dfr_Layout" and boolean value for success of parsing.
    """

    str_Extension = transfer_rules["Extension"]
    str_Engine = transfer_rules["Engine"]
    str_Worksheet = transfer_rules["Worksheet"]

    # Get the first read:
    if str_Extension == "csv" or str_Extension == "txt":
        try:
            dfr_ParsedTransfer = pd.read_csv(str_FilePath, sep=None, header=None, index_col=False, engine=str_Engine)
        except:
            # Couldn't parse, return empty dataframe and no success
            return pd.DataFrame(), False
    elif str_Extension[0:3] == "xls":
        try:
            dfr_ParsedTransfer = pd.read_excel(str_FilePath, sheet_name=str_Worksheet, header=None, index_col=None, engine=str_Engine)
        except:
            # Couldn't parse, return empty dataframe and no success
            return pd.DataFrame(), False

    # Verify whether we're dealing with a valid transfer file:
    
    if transfer_rules["Verification"]["Use"] == True:
        bool_Verified = False
        for idx in dfr_ParsedTransfer.index:
            if dfr_ParsedTransfer.loc[idx, transfer_rules["Verification"]["Column"]] == transfer_rules.loc["Verification"]["Keyword"]:
                bool_Verified = True
                break
        if bool_Verified == False:
            print("could not verify file")
            # Couldn't parse, return empty dataframe and no success
            return pd.DataFrame(), False
    
    # Default stop row as shape[0] in case the end of dataframe is end of entries
    int_StopRow = dfr_ParsedTransfer.shape[0]

    # Find start and stop of transfer entries
    if not dfr_ParsedTransfer.shape[0] == 0:
        # 1. Find start:
        if transfer_rules["Start"]["UseKeyword"] == True:
            for row in range(dfr_ParsedTransfer.shape[0]):
                int_StartCol = int(transfer_rules["Start"]["KeywordColumn"])
                if dfr_ParsedTransfer.iloc[row,int_StartCol] == transfer_rules["Start"]["Keyword"]:
                    int_StartRow = row
                    break
        elif transfer_rules["Start"]["UseCoordinates"] == True:
            int_StartRow = transfer_rules["Start"]["Coordinates"][0]
            int_StartCol = transfer_rules["Start"]["Coordinates"][1]
        else:
            # Couldn't parse, return empty dataframe and no success
            return pd.DataFrame(), False
        # 2. Find stop:
        if transfer_rules["Stop"]["UseKeyword"] == True:
            for row in range(int_StartRow+1, dfr_ParsedTransfer.shape[0]):
                int_StopCol = int(transfer_rules["Stop"]["Column"])
                if dfr_ParsedTransfer.iloc[row,int_StopCol] == transfer_rules["Stop"]["Keyword"]:
                    int_StopRow = row-1
                    break
        elif transfer_rules["Stop"]["UseCoordinates"] == True:
            int_StopRow = transfer_rules["Stop"]["Coordinates"][0] - int_StartRow
            int_StopCol = transfer_rules.loc["Stop"]["Coordinates"][1] - int_StartCol
        elif transfer_rules["Stop"]["UseEmptyLine"] == True:
            int_StopCol = dfr_ParsedTransfer.shape[1]
            for row in range(int_StartRow+1, dfr_ParsedTransfer.shape[0]):
                if pd.isna(dfr_ParsedTransfer.iloc[row,0]) == True:
                    int_StopRow = row-1
                    break
        else:
            # Couldn't parse, return empty dataframe and no success
            return pd.DataFrame(), False

        # Ensure we don't end up with a one-column dataframe -> Default stop column to last column of dataframe
        if int_StopCol == int_StartCol:
            int_StopCol = dfr_ParsedTransfer.shape[1]

        # Rename column titles:
        lst_OldColumnNames = dfr_ParsedTransfer.columns
        lst_NewColumnNames = dfr_ParsedTransfer.loc[int_StartRow].tolist()

        # Create dictionary for renaming
        dic_Rename = {}
        for i in range(len(lst_OldColumnNames)):
            dic_Rename[lst_OldColumnNames[i]] = lst_NewColumnNames[i]
        dfr_ParsedTransfer = dfr_ParsedTransfer.iloc[int_StartRow+1:int_StopRow,int_StartCol:int_StopCol].rename(columns=dic_Rename).reset_index()

        # Reduce columns
        lst_ReducedColumnsParsed = []
        lst_ReducedColumnsLayout = []
        for key in transfer_rules["TransferFileColumns"].keys():
            if not transfer_rules["TransferFileColumns"][key]["Mapped"] == None:
                lst_ReducedColumnsParsed.append(transfer_rules["TransferFileColumns"][key]["Mapped"])
                lst_ReducedColumnsLayout.append(transfer_rules["TransferFileColumns"][key]["Name"])
        dfr_ParsedTransfer = dfr_ParsedTransfer[lst_ReducedColumnsParsed]
        # Check whether "Sample Name" or "Sample ID" or both are used. If both are used, "Sample ID" will be given prefernce
        # for simplicity. This is used to differentiate between sample and solvent transfers
        if "Sample ID" in lst_ReducedColumnsLayout:
            smpl = get_index(transfer_rules["TransferFileColumns"], "Sample ID")
            smpl_mapped = transfer_rules["TransferFileColumns"][smpl]["Mapped"]
        elif "Sample Name" in lst_ReducedColumnsLayout:
            str_SampleIdentifier = "Sample Name"
            smpl = get_index(transfer_rules["TransferFileColumns"], "Sample Name")
            smpl_mapped = transfer_rules["TransferFileColumns"][smpl]["Mapped"]
        else:
            # In this case, there is no point in using this transfer file!
            return pd.DataFrame(), False
        # If we do want to catch solvent=only transfers, make sure that column is in the layout dataframe, even if it
        # was not assigned (might not be explicitly labelled in transfer files):
        if transfer_rules["CatchSolventTransfers"] == True:
            if not "Solvent Transfer Volume" in lst_ReducedColumnsLayout:
                lst_ReducedColumnsLayout.append("Solvent Transfer Volume")
                str_SolventTransferIdentifier = "Sample Transfer Volume"
            else:
                str_SolventTransferIdentifier = "Solvent Transfer Volume"
            solv = get_index(transfer_rules["TransferFileColumns"], "Solvent Transfer Volume")
            solv_mapped = transfer_rules["TransferFileColumns"][solv]["Mapped"]
        
        # Create the actual layout dataframe to return
        # Get the list of destination plates:
        dpn = get_index(transfer_rules["TransferFileColumns"], "DestinationPlateName")
        if dpn is None:
            dpn = get_index(transfer_rules["TransferFileColumns"], "DestinationPlateBarcode")

        lst_DestinationPlates = dfr_ParsedTransfer[transfer_rules["TransferFileColumns"][dpn]["Mapped"]].dropna().unique()
        dfr_Layout = pd.DataFrame(index=lst_DestinationPlates,columns=lst_ReducedColumnsLayout)
        # Get columns and rows based on plate format
        int_PlateRows = pf.plate_rows(transfer_rules["DestinationPlateFormat"])
        int_PlateColumns = pf.plate_columns(transfer_rules["DestinationPlateFormat"])

        lst_PlateRows = []
        for row in range(int_PlateRows):
            lst_PlateRows.append(chr(row+65))
        lst_PlateColumns = [*range(1,int_PlateColumns+1)] # asterisk is unpacking operator -> turns range into list!
        # Add sub-dataframes:
        for plate in dfr_Layout.index:
            for column in dfr_Layout.columns:
                dfr_Layout.at[plate,column] = pd.DataFrame(index=lst_PlateRows,columns=lst_PlateColumns)

        # Populate layot dataframe:
        # Go through each row in parsed transfer file:
        dpw = get_index(transfer_rules["TransferFileColumns"], "DestinationWell")
        dest_mapped = transfer_rules["TransferFileColumns"][dpw]["Mapped"]
        for row in dfr_ParsedTransfer.index:
            # Get coordinates of destination well
            tpl_Well = pf.SplitCoordinates(dfr_ParsedTransfer.loc[row,dest_mapped])
            # Find destination plate
            plate = dfr_ParsedTransfer.loc[row,dest_mapped]
            # Only use all columns if there is a sample ID associated:
            str_Fnord = dfr_ParsedTransfer.loc[row, smpl_mapped] 
            if pd.isna(str_Fnord) == False:
                for key in transfer_rules["TransferFileColumns"].keys():
                    mapped = transfer_rules["TransferFileColumns"][key]["Mapped"]
                    if not mapped == None:
                        col = transfer_rules["TransferFileColumns"][key]["Name"]
                        dfr_Layout.loc[plate,col].loc[tpl_Well[0],tpl_Well[1]] = ( # line break with parentheses for better readability
                        dfr_ParsedTransfer.loc[row, mapped])
            # If there is no sample associated, it could either be solvent only or backfill:
            elif transfer_rules["CatchSolventOnlyTransfers"] == True:
                dfr_Layout.loc[plate,"Solvent Transfer Volume"].loc[tpl_Well[0],tpl_Well[1]] = ( # line break with parentheses for better readability
                dfr_ParsedTransfer.loc[row, solv_mapped])

        return dfr_Layout, True
    
    def get_index(columns, col):
        """
        Find index of the column in the dictionary.
        Boxed myself into a cornder by arranging the dictionary like this, so to save
        code I had to write this function.

        Arguments:
            columns - > dictionary. "TransferFileColumns" section of transfer_rules dictionary
            col -> str. The column to look for

        Returns
            key of the requested column or None if not fourd.
        """
        for key in columns.keys():
            if columns[key]["Name"] == col:
                return key
        return None