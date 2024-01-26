########################################################################
##                                                                    ##
##    #####    ####   ##      ##    #####    ####   ######   ####     ##
##    ##  ##  ##  ##  ##      ##    ##  ##  ##  ##    ##    ##  ##    ##
##    #####   ######  ##  ##  ##    ##  ##  ######    ##    ######    ##
##    ##  ##  ##  ##  ##  ##  ##    ##  ##  ##  ##    ##    ##  ##    ##
##    ##  ##  ##  ##   ########     #####   ##  ##    ##    ##  ##    ##
##                                                                    ##
##    #####   ######   ####   #####   ######  #####                   ##
##    ##  ##  ##      ##  ##  ##  ##  ##      ##  ##                  ##
##    #####   ####    ######  ##  ##  ####    #####                   ##
##    ##  ##  ##      ##  ##  ##  ##  ##      ##  ##                  ##
##    ##  ##  ######  ##  ##  #####   ######  ##  ##                  ##
##                                                                    ##
########################################################################
"""
    In this module:
    
    User interface elements for determining the rules to read raw data files
    for a certain assay.

"""

# Imports ##############################################################################

import wx
import wx.xrc
import wx.grid

import pandas as pd
import os
from pathlib import Path
import zipfile as zf
import shutil
import datetime
import copy

import json as js

import editor.rawdatafunctions as rf
import lib_platefunctions as pf
import lib_excelfunctions as ef
import lib_messageboxes as mb
import lib_colourscheme as cs

################################################################################################
##                                                                                            ##
##    #####   ######  ######  ##  ##  ##  ######    #####   ##  ##  ##      ######   #####    ##
##    ##  ##  ##      ##      ##  ### ##  ##        ##  ##  ##  ##  ##      ##      ##        ##
##    ##  ##  ####    ####    ##  ######  ####      #####   ##  ##  ##      ####     ####     ##
##    ##  ##  ##      ##      ##  ## ###  ##        ##  ##  ##  ##  ##      ##          ##    ##
##    #####   ######  ##      ##  ##  ##  ######    ##  ##   ####   ######  ######  #####     ##
##                                                                                            ##
################################################################################################

