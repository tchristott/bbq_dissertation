##############################################################################
##                                                                          ##
##    ######  ##  ##   #####  ######  ##                                    ##
##    ##      ##  ##  ##      ##      ##                                    ##
##    ####     ####   ##      ####    ##                                    ##
##    ##      ##  ##  ##      ##      ##                                    ##
##    ######  ##  ##   #####  ######  ######                                ##
##                                                                          ##
##    ######  ##  ##  ##  ##   #####  ######  ##   ####   ##  ##   #####    ##
##    ##      ##  ##  ### ##  ##        ##    ##  ##  ##  ### ##  ##        ##
##    ####    ##  ##  ######  ##        ##    ##  ##  ##  ######   ####     ##
##    ##      ##  ##  ## ###  ##        ##    ##  ##  ##  ## ###      ##    ##
##    ##       ####   ##  ##   #####    ##    ##   ####   ##  ##  #####     ##
##                                                                          ##
##############################################################################
"""
    In this module:

    Functions to deal with MS Excel files
"""


# Imports #####################################################################################################################################################

import xlrd
import pandas as pd
import os
import xmltodict
import zipfile as zf
from pathlib import Path

###############################################################################################################################################################

def GetWorksheets(str_FilePath, str_Extension):
    """
    Takes the file path (str_FilePath as string) and file extension (str_Extension as string) of an MS Excel file
    and returns the names of the worksheets therein as a list.

    Includes contingency in case the file is not a true Excel file: Returns empty list.
    """

    # Approach for "old" Excel files
    try:
    # if str_Extension == "xls":
        # Load Excel file with xlrd such that worksheet contents will only be loaded when accessed:
        wbk = xlrd.open_workbook(str_FilePath, on_demand=True)
        return wbk.sheet_names()
    except:
        None
    
    # Approach for "new" Excel files
    # elif str_Extension == "xlsx":
    try:
        lst_Worksheets = []
        dic_Worksheets = {}
        bool_SingleSheet = False
        zip_Excel = zf.ZipFile(str_FilePath, "r")
        zip_Excel.extract(r"xl/workbook.xml",os.path.join(Path.home(),"bbqtempdir"))
        str_Path = os.path.join(Path.home(),"bbqtempdir","xl","workbook.xml")
        dic_XML = xmltodict.parse(open(str_Path).read())
        # Go to correct level based on .xlsx file format definition
        for sheet in dic_XML["workbook"]["sheets"]["sheet"]:
            int_Numerical = None
            str_Name = None
            if hasattr(sheet, "keys") == True:
                # There is more than one sheet in the file
                for key in sheet.keys():
                    # Find the key that has the numerical sheet ID and the key that has the sheet name
                    if key.find("sheetId") != -1:
                        int_Numerical = int(sheet[key]) -1
                    if key.find("name") != -1:
                        str_Name = sheet[key]
                    if not int_Numerical == None and not str_Name == None:
                        dic_Worksheets[int_Numerical] = str_Name
            else:
                # There is only one sheet in this workbook, break the for loop
                bool_SingleSheet = True
                break
        if bool_SingleSheet == True:
            # Temporarily assign dic_XML["workbook"]["sheets"]["sheet"] to variable singlesheet to make code easier to write
            singlesheet = dic_XML["workbook"]["sheets"]["sheet"]
            for key in singlesheet.keys():
            # Find the key that has the numerical sheet ID and the key that has the sheet name
                if key.find("sheetId") != -1:
                    int_Numerical = int(singlesheet[key]) -1
                if key.find("name") != -1:
                    str_Name = singlesheet[key]
                if not int_Numerical == None and not str_Name == None:
                    dic_Worksheets[int_Numerical] = str_Name
            # set singlesheet to None to break link
            singlesheet = None
        for sheet in dic_Worksheets.keys():
            lst_Worksheets.append(dic_Worksheets[sheet])
        return lst_Worksheets
    except:
        None

    # If file can't be parsed, it's a different file type masquerading as an Excel file. Return empty list.
    return []

def direct_read(str_FilePath, str_Extension, str_SheetToOpen):
    """
    Takes information about file and returns all contents, which function was used to open it and which engine was used.
    
    Arguments:
    str_FilePath -> string
    str_Extension -> string
    str_SheetToOpen -? string

    Returns:
        dfr_DirectRead,
        str_FileType,
        str_Engine
    """

    # Select correct parser based on file extension
    if str_Extension == "csv" or str_Extension == "txt":
        try:
            return pd.read_csv(str_FilePath, sep=None, header=None, index_col=False, engine="python"),"csv", "python"
        except:
            return None, None, None
    elif str_Extension[0:3] == "xls":
        try:
            # Try first engine: openpyxl
            return pd.read_excel(str_FilePath, sheet_name=str_SheetToOpen, header=None, index_col=None, engine="openpyxl"), "xls", "openpyxl"
        except:
            try:
                # Try second engine: xlrd
                return pd.read_excel(str_FilePath, sheet_name=str_SheetToOpen, header=None, index_col=None, engine="xlrd"), "xls", "xlrd"
            except:
                try:
                    # Assume file extension is incorrect: Try to read it as a .csv or .txt file:
                    return pd.read_csv(str_FilePath, sep=None, header=None, index_col=False, engine="python"), "csv", "python"
                except:
                    return None, None, None