class RawDataRules (wx.Panel):

    def __init__(self, parent, wkflw, assay):
        """
        Initialises class attributes.
        
        Arguments:
            parent -> wx object. Parent object of this panel
            wkflow -> wofklow editor window
            assay -> assay definition dictionary
        """
        wx.Panel.__init__(self, parent,
                          id = wx.ID_ANY,
                          pos = wx.DefaultPosition, size = wx.DefaultSize,
                          style = wx.TAB_TRAVERSAL, name = wx.EmptyString)

        self.SetSizeHints(wx.DefaultSize, wx.DefaultSize)
        self.SetBackgroundColour(cs.BgUltraLight)
        self.pnlbgclr = cs.BgLight

        self.location = os.path.dirname(os.path.realpath(__file__))

        self.parent = parent
        self.wkflw = wkflw
        self.assay = assay

        self.rule_set = rf.CreateBlankRuleSet()
        # Associated variables:
        self.tpl_ExampleFileVerificationKeywordCoordinates = None
        self.tpl_ExampleFileNewDatasetKeywordCoordinates = None
        self.bool_ExampleFileLoaded = False

        self.szr_Surround = wx.BoxSizer(wx.HORIZONTAL)

        self.pnl_Wizard = wx.Panel(self)
        self.pnl_Wizard.SetBackgroundColour(cs.BgUltraLight)
        self.szr_Wizard = wx.BoxSizer(wx.VERTICAL)

        # Simplebook ####################################################################
        # To make the generation of the dataframe easy, user will be guided through a
        # wizard. wxPython offers an inbuilt Wizard, but I'll make
        # my own with a simplebook to have more flexibility.
        self.sbk_Wizard = wx.Simplebook(self.pnl_Wizard,
                                        size = wx.Size(420,-1),
                                        style = wx.TAB_TRAVERSAL)
        self.sbk_Wizard.SetMaxSize(wx.Size(420,600))
        # Define dictionary that holds saving functions for each page:
        self.dic_PageSaveFunctions = {}

        # #   #  #### ##### ####  #   #  #### ##### #  ###  #   #  ####
        # ##  # #       #   #   # #   # #       #   # #   # ##  # #
        # #####  ###    #   ####  #   # #       #   # #   # #####  ###
        # #  ##     #   #   #   # #   # #       #   # #   # #  ##     #
        # #   # ####    #   #   #  ###   ####   #   #  ###  #   # ####

        # Wizard Page: Instructions #####################################################
        self.pnl_Instructions = wx.ScrolledWindow(self.sbk_Wizard,
                                                  style = wx.TAB_TRAVERSAL|wx.VSCROLL)
        self.pnl_Instructions.SetScrollRate(5,5)
        self.pnl_Instructions.SetBackgroundColour(self.pnlbgclr)
        self.szr_Instructions = wx.BoxSizer(wx.VERTICAL)
        self.lbl_Instructions = wx.StaticText(self.pnl_Instructions,
                                              label = u"Instructions")
        self.szr_Instructions.Add(self.lbl_Instructions, 0, wx.ALL, 5)
        # All elements added to sizer
        self.pnl_Instructions.SetSizer( self.szr_Instructions )
        self.pnl_Instructions.Layout()
        self.szr_Instructions.Fit( self.pnl_Instructions )
        # Add to simplebook #############################################################
        self.sbk_Wizard.AddPage(self.pnl_Instructions, u"Instructions", True)
        self.dic_PageSaveFunctions["Instructions"] = self.fun_Dummy
        #################################################################################


        ##### #   #  ###  #   # ####  #     #####    ##### # #     #####
        #      # #  #   # ## ## #   # #     #        #     # #     #
        ###     #   ##### ##### ####  #     ###      ###   # #     ###
        #      # #  #   # # # # #     #     #        #     # #     #
        ##### #   # #   # #   # #     ##### #####    #     # ##### #####

        #  Wizard Page: Example File and Verification ###################################
        self.pnl_ExampleFile = wx.ScrolledWindow(self.sbk_Wizard,
                                                 style = wx.TAB_TRAVERSAL|wx.VSCROLL)
        self.pnl_ExampleFile.SetScrollRate(5,5)
        self.pnl_ExampleFile.SetBackgroundColour(self.pnlbgclr)
        self.szr_ExampleFile = wx.BoxSizer(wx.VERTICAL)
        # File selection
        self.szr_FileSelection = wx.BoxSizer(wx.VERTICAL)
        self.lbl_FileSelection = wx.StaticText(self.pnl_ExampleFile,
                                               label = u"Select a raw data file")
        self.szr_FileSelection.Add(self.lbl_FileSelection, 0, wx.ALL, 5)
        self.fpk_RawDataFile = wx.FilePickerCtrl(self.pnl_ExampleFile, 
                                                 message = u"Select a file",
                                                 wildcard = u"*.*")
        self.szr_FileSelection.Add(self.fpk_RawDataFile, 0, wx.ALL, 5 )
        self.lbl_Worksheet = wx.StaticText(self.pnl_ExampleFile,
                                           label = u"If multiple worksheets, use:")
        self.lbl_Worksheet.Wrap(-1)
        self.lbl_Worksheet.Enable(False)
        self.szr_FileSelection.Add(self.lbl_Worksheet, 0, wx.ALL, 5)
        self.ckl_Worksheets = wx.CheckListBox(self.pnl_ExampleFile, wx.ID_ANY,
                                              wx.DefaultPosition, wx.DefaultSize, [], 0 )
        self.ckl_Worksheets.Enable(False)
        self.szr_FileSelection.Add(self.ckl_Worksheets, 0, wx.ALL, 5)
        self.btn_ParseFile = wx.Button(self.pnl_ExampleFile,
                                       label = u"Parse file >")
        self.btn_ParseFile.Enable(False)
        self.szr_FileSelection.Add(self.btn_ParseFile, 0, wx.ALL, 5)
        self.szr_ExampleFile.Add(self.szr_FileSelection, 0, wx.ALL, 5)
        self.lin_ExampleFile = wx.StaticLine(self.pnl_ExampleFile,
                                             style = wx.LI_HORIZONTAL)
        self.szr_ExampleFile.Add(self.lin_ExampleFile, 0, wx.EXPAND|wx.ALL, 5)
        # Verification ////
        self.chk_Verification = wx.CheckBox(self.pnl_ExampleFile,
                                            label = u"Verify file is a correct raw data file by use of a keyword")
        self.chk_Verification.SetValue(True)
        self.szr_ExampleFile.Add(self.chk_Verification, 0, wx.ALL, 5)
        self.szr_Verification = wx.BoxSizer(wx.VERTICAL)
        # Keyword
        self.szr_VerificationKeyword = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_VerificationKeyword.Add((0,0), 0, wx.ALL, 5)
        self.lbl_VerificationKeyword = wx.StaticText(self.pnl_ExampleFile, wx.ID_ANY,
                                                     u"Keyword:", wx.DefaultPosition,
                                                     wx.DefaultSize, 0)
        self.szr_VerificationKeyword.Add(self.lbl_VerificationKeyword, 0,
                                         wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.txt_VerificationKeyword = wx.TextCtrl(self.pnl_ExampleFile, wx.ID_ANY,
                                                   wx.EmptyString, wx.DefaultPosition,
                                                   wx.Size(150,-1), wx.TE_READONLY)
        self.szr_VerificationKeyword.Add(self.txt_VerificationKeyword, 0,
                                         wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.txt_VerificationKeywordEditable = wx.TextCtrl(self.pnl_ExampleFile, wx.ID_ANY,
                                                           wx.EmptyString,
                                                           wx.DefaultPosition,
                                                           wx.Size(150,-1), 0)
        self.szr_VerificationKeyword.Add(self.txt_VerificationKeywordEditable, 0,
                                         wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.txt_VerificationKeywordEditable.Show(False)
        self.szr_Verification.Add(self.szr_VerificationKeyword, 0, wx.ALL, 0)
        # Row
        self.szr_VerificationKeywordRow = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_VerificationKeywordRow.Add((0,0), 0, wx.ALL, 5)
        self.rad_VerificationKeywordRow = wx.RadioButton(self.pnl_ExampleFile, wx.ID_ANY,
                                                         u"in row", wx.DefaultPosition,
                                                         wx.DefaultSize, wx.RB_SINGLE)
        self.szr_VerificationKeywordRow.Add(self.rad_VerificationKeywordRow, 0,
                                            wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.txt_VerificationKeywordRow = wx.TextCtrl(self.pnl_ExampleFile, wx.ID_ANY,
                                                      wx.EmptyString, wx.DefaultPosition,
                                                      wx.Size(30,-1), wx.TE_READONLY)
        self.szr_VerificationKeywordRow.Add(self.txt_VerificationKeywordRow, 0,
                                            wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.szr_Verification.Add(self.szr_VerificationKeywordRow, 0, wx.ALL, 0)
        # Column
        self.szr_VerificationKeywordColumn = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_VerificationKeywordColumn.Add((0,0), 0, wx.ALL, 5)
        self.rad_VerificationKeywordColumn = wx.RadioButton(self.pnl_ExampleFile, wx.ID_ANY,
                                                            u"in column", wx.DefaultPosition,
                                                            wx.DefaultSize, wx.RB_SINGLE)
        self.rad_VerificationKeywordColumn.SetValue(True)
        self.szr_VerificationKeywordColumn.Add(self.rad_VerificationKeywordColumn, 0,
                                               wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.txt_VerificationKeywordColumn = wx.TextCtrl(self.pnl_ExampleFile, wx.ID_ANY,
                                                         wx.EmptyString, wx.DefaultPosition,
                                                         wx.Size(30,-1), wx.TE_READONLY)
        self.szr_VerificationKeywordColumn.Add(self.txt_VerificationKeywordColumn, 0,
                                               wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.szr_Verification.Add(self.szr_VerificationKeywordColumn, 0, wx.ALL, 0)
        # Exact?
        self.szr_VerificationExact = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_VerificationExact.Add((0,0), 0, wx.ALL, 5)
        self.chk_VerificationExact = wx.CheckBox(self.pnl_ExampleFile, wx.ID_ANY,
                                                 u"Keyword exactly like in example file.",
                                                 wx.DefaultPosition, wx.DefaultSize, 0)
        self.chk_VerificationExact.SetValue(True)
        self.szr_VerificationExact.Add(self.chk_VerificationExact, 0, wx.ALL, 0)
        self.szr_Verification.Add(self.szr_VerificationExact, 0, wx.ALL, 5)
        self.szr_ExampleFile.Add(self.szr_Verification, 0, wx.ALL, 5)
        # All elements added to sizer
        self.pnl_ExampleFile.SetSizer(self.szr_ExampleFile)
        self.pnl_ExampleFile.Layout()
        self.szr_Verification.Fit( self.pnl_ExampleFile )
        # Add to simplebook #############################################################
        self.sbk_Wizard.AddPage(self.pnl_ExampleFile, u"ExampleFile", False)
        self.dic_PageSaveFunctions["ExampleFile"] = self.save_example_file
        #################################################################################


        ####   ###  #####  ###      ###  ####   ####  ###  #   # #  ####  ###  ##### #  ###  #   #
        #   # #   #   #   #   #    #   # #   # #     #   # ##  # # #     #   #   #   # #   # ##  #
        #   # #####   #   #####    #   # ####  #  ## ##### ##### #  ###  #####   #   # #   # #####
        #   # #   #   #   #   #    #   # #   # #   # #   # #  ## #     # #   #   #   # #   # #  ## 
        ####  #   #   #   #   #     ###  #   #  #### #   # #   # # ####  #   #   #   #  ###  #   #

        # Wizard Page: Data Organisation ################################################
        self.pnl_DataOrganisation = wx.ScrolledWindow(self.sbk_Wizard,
                                                      style = wx.TAB_TRAVERSAL|wx.VSCROLL)
        self.pnl_DataOrganisation.SetScrollRate(5,5)
        self.pnl_DataOrganisation.SetBackgroundColour(self.pnlbgclr)
        self.szr_DataOrganisation = wx.BoxSizer(wx.VERTICAL)
        # Data organisation: Per sample or per plate ////
        self.lbl_SampleOrPlate = wx.StaticText(self.pnl_DataOrganisation, 
                                               label = u"What does the data represent:")
        self.szr_DataOrganisation.Add(self.lbl_SampleOrPlate, 0, wx.ALL, 5)
        self.rad_Plate = wx.RadioButton(self.pnl_DataOrganisation,
                                        label = u"Datapoints representing wells of a mitcrotitre plate",
                                        style = wx.RB_SINGLE)
        self.rad_Plate.SetValue(True)
        self.szr_DataOrganisation.Add(self.rad_Plate, 0, wx.ALL, 5)
        # Number of wells if plate
        self.szr_Wells = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_Wells.Add((25,25), 0, wx.ALL, 0)
        self.lbl_Wells = wx.StaticText(self.pnl_DataOrganisation, wx.ID_ANY,
                                       u"Assay plate has", wx.DefaultPosition,
                                       wx.DefaultSize, 0)
        self.lbl_Wells.Wrap(-1)
        self.szr_Wells.Add(self.lbl_Wells, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.cbo_Wells = wx.ComboBox(self.pnl_DataOrganisation, wx.ID_ANY, u"",
                                     wx.DefaultPosition, wx.DefaultSize,
                                     ["6","12","24","48","96","384","1536"],
                                     wx.CB_READONLY)
        self.cbo_Wells.SetSelection(self.cbo_Wells.FindString(str(self.rule_set["AssayPlateFormat"])))
        self.szr_Wells.Add(self.cbo_Wells, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.lbl_Wells = wx.StaticText(self.pnl_DataOrganisation, wx.ID_ANY, u"wells.",
                                       wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_Wells.Wrap(-1)
        self.szr_Wells.Add(self.lbl_Wells, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.szr_DataOrganisation.Add(self.szr_Wells, 0, wx.ALL, 0)
        self.rad_Sample = wx.RadioButton(self.pnl_DataOrganisation, wx.ID_ANY, u"One sample or a collection of samples", wx.DefaultPosition,
                                        wx.DefaultSize, wx.RB_SINGLE)
        self.rad_Sample.SetValue(False)
        self.szr_DataOrganisation.Add(self.rad_Sample, 0, wx.ALL, 5)
        self.lin_SampleOrPlate = wx.StaticLine( self.pnl_DataOrganisation, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.LI_HORIZONTAL )
        self.szr_DataOrganisation.Add(self.lin_SampleOrPlate, 0, wx.EXPAND|wx.ALL, 5)
        # Data in grid or table /////
        self.lbl_GridOrTable = wx.StaticText(self.pnl_DataOrganisation, wx.ID_ANY, u"How is the data arranged:", wx.DefaultPosition,
                                            wx.DefaultSize, 0)
        self.lbl_GridOrTable.Wrap(-1)
        self.szr_DataOrganisation.Add(self.lbl_GridOrTable, 0, wx.ALL, 5)
        self.rad_Grid = wx.RadioButton(self.pnl_DataOrganisation, wx.ID_ANY, u"Grid representing a microtitre plate.", wx.DefaultPosition,
                                        wx.DefaultSize, wx.RB_SINGLE)
        self.rad_Grid.SetValue(True)
        self.szr_DataOrganisation.Add(self.rad_Grid, 0, wx.ALL, 5)
        self.szr_GridMoreInfo = wx.FlexGridSizer(2, 2, 0, 0)
        self.szr_GridMoreInfo.SetFlexibleDirection( wx.BOTH )
        self.szr_GridMoreInfo.SetNonFlexibleGrowMode( wx.FLEX_GROWMODE_SPECIFIED )
        self.szr_GridMoreInfo.Add((25,0), 0, wx.ALL, 0)
        self.lbl_GridMoreInfo = wx.StaticText(self.pnl_DataOrganisation, wx.ID_ANY,
                                            u"E.g. for a 384 well plate: a grid of columns 1-24 and rows A-P. " + 
                                            u"Row and column labels may or may not be included in the file.",
                                            wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_GridMoreInfo.Wrap(380)
        self.szr_GridMoreInfo.Add(self.lbl_GridMoreInfo, 0, wx.ALL, 0)
        self.szr_GridMoreInfo.Add((25,0), 0, wx.ALL, 0)
        self.chk_GridLabelsIncluded = wx.CheckBox(self.pnl_DataOrganisation, wx.ID_ANY, u"Row and column labels are included.",
                                                wx.DefaultPosition, wx.DefaultSize, 0)
        self.chk_GridLabelsIncluded.SetValue(True)
        self.szr_GridMoreInfo.Add(self.chk_GridLabelsIncluded, 0, wx.ALL, 5)
        self.szr_DataOrganisation.Add(self.szr_GridMoreInfo, 0, wx.ALL, 5)
        self.rad_Table = wx.RadioButton(self.pnl_DataOrganisation, wx.ID_ANY, u"Table with two or more columns", wx.DefaultPosition, wx.DefaultSize,
                                        wx.RB_SINGLE)
        self.rad_Table.SetValue(False)
        self.szr_DataOrganisation.Add(self.rad_Table, 0, wx.ALL, 5)
        self.lin_GridOrTable = wx.StaticLine( self.pnl_DataOrganisation, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.LI_HORIZONTAL )
        self.szr_DataOrganisation.Add(self.lin_GridOrTable, 0, wx.EXPAND|wx.ALL, 5)
        # Beginning of Dataset ////
        self.szr_BeginningOfDataset = wx.BoxSizer(wx.VERTICAL)
        self.lbl_DataStart = wx.StaticText(self.pnl_DataOrganisation, wx.ID_ANY, u"Find start of data entries by", wx.DefaultPosition,
                                            wx.DefaultSize, 0)
        self.lbl_DataStart.Wrap(-1)
        self.szr_BeginningOfDataset.Add(self.lbl_DataStart, 0, wx.ALL, 5)
        # Keyword
        self.rad_StartKeyword = wx.RadioButton(self.pnl_DataOrganisation, wx.ID_ANY, u"Unique keyword and offset", wx.DefaultPosition,
                                                wx.DefaultSize,    wx.RB_SINGLE)
        self.rad_StartKeyword.SetValue(True)
        self.szr_BeginningOfDataset.Add(self.rad_StartKeyword, 0, wx.ALL, 5)
        self.szr_StartKeyword = wx.BoxSizer(wx.VERTICAL)
        self.szr_StartKeywordTextBoxes = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_StartKeywordTextBoxes.Add((25,25), 0, wx.ALL, 0)
        self.lbl_StartKeyword = wx.StaticText(self.pnl_DataOrganisation, wx.ID_ANY, u"Keyword", wx.DefaultPosition, wx.DefaultSize, 0)
        self.szr_StartKeywordTextBoxes.Add(self.lbl_StartKeyword, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.txt_StartKeyword = wx.TextCtrl(self.pnl_DataOrganisation, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size(150,-1), wx.TE_READONLY)
        self.szr_StartKeywordTextBoxes.Add(self.txt_StartKeyword, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.txt_StartKeywordEditable = wx.TextCtrl(self.pnl_DataOrganisation, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size(150,-1), 0)
        self.szr_StartKeywordTextBoxes.Add(self.txt_StartKeywordEditable, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.szr_StartKeywordTextBoxes.Hide(self.txt_StartKeyword)
        self.lbl_StartKeywordColumn = wx.StaticText(self.pnl_DataOrganisation, wx.ID_ANY, u"in column", wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_StartKeywordColumn.Wrap(-1)
        self.szr_StartKeywordTextBoxes.Add(self.lbl_StartKeywordColumn, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.txt_StartKeywordColumn = wx.TextCtrl(self.pnl_DataOrganisation, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size(30,-1),
                                                    wx.TE_READONLY)
        self.szr_StartKeywordTextBoxes.Add(self.txt_StartKeywordColumn, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.szr_StartKeyword.Add(self.szr_StartKeywordTextBoxes, 0, wx.ALL, 0)
        self.szr_StartKeywordOffset = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_StartKeywordOffset.Add((25,25), 0, wx.ALL, 0)
        self.lbl_StartKeywordOffset = wx.StaticText(self.pnl_DataOrganisation, wx.ID_ANY, u"Offset by", wx.DefaultPosition, wx.DefaultSize, 0)
        self.szr_StartKeywordOffset.Add(self.lbl_StartKeywordOffset, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.txt_StartKeywordOffsetRows = wx.TextCtrl(self.pnl_DataOrganisation, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size(30,-1),
                                                    wx.TE_READONLY)
        self.szr_StartKeywordOffset.Add(self.txt_StartKeywordOffsetRows, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.lbl_StartKeywordOffsetRows = wx.StaticText(self.pnl_DataOrganisation, wx.ID_ANY, u"rows and", wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_StartKeywordOffsetRows.Wrap(-1)
        self.szr_StartKeywordOffset.Add(self.lbl_StartKeywordOffsetRows, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.txt_StartKeywordOffsetColumns = wx.TextCtrl(self.pnl_DataOrganisation, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size(30,-1),
                                                        wx.TE_READONLY)
        self.szr_StartKeywordOffset.Add(self.txt_StartKeywordOffsetColumns, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.lbl_StartKeywordOffsetColumns = wx.StaticText(self.pnl_DataOrganisation, wx.ID_ANY, u"columns.", wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_StartKeywordOffsetColumns.Wrap(-1)
        self.szr_StartKeywordOffset.Add(self.lbl_StartKeywordOffsetColumns, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.szr_StartKeyword.Add(self.szr_StartKeywordOffset, 0, wx.ALL, 0)
        self.szr_StartKeywordExact = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_StartKeywordExact.Add((25,25), 0, wx.ALL, 0)
        self.chk_StartKeywordExact = wx.CheckBox( self.pnl_DataOrganisation, wx.ID_ANY, u"Keyword is exactly like in example file.",
                                            wx.DefaultPosition, wx.DefaultSize, 0)
        self.szr_StartKeywordExact.Add(self.chk_StartKeywordExact, 0, wx.ALL, 0)
        self.szr_StartKeyword.Add(self.szr_StartKeywordExact, 0, wx.ALL, 5)
        self.szr_BeginningOfDataset.Add(self.szr_StartKeyword, 0, wx.ALL, 0)
        self.dic_StartKeywordGUI = {"keywordlabel":self.lbl_StartKeyword,"keywordtext":self.txt_StartKeyword,
                                    "keywordtexteditable":self.txt_StartKeyword,
                                    "columnlabel":self.lbl_StartKeywordColumn,"columntext":self.txt_StartKeywordColumn,
                                    "exactcheckbox":self.chk_StartKeywordExact,
                                    "offset":self.lbl_StartKeywordOffset,"offsetcols":self.lbl_StartKeywordOffsetColumns,
                                    "offsetcolstext":self.txt_StartKeywordOffsetColumns,"offsetrows":self.lbl_StartKeywordOffsetRows,
                                    "offsetrowstext":self.txt_StartKeywordOffsetRows}
        # Coordinates
        self.rad_StartCoordinates = wx.RadioButton(self.pnl_DataOrganisation, wx.ID_ANY, u"Absolute coordinates", wx.DefaultPosition,
                                                    wx.DefaultSize, wx.RB_SINGLE)
        self.szr_BeginningOfDataset.Add(self.rad_StartCoordinates, 0, wx.ALL, 5)
        self.szr_StartCoordinates = wx.BoxSizer(wx.VERTICAL)
        self.szr_StartCoordinatesTextBoxes = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_StartCoordinatesTextBoxes.Add((25,25), 0, wx.ALL, 0)
        self.lbl_StartCoordinatesColumn = wx.StaticText(self.pnl_DataOrganisation, wx.ID_ANY, u"Column", wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_StartCoordinatesColumn.Wrap(-1)
        self.lbl_StartCoordinatesColumn.Enable(False)
        self.szr_StartCoordinatesTextBoxes.Add(self.lbl_StartCoordinatesColumn, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.txt_StartCoordinatesColumn = wx.TextCtrl(self.pnl_DataOrganisation, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size(30,-1),
                                                    wx.TE_READONLY)
        self.txt_StartCoordinatesColumn.Enable(False)
        self.szr_StartCoordinatesTextBoxes.Add(self.txt_StartCoordinatesColumn, 0, wx.ALL, 5)
        self.lbl_StartCoordinatesRow = wx.StaticText(self.pnl_DataOrganisation, wx.ID_ANY, u"Row", wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_StartCoordinatesRow.Wrap(-1)
        self.lbl_StartCoordinatesRow.Enable(False)
        self.szr_StartCoordinatesTextBoxes.Add(self.lbl_StartCoordinatesRow, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.txt_StartCoordinatesRow = wx.TextCtrl(self.pnl_DataOrganisation, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size(30,-1),
                                                wx.TE_READONLY)
        self.txt_StartCoordinatesRow.Enable(False)
        self.szr_StartCoordinatesTextBoxes.Add(self.txt_StartCoordinatesRow, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.dic_StartCoordinatesGUI = {"collabel":self.lbl_StartCoordinatesColumn,"coltext":self.txt_StartCoordinatesColumn,
                                        "rowlabel":self.lbl_StartCoordinatesRow,"rowtext":self.txt_StartCoordinatesRow}
        self.szr_StartCoordinates.Add(self.szr_StartCoordinatesTextBoxes, 0, wx.ALL, 0)
        self.szr_BeginningOfDataset.Add(self.szr_StartCoordinates, 0, wx.ALL, 0)
        self.szr_BeginningOfDataset.Hide(self.szr_StartCoordinates)
        self.szr_DataOrganisation.Add(self.szr_BeginningOfDataset, 0, wx.ALL, 0)

        # All elements added to sizer
        self.pnl_DataOrganisation.SetSizer(self.szr_DataOrganisation)
        self.pnl_DataOrganisation.Layout()
        self.szr_DataOrganisation.Fit(self.pnl_DataOrganisation)
        # Add to simplebook #########################################################################################################################
        self.sbk_Wizard.AddPage(self.pnl_DataOrganisation, u"DataOrganisation", False)
        self.dic_PageSaveFunctions["DataOrganisation"] = self.save_data_organisation
        #############################################################################################################################################


        #   # #   # #     ##### # ####  #     #####    ####   ###  #####  ###   #### ##### #####  ####
        ## ## #   # #       #   # #   # #     #        #   # #   #   #   #   # #     #       #   #
        ##### #   # #       #   # ####  #     ###      #   # #####   #   #####  ###  ###     #    ###
        # # # #   # #       #   # #     #     #        #   # #   #   #   #   #     # #       #       #
        #   #  ###  #####   #   # #     ##### #####    ####  #   #   #   #   # ####  #####   #   ####

        # Multiple datasets #########################################################################################################################
        self.pnl_MultipleDatasets = wx.ScrolledWindow(self.sbk_Wizard,
                                                      style = wx.TAB_TRAVERSAL|wx.VSCROLL)
        self.pnl_MultipleDatasets.SetScrollRate(5,5)
        self.pnl_MultipleDatasets.SetBackgroundColour(self.pnlbgclr)
        self.szr_MultipleDatasets = wx.BoxSizer(wx.VERTICAL)
        self.lbl_MultipleDatasets = wx.StaticText(self.pnl_MultipleDatasets,
                                                  label = u"Are there multiple datasets:")
        self.lbl_MultipleDatasets.Wrap(-1)
        self.szr_MultipleDatasets.Add(self.lbl_MultipleDatasets, 0, wx.ALL, 5)
        self.rad_SingleDataset = wx.RadioButton(self.pnl_MultipleDatasets, wx.ID_ANY, u"No, just a single dataset", wx.DefaultPosition,
                                                wx.DefaultSize, wx.RB_SINGLE)
        self.rad_SingleDataset.SetValue(True)
        self.szr_MultipleDatasets.Add(self.rad_SingleDataset, 0, wx.ALL, 5)
        self.rad_MultipleDatasets = wx.RadioButton(self.pnl_MultipleDatasets, wx.ID_ANY, u"Yes, e.g. multiple plates",    wx.DefaultPosition,
                                                    wx.DefaultSize, wx.RB_SINGLE)
        self.rad_MultipleDatasets.SetValue(False)
        self.szr_MultipleDatasets.Add(self.rad_MultipleDatasets, 0, wx.ALL, 5)
        # Yes Multiple Datasets \\\\\
        self.szr_YesMultipleDatasets = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_YesMultipleDatasets.Add((25,-1), 1, wx.ALL, 0)
        self.szr_YesMultipleDatasetsRightColumn = wx.BoxSizer(wx.VERTICAL)
        # Number of datasets
        self.lbl_NumberOfDatasets = wx.StaticText(self.pnl_MultipleDatasets, wx.ID_ANY, u"Determine the number of datasets:", wx.DefaultPosition,
                                                    wx.DefaultSize, 0)
        self.lbl_NumberOfDatasets.Wrap(-1)
        self.lbl_NumberOfDatasets.Enable(False)
        self.szr_YesMultipleDatasetsRightColumn.Add(self.lbl_NumberOfDatasets, 0, wx.ALL, 5)
        self.rad_DynamicDatasets = wx.RadioButton(self.pnl_MultipleDatasets, wx.ID_ANY, u"Dynamically determine number of datasets",
                                                    wx.DefaultPosition, wx.DefaultSize, wx.RB_SINGLE)
        self.rad_DynamicDatasets.Enable(False)
        self.rad_DynamicDatasets.SetValue(True)
        self.szr_YesMultipleDatasetsRightColumn.Add(self.rad_DynamicDatasets, 0, wx.ALL, 5)
        self.szr_FixedDatasets = wx.BoxSizer(wx.HORIZONTAL)
        self.rad_FixedDatasets = wx.RadioButton(self.pnl_MultipleDatasets, wx.ID_ANY, u"Fixed number of datasets", wx.DefaultPosition,
                                                    wx.DefaultSize, wx.RB_SINGLE)
        self.rad_FixedDatasets.Enable(False)
        self.szr_FixedDatasets.Add(self.rad_FixedDatasets, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.txt_FixedDatasets = wx.TextCtrl(self.pnl_MultipleDatasets, wx.ID_ANY, u"2", wx.DefaultPosition, wx.Size(30,-1), 0)
        self.txt_FixedDatasets.Enable(False)
        self.szr_FixedDatasets.Add(self.txt_FixedDatasets, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.szr_YesMultipleDatasetsRightColumn.Add(self.szr_FixedDatasets, 0, wx.ALL, 0)
        # Direction of Datasets
        self.lbl_DirectionOfDatasets = wx.StaticText(self.pnl_MultipleDatasets, wx.ID_ANY, u"How are datasets organised", wx.DefaultPosition,
                                                        wx.DefaultSize, 0)
        self.lbl_DirectionOfDatasets.Wrap(-1)
        self.lbl_DirectionOfDatasets.Enable(False)
        self.szr_YesMultipleDatasetsRightColumn.Add(self.lbl_DirectionOfDatasets, 1, wx.ALL, 0)
        self.rad_DatasetsVertically = wx.RadioButton(self.pnl_MultipleDatasets, wx.ID_ANY, u"Vertically", wx.DefaultPosition,
                                                    wx.DefaultSize, wx.RB_SINGLE)
        self.rad_DatasetsVertically.SetValue(True)
        self.rad_DatasetsVertically.Enable(False)
        self.szr_YesMultipleDatasetsRightColumn.Add(self.rad_DatasetsVertically, 0, wx.ALL, 5)
        self.rad_DatasetsHorizontally = wx.RadioButton(self.pnl_MultipleDatasets, wx.ID_ANY, u"Horizontally", wx.DefaultPosition,
                                                    wx.DefaultSize, wx.RB_SINGLE)
        self.rad_DatasetsHorizontally.Enable(False)
        self.szr_YesMultipleDatasetsRightColumn.Add(self.rad_DatasetsHorizontally, 0, wx.ALL, 5)
        # Separation of Datasets
        self.lbl_SeparationOfDatasets = wx.StaticText(self.pnl_MultipleDatasets, wx.ID_ANY, u"How are datasets separated", wx.DefaultPosition,
                                                        wx.DefaultSize, 0)
        self.lbl_SeparationOfDatasets.Wrap(-1)
        self.lbl_SeparationOfDatasets.Enable(False)
        self.szr_YesMultipleDatasetsRightColumn.Add(self.lbl_SeparationOfDatasets, 0, wx.ALL, 0)
        # Same as main dataset
        self.rad_DatasetSameAsMain = wx.RadioButton(self.pnl_MultipleDatasets, wx.ID_ANY, u"Same as main dataset", wx.DefaultPosition,
                                                    wx.DefaultSize, wx.RB_SINGLE)
        self.rad_DatasetSameAsMain.SetValue(True)
        self.rad_DatasetSameAsMain.Enable(False)
        self.szr_YesMultipleDatasetsRightColumn.Add(self.rad_DatasetSameAsMain, 0, wx.ALL, 5)
        # Keyword
        self.rad_DatasetKeyword = wx.RadioButton(self.pnl_MultipleDatasets, wx.ID_ANY, u"Unique keyword and offset", wx.DefaultPosition,
                                                    wx.DefaultSize, wx.RB_SINGLE)
        self.rad_DatasetKeyword.SetValue(False)
        self.rad_DatasetKeyword.Enable(False)
        self.szr_YesMultipleDatasetsRightColumn.Add(self.rad_DatasetKeyword, 0, wx.ALL, 5)
        self.szr_DatasetKeyword = wx.BoxSizer(wx.VERTICAL)
        self.szr_DatasetKeywordTextBoxesOne = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_DatasetKeywordTextBoxesOne.Add((25,25),1,wx.ALL,0)
        self.lbl_DatasetKeyword = wx.StaticText(self.pnl_MultipleDatasets, wx.ID_ANY, u"Keyword", wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_DatasetKeyword.Wrap(-1)
        self.szr_DatasetKeywordTextBoxesOne.Add(self.lbl_DatasetKeyword,0,wx.ALIGN_CENTER_VERTICAL|wx.ALL,5)
        self.txt_DatasetKeyword = wx.TextCtrl(self.pnl_MultipleDatasets, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, wx.TE_READONLY)
        self.szr_DatasetKeywordTextBoxesOne.Add(self.txt_DatasetKeyword, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.lbl_DatasetKeywordColumn = wx.StaticText(self.pnl_MultipleDatasets, wx.ID_ANY, u"in column", wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_DatasetKeywordColumn.Wrap(-1)
        self.szr_DatasetKeywordTextBoxesOne.Add(self.lbl_DatasetKeywordColumn, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.txt_DatasetKeywordColumn = wx.TextCtrl(self.pnl_MultipleDatasets, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size(30,-1),
                                                    wx.TE_READONLY)
        self.szr_DatasetKeywordTextBoxesOne.Add(self.txt_DatasetKeywordColumn, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.szr_DatasetKeyword.Add(self.szr_DatasetKeywordTextBoxesOne,0,wx.ALL,0)
        self.szr_DatasetKeywordOffset = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_DatasetKeywordOffset.Add((25,25),1,wx.ALL,0)
        self.lbl_DatasetKeywordOffset = wx.StaticText(self.pnl_MultipleDatasets, wx.ID_ANY, u"Offset by", wx.DefaultPosition, wx.DefaultSize, 0)
        self.szr_DatasetKeywordOffset.Add(self.lbl_DatasetKeywordOffset, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.txt_DatasetKeywordOffsetRows = wx.TextCtrl(self.pnl_MultipleDatasets, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size(30,-1),
                                                    wx.TE_READONLY)
        self.szr_DatasetKeywordOffset.Add(self.txt_DatasetKeywordOffsetRows, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.lbl_DatasetKeywordOffsetRows = wx.StaticText(self.pnl_MultipleDatasets, wx.ID_ANY, u"rows and", wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_DatasetKeywordOffsetRows.Wrap(-1)
        self.szr_DatasetKeywordOffset.Add(self.lbl_DatasetKeywordOffsetRows, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.txt_DatasetKeywordOffsetColumns = wx.TextCtrl(self.pnl_MultipleDatasets, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size(30,-1),
                                                        wx.TE_READONLY)
        self.szr_DatasetKeywordOffset.Add(self.txt_DatasetKeywordOffsetColumns, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.lbl_DatasetKeywordOffsetColumns = wx.StaticText(self.pnl_MultipleDatasets, wx.ID_ANY, u"columns.", wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_DatasetKeywordOffsetColumns.Wrap(-1)
        self.szr_DatasetKeywordOffset.Add(self.lbl_DatasetKeywordOffsetColumns, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.szr_DatasetKeyword.Add(self.szr_DatasetKeywordOffset, 0, wx.ALL, 0)
        self.szr_YesMultipleDatasetsRightColumn.Add(self.szr_DatasetKeyword, 0, wx.ALL, 0)
        self.dic_DatasetKeywordGUI = {"keywordlabel":self.lbl_DatasetKeyword,"keyword":self.txt_DatasetKeyword,
                                        "columnlabel":self.lbl_DatasetKeywordColumn,"columntext":self.txt_DatasetKeywordColumn,
                                        "offsetlabel":self.lbl_DatasetKeywordOffset,"offsetrows":self.txt_DatasetKeywordOffsetRows,
                                        "offsetlabel2":self.lbl_DatasetKeywordOffsetRows,"offsetcolumns":self.txt_DatasetKeywordOffsetColumns,
                                        "offsetlabel3":self.lbl_DatasetKeywordOffsetColumns}
        for element in self.dic_DatasetKeywordGUI.keys():
            self.dic_DatasetKeywordGUI[element].Enable(False)
        # Offset from previous
        self.rad_DatasetOffset = wx.RadioButton(self.pnl_MultipleDatasets, wx.ID_ANY, u"Fixed offset from preceding dataset", wx.DefaultPosition,
                                                        wx.DefaultSize,    wx.RB_SINGLE)
        self.rad_DatasetOffset.Enable(False)
        self.szr_YesMultipleDatasetsRightColumn.Add(self.rad_DatasetOffset, 0, wx.ALL, 5)
        self.szr_DatasetOffset = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_DatasetOffset.Add((25,25),0,wx.ALL,0)
        self.lbl_DatasetOffsetBy = wx.StaticText(self.pnl_MultipleDatasets, wx.ID_ANY, u"By", wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_DatasetOffsetBy.Wrap(-1)
        self.lbl_DatasetOffsetBy.Enable(False)
        self.szr_DatasetOffset.Add(self.lbl_DatasetOffsetBy, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.txt_DatasetOffsetRows = wx.TextCtrl(self.pnl_MultipleDatasets, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size(30,-1),
                                                wx.TE_READONLY)
        self.txt_DatasetOffsetRows.Enable(False)
        self.szr_DatasetOffset.Add(self.txt_DatasetOffsetRows, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.lbl_DatasetOffsetRows = wx.StaticText(self.pnl_MultipleDatasets, wx.ID_ANY, u"rows and", wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_DatasetOffsetRows.Wrap(-1)
        self.lbl_DatasetOffsetRows.Enable(False)
        self.szr_DatasetOffset.Add(self.lbl_DatasetOffsetRows, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.txt_DatasetOffsetColumns = wx.TextCtrl(self.pnl_MultipleDatasets, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size(30,-1),
                                                    wx.TE_READONLY)
        self.txt_DatasetOffsetColumns.Enable(False)
        self.szr_DatasetOffset.Add(self.txt_DatasetOffsetColumns, 0, wx.ALL, 5)
        self.lbl_DatasetOffsetColumns = wx.StaticText(self.pnl_MultipleDatasets, wx.ID_ANY, u"columns.", wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_DatasetOffsetColumns.Wrap(-1)
        self.lbl_DatasetOffsetColumns.Enable(False)
        self.szr_DatasetOffset.Add(self.lbl_DatasetOffsetColumns, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.szr_YesMultipleDatasetsRightColumn.Add(self.szr_DatasetOffset, 0, wx.ALL, 0)
        self.dic_DatasetOffsetGUI = {"bylabel":self.lbl_DatasetOffsetBy,
                                        "collabel":self.lbl_DatasetOffsetColumns,
                                        "coltext":self.txt_DatasetOffsetColumns,
                                        "rowlabel":self.lbl_DatasetOffsetRows,
                                        "rowtext":self.txt_DatasetOffsetRows}
        for element in self.dic_DatasetOffsetGUI.keys():
            self.dic_DatasetOffsetGUI[element].Enable(False)
        self.szr_YesMultipleDatasetsRightColumn.Hide(self.szr_DatasetOffset)
        # Empty row
        self.rad_DatasetEmptyLine = wx.RadioButton(self.pnl_MultipleDatasets, wx.ID_ANY, u"Empty row", wx.DefaultPosition, wx.DefaultSize,
                                                    wx.RB_SINGLE)
        self.rad_DatasetEmptyLine.Enable(False)
        self.szr_YesMultipleDatasetsRightColumn.Add(self.rad_DatasetEmptyLine, 0, wx.ALL, 5)

        self.szr_YesMultipleDatasets.Add(self.szr_YesMultipleDatasetsRightColumn, 0, wx.ALL, 0)
        self.szr_MultipleDatasets.Add(self.szr_YesMultipleDatasets, 0, wx.ALL, 0)
        self.szr_MultipleDatasets.Hide(self.szr_YesMultipleDatasets)
        # Dictionaries for hiding screen elements. List in order of hierarchy!
        self.dic_DatasetsDetailsElements = {"keyword":self.szr_DatasetKeyword,
                                                "coordinates":self.szr_DatasetOffset}
        self.dic_DatasetsDetailsHidden = {"keyword":True,
                                            "coordinates":True}

        # All elements added to sizer
        self.pnl_MultipleDatasets.SetSizer( self.szr_MultipleDatasets )
        self.pnl_MultipleDatasets.Layout()
        self.szr_MultipleDatasets.Fit( self.pnl_MultipleDatasets )
        # Add to simplebook #########################################################################################################################
        self.sbk_Wizard.AddPage(self.pnl_MultipleDatasets, u"MultipleDatasets", False)
        self.dic_PageSaveFunctions["MultipleDatasets"] = self.save_multiple_datasets
        #############################################################################################################################################


         #### #   # ####        ####   ###  #####  ###   #### ##### #####  ####
        #     #   # #   #       #   # #   #   #   #   # #     #       #   #
         ###  #   # ####  ##### #   # #####   #   #####  ###  ###     #    ###
            # #   # #   #       #   # #   #   #   #   #     # #       #       #
        ####   ###  ####        ####  #   #   #   #   # ####  #####   #   ####

        # Wizard Page: Sub-datasets #################################################################################################################
        self.pnl_SubDatasets = wx.ScrolledWindow(self.sbk_Wizard,
                                                 style = wx.TAB_TRAVERSAL|wx.VSCROLL)
        self.pnl_SubDatasets.SetScrollRate(5,5)
        self.pnl_SubDatasets.SetBackgroundColour(self.pnlbgclr)
        self.szr_SubDatasets = wx.BoxSizer(wx.VERTICAL)
        #self.lbl_SubDatasets = wx.StaticText(self.pnl_SubDatasets, wx.ID_ANY, u"Sub-datasets", wx.DefaultPosition, wx.DefaultSize, 0)
        #self.lbl_SubDatasets.Wrap(-1)
        #self.szr_SubDatasets.Add(self.lbl_SubDatasets, 0, wx.ALL, 5)
        self.lbl_SubDatasetsExplainer = wx.StaticText(self.pnl_SubDatasets, wx.ID_ANY,
                                                    u"Sub-datasets" + "\n" + "\n"
                                                    u"Some assays generate sub-datasets, that is data that is still connected to the same " +
                                                    u"assay plate or sample. Practical examples would be measurements of the same plate at " +
                                                    u"different wavelengths (e.g. FRET) or timepoints (enzymatic reaction) or different " +
                                                    u"concentrations of the same analyte over the same flow cell in a surface plasmon resonance " +
                                                    u"experiment." + "\n" + "\n" + u"Do we have sub-datasets?",
                                                    wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_SubDatasetsExplainer.Wrap(375)
        self.szr_SubDatasets.Add(self.lbl_SubDatasetsExplainer, 0, wx.ALL, 5)
        self.rad_NoSubDatasets = wx.RadioButton(self.pnl_SubDatasets, wx.ID_ANY, u"No, just a single dataset per plate/sample.", wx.DefaultPosition, wx.DefaultSize,
                                                wx.RB_SINGLE)
        self.rad_NoSubDatasets.SetValue(True)
        self.szr_SubDatasets.Add(self.rad_NoSubDatasets, 0, wx.ALL, 5)
        # Yes, we do have sub-datasets \\\\\
        self.rad_YesSubDatasets = wx.RadioButton(self.pnl_SubDatasets, wx.ID_ANY, u"Yes, e.g. multiple readings at different wavelengths.",
                                                wx.DefaultPosition, wx.DefaultSize, wx.RB_SINGLE)
        self.rad_YesSubDatasets.SetValue(False)
        self.szr_SubDatasets.Add(self.rad_YesSubDatasets, 0, wx.ALL, 5)
        self.szr_YesSubDatasets = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_YesSubDatasets.Add((25,-1),1, wx.ALL,0)
        self.szr_YesSubDatasetsRightColumn = wx.BoxSizer(wx.VERTICAL)
        # Number of sub-datasets
        self.szr_NumberOfSubDatasets = wx.BoxSizer(wx.HORIZONTAL)
        self.lbl_NumberOfSubDatasets = wx.StaticText(self.pnl_SubDatasets, wx.ID_ANY, u"Determine the number of sub-datasets:", wx.DefaultPosition,
                                                    wx.DefaultSize, 0)
        self.lbl_NumberOfSubDatasets.Wrap(-1)
        self.lbl_NumberOfSubDatasets.Enable(False)
        self.szr_NumberOfSubDatasets.Add(self.lbl_NumberOfSubDatasets, 0, wx.ALL, 0)
        self.szr_YesSubDatasetsRightColumn.Add(self.szr_NumberOfSubDatasets, 0, wx.ALL, 0)
        self.szr_DynamicSubDatasets = wx.BoxSizer(wx.HORIZONTAL)
        self.rad_DynamicSubDatasets = wx.RadioButton(self.pnl_SubDatasets, wx.ID_ANY, u"Dynamically determine number of sub-datasets",
                                                    wx.DefaultPosition, wx.DefaultSize, wx.RB_SINGLE)
        self.rad_DynamicSubDatasets.Enable(False)
        self.rad_DynamicSubDatasets.SetValue(True)
        self.szr_DynamicSubDatasets.Add(self.rad_DynamicSubDatasets, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.szr_YesSubDatasetsRightColumn.Add(self.szr_DynamicSubDatasets, 0, wx.ALL, 0)
        self.szr_FixedSubDatasets = wx.BoxSizer(wx.HORIZONTAL)
        self.rad_FixedSubDatasets = wx.RadioButton(self.pnl_SubDatasets, wx.ID_ANY, u"Fixed number of sub-datasets:", wx.DefaultPosition,
                                                    wx.DefaultSize, wx.RB_SINGLE)
        self.rad_FixedSubDatasets.Enable(False)
        self.szr_FixedSubDatasets.Add(self.rad_FixedSubDatasets, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.txt_FixedSubDatasets = wx.TextCtrl(self.pnl_SubDatasets, wx.ID_ANY, u"2", wx.DefaultPosition, wx.Size(30,-1), 0)
        self.txt_FixedSubDatasets.Enable(False)
        self.szr_FixedSubDatasets.Add(self.txt_FixedSubDatasets, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.szr_YesSubDatasetsRightColumn.Add(self.szr_FixedSubDatasets, 0, wx.ALL, 0)
        # Direction of Sub-datasets
        self.lbl_DirectionOfSubDatasets = wx.StaticText(self.pnl_SubDatasets, wx.ID_ANY, u"How are datasets organised", wx.DefaultPosition,
                                                        wx.DefaultSize, 0)
        self.lbl_DirectionOfSubDatasets.Wrap(-1)
        self.lbl_DirectionOfSubDatasets.Enable(False)
        self.szr_YesSubDatasetsRightColumn.Add(self.lbl_DirectionOfSubDatasets, 1, wx.ALL, 0)
        self.rad_SubDatasetsVertically = wx.RadioButton(self.pnl_SubDatasets, wx.ID_ANY, u"Vertically", wx.DefaultPosition,
                                                    wx.DefaultSize, wx.RB_SINGLE)
        self.rad_SubDatasetsVertically.SetValue(True)
        self.rad_SubDatasetsVertically.Enable(False)
        self.szr_YesSubDatasetsRightColumn.Add(self.rad_SubDatasetsVertically, 0, wx.ALL, 5)
        self.rad_SubDatasetsHorizontally = wx.RadioButton(self.pnl_SubDatasets, wx.ID_ANY, u"Horizontally", wx.DefaultPosition,
                                                    wx.DefaultSize, wx.RB_SINGLE)
        self.rad_SubDatasetsHorizontally.Enable(False)
        self.szr_YesSubDatasetsRightColumn.Add(self.rad_SubDatasetsHorizontally, 0, wx.ALL, 5)
        # Separation of sub-datasets
        self.szr_SeparationOfSubDatasets = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_SeparationOfSubDatasetsDetails = wx.BoxSizer(wx.VERTICAL)
        self.lbl_SeparationOfSubDatasets = wx.StaticText(self.pnl_SubDatasets, wx.ID_ANY, u"How are sub-datasets separated:", wx.DefaultPosition,
                                                        wx.DefaultSize, 0)
        self.lbl_SeparationOfSubDatasets.Wrap(-1)
        self.lbl_SeparationOfSubDatasets.Enable(False)
        self.szr_SeparationOfSubDatasetsDetails.Add(self.lbl_SeparationOfSubDatasets, 0, wx.ALL, 0)
        # Same as main dataset
        self.rad_SubDatasetsameAsMain = wx.RadioButton(self.pnl_SubDatasets, wx.ID_ANY, u"Same as main dataset", wx.DefaultPosition,
                                                    wx.DefaultSize, wx.RB_SINGLE)
        self.rad_SubDatasetsameAsMain.SetValue(True)
        self.rad_SubDatasetsameAsMain.Enable(False)
        self.szr_SeparationOfSubDatasetsDetails.Add(self.rad_SubDatasetsameAsMain, 0, wx.ALL, 5)
        # Keyword
        self.rad_SubDatasetKeyword = wx.RadioButton(self.pnl_SubDatasets, wx.ID_ANY, u"Unique keyword and offset:", wx.DefaultPosition,
                                                    wx.DefaultSize, wx.RB_SINGLE)
        self.rad_SubDatasetKeyword.SetValue(False)
        self.rad_SubDatasetKeyword.Enable(False)
        self.szr_SeparationOfSubDatasetsDetails.Add(self.rad_SubDatasetKeyword, 0, wx.ALL, 5)
        self.szr_SubDatasetKeyword = wx.BoxSizer(wx.VERTICAL)
        self.szr_SubDatasetKeywordTextBoxesOne = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_SubDatasetKeywordTextBoxesOne.Add((25,25),1,wx.ALL,0)
        self.lbl_SubDatasetKeyword = wx.StaticText(self.pnl_SubDatasets, wx.ID_ANY, u"Keyword", wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_SubDatasetKeyword.Wrap(-1)
        self.szr_SubDatasetKeywordTextBoxesOne.Add(self.lbl_SubDatasetKeyword,0,wx.ALIGN_CENTER_VERTICAL|wx.ALL,5)
        self.txt_SubDatasetKeyword = wx.TextCtrl(self.pnl_SubDatasets, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, wx.TE_READONLY)
        self.szr_SubDatasetKeywordTextBoxesOne.Add(self.txt_SubDatasetKeyword, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.lbl_SubDatasetKeywordColumn = wx.StaticText(self.pnl_SubDatasets, wx.ID_ANY, u"in column", wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_SubDatasetKeywordColumn.Wrap(-1)
        self.szr_SubDatasetKeywordTextBoxesOne.Add(self.lbl_SubDatasetKeywordColumn, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.txt_SubDatasetKeywordColumn = wx.TextCtrl(self.pnl_SubDatasets, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size(30,-1),
                                                    wx.TE_READONLY)
        self.szr_SubDatasetKeywordTextBoxesOne.Add(self.txt_SubDatasetKeywordColumn, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.szr_SubDatasetKeyword.Add(self.szr_SubDatasetKeywordTextBoxesOne,0,wx.ALL,0)
        self.szr_SubDatasetKeywordOffset = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_SubDatasetKeywordOffset.Add((25,25),1,wx.ALL,0)
        self.lbl_SubDatasetKeywordOffset = wx.StaticText(self.pnl_SubDatasets, wx.ID_ANY, u"Offset by", wx.DefaultPosition, wx.DefaultSize, 0)
        self.szr_SubDatasetKeywordOffset.Add(self.lbl_SubDatasetKeywordOffset, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.txt_SubDatasetKeywordOffsetRows = wx.TextCtrl(self.pnl_SubDatasets, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size(30,-1),
                                                    wx.TE_READONLY)
        self.szr_SubDatasetKeywordOffset.Add(self.txt_SubDatasetKeywordOffsetRows, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.lbl_SubDatasetKeywordOffsetRows = wx.StaticText(self.pnl_SubDatasets, wx.ID_ANY, u"rows and", wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_SubDatasetKeywordOffsetRows.Wrap(-1)
        self.szr_SubDatasetKeywordOffset.Add(self.lbl_SubDatasetKeywordOffsetRows, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.txt_SubDatasetKeywordOffsetColumns = wx.TextCtrl(self.pnl_SubDatasets, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size(30,-1),
                                                        wx.TE_READONLY)
        self.szr_SubDatasetKeywordOffset.Add(self.txt_SubDatasetKeywordOffsetColumns, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.lbl_SubDatasetKeywordOffsetColumns = wx.StaticText(self.pnl_SubDatasets, wx.ID_ANY, u"columns.", wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_SubDatasetKeywordOffsetColumns.Wrap(-1)
        self.szr_SubDatasetKeywordOffset.Add(self.lbl_SubDatasetKeywordOffsetColumns, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.szr_SubDatasetKeyword.Add(self.szr_SubDatasetKeywordOffset, 0, wx.ALL, 0)
        self.szr_SeparationOfSubDatasetsDetails.Add(self.szr_SubDatasetKeyword, 0, wx.ALL, 0)
        self.dic_SubDatasetKeywordGUI = {"keywordlabel":self.lbl_SubDatasetKeyword,"keyword":self.txt_SubDatasetKeyword,
                                        "columnlabel":self.lbl_SubDatasetKeywordColumn,"columntext":self.txt_SubDatasetKeywordColumn,
                                        "offsetlabel":self.lbl_SubDatasetKeywordOffset,"offsetrows":self.txt_SubDatasetKeywordOffsetRows,
                                        "offsetlabel2":self.lbl_SubDatasetKeywordOffsetRows,"offsetcolumns":self.txt_SubDatasetKeywordOffsetColumns,
                                        "offsetlabel3":self.lbl_SubDatasetKeywordOffsetColumns}
        for element in self.dic_SubDatasetKeywordGUI.keys():
            self.dic_SubDatasetKeywordGUI[element].Enable(False)
        # Offset from previous
        self.rad_SubDatasetOffset = wx.RadioButton(self.pnl_SubDatasets, wx.ID_ANY, u"Offset from preceding sub-dataset", wx.DefaultPosition,
                                                        wx.DefaultSize,    wx.RB_SINGLE)
        self.rad_SubDatasetOffset.Enable(False)
        self.szr_SeparationOfSubDatasetsDetails.Add(self.rad_SubDatasetOffset, 0, wx.ALL, 5)
        self.szr_SubDatasetOffset = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_SubDatasetOffset.Add((25,25),0,wx.ALL,0)
        self.lbl_SubDatasetOffsetBy = wx.StaticText(self.pnl_SubDatasets, wx.ID_ANY, u"By", wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_SubDatasetOffsetBy.Wrap(-1)
        self.lbl_SubDatasetOffsetBy.Enable(False)
        self.szr_SubDatasetOffset.Add(self.lbl_SubDatasetOffsetBy, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.txt_SubDatasetOffsetRows = wx.TextCtrl(self.pnl_SubDatasets, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size(30,-1),
                                                wx.TE_READONLY)
        self.txt_SubDatasetOffsetRows.Enable(False)
        self.szr_SubDatasetOffset.Add(self.txt_SubDatasetOffsetRows, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.lbl_SubDatasetOffsetRows = wx.StaticText(self.pnl_SubDatasets, wx.ID_ANY, u"rows and", wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_SubDatasetOffsetRows.Wrap(-1)
        self.lbl_SubDatasetOffsetRows.Enable(False)
        self.szr_SubDatasetOffset.Add(self.lbl_SubDatasetOffsetRows, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.txt_SubDatasetOffsetColumns = wx.TextCtrl(self.pnl_SubDatasets, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size(30,-1),
                                                    wx.TE_READONLY)
        self.txt_SubDatasetOffsetColumns.Enable(False)
        self.szr_SubDatasetOffset.Add(self.txt_SubDatasetOffsetColumns, 0, wx.ALL, 5)
        self.lbl_SubDatasetOffsetColumns = wx.StaticText(self.pnl_SubDatasets, wx.ID_ANY, u"columns.", wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_SubDatasetOffsetColumns.Wrap(-1)
        self.lbl_SubDatasetOffsetColumns.Enable(False)
        self.szr_SubDatasetOffset.Add(self.lbl_SubDatasetOffsetColumns, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.szr_SeparationOfSubDatasetsDetails.Add(self.szr_SubDatasetOffset, 0, wx.ALL, 0)
        self.dic_SubDatasetOffsetGUI = {"bylabel":self.lbl_SubDatasetOffsetBy,
                                        "collabel":self.lbl_SubDatasetOffsetColumns,
                                        "coltext":self.txt_SubDatasetOffsetColumns,
                                        "rowlabel":self.lbl_SubDatasetOffsetRows,
                                        "rowtext":self.txt_SubDatasetOffsetRows}
        for element in self.dic_SubDatasetOffsetGUI.keys():
            self.dic_SubDatasetOffsetGUI[element].Enable(False)
        self.szr_SeparationOfSubDatasetsDetails.Hide(self.szr_SubDatasetOffset)
        # Empty row
        self.szr_SubDatasetEmptyLine = wx.BoxSizer(wx.HORIZONTAL)
        self.rad_SubDatasetEmptyLine = wx.RadioButton(self.pnl_SubDatasets, wx.ID_ANY, u"Empty row", wx.DefaultPosition, wx.DefaultSize,
                                                    wx.RB_SINGLE)
        self.rad_SubDatasetEmptyLine.Enable(False)
        self.szr_SubDatasetEmptyLine.Add(self.rad_SubDatasetEmptyLine, 0, wx.ALL, 5)
        self.szr_SeparationOfSubDatasetsDetails.Add(self.szr_SubDatasetEmptyLine, 0, wx.ALL, 0)

        self.szr_SeparationOfSubDatasets.Add(self.szr_SeparationOfSubDatasetsDetails, 0, wx.ALL, 0)

        self.szr_YesSubDatasetsRightColumn.Add(self.szr_SeparationOfSubDatasets, 0, wx.ALL, 0)
        self.szr_YesSubDatasets.Add(self.szr_YesSubDatasetsRightColumn, 0, wx.ALL, 0)
        self.szr_SubDatasets.Add(self.szr_YesSubDatasets, 0, wx.ALL, 0)
        self.szr_SubDatasets.Hide(self.szr_YesSubDatasets)
        # Dictionaries for hiding screen elements. List in order of hierarchy!
        self.dic_SubDatasetsDetailsElements = {"keyword":self.szr_SubDatasetKeyword,
                                                "coordinates":self.szr_SubDatasetOffset}
        self.dic_SubDatasetsDetailsHidden = {"keyword":True,
                                            "coordinates":True}
        # All elements added to sizer
        self.pnl_SubDatasets.SetSizer( self.szr_SubDatasets )
        self.pnl_SubDatasets.Layout()
        self.szr_SubDatasets.Fit( self.pnl_SubDatasets )
        # Add to simplebook #########################################################################################################################
        self.sbk_Wizard.AddPage(self.pnl_SubDatasets, u"SubDatasets", False)
        self.dic_PageSaveFunctions["SubDatasets"] = self.save_sub_datasets
        #############################################################################################################################################

         #### #####  ###  ####
        #       #   #   # #   #
         ###    #   #   # ####
            #   #   #   # #
        ####    #    ###  #

        # Stop ######################################################################################################################################
        self.pnl_Stop = wx.ScrolledWindow(self.sbk_Wizard,
                                          style = wx.TAB_TRAVERSAL|wx.VSCROLL)
        self.pnl_Stop.SetScrollRate(5,5)
        self.pnl_Stop.SetBackgroundColour(self.pnlbgclr)
        self.szr_Stop = wx.BoxSizer(wx.VERTICAL)
        self.lbl_TransfersStop = wx.StaticText(self.pnl_Stop,
                                               label = u"Find end of data entries by")
        self.lbl_TransfersStop.Wrap(-1)
        self.szr_Stop.Add(self.lbl_TransfersStop, 0, wx.ALL, 5)
        # Keyword
        self.szr_StopKeyword = wx.BoxSizer(wx.HORIZONTAL)
        self.rad_StopKeyword = wx.RadioButton(self.pnl_Stop,
                                              label = u"unique keyword",
                                              style =  wx.RB_SINGLE)
        self.rad_StopKeyword.SetValue(True)
        self.szr_StopKeyword.Add(self.rad_StopKeyword, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.txt_StopKeyword = wx.TextCtrl(self.pnl_Stop,
                                           style = wx.TE_READONLY)
        self.szr_StopKeyword.Add(self.txt_StopKeyword, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.lbl_StopKeywordColumn = wx.StaticText(self.pnl_Stop,
                                                   label = u"in column")
        self.lbl_StopKeywordColumn.Wrap(-1)
        self.szr_StopKeyword.Add(self.lbl_StopKeywordColumn, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.txt_StopKeywordColumn = wx.TextCtrl(self.pnl_Stop,
                                                 size = wx.Size(30,-1),
                                                 style = wx.TE_READONLY)
        self.szr_StopKeyword.Add(self.txt_StopKeywordColumn, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.szr_Stop.Add(self.szr_StopKeyword, 0, wx.ALL, 5)
        self.dic_StopKeywordGUI = {"text":self.txt_StopKeyword,"columnlabel":self.lbl_StopKeywordColumn,"columntext":self.txt_StopKeywordColumn}
        # Coordinates
        self.szr_StopCoordinates = wx.BoxSizer(wx.HORIZONTAL)
        self.rad_StopCoordinates = wx.RadioButton(self.pnl_Stop,
                                                  label = u"absolute coordinates:",
                                                  style = wx.RB_SINGLE)
        self.szr_StopCoordinates.Add(self.rad_StopCoordinates, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.lbl_StopCoordinatesColumn = wx.StaticText(self.pnl_Stop, wx.ID_ANY, u"Column", wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_StopCoordinatesColumn.Wrap(-1)
        self.lbl_StopCoordinatesColumn.Enable(False)
        self.szr_StopCoordinates.Add(self.lbl_StopCoordinatesColumn, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.txt_StopCoordinatesColumn = wx.TextCtrl(self.pnl_Stop, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size(30,-1), wx.TE_READONLY)
        self.txt_StopCoordinatesColumn.Enable(False)
        self.szr_StopCoordinates.Add(self.txt_StopCoordinatesColumn, 0, wx.ALL, 5)
        self.lbl_StopCoordinatesRow = wx.StaticText(self.pnl_Stop, wx.ID_ANY, u"Row", wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_StopCoordinatesRow.Wrap(-1)
        self.lbl_StopCoordinatesRow.Enable(False)
        self.szr_StopCoordinates.Add(self.lbl_StopCoordinatesRow, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.txt_StopCoordinatesRow = wx.TextCtrl(self.pnl_Stop, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size(30,-1), wx.TE_READONLY)
        self.txt_StopCoordinatesRow.Enable(False)
        self.szr_StopCoordinates.Add(self.txt_StopCoordinatesRow, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.szr_Stop.Add(self.szr_StopCoordinates, 0, wx.ALL, 5)
        self.dic_StopCoordinatesGUI = {"collabel":self.lbl_StopCoordinatesColumn,
                                       "coltext":self.txt_StopCoordinatesColumn,
                                       "rowlabel":self.lbl_StopCoordinatesRow,
                                       "rowtext":self.txt_StopCoordinatesRow}
        # Empty row
        self.szr_StopEmptyLine = wx.BoxSizer(wx.HORIZONTAL)
        self.rad_StopEmptyLine = wx.RadioButton(self.pnl_Stop,
                                                label = u"Empty row",
                                                style = wx.RB_SINGLE)
        self.szr_StopEmptyLine.Add(self.rad_StopEmptyLine, 0, wx.ALL, 5)
        self.szr_Stop.Add(self.szr_StopEmptyLine, 0, wx.ALL, 5)
        # All elements added to sizer
        self.pnl_Stop.SetSizer( self.szr_Stop )
        self.pnl_Stop.Layout()
        self.szr_Stop.Fit( self.pnl_Stop )
        # Add to simplebook #########################################################################################################################
        self.sbk_Wizard.AddPage(self.pnl_Stop, u"EndOfDataset", False)
        #############################################################################################################################################


        # Add simplebook to main sizer ##############################################################################################################
        self.szr_Wizard.Add(self.sbk_Wizard, 1, wx.EXPAND|wx.ALL, 5)

        # Simplebook Next/Back/Finish buttons #######################################################################################################
        self.szr_WizardButtons = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_WizardButtons.SetMinSize(wx.Size(420,35))
        self.szr_WizardButtons.Add((-1,-1), 1 , wx.EXPAND, 5)
        self.btn_WizardBack = wx.Button(self.pnl_Wizard,
                                        label = u"< Back",
                                        size = wx.Size(50,25))
        self.btn_WizardBack.Enable(False)
        self.szr_WizardButtons.Add(self.btn_WizardBack, 0, wx.ALL, 5)
        self.btn_WizardNext = wx.Button(self.pnl_Wizard,
                                        label = u"Next >",
                                        size = wx.Size(50,25))
        self.szr_WizardButtons.Add(self.btn_WizardNext, 0, wx.ALL, 5)
        self.btn_WizardPrintRules = wx.Button(self.pnl_Wizard, 
                                              label = u"Print rules", 
                                              size = wx.Size(50,25))
        self.szr_WizardButtons.Add(self.btn_WizardPrintRules, 0, wx.ALL, 5)

        self.szr_Wizard.Add(self.szr_WizardButtons, 0, wx.FIXED_MINSIZE, 5)
        self.pnl_Wizard.SetSizer(self.szr_Wizard)
        self.pnl_Wizard.Layout()
        self.szr_Wizard.Fit(self.pnl_Wizard)

        # Finish RawDataWizard Sizer
        self.szr_Surround.Add(self.pnl_Wizard, 0, wx.EXPAND, 5)


        # Raw Data File Direct Read Grid ############################################################################################################
        self.grd_ExampleFile = wx.grid.Grid(self)
        # Grid
        self.grd_ExampleFile.CreateGrid(0, 0)
        self.grd_ExampleFile.EnableEditing(False)
        self.grd_ExampleFile.EnableGridLines(True)
        self.grd_ExampleFile.EnableDragGridSize(False)
        self.grd_ExampleFile.SetMargins(0, 0)
        # Columns
        self.grd_ExampleFile.EnableDragColMove(False)
        self.grd_ExampleFile.EnableDragColSize(True)
        self.grd_ExampleFile.SetColLabelAlignment(wx.ALIGN_CENTER, wx.ALIGN_CENTER)
        # Rows
        self.grd_ExampleFile.EnableDragRowSize(True)
        self.grd_ExampleFile.SetRowLabelSize(30)
        self.grd_ExampleFile.SetRowLabelAlignment(wx.ALIGN_CENTER, wx.ALIGN_CENTER)
        # Label Appearance
        # N/A
        # Cell Defaults
        self.dic_CurrentGridHighlights = {}
        self.grd_ExampleFile.SetDefaultCellAlignment(wx.ALIGN_LEFT, wx.ALIGN_TOP)
        self.szr_Surround.Add(self.grd_ExampleFile, 1, wx.ALL, 5)
        self.grd_ExampleFile.Show(False)
        #############################################################################################################################################

        self.SetSizer( self.szr_Surround )
        self.Layout()

        self.Centre( wx.BOTH )

        ####  # #   # ####  # #   #  ####
        #   # # ##  # #   # # ##  # #
        ####  # ##### #   # # ##### #  ##
        #   # # #  ## #   # # #  ## #   #
        ####  # #   # ####  # #   #  ####

        # Bindings ##################################################################################################################################
        
        # Example File And Verification Wizard Page
        self.fpk_RawDataFile.Bind(wx.EVT_FILEPICKER_CHANGED, self.FileSelected)
        self.btn_ParseFile.Bind(wx.EVT_BUTTON, self.ParseRawDataFile)
        self.chk_Verification.Bind(wx.EVT_CHECKBOX, self.OnChkVerification)
        self.rad_VerificationKeywordColumn.Bind(wx.EVT_CHECKBOX, self.OnChkVerificationKWCol)
        self.rad_VerificationKeywordRow.Bind(wx.EVT_CHECKBOX, self.OnChkVerificationKWRow)
        self.chk_VerificationExact.Bind(wx.EVT_CHECKBOX, self.OnChkVerificationExact)

        # Data Organisation Wizard Page
        self.rad_Plate.Bind(wx.EVT_RADIOBUTTON, self.OnRadPlate)
        self.rad_Sample.Bind(wx.EVT_RADIOBUTTON, self.OnRadSample)
        self.rad_Grid.Bind(wx.EVT_RADIOBUTTON, self.OnRadGrid)
        self.rad_Table.Bind(wx.EVT_RADIOBUTTON, self.OnRadTable)
        self.rad_StartKeyword.Bind(wx.EVT_RADIOBUTTON, self.OnRadStartKeyword)
        self.chk_StartKeywordExact.Bind(wx.EVT_CHECKBOX, self.OnChkStartKeywordExact)
        self.rad_StartCoordinates.Bind(wx.EVT_RADIOBUTTON, self.OnRadStartCoordinates)

        # Multiple Datasets Wizard Page
        self.rad_SingleDataset.Bind(wx.EVT_RADIOBUTTON, self.OnRadSingleDataset)
        self.rad_MultipleDatasets.Bind(wx.EVT_RADIOBUTTON, self.OnRadMultipleDatasets)
        self.rad_FixedDatasets.Bind(wx.EVT_RADIOBUTTON, self.OnRadFixedDatasets)
        self.txt_FixedDatasets.Bind(wx.EVT_TEXT, lambda event: self.OnText(event, True))
        self.rad_DatasetsVertically.Bind(wx.EVT_CHECKBOX, self.OnRadDatasetsVertically)
        self.rad_DatasetsHorizontally.Bind(wx.EVT_CHECKBOX, self.OnRadDatasetsHorizontally)
        self.rad_DynamicDatasets.Bind(wx.EVT_RADIOBUTTON, self.OnRadDynamicDatasets)
        self.rad_DatasetSameAsMain.Bind(wx.EVT_RADIOBUTTON, self.OnRadDatasetSameAsMain)
        self.rad_DatasetKeyword.Bind(wx.EVT_RADIOBUTTON, self.OnRadDatasetKeyword)
        self.rad_DatasetOffset.Bind(wx.EVT_RADIOBUTTON, self.OnRadDatasetOffset)
        self.rad_DatasetEmptyLine.Bind(wx.EVT_RADIOBUTTON, self.OnRadDatasetEmptyLine)

        # Sub-Datasets Wizard Page
        self.rad_NoSubDatasets.Bind(wx.EVT_RADIOBUTTON, self.OnRadNoSubDatasets)
        self.rad_YesSubDatasets.Bind(wx.EVT_RADIOBUTTON, self.OnRadYesSubDatasets)
        self.rad_FixedSubDatasets.Bind(wx.EVT_RADIOBUTTON, self.OnRadFixedSubDatasets)
        self.rad_DynamicSubDatasets.Bind(wx.EVT_RADIOBUTTON, self.OnRadDynamicSubDatasets)
        self.rad_SubDatasetsVertically.Bind(wx.EVT_RADIOBUTTON, self.OnRadSubDatasetsVertically)
        self.rad_SubDatasetsHorizontally.Bind(wx.EVT_RADIOBUTTON, self.OnRadSubDatasetsHorizontally)
        self.rad_SubDatasetsameAsMain.Bind(wx.EVT_RADIOBUTTON, self.OnRadSubDatasetSameAsMain)
        self.rad_SubDatasetKeyword.Bind(wx.EVT_RADIOBUTTON, self.OnRadSubDatasetKeyword)
        self.rad_SubDatasetOffset.Bind(wx.EVT_RADIOBUTTON, self.OnRadSubDatasetOffset)
        self.rad_SubDatasetEmptyLine.Bind(wx.EVT_RADIOBUTTON, self.OnRadSubDatasetEmptyLine)

        # Beginning of Datasets Wizard Page
        self.rad_StopKeyword.Bind(wx.EVT_RADIOBUTTON, self.OnRadStopKeyword)
        self.rad_StopCoordinates.Bind(wx.EVT_RADIOBUTTON, self.OnRadStopCoordinates)
        self.rad_StopEmptyLine.Bind(wx.EVT_RADIOBUTTON, self.OnRadStopEmptyLine)

        # Wizard navigation buttons
        self.btn_WizardBack.Bind(wx.EVT_BUTTON, self.on_wzd_back)
        self.btn_WizardNext.Bind(wx.EVT_BUTTON, self.on_wzd_next)
        self.btn_WizardPrintRules.Bind(wx.EVT_BUTTON, self.PrintRules)

        # Example File Direct Read Grid
        self.grd_ExampleFile.Bind(wx.grid.EVT_GRID_CELL_RIGHT_CLICK, self.OnGridFrightClick)
        #############################################################################################################################################


    def __del__( self ):
        pass

    def on_wzd_back(self, event):
        """
        Event handler. Goes back one page in the wizard.
        """
        # Get page indices
        int_CurrentPage = self.sbk_Wizard.GetSelection()
        int_BackPage = int_CurrentPage - 1

        # Save information and check whether we can proceed:
        str_Proceed = self.dic_PageSaveFunctions[self.sbk_Wizard.GetPageText(int_CurrentPage)]()
        if "Backward" in str_Proceed:
            if int_BackPage >= 0:
                self.sbk_Wizard.SetSelection(int_BackPage)
                # Ensure buttons are enabled/disabled correctly:
                if int_BackPage == 0:
                    self.btn_WizardBack.Enable(False)
                if int_BackPage < self.sbk_Wizard.GetPageCount()-1:
                    self.btn_WizardNext.Enable(True)
        
        
        # Check for grid highlights:

    def on_wzd_next(self, event):
        # Get page indices
        int_CurrentPage = self.sbk_Wizard.GetSelection()
        int_NextPage = int_CurrentPage + 1

        # Save information and check whether we can proceed:
        str_Proceed = self.dic_PageSaveFunctions[self.sbk_Wizard.GetPageText(int_CurrentPage)]()
        if not "Stop" in str_Proceed:
            if int_NextPage < self.sbk_Wizard.GetPageCount():
                self.sbk_Wizard.SetSelection(int_NextPage)
                # Ensure buttons are enabled/disabled correctly:
                if int_NextPage > 0:
                    self.btn_WizardBack.Enable(True)
                if int_NextPage == self.sbk_Wizard.GetPageCount()-1:
                    self.btn_WizardNext.Enable(False)
        else:
            mb.info(self, "One or more fields have not been filled out.")

        # Check for grid highlights:
    

    ##### #   # ##### #   # #####    #   #  ###  #   # ####  #     ##### ####   ####
    #     #   # #     ##  #   #      #   # #   # ##  # #   # #     #     #   # #
    ###   #   # ###   #####   #      ##### ##### ##### #   # #     ###   ####   ###
    #      # #  #     #  ##   #      #   # #   # #  ## #   # #     #     #   #     #
    #####   #   ##### #   #   #      #   # #   # #   # ####  ##### ##### #   # ####

    # Event handlers for simple book pages ##########################################################################################################

    def OnText(self, event, zero=False):
        str_Input = event.GetEventObject().GetLineText(0)
        if len(str_Input) == 0:
            mb.info(self,"Field can't be empty.")
        if zero == True and str_Input == "0":
            mb.info(self,"Field can't be 0 (zero).")


    def OnChkVerification(self, event):
        bool_Verification = self.chk_Verification.GetValue()
        self.txt_VerificationKeyword.Enable(bool_Verification)
        self.txt_VerificationKeywordEditable.Enable(bool_Verification)
        self.rad_VerificationKeywordColumn.Enable(bool_Verification)
        self.txt_VerificationKeywordColumn.Enable(bool_Verification)
        self.rad_VerificationKeywordRow.Enable(bool_Verification)
        self.txt_VerificationKeywordRow.Enable(bool_Verification)
        self.chk_VerificationExact.Enable(bool_Verification)

    def OnChkVerificationKWCol(self, event):
        bol = event.GetEventObject().GetValue()
        self.rad_VerificationKeywordColumn.Enable(bol)
        self.rad_VerificationKeywordRow.Enable(bol)

    def OnChkVerificationKWRow(self, event):
        bol = event.GetEventObject().GetValue()
        self.rad_VerificationKeywordColumn.Enable(bol)
        self.rad_VerificationKeywordRow.Enable(bol)

    def OnChkVerificationExact(self, event):
        bool_CheckBox = self.chk_VerificationExact.GetValue()
        self.txt_VerificationKeyword.Show(bool_CheckBox)
        self.txt_VerificationKeyword.Enable(bool_CheckBox)
        self.txt_VerificationKeywordEditable.Show(not bool_CheckBox)
        self.txt_VerificationKeywordEditable.Enable(not bool_CheckBox)
        self.szr_VerificationKeyword.Layout()

    def OnRadPlate(self, event):
        self.rad_Sample.SetValue(False)
        self.szr_DataOrganisation.Show(self.szr_Wells)

        self.szr_DataOrganisation.Layout()

    def OnRadSample(self, event):
        self.rad_Plate.SetValue(False)
        self.szr_DataOrganisation.Hide(self.szr_Wells)

        self.szr_DataOrganisation.Layout()


    def OnRadGrid(self, event):
        self.rad_Table.SetValue(False)
        self.lbl_GridMoreInfo.Enable(True)
        self.chk_GridLabelsIncluded.Enable(True)

        self.szr_DataOrganisation.Show(self.szr_GridMoreInfo)
        self.szr_DataOrganisation.Layout()

    def OnRadTable(self, event):
        self.rad_Grid.SetValue(False)
        self.lbl_GridMoreInfo.Enable(False)
        self.chk_GridLabelsIncluded.Enable(False)

        self.szr_DataOrganisation.Hide(self.szr_GridMoreInfo)
        self.szr_DataOrganisation.Layout()

    def OnRadStartKeyword(self,event):

        for element in self.dic_StartKeywordGUI:
            self.dic_StartKeywordGUI[element].Enable(True)
        self.szr_BeginningOfDataset.Show(self.szr_StartKeyword)
        # Ensure the correct textctrl is showing by calling the event handler with a dummy event:
        self.OnChkStartKeywordExact(None)

        for element in self.dic_StartCoordinatesGUI:
            self.dic_StartCoordinatesGUI[element].Enable(False)
        self.szr_BeginningOfDataset.Hide(self.szr_StartCoordinates)
        self.rad_StartCoordinates.SetValue(False)

        self.szr_BeginningOfDataset.Layout()
        self.szr_DataOrganisation.Layout()

    def OnRadStartCoordinates(self,event):

        for element in self.dic_StartKeywordGUI:
            self.dic_StartKeywordGUI[element].Enable(False)
        self.szr_BeginningOfDataset.Hide(self.szr_StartKeyword)
        self.rad_StartKeyword.SetValue(False)

        for element in self.dic_StartCoordinatesGUI:
            self.dic_StartCoordinatesGUI[element].Enable(True)
        self.szr_BeginningOfDataset.Show(self.szr_StartCoordinates)

        self.szr_BeginningOfDataset.Layout()
        self.szr_DataOrganisation.Layout()

    def OnChkStartKeywordExact(self, event):
        bool_Exact = self.chk_StartKeywordExact.GetValue()
        self.txt_StartKeywordEditable.Show(not bool_Exact)
        self.txt_StartKeyword.Show(bool_Exact)
        self.szr_StartKeywordTextBoxes.Layout()
        
    def OnRadNoSubDatasets(self, event):
        self.Freeze()

        self.szr_SubDatasets.Hide(self.szr_YesSubDatasets)

        self.lbl_DirectionOfSubDatasets.Enable(True)
        self.rad_SubDatasetsVertically.Enable(True)
        self.rad_SubDatasetsHorizontally.Enable(True)

        self.rad_YesSubDatasets.SetValue(False)
        self.lbl_NumberOfSubDatasets.Enable(False)
        self.rad_FixedSubDatasets.Enable(False)
        self.txt_FixedSubDatasets.Enable(False)
        self.rad_DynamicSubDatasets.Enable(False)
        
        self.rad_SubDatasetsameAsMain.Enable(False)
        self.lbl_SeparationOfSubDatasets.Enable(False)
        self.rad_SubDatasetKeyword.Enable(False)
        for element in self.dic_SubDatasetKeywordGUI.keys():
            self.dic_SubDatasetKeywordGUI[element].Enable(False)
        self.rad_SubDatasetOffset.Enable(False)
        for element in self.dic_SubDatasetOffsetGUI.keys():
            self.dic_SubDatasetOffsetGUI[element].Enable(False)
        self.rad_SubDatasetEmptyLine.Enable(False)

        self.Layout()
        self.Thaw()
    
    def OnRadYesSubDatasets(self, event):
        self.Freeze()

        self.rad_NoSubDatasets.SetValue(False)
        self.lbl_NumberOfSubDatasets.Enable(True)
        self.rad_FixedSubDatasets.Enable(True)
        self.txt_FixedSubDatasets.Enable(self.rad_FixedSubDatasets.GetValue())
        self.rad_DynamicSubDatasets.Enable(True)

        self.lbl_DirectionOfSubDatasets.Enable(True)
        self.rad_SubDatasetsVertically.Enable(True)
        self.rad_SubDatasetsHorizontally.Enable(True)

        self.lbl_SeparationOfSubDatasets.Enable(True)

        self.rad_SubDatasetsameAsMain.Enable(True)
        self.rad_SubDatasetKeyword.Enable(True)
        if self.rad_SubDatasetKeyword.GetValue() == True:
            for element in self.dic_SubDatasetKeywordGUI.keys():
                self.dic_SubDatasetKeywordGUI[element].Enable(True)
        self.rad_SubDatasetOffset.Enable(True)
        if self.rad_SubDatasetOffset.GetValue() == True:
            for element in self.dic_SubDatasetOffsetGUI.keys():
                self.dic_SubDatasetOffsetGUI[element].Enable(True)
        self.rad_SubDatasetEmptyLine.Enable(True)

        # Hide/show sizers based on dictionary values (updated by event handlers for corresponding radiobuttons)
        self.szr_SubDatasets.Show(self.szr_YesSubDatasets, True)
        for element in self.dic_SubDatasetsDetailsElements.keys():
            if self.dic_SubDatasetsDetailsHidden[element] == True:
                self.szr_SeparationOfSubDatasetsDetails.Hide(self.dic_SubDatasetsDetailsElements[element])
            else:
                self.szr_SeparationOfSubDatasetsDetails.Show(self.dic_SubDatasetsDetailsElements[element])
        self.szr_SubDatasets.Layout()
        self.Thaw()

    def OnRadFixedSubDatasets(self, event):
        self.rad_DynamicSubDatasets.SetValue(False)
        self.txt_FixedSubDatasets.Enable(True)

    def OnRadDynamicSubDatasets(self, event):
        self.rad_FixedSubDatasets.SetValue(False)
        self.txt_FixedSubDatasets.Enable(False)

    def OnRadSubDatasetsVertically(self, event):
        self.rad_SubDatasetsHorizontally.SetValue(False)

    def OnRadSubDatasetsHorizontally(self, event):
        self.rad_SubDatasetsVertically.SetValue(False)

    def OnRadSubDatasetSameAsMain(self, event):
        self.rad_SubDatasetKeyword.SetValue(False)
        self.rad_SubDatasetOffset.SetValue(False)
        self.rad_SubDatasetEmptyLine.SetValue(False)
        for element in self.dic_SubDatasetKeywordGUI.keys():
            self.dic_SubDatasetKeywordGUI[element].Enable(False)
        for element in self.dic_SubDatasetOffsetGUI.keys():
            self.dic_SubDatasetOffsetGUI[element].Enable(False)
        self.dic_SubDatasetsDetailsHidden["keyword"] = True
        self.szr_SeparationOfSubDatasetsDetails.Hide(self.dic_SubDatasetsDetailsElements["keyword"])
        self.dic_SubDatasetsDetailsHidden["coordinates"] = True
        self.szr_SeparationOfSubDatasetsDetails.Hide(self.dic_SubDatasetsDetailsElements["coordinates"])
        self.szr_SubDatasets.Layout()

    def OnRadSubDatasetKeyword(self, event):
        self.rad_SubDatasetsameAsMain.SetValue(False)
        self.rad_SubDatasetOffset.SetValue(False)
        self.rad_SubDatasetEmptyLine.SetValue(False)
        for element in self.dic_SubDatasetKeywordGUI.keys():
            self.dic_SubDatasetKeywordGUI[element].Enable(True)
        for element in self.dic_SubDatasetOffsetGUI.keys():
            self.dic_SubDatasetOffsetGUI[element].Enable(False)
        self.dic_SubDatasetsDetailsHidden["keyword"] = False
        self.szr_SeparationOfSubDatasetsDetails.Show(self.dic_SubDatasetsDetailsElements["keyword"])
        self.dic_SubDatasetsDetailsHidden["coordinates"] = True
        self.szr_SeparationOfSubDatasetsDetails.Hide(self.dic_SubDatasetsDetailsElements["coordinates"])
        self.szr_SubDatasets.Layout()

    def OnRadSubDatasetOffset(self, event):
        self.rad_SubDatasetsameAsMain.SetValue(False)
        self.rad_SubDatasetKeyword.SetValue(False)
        self.rad_SubDatasetEmptyLine.SetValue(False)
        for element in self.dic_SubDatasetKeywordGUI.keys():
            self.dic_SubDatasetKeywordGUI[element].Enable(False)
        for element in self.dic_SubDatasetOffsetGUI.keys():
            self.dic_SubDatasetOffsetGUI[element].Enable(True)
        self.dic_SubDatasetsDetailsHidden["keyword"] = True
        self.szr_SeparationOfSubDatasetsDetails.Hide(self.dic_SubDatasetsDetailsElements["keyword"])
        self.dic_SubDatasetsDetailsHidden["coordinates"] = False
        self.szr_SeparationOfSubDatasetsDetails.Show(self.dic_SubDatasetsDetailsElements["coordinates"])
        self.szr_SubDatasets.Layout()

    def OnRadSubDatasetEmptyLine(self, event):
        self.rad_SubDatasetsameAsMain.SetValue(False)
        self.rad_SubDatasetKeyword.SetValue(False)
        self.rad_SubDatasetOffset.SetValue(False)
        for element in self.dic_SubDatasetKeywordGUI.keys():
            self.dic_SubDatasetKeywordGUI[element].Enable(False)
        for element in self.dic_SubDatasetOffsetGUI.keys():
            self.dic_SubDatasetOffsetGUI[element].Enable(False)
        self.dic_SubDatasetsDetailsHidden["keyword"] = True
        self.szr_SeparationOfSubDatasetsDetails.Hide(self.dic_SubDatasetsDetailsElements["keyword"])
        self.dic_SubDatasetsDetailsHidden["coordinates"] = True
        self.szr_SeparationOfSubDatasetsDetails.Hide(self.dic_SubDatasetsDetailsElements["coordinates"])
        self.szr_SubDatasets.Layout()

    def OnRadSingleDataset(self, event):
        self.Freeze()

        self.szr_MultipleDatasets.Hide(self.szr_YesMultipleDatasets)

        self.rad_MultipleDatasets.SetValue(False)

        self.lbl_DirectionOfDatasets.Enable(True)
        self.rad_DatasetsVertically.Enable(True)
        self.rad_DatasetsHorizontally.Enable(True)

        self.lbl_NumberOfDatasets.Enable(False)
        self.rad_FixedDatasets.Enable(False)
        self.txt_FixedDatasets.Enable(self.rad_FixedDatasets.GetValue())
        self.rad_DynamicDatasets.Enable(False)

        self.lbl_SeparationOfDatasets.Enable(False)

        self.rad_DatasetSameAsMain.Enable(False)
        self.rad_DatasetKeyword.Enable(False)
        for element in self.dic_DatasetKeywordGUI.keys():
            self.dic_DatasetKeywordGUI[element].Enable(False)
        self.rad_DatasetOffset.Enable(False)
        for element in self.dic_DatasetOffsetGUI.keys():
            self.dic_DatasetOffsetGUI[element].Enable(False)
        self.rad_DatasetEmptyLine.Enable(False)

        self.Layout()
        self.Thaw()

    def OnRadMultipleDatasets(self, event):
        self.Freeze()

        self.szr_MultipleDatasets.Show(self.szr_YesMultipleDatasets)

        self.rad_SingleDataset.SetValue(False)

        self.lbl_DirectionOfDatasets.Enable(True)
        self.rad_DatasetsVertically.Enable(True)
        self.rad_DatasetsHorizontally.Enable(True)

        self.lbl_NumberOfDatasets.Enable(True)
        self.rad_FixedDatasets.Enable(True)
        self.txt_FixedDatasets.Enable(self.rad_FixedDatasets.GetValue())
        self.rad_DynamicDatasets.Enable(True)

        self.lbl_SeparationOfDatasets.Enable(True)

        self.rad_DatasetSameAsMain.Enable(True)
        self.rad_DatasetKeyword.Enable(True)
        if self.rad_DatasetKeyword.GetValue() == True:
            for element in self.dic_DatasetKeywordGUI.keys():
                self.dic_DatasetKeywordGUI[element].Enable(True)
        self.rad_DatasetOffset.Enable(True)
        if self.rad_DatasetOffset.GetValue() == True:
            for element in self.dic_DatasetOffsetGUI.keys():
                self.dic_DatasetOffsetGUI[element].Enable(True)
        self.rad_DatasetEmptyLine.Enable(True)

        # Hide/show sizers based on dictionary values (updated by event handlers for corresponding radiobuttons)
        self.szr_MultipleDatasets.Show(self.szr_YesMultipleDatasets, True)
        for element in self.dic_DatasetsDetailsElements.keys():
            if self.dic_DatasetsDetailsHidden[element] == True:
                self.szr_YesMultipleDatasetsRightColumn.Hide(self.dic_DatasetsDetailsElements[element])
            else:
                self.szr_YesMultipleDatasetsRightColumn.Show(self.dic_DatasetsDetailsElements[element])
        
        self.szr_MultipleDatasets.Layout()
        self.Thaw()

    def OnRadFixedDatasets(self, event):
        self.rad_DynamicDatasets.SetValue(False)
        self.txt_FixedDatasets.Enable(True)

    def OnRadDynamicDatasets(self, event):
        self.rad_FixedDatasets.SetValue(False)
        self.txt_FixedDatasets.Enable(False)

    def OnRadDatasetsVertically(self, event):
        self.rad_DatasetsHorizontally.SetValue(False)
    
    def OnRadDatasetsHorizontally(self, event):
        self.rad_DatasetsVertically.SetValue(False)

    def OnRadDatasetSameAsMain(self, event):
        self.rad_DatasetKeyword.SetValue(False)
        self.rad_DatasetOffset.SetValue(False)
        self.rad_DatasetEmptyLine.SetValue(False)
        for element in self.dic_DatasetKeywordGUI.keys():
            self.dic_DatasetKeywordGUI[element].Enable(False)
            self.dic_DatasetKeywordGUI[element].Show(False)
        for element in self.dic_DatasetOffsetGUI.keys():
            self.dic_DatasetOffsetGUI[element].Enable(False)
            self.dic_DatasetOffsetGUI[element].Show(False)
        self.dic_DatasetsDetailsHidden["keyword"] = True
        self.szr_YesMultipleDatasetsRightColumn.Hide(self.dic_DatasetsDetailsElements["keyword"])
        self.dic_DatasetsDetailsHidden["coordinates"] = True
        self.szr_YesMultipleDatasetsRightColumn.Hide(self.dic_DatasetsDetailsElements["coordinates"])
        # Layout all relevant sizers
        self.szr_YesMultipleDatasetsRightColumn.Layout()
        self.szr_YesMultipleDatasets.Layout()
        self.szr_MultipleDatasets.Layout()

    def OnRadDatasetKeyword(self, event):
        self.rad_DatasetSameAsMain.SetValue(False)
        self.rad_DatasetOffset.SetValue(False)
        self.rad_DatasetEmptyLine.SetValue(False)
        for element in self.dic_DatasetKeywordGUI.keys():
            self.dic_DatasetKeywordGUI[element].Enable(True)
            self.dic_DatasetKeywordGUI[element].Show(True)
        for element in self.dic_DatasetOffsetGUI.keys():
            self.dic_DatasetOffsetGUI[element].Enable(False)
            self.dic_DatasetOffsetGUI[element].Show(False)
        self.dic_DatasetsDetailsHidden["keyword"] = False
        self.szr_YesMultipleDatasetsRightColumn.Show(self.dic_DatasetsDetailsElements["keyword"])
        self.dic_DatasetsDetailsHidden["coordinates"] = True
        self.szr_YesMultipleDatasetsRightColumn.Hide(self.dic_DatasetsDetailsElements["coordinates"])
        # Layout all relevant sizers
        self.szr_YesMultipleDatasetsRightColumn.Layout()
        self.szr_YesMultipleDatasets.Layout()
        self.szr_MultipleDatasets.Layout()

    def OnRadDatasetOffset(self, event):
        self.rad_DatasetSameAsMain.SetValue(False)
        self.rad_DatasetKeyword.SetValue(False)
        self.rad_DatasetEmptyLine.SetValue(False)
        for element in self.dic_DatasetKeywordGUI.keys():
            self.dic_DatasetKeywordGUI[element].Enable(False)
            self.dic_DatasetKeywordGUI[element].Show(False)
        for element in self.dic_DatasetOffsetGUI.keys():
            self.dic_DatasetOffsetGUI[element].Enable(True)
            self.dic_DatasetOffsetGUI[element].Show(True)
        self.dic_DatasetsDetailsHidden["keyword"] = True
        self.szr_YesMultipleDatasetsRightColumn.Hide(self.dic_DatasetsDetailsElements["keyword"])
        self.dic_DatasetsDetailsHidden["coordinates"] = False
        self.szr_YesMultipleDatasetsRightColumn.Show(self.dic_DatasetsDetailsElements["coordinates"])
        # Layout all relevant sizers
        self.szr_YesMultipleDatasetsRightColumn.Layout()
        self.szr_YesMultipleDatasets.Layout()
        self.szr_MultipleDatasets.Layout()

    def OnRadDatasetEmptyLine(self, event):
        self.rad_DatasetSameAsMain.SetValue(False)
        self.rad_DatasetKeyword.SetValue(False)
        self.rad_DatasetOffset.SetValue(False)
        for element in self.dic_DatasetKeywordGUI.keys():
            self.dic_DatasetKeywordGUI[element].Enable(False)
            self.dic_DatasetKeywordGUI[element].Show(False)
        for element in self.dic_DatasetOffsetGUI.keys():
            self.dic_DatasetOffsetGUI[element].Enable(False)
            self.dic_DatasetOffsetGUI[element].Show(False)
        self.dic_DatasetsDetailsHidden["keyword"] = True
        self.szr_YesMultipleDatasetsRightColumn.Hide(self.dic_DatasetsDetailsElements["keyword"])
        self.dic_DatasetsDetailsHidden["coordinates"] = True
        self.szr_YesMultipleDatasetsRightColumn.Hide(self.dic_DatasetsDetailsElements["coordinates"])
        # Layout all relevant sizers
        self.szr_YesMultipleDatasetsRightColumn.Layout()
        self.szr_YesMultipleDatasets.Layout()
        self.szr_MultipleDatasets.Layout()


    def OnWellCommbo(self,event):
        self.rule_set["DestinationPlateFormat"] = int(self.cbo_Wells.GetValue())

    
    def OnRadStopKeyword(self, event):
        for element in self.dic_StopKeywordGUI:
            self.dic_StopKeywordGUI[element].Enable(True)
        self.rule_set["UseStopKeyword"] = True

        for element in self.dic_StopCoordinatesGUI:
            self.dic_StopCoordinatesGUI[element].Enable(False)
        self.rad_StopCoordinates.SetValue(False)
        self.rule_set["UseStartCoordinates"] = False

        self.rad_StopEmptyLine.SetValue(False)
        self.rule_set["UseStopEmptyLine"] = False

    def OnRadStopCoordinates(self, event):
        for element in self.dic_StopKeywordGUI:
            self.dic_StopKeywordGUI[element].Enable(False)
        self.rad_StopKeyword.SetValue(False)
        self.rule_set["UseStopKeyword"] = False

        for element in self.dic_StopCoordinatesGUI:
            self.dic_StopCoordinatesGUI[element].Enable(True)
        self.rule_set["UseStartCoordinates"] = True

        self.rad_StopEmptyLine.SetValue(False)
        self.rule_set["UseStopEmptyLine"] = False

    def OnRadStopEmptyLine(self, event):
        for element in self.dic_StopKeywordGUI:
            self.dic_StopKeywordGUI[element].Enable(False)
        self.rad_StopKeyword.SetValue(False)
        self.rule_set["UseStopKeyword"] = False

        for element in self.dic_StopCoordinatesGUI:
            self.dic_StopCoordinatesGUI[element].Enable(False)
        self.rad_StopCoordinates.SetValue(False)
        self.rule_set["UseStartCoordinates"] = False

        self.rule_set["UseStopEmptyLine"] = True

    def OnGridFrightClick(self, event):
        self.PopupMenu(GridContextMenu(self, event))

    def GridNewHighlight(self, str_Highlight, int_NewRow, int_NewCol):
        if str_Highlight in self.dic_CurrentGridHighlights.keys():
            tpl_Highlight = self.dic_CurrentGridHighlights[str_Highlight]
            self.grd_ExampleFile.SetCellBackgroundColour(tpl_Highlight[0],tpl_Highlight[1],(255,255,255))
            self.grd_ExampleFile.DeselectCell(tpl_Highlight[0],tpl_Highlight[1])
        self.dic_CurrentGridHighlights[str_Highlight] = (int_NewRow,int_NewCol)
        self.grd_ExampleFile.SetCellBackgroundColour(int_NewRow,int_NewCol,(255,255,0))
        self.grd_ExampleFile.SelectBlock(int_NewRow,int_NewCol,int_NewRow,int_NewCol)

    def FileSelected(self, event):

        self.btn_ParseFile.Enable(True)

        str_FilePath = self.fpk_RawDataFile.GetPath()
        # Determine file extension to get most likely candidate for file reader:
        str_Extension = os.path.splitext(str_FilePath)[1][1:]
        # Create blank slate in checklist:
        self.ckl_Worksheets.Clear()
        lst_Worksheets = ef.GetWorksheets(str_FilePath, str_Extension)
        if str_Extension[0:3] == "xls" and len(lst_Worksheets) > 0:
            self.ckl_Worksheets.InsertItems(lst_Worksheets,0)
            self.lbl_Worksheet.Enable(True)
            self.ckl_Worksheets.Enable(True)
            self.ckl_Worksheets.SetSelection(0)
        else:
            self.lbl_Worksheet.Enable(False)
            self.ckl_Worksheets.Enable(False)

    def ParseRawDataFile(self, event):
        """
        Reads transfer file and returns file  type and engine to use for parsing by calling DirectRead function.
        After getting the result, update rule_set and the relevant GUI elements.
        """
        self.Freeze()
        str_FilePath = self.fpk_RawDataFile.GetPath()
        str_Extension = os.path.splitext(str_FilePath)[1][1:]

        # Get worksheets to open, if applicable:
        if self.ckl_Worksheets.GetCount() > 0:
            lst_Worksheets = []
            for i in range(self.ckl_Worksheets.GetCount()):
                if self.ckl_Worksheets.IsChecked(i) == True:
                    lst_Worksheets.append(self.ckl_Worksheets.GetString(i))
        else:
            lst_Worksheets = [""]

        for worksheet in lst_Worksheets:
            dfr_DirectRead, str_FileType, str_Engine = ef.direct_read(str_FilePath,
                                                                      str_Extension,
                                                                      worksheet)
        # DirectRead returns None for all three objects if the file can't be parsed.
        # A real DataFrame would throw an error if compared to None, so we test the next object in line.
        if str_FileType == None:
            return None

        # Update rule_set with results from file reading
        self.rule_set["Extension"] = str_Extension
        self.rule_set["FileType"] = str_FileType
        self.rule_set["Engine"] = str_Engine
        # We only need the worksheet if it is an excel file:
        if str_FileType == "xls":
            self.rule_set["Worksheet"] = lst_Worksheets
        else:
            self.rule_set["Worksheet"] = None

        # Reset grid, if required:
        if self.grd_ExampleFile.GetNumberCols() > 0:
            self.grd_ExampleFile.DeleteCols(0, self.grd_ExampleFile.GetNumberCols())
        if self.grd_ExampleFile.GetNumberRows() > 0:
            self.grd_ExampleFile.DeleteRows(0, self.grd_ExampleFile.GetNumberRows())
        # Add rows and colums
        if dfr_DirectRead.shape[0] > 0:
            self.grd_ExampleFile.AppendRows(dfr_DirectRead.shape[0])
            self.grd_ExampleFile.AppendCols(dfr_DirectRead.shape[1])
            # Populate grid
            for row in range(dfr_DirectRead.shape[0]):
                for col in range(dfr_DirectRead.shape[1]):
                    if not pd.isna(dfr_DirectRead.iloc[row,col]) == True:
                        self.grd_ExampleFile.SetCellValue(row,col,str(dfr_DirectRead.iloc[row,col]))
        else:
            self.grd_ExampleFile.AppendRows(1)
            self.grd_ExampleFile.AppendCols(1)
            self.grd_ExampleFile.SetCellValue(0,0,"[EMPTY WORKSHEET/FILE]")
        #self.grd_ExampleFile.AutoSizeColumns(True)

        self.bool_ExampleFileLoaded = True

        self.grd_ExampleFile.Show(True)
        self.Layout()
        self.Thaw()


    def PrintRules(self, event):
        print("Rule set:")
        print(self.rule_set)

        


    def CheckRules(self):
        """
        Checks whether rules to parse raw data file are consistent.
        """
        if self.rule_set["Verification"]["Use"] == True:
            if self.rule_set["Verification"]["Keyword"] == None or self.rule_set["Verification"]["Keyword"] == "":
                mb.info(self, "No keyword to verify the raw data file given.")
                return False
            if self.rule_set["Verification"]["Column"] == None or self.rule_set["Verification"]["Column"] == "":
                mb.info(self, "No keyword to verify the raw data file given.")
                return False

        if not self.rule_set["PlateOrSample"] in ["Plate","Sample"]:
            mb.info(self, "Cannot tell whether raw data is organised in samples or plates.")
            return False

        if self.rule_set["UseStartKeyword"] == True:
            if self.rule_set["StartKeyword"] == None or self.rule_set["StartKeyword"] == "":
                mb.info(self, "No keyword for start of transfer data given")
                return False
            if self.rule_set["StartKeywordColumn"] == None or self.rule_set["StartKeywordColumn"] == "":
                mb.info(self, "No column for keyword for start of transfer data given")
                return False
        if self.rule_set["UseStopKeyword"] == True:
            if self.rule_set["StopKeyword"] == None or self.rule_set["StopKeyword"] == "":
                mb.info(self, "No keyword for end of transfer data given.")
                return False
            if self.rule_set["StopKeywordColumn"] == None or self.rule_set["StopKeywordColumn"] == "":
                mb.info(self, "No column for keyword for end of transfer data given")
                return False
        if self.rule_set["UseStartCoordinates"] == True and self.rule_set["StartCoordinates"] == None:
                mb.info(self, "No keyword for start of transfer data given")
                return False
        if self.rule_set["UseStopCoordinates"] == True and self.rule_set["StopCoordinates"] == None:
                mb.info(self, "No keyword for end of transfer data given.")
                return False
        return True

    def CheckColumns(self):
        """
        Checks whether the minimum required columns are assigned
        """
        #if (self.rule_set["TransferFileColumns"].loc["Destination Plate Name"] == None and 
        #    self.rule_set["TransferFileColumns"].loc["Destination Plate Barcode"] == None):
        #    mb.info(self, "Either 'Destination Plate Name' or 'Destination Plate Barcode' need to have a column assigned")
        #    return False
        #if self.rule_set["TransferFileColumns"].loc["Destination Well"] == None:
        #    mb.info(self, "No 'Destination Well' column assigned.")
        #    return False
        #if self.rule_set["TransferFileColumns"].loc["Destination Concentration"] == None:
        #    mb.info(self, "Needs at least a destination concentration or source concentration + transfer volume")
        #if (self.rule_set["TransferFileColumns"].loc["Destination Concentration"] == None and
        #    self.rule_set["TransferFileColumns"].loc["Source Concentration"] == None):
        #    mb.info(self, "Needs at least a destination concentration or source concentration + transfer volume")
        #    return False
        return True

    def CheckForDataFrame(self):
        """
        Checks whether rule_set exists and has been created properly.
        """
        if hasattr(self, "rule_set") == False:
            return False
        else:
            if len(self.rule_set) > 0:
                return True
            else:
                return False

    ####  #   # #     #####     ####  ###  #   # # #   #  ####
    #   # #   # #     #        #     #   # #   # # ##  # #
    ####  #   # #     ###       ###  ##### #   # # ##### #  ##
    #   # #   # #     #            # #   #  # #  # #  ## #   #
    #   #  ###  ##### #####    ####  #   #   #   # #   #  ####

    # Simplebook page saving functions ##############################################################################################################

    def fun_Dummy(self):
        return "Forward"

    def save_metadata(self):
        """
        Saves meta data to rule_set.
        """

        str_Return = "Backward"

        if self.CheckForDataFrame() == True:
            self.rule_set["Timestamp"] = self.txt_Timestamp.GetLineText(0)
            self.rule_set["Device"] = self.txt_Device.GetLineText(0)
            self.rule_set["AssayType"] = self.txt_Assay.GetLineText(0)
            self.rule_set["Device"] = self.txt_Device.GetLineText(0)
            self.rule_set["Description"] = self.txt_Description.GetValue()
            str_Return = str_Return + "Forward"
            self.save_assay_definition()
        else:
            mb.info(self, "Dataframe for ruleset has not been created.")
            str_Return = "Stop"

        return str_Return

    def save_example_file(self):
        """
        Saves file type info and verification info to rule_set.
        """

        str_Return = "Backward"

        if self.CheckForDataFrame() == True:
            self.rule_set["Verification"]["Use"] = self.chk_Verification.GetValue()
            if self.rule_set["Verification"]["Use"] == True:
                # Test if any fields are not filled out:
                if len(self.txt_VerificationKeyword.GetLineText(0)) > 0:
                    if self.chk_VerificationExact.GetValue() == True:
                        self.rule_set["Verification"]["Keyword"] = self.txt_VerificationKeyword.GetLineText(0)
                        self.rule_set["Verification"]["Exact"] = True
                    else:
                        self.rule_set["Verification"]["Keyword"] = self.txt_VerificationKeywordEditable.GetLineText(0)
                        self.rule_set["Verification"]["Exact"] = False
                    if self.rad_VerificationKeywordColumn.GetValue() == True:
                        self.rule_set["Verification"]["Axis"] = 0
                    elif self.rad_VerificationKeywordRow.GetValue() == True:
                        self.rule_set["Verification"]["Axis"] = 1
                    str_Return +=  "Forward"
                    if len(self.txt_VerificationKeywordRow.GetLineText(0)) > 0:
                        # Remember: Human readable indexing shown in UI!
                        self.rule_set["Verification"]["Row"] = int(self.txt_VerificationKeywordRow.GetLineText(0))-1
                        str_Return +=  "Forward"
                    else:
                        str_Return += "Stop"
                    if len(self.txt_VerificationKeywordColumn.GetLineText(0)) > 0:
                        self.rule_set["Verification"]["Column"] = 65 - ord(self.txt_VerificationKeywordColumn.GetLineText(0))
                        str_Return +=  "Forward"
                    else:
                        str_Return += "Stop"
                # Fields are not filled out
                else:
                    str_Return += "Stop"
            else:
                self.rule_set["Verification"]["Keyword"] = None
                self.rule_set["Verification"]["Column"] = None
                self.rule_set["Verification"]["Row"] = None
                self.rule_set["Verification"]["Axis"] = None
                self.rule_set["Verification"]["Exact"] = False
            str_Return += "Forward"
            self.save_assay_definition()
        else:
            mb.info(self, "Dataframe for ruleset has not been created.")
            str_Return += "Stop"

        return str_Return

    def save_data_organisation(self):
        """
        Saves info about top level of data organisation to rule_set.
        """

        str_Return = "Backward"

        if self.CheckForDataFrame() == True:
            # Data representation
            if self.rad_Grid.GetValue() == True:
                self.rule_set["GridOrTable"] = "Grid"
                self.rule_set["GridLabelsIncluded"] = self.chk_GridLabelsIncluded.GetValue()
            else:
                self.rule_set["GridOrTable"] = "Table"
                self.rule_set["GridLabelsIncluded"] = False
            # Data start
            if self.rad_StartKeyword.GetValue() == True:
                self.rule_set["UseDatasetKeyword"] = True
                if self.chk_StartKeywordExact.GetValue() == True:
                    self.rule_set["ExactDatasetKeyword"] = True
                    self.rule_set["DatasetKeyword"] = self.txt_StartKeyword.GetLineText(0)
                else:
                    self.rule_set["ExactDatasetKeyword"] = False
                    self.rule_set["DatasetKeyword"] = self.txt_StartKeywordEditable.GetLineText(0)
                if len(self.txt_StartKeywordColumn.GetLineText(0)) > 0:
                    self.rule_set["DatasetKeywordColumn"] = 65-ord(self.txt_StartKeywordColumn.GetLineText(0))
                    # 65 is the unicode for "A"
                else:
                    self.rule_set["DatasetKeywordColumn"] = None
                    str_Return += "Stop"
                if len(self.txt_StartKeywordOffsetRows.GetLineText(0)) > 0 and len(self.txt_StartKeywordOffsetColumns.GetLineText(0)) > 0:
                    self.rule_set["DatasetKeywordOffset"] = (int(self.txt_StartKeywordOffsetRows.GetLineText(0)),
                                                                                int(self.txt_StartKeywordOffsetColumns.GetLineText(0)))
                else:
                    self.rule_set["DatasetKeywordOffset"] = None
                    str_Return += "Stop"
                self.rule_set["ExactDatasetKeyword"] = self.chk_StartKeywordExact.GetValue()
                self.rule_set["DatasetCoordinates"] = None

            else:
                self.rule_set["UseDatasetKeyword"] = False
                self.rule_set["DatasetKeywordColumn"] = None
                self.rule_set["DatasetKeywordOffset"] = None
                if len(self.txt_StartCoordinatesColumn.GetLineText(0)) > 0 and self.txt_StartCoordinatesRow.GetLineText(0):
                    self.rule_set["DatasetCoordinates"] = (int(self.txt_StartCoordinatesRow.GetLineText(0)),
                                                                            65-ord(self.txt_StartCoordinatesColumn.GetLineText(0)))
                else:
                    self.rule_set["DatasetCoordinates"] = None
                    str_Return += "Stop"
            # Wells:
            self.rule_set["AssayPlateFormat"] = int(self.cbo_Wells.GetString(self.cbo_Wells.GetSelection()))
            str_Return += "Forward"
            self.save_assay_definition()
        else:
            mb.info(self, "Dataframe for ruleset has not been created.")
            str_Return += "Stop"

        return str_Return

    def save_multiple_datasets(self):

        str_Return = "Backward"

        if self.CheckForDataFrame() == True:
            if self.rad_MultipleDatasets.GetValue() == True:
                self.rule_set["MultipleDatasets"] = True
                # How many~
                if self.rad_DynamicDatasets.GetValue() == True:
                    self.rule_set["NumberMultipleDatasets"] = -1
                else:
                    if len(self.txt_DatasetKeyword.GetLineText(0)) > 0 and self.rule_set["NumberMultipleDatasets"] != "0":
                        self.rule_set["NumberMultipleDatasets"] = int(self.txt_FixedDatasets.GetLineText(0))
                    else:
                        str_Return += "Stop"
                # Axis?
                if self.rad_DatasetsVertically.GetValue() == True:
                    self.rule_set["DatasetAxis"] = 0
                elif self.rad_DatasetsHorizontally.GetValue() == True:
                    self.rule_set["DatasetAxis"] = 1
                # How separated?
                if self.rad_DatasetKeyword.GetValue() == True:
                    self.rule_set["NewDatasetSeparator"] = "Keyword"
                    self.rule_set["ExactNewDatasetKeyword"] = False
                    self.rule_set["NewDatasetKeyword"] = self.txt_DatasetKeyword.GetLineText(0)
                    if len(self.txt_DatasetKeyword.GetLineText(0)) > 0:
                        self.rule_set["NewDatasetKeywordColumn"] = 65-int(self.txt_DatasetKeyword.GetLineText(0))
                    else:
                        self.rule_set["NewDatasetKeywordColumn"] = None
                        str_Return += "Stop"
                    if len(self.txt_DatasetKeywordOffsetRows.GetLineText(0)) > 0 and len(self.txt_DatasetKeywordOffsetColumns.GetLineText(0)) > 0:
                        self.rule_set["NewDatasetKeywordOffset"] = (int(self.txt_DatasetKeywordOffsetRows.GetLineText(0)),
                                                                                        int(self.txt_DatasetKeywordOffsetColumns.GetLineText(0)))
                    else:
                        self.rule_set["NewDatasetKeywordOffset"] = None
                    self.rule_set["NewDatasetOffset"] = None
                elif self.rad_DatasetOffset.GetValue() == True:
                    self.rule_set["NewDatasetSeparator"] = "SetDistance"
                    self.rule_set["NewDatasetKeywordOffset"] = None
                    if len(self.txt_DatasetOffsetRows.GetLineText(0)) > 0 and len(self.txt_DatasetOffsetColumns.GetLineText(0)) > 0:
                        self.rule_set["NewDatasetOffset"] = (int(self.txt_DatasetOffsetRows.GetLineText(0)),
                                                                                    int(self.txt_DatasetOffsetColumns.GetLineText(0)))
                elif self.rad_DatasetEmptyLine.GetValue() == True:
                    self.rule_set["NewDatasetSeparator"] = "EmptyLine"
                    self.rule_set["NewDatasetKeyword"] = None
                    self.rule_set["NewDatasetKeywordColumn"] = None
                    self.rule_set["NewDatasetOffset"] = None
        
            else:
                self.rule_set["NumberMultipleDatasets"] = 1
                self.rule_set["NewDatasetSeparator"] = None
                self.rule_set["NewDatasetKeyword"] = None
                self.rule_set["NewDatasetKeywordColumn"] = None
                self.rule_set["NewDatasetOffset"] = None
    
                #self.rule_set["DatasetNamesFromFile"] = True
                #self.rule_set["DatasetNames"] = None
                    # This will either be a n-tuple defined from user input or an n-tuple from data file readout.
                #self.rule_set["DatasetNamesFromFile"] = False
                    # Options: True
                    #          False
                    # Explanation: If True, the names of datasets (effectively column titles if in table format)
                    #              will be taken from file. Otherwise entered by user in GUI.
                #self.rule_set["DatasetNames"] = None
                    # Will be tuple of strings. Either parsed from file or entered by user.
                    # These will be used as indices for the generated rawdata dataframe.
            str_Return += "Forward"
            self.save_assay_definition()
        else:
            mb.info(self, "Dataframe for ruleset has not been created.")
            str_Return += "Stop"
        
        return str_Return

    def save_sub_datasets(self):
        """
        Saves info about sub-datasets to rule_set.
        """

        str_Return = "Backward"

        if self.CheckForDataFrame() == True:
            if self.rad_YesSubDatasets.GetValue() == True:
                self.rule_set["UseSubDatasets"] = True
                # How many?
                if self.rad_DynamicSubDatasets.GetValue() == True:
                    self.rule_set["NumberSubDatasets"] = -1
                else:
                    self.rule_set["NumberSubDatasets"] = int(self.txt_FixedSubDatasets.GetLineText(0))
                # Axis?
                if self.rad_SubDatasetsVertically.GetValue() == True:
                    self.rule_set["SubDatasetAxis"] = 0
                elif self.rad_SubDatasetsHorizontally.GetValue() == True:
                    self.rule_set["SubDatasetAxis"] = 1
                # How separated?
                if self.rad_SubDatasetsameAsMain.GetValue() == True:
                    self.rule_set["SubDatasetseparator"] = "SameAsMain"
                    self.rule_set["SubDatasetKeyword"] = None
                    self.rule_set["SubDatasetKeywordOffset"] = None
                    self.rule_set["SubDatasetDistance"] = None
                elif self.rad_SubDatasetKeyword.GetValue() == True:
                    self.rule_set["SubDatasetseparator"] = "Keyword"
                    self.rule_set["SubDatasetKeyword"] = self.txt_SubDatasetKeyword.GetLineText(0)
                    self.rule_set["SubDatasetKeywordOffset"] = (int(self.txt_SubDatasetKeywordOffsetRows.GetLineText(0)),
                                                                                int(self.txt_SubDatasetKewywordOffsetColumns.GetLineText(0)))
                    self.rule_set["SubDatasetDistance"] = None
                elif self.rad_SubDatasetOffset.GetValue() == True:
                    self.rule_set["SubDatasetseparator"] = "SetDistance"
                    self.rule_set["SubDatasetKeyword"] = None
                    self.rule_set["SubDatasetDistance"] = (int(self.txt_SubDatasetOffsetRows.GetLineText(0)),
                                                                                int(self.txt_SubDatasetOffsetColumns.GetLineText(0)))
                else:
                    self.rule_set["SubDatasetseparator"] = "EmptyLine"
                    self.rule_set["SubDatasetKeyword"] = None
                    self.rule_set["SubDatasetDistance"] = None
            else:
                self.rule_set["UseSubDatasets"] = False
                self.rule_set["NumberSubDatasets"] = 1
        

        self.rule_set["SubDatasetNamesFromFile"] = True
        self.rule_set["SubDatasetNames"] = None
        # This will either be a n-tuple defined from user input or an n-tuple from data file readout.

        return str_Return
    
    def save_assay_definition(self):
        """
        Writes the ruleset to the assay definition dictionary
        """
        self.assay["RawDataRules"] = copy.deepcopy(self.rule_set)

    def export_ruleset(self, event):
        # First, check that everything has been filled out properly
        #if self.CheckColumns() == False:
        #    return None
        #if self.CheckRules() == False:
        #    return None

        # Get file path:
        with wx.FileDialog(self, "Save project file", wildcard="BBQ rawdata rules files (*.rawdatarules)|*.rawdatarules",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as fileDialog:
            # Exit via returning nothing if the user changed their mind
            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return
            str_SaveFilePath = fileDialog.GetPath()
            # Prevent duplication of file extension
            if str_SaveFilePath.find(".rawdatarules") == -1:
                str_SaveFilePath = str_SaveFilePath + ".rawdatarules"
        # Write dictionary to json:
        try:
            json_object = js.dumps(self.rule_set, indent = 4)
            open(str_SaveFilePath, "w").write(json_object)
        except:
            return False


        return True


 #####   ####   ##  ##  ######  ######  ##  ##  ######      ##    ##  ######  ##  ##  ##  ##
##      ##  ##  ### ##    ##    ##       ####     ##        ###  ###  ##      ### ##  ##  ##
##      ##  ##  ######    ##    ####      ##      ##        ########  ####    ######  ##  ##
##      ##  ##  ## ###    ##    ##       ####     ##        ## ## ##  ##      ## ###  ##  ##
 #####   ####   ##  ##    ##    ######  ##  ##    ##        ##    ##  ######  ##  ##   ####

class GridContextMenu(wx.Menu):
    def __init__(self, parent, rightclick):
        super(GridContextMenu, self).__init__()
        """
        Context menu to define keywords, locations, etc. on grid.
        """
        self.parent = parent

        #real_path = os.path.realpath(__file__)
        #dir_path = os.path.dirname(real_path)
        #str_MenuIconsPath = dir_path + r"\menuicons"

        str_CurrentPage = self.parent.sbk_Wizard.GetPageText(self.parent.sbk_Wizard.GetSelection())


        # Save EventObject in instance variable
        self.grid = rightclick.GetEventObject()
        self.row = rightclick.GetRow()
        self.col = rightclick.GetCol()

        # File Verification Keyword
        if str_CurrentPage == "ExampleFile":
            if self.parent.chk_Verification.GetValue() == True:
                self.mi_VerificationKeyword = wx.MenuItem(self, wx.ID_ANY, u"File verification keyword", wx.EmptyString, wx.ITEM_NORMAL)
                #self.mi_VerificationKeyword.SetBitmap(wx.Bitmap(str_MenuIconsPath + r"\TickBoxTicked.ico"))
                self.Append(self.mi_VerificationKeyword)
                self.Bind(wx.EVT_MENU, lambda event: self.VerificationKeyword(event, self.row, self.col), self.mi_VerificationKeyword)
        
        # Start Keyword and offset
        if str_CurrentPage == "DataOrganisation":
            if self.parent.rad_StartKeyword.GetValue() == True:
                # Keyword
                self.mi_DataStartKeyword = wx.MenuItem(self, wx.ID_ANY, u"Start keyword for dataset", wx.EmptyString, wx.ITEM_NORMAL)
                #self.mi_DataStartKeyword.SetBitmap(wx.Bitmap(str_MenuIconsPath + r"\TickBoxTicked.ico"))
                self.Append(self.mi_DataStartKeyword)
                self.Bind(wx.EVT_MENU, lambda event: self.DataStartKeyword(event, self.row, self.col), self.mi_DataStartKeyword)
                # Offset
                self.mi_DataStartKeywordOffset = wx.MenuItem(self, wx.ID_ANY, u"Offset from keyword", wx.EmptyString, wx.ITEM_NORMAL)
                #self.mi_DataStartKeyword.SetBitmap(wx.Bitmap(str_MenuIconsPath + r"\TickBoxTicked.ico"))
                self.Append(self.mi_DataStartKeywordOffset)
                self.Bind(wx.EVT_MENU, lambda event: self.DataStartKeywordOffset(event, self.row, self.col), self.mi_DataStartKeywordOffset)
        
        # Start Coordinates
        if str_CurrentPage == "DataOrganisation":
            if self.parent.rad_StartCoordinates.GetValue() == True:
                self.mi_TransferStartCoordinates = wx.MenuItem(self, wx.ID_ANY, u"Start coordinates for Transfer", wx.EmptyString, wx.ITEM_NORMAL)
                self.Append(self.mi_TransferStartCoordinates)
                self.Bind(wx.EVT_MENU, lambda event: self.TransferStartCoordinates(event, self.row, self.col), self.mi_TransferStartCoordinates)

        # New Dataset Keyword
        if str_CurrentPage == "MultipleDatasets":
            if self.parent.rad_DatasetKeyword.GetValue() == True:
                # Keyword
                self.mi_NewDatasetKeyword = wx.MenuItem(self, wx.ID_ANY, u"Start keyword for new dataset", wx.EmptyString, wx.ITEM_NORMAL)
                #self.mi_NewDatasetKeyword.SetBitmap(wx.Bitmap(str_MenuIconsPath + r"\TickBoxTicked.ico"))
                self.Append(self.mi_NewDatasetKeyword)
                self.Bind(wx.EVT_MENU, lambda event: self.NewDatasetKeyword(event, self.row, self.col), self.mi_NewDatasetKeyword)
                # Offset
                self.mi_NewDatasetKeywordOffset = wx.MenuItem(self, wx.ID_ANY, u"Offset from keyword", wx.EmptyString, wx.ITEM_NORMAL)
                #self.mi_NewDatasetKeyword.SetBitmap(wx.Bitmap(str_MenuIconsPath + r"\TickBoxTicked.ico"))
                self.Append(self.mi_NewDatasetKeywordOffset)
                self.Bind(wx.EVT_MENU, lambda event: self.NewDatasetKeywordOffset(event, self.row, self.col), self.mi_NewDatasetKeywordOffset)

        # New Dataset Offset
        if str_CurrentPage == "MultipleDatasets":
            if self.parent.rad_DatasetOffset.GetValue() == True:
                self.mi_NewDatasetOffset = wx.MenuItem(self, wx.ID_ANY, u"Offset for new dataset", wx.EmptyString, wx.ITEM_NORMAL)
                self.Append(self.mi_NewDatasetOffset)
                self.Bind(wx.EVT_MENU, lambda event: self.NewDatasetOffset(event, self.row, self.col), self.mi_NewDatasetOffset)
        #self.AppendSeparator()

    def VerificationKeyword(self, event, row, col):
        # Update Wizard Page
        self.parent.txt_VerificationKeyword.SetValue(self.grid.GetCellValue(row, col))
        self.parent.txt_VerificationKeywordEditable.SetValue(self.grid.GetCellValue(row, col))
        self.parent.txt_VerificationKeywordRow.SetValue(str(row+1)) # Human friendly indexing!
        self.parent.txt_VerificationKeywordColumn.SetValue(str(chr(col+65)))
        # Highlight on Grid:
        self.parent.GridNewHighlight("VerificationKeyword",row,col)
        # Ruleset gets updated changing the page of the wizard.
        self.parent.tpl_ExampleFileVerificationKeywordCoordinates = (row, col)

    def DataStartKeyword(self, event, row, col):
        # Update display
        self.parent.txt_StartKeyword.SetValue(self.grid.GetCellValue(row, col))
        self.parent.txt_StartKeywordEditable.SetValue(self.grid.GetCellValue(row, col))
        self.parent.txt_StartKeywordColumn.SetValue(str(chr(col+65)))
        self.parent.txt_StartCoordinatesColumn.SetValue("")
        self.parent.txt_StartCoordinatesRow.SetValue("")
        # Highlight on Grid:
        self.parent.GridNewHighlight("DataStartKeyword",row,col)
        # Ruleset gets updated changing the page of the wizard.
        self.parent.tpl_ExampleFileStartKeywordCoordinates = (row, col)

    def DataStartKeywordOffset(self, event, row, col):
        tpl_Keyword = self.parent.tpl_ExampleFileStartKeywordCoordinates
        tpl_Offset = (row-tpl_Keyword[0], col-tpl_Keyword[1])
        # Highlight on Grid:
        self.parent.GridNewHighlight("DataStartKeywordOffset",row,col)
        # Update display
        self.parent.txt_StartKeywordOffsetRows.SetValue(str(tpl_Offset[0]))
        self.parent.txt_StartKeywordOffsetColumns.SetValue(str(tpl_Offset[1]))
        # Ruleset gets updated changing the page of the wizard.

    def NewDatasetKeyword(self, event, row, col):
        # Update display
        self.parent.txt_DatasetKeyword.SetValue(self.grid.GetCellValue(row, col))
        #self.parent.txt_DatasetKeywordEditable.SetValue(self.grid.GetCellValue(row, col))
        self.parent.txt_DatasetKeywordColumn.SetValue(str(chr(col+65)))
        # Highlight on Grid:
        self.parent.GridNewHighlight("NewDatasetKeyword",row,col)
        # Ruleset gets updated changing the page of the wizard.
        self.parent.tpl_ExampleFileNewDatasetKeywordCoordinates = (row, col)

    def NewDatasetKeywordOffset(self, event, row, col):
        tpl_Keyword = self.parent.tpl_ExampleFileNewDatasetKeywordCoordinates
        tpl_Offset = (row-tpl_Keyword[0], col-tpl_Keyword[1])
        # Update display
        self.parent.txt_DatasetKeywordOffsetRows.SetValue(str(tpl_Offset[0]))
        self.parent.txt_DatasetKeywordOffsetColumns.SetValue(str(tpl_Offset[1]))
        # Ruleset gets updated changing the page of the wizard.

    def NewDatasetOffset(self, event, row, col):
        # Get start of previous dataset
        int_offsetrows = int(self.parent.txt_StartKeywordOffsetRows.GetLineText(0))
        int_offsetcols = int(self.parent.txt_StartKeywordOffsetColumns.GetLineText(0))
        # Calculate offset
        int_DatasetStartRows = row - (self.parent.tpl_ExampleFileStartKeywordCoordinates[0] + int_offsetrows)
        int_DatasetStartCols = col - (self.parent.tpl_ExampleFileStartKeywordCoordinates[1] + int_offsetcols)
        # Update display
        self.parent.txt_DatasetOffsetRows.SetValue(str(int_DatasetStartRows))
        self.parent.txt_DatasetOffsetColumns.SetValue(str(int_DatasetStartCols))

    def TransferStartCoordinates(self, event, row, col):
        # Update display
        self.parent.txt_StartKeyword.SetValue("")
        self.parent.txt_StartKeywordEditable.SetValue("")
        self.parent.txt_StartKeywordColumn.SetValue("")
        self.parent.txt_StartCoordinatesColumn.SetValue(chr(col+65))
        self.parent.txt_StartCoordinatesRow.SetValue(str(row+1))
        # Update ruleset
        self.parent.rule_set["StartKeyword"] = None
        self.parent.rule_set["StartKeywordColumn"] = None
        self.parent.rule_set["StartCoordinates"] = (row,col)