"""
    In this module:
    
    User interface elements for determining the rules to read liquid handler transfer files for a certain assay.

"""

# Imports ###########################################################################################################################################

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

import editor.dragndrop as dd
import editor.transferfunctions as tf
import lib_messageboxes as mb
import lib_excelfunctions as ef
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

class TransferRules(wx.Panel):

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

        self.assay["TransferRules"] = tf.CreateBlankRuleSet()
        self.rule_set = self.assay["TransferRules"]
        # Associated variables:
        self.tpl_ExampleFileVerificationKeywordCoordinates = None
        self.tpl_ExampleFileNewDatasetKeywordCoordinates = None
        self.bool_ExampleFileLoaded = False

        self.szr_Surround = wx.BoxSizer(wx.HORIZONTAL)

        self.pnl_Wizard = wx.Panel(self)
        self.pnl_Wizard.SetBackgroundColour(cs.BgUltraLight)
        self.szr_Wizard = wx.BoxSizer(wx.VERTICAL)

        # Simplebook ###################################################################
        # To make the generation of the dataframe easy, user will be guided through a
        # wizard. wxPython offers an inbuilt Wizard, but I'll make
        # my own with a simplebook to have more flexibility.
        self.sbk_Wizard = wx.Simplebook(self.pnl_Wizard,
                                        size = wx.Size(420,-1),
                                        style = wx.TAB_TRAVERSAL)
        self.sbk_Wizard.SetMaxSize(wx.Size(420,630))
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
        self.pnl_Instructions.SetSizer(self.szr_Instructions)
        self.pnl_Instructions.Layout()
        self.szr_Instructions.Fit(self.pnl_Instructions)
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
                                               label = u"Select a transfer file")
        self.szr_FileSelection.Add(self.lbl_FileSelection, 0, wx.ALL, 5)
        self.fpk_TransferFile = wx.FilePickerCtrl(self.pnl_ExampleFile, 
                                                  message = u"Select a file",
                                                  wildcard = u"*.*")
        self.szr_FileSelection.Add(self.fpk_TransferFile, 0, wx.ALL, 5)
        self.lbl_Worksheet = wx.StaticText(self.pnl_ExampleFile,
                                           label = u"If multiple worksheets, use:")
        self.lbl_Worksheet.Wrap(-1)
        self.lbl_Worksheet.Enable(False)
        self.szr_FileSelection.Add(self.lbl_Worksheet, 0, wx.ALL, 5)
        self.ckl_Worksheets = wx.CheckListBox(self.pnl_ExampleFile,
                                              choices = [])
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
                                            label = u"Verify file is a correct transfer file by use of a keyword")
        self.chk_Verification.SetValue(True)
        self.szr_ExampleFile.Add(self.chk_Verification, 0, wx.ALL, 5)
        self.szr_Verification = wx.BoxSizer(wx.VERTICAL)
        # Keyword
        self.szr_VerificationKeyword = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_VerificationKeyword.Add((0,0), 0, wx.ALL, 5)
        self.lbl_VerificationKeyword = wx.StaticText(self.pnl_ExampleFile,
                                                     label = u"Keyword:")
        self.szr_VerificationKeyword.Add(self.lbl_VerificationKeyword, 0,
                                         wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.txt_VerificationKeyword = wx.TextCtrl(self.pnl_ExampleFile,
                                                   size = wx.Size(150,-1),
                                                   style = wx.TE_READONLY)
        self.szr_VerificationKeyword.Add(self.txt_VerificationKeyword, 0,
                                         wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.txt_VerificationKeywordEditable = wx.TextCtrl(self.pnl_ExampleFile,
                                                           size = wx.Size(150,-1))
        self.szr_VerificationKeyword.Add(self.txt_VerificationKeywordEditable, 0,
                                         wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.txt_VerificationKeywordEditable.Show(False)
        self.szr_Verification.Add(self.szr_VerificationKeyword, 0, wx.ALL, 0)
        # Column
        self.szr_VerificationKeywordColumn = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_VerificationKeywordColumn.Add((0,0), 0, wx.ALL, 5)
        self.rad_VerificationKeywordColumn = wx.RadioButton(self.pnl_ExampleFile,
                                                            label = u"in column",
                                                            style = wx.RB_SINGLE)
        self.rad_VerificationKeywordColumn.SetValue(True)
        self.szr_VerificationKeywordColumn.Add(self.rad_VerificationKeywordColumn, 0,
                                               wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.txt_VerificationKeywordColumn = wx.TextCtrl(self.pnl_ExampleFile,
                                                         size = wx.Size(30,-1),
                                                         style = wx.TE_READONLY)
        self.szr_VerificationKeywordColumn.Add(self.txt_VerificationKeywordColumn, 0,
                                               wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.szr_Verification.Add(self.szr_VerificationKeywordColumn, 0, wx.ALL, 0)
        # Row
        self.szr_VerificationKeywordRow = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_VerificationKeywordRow.Add((0,0), 0, wx.ALL, 5)
        self.rad_VerificationKeywordRow = wx.RadioButton(self.pnl_ExampleFile,
                                                         label = u"in row",
                                                         style = wx.RB_SINGLE)
        self.szr_VerificationKeywordRow.Add(self.rad_VerificationKeywordRow, 0,
                                            wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.txt_VerificationKeywordRow = wx.TextCtrl(self.pnl_ExampleFile,
                                                      size = wx.Size(30,-1),
                                                      style = wx.TE_READONLY)
        self.szr_VerificationKeywordRow.Add(self.txt_VerificationKeywordRow, 0,
                                            wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.szr_Verification.Add(self.szr_VerificationKeywordRow, 0, wx.ALL, 0)
        # Exact?
        self.szr_VerificationKeywordExact = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_VerificationKeywordExact.Add((0,0), 0, wx.ALL, 5)
        self.chk_VerificationKeywordExact = wx.CheckBox(self.pnl_ExampleFile,
                                                        label = u"Keyword exactly like in example file.")
        self.chk_VerificationKeywordExact.SetValue(True)
        self.szr_VerificationKeywordExact.Add(self.chk_VerificationKeywordExact, 0, wx.ALL, 0)
        self.szr_Verification.Add(self.szr_VerificationKeywordExact, 0, wx.ALL, 5)
        self.szr_ExampleFile.Add(self.szr_Verification, 0, wx.ALL, 5)
        self.lin_Verification = wx.StaticLine(self.pnl_ExampleFile,
                                              style = wx.LI_HORIZONTAL)
        self.szr_ExampleFile.Add(self.lin_Verification, 0, wx.EXPAND|wx.ALL, 5)
        # Contains Exceptions ////
        #self.chk_Exceptions = wx.CheckBox(self.pnl_ExampleFile,
        #                                  label = u"Catch exceptions/errors")
        #self.chk_Exceptions.SetValue(True)
        #self.szr_ExampleFile.Add(self.chk_Exceptions, 0, wx.ALL, 5)
        #self.lin_Exceptons = wx.StaticLine(self.pnl_ExampleFile, 
        #                                   style = wx.LI_HORIZONTAL)
        #self.szr_ExampleFile.Add(self.lin_Exceptons, 0, wx.EXPAND|wx.ALL, 5)
        # Solvent Transfers ////
        self.chk_SolventTransfers = wx.CheckBox(self.pnl_ExampleFile,
                                                label = u"Catch solvent-only transfers")
        self.chk_SolventTransfers.SetValue(True)
        self.szr_ExampleFile.Add(self.chk_SolventTransfers, 0, wx.ALL, 5)
        ################################################################################
        # All elements added to sizer
        self.pnl_ExampleFile.SetSizer(self.szr_ExampleFile)
        self.pnl_ExampleFile.Layout()
        self.szr_Verification.Fit(self.pnl_ExampleFile)
        # Add to simplebook #############################################################
        self.sbk_Wizard.AddPage(self.pnl_ExampleFile, u"ExampleFile", False)
        self.dic_PageSaveFunctions["ExampleFile"] = self.save_example_file
        #################################################################################


        #####  ###  #####  ###      ###  ####   ####  ###  #   # #  ####  ###  ##### #  ###  #   #
        #     #   #   #   #   #    #   # #   # #     #   # ##  # # #     #   #   #   # #   # ##  #
        ##### #####   #   #####    #   # ####  #  ## ##### ##### #  ###  #####   #   # #   # #####
        #     #   #   #   #   #    #   # #   # #   # #   # #  ## #     # #   #   #   # #   # #  ## 
        ##### #   #   #   #   #     ###  #   #  #### #   # #   # # ####  #   #   #   #  ###  #   #

        # Wizard Page: Entry Organisation ##############################################
        self.pnl_Entries = wx.ScrolledWindow(self.sbk_Wizard,
                                             style = wx.TAB_TRAVERSAL|wx.VSCROLL)
        self.pnl_Entries.SetScrollRate(5,5)
        self.pnl_Entries.SetBackgroundColour(self.pnlbgclr)
        self.szr_Entries = wx.BoxSizer(wx.VERTICAL)
        # Start ########################################################################
        self.lbl_EntriesStart = wx.StaticText(self.pnl_Entries,
                                                label = u"Find start of transfer entries by")
        self.lbl_EntriesStart.Wrap(-1)
        self.szr_Entries.Add(self.lbl_EntriesStart, 0, wx.ALL, 5)
        # Keyword
        self.szr_StartKeyword = wx.BoxSizer(wx.HORIZONTAL)
        self.rad_StartKeyword = wx.RadioButton(self.pnl_Entries,
                                               label = u"unique keyword",
                                               style = wx.RB_SINGLE)
        self.rad_StartKeyword.SetValue(True)
        self.szr_StartKeyword.Add(self.rad_StartKeyword, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.txt_StartKeyword = wx.TextCtrl(self.pnl_Entries,
                                            value = wx.EmptyString,
                                            style = wx.TE_READONLY)
        self.szr_StartKeyword.Add(self.txt_StartKeyword, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.txt_StartKeywordEditable = wx.TextCtrl(self.pnl_Entries,
                                                    value = wx.EmptyString)
        self.txt_StartKeywordEditable.Enable(False)
        self.txt_StartKeywordEditable.Show(False)
        self.szr_StartKeyword.Add(self.txt_StartKeywordEditable, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.lbl_StartKeywordColumn = wx.StaticText(self.pnl_Entries, label = u"in column")
        self.lbl_StartKeywordColumn.Wrap(-1)
        self.szr_StartKeyword.Add(self.lbl_StartKeywordColumn, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.txt_StartKeywordColumn = wx.TextCtrl(self.pnl_Entries,
                                                  value = wx.EmptyString,
                                                  size = wx.Size(30,-1),
                                                  style = wx.TE_READONLY)
        self.szr_StartKeyword.Add(self.txt_StartKeywordColumn, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.szr_Entries.Add(self.szr_StartKeyword, 0, wx.ALL, 5)
        # Exact?
        self.szr_KeywordExact = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_KeywordExact.Add((10,0), 0, wx.ALL, 5)
        self.chk_StartKeywordExact = wx.CheckBox(self.pnl_Entries,
                                                 label = u"Keyword exactly like in example file.")
        self.chk_StartKeywordExact.SetValue(True)
        self.szr_KeywordExact.Add(self.chk_StartKeywordExact, 0, wx.ALL, 0)
        self.szr_Entries.Add(self.szr_KeywordExact, 0, wx.ALL, 5)
        self.dic_StartKeywordGUI = {"text":self.txt_StartKeyword,
                                    "text_editable":self.txt_StartKeywordEditable,
                                    "exact":self.chk_StartKeywordExact,
                                    "columnlabel":self.lbl_StartKeywordColumn,
                                    "columntext":self.txt_StartKeywordColumn}
        # Coordinates
        self.szr_StartCoordinates = wx.BoxSizer(wx.HORIZONTAL)
        self.rad_StartCoordinates = wx.RadioButton(self.pnl_Entries,
                                                   label = u"absolute coordinates:",
                                                   style = wx.RB_SINGLE)
        self.szr_StartCoordinates.Add(self.rad_StartCoordinates, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.lbl_StartCoordinatesColumn = wx.StaticText(self.pnl_Entries, label = u"Column")
        self.lbl_StartCoordinatesColumn.Wrap(-1)
        self.lbl_StartCoordinatesColumn.Enable(False)
        self.szr_StartCoordinates.Add(self.lbl_StartCoordinatesColumn, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.txt_StartCoordinatesColumn = wx.TextCtrl(self.pnl_Entries,
                                                      value = wx.EmptyString,
                                                      size = wx.Size(30,-1),
                                                      style = wx.TE_READONLY)
        self.txt_StartCoordinatesColumn.Enable(False)
        self.szr_StartCoordinates.Add(self.txt_StartCoordinatesColumn, 0, wx.ALL, 5)
        self.lbl_StartCoordinatesRow = wx.StaticText(self.pnl_Entries,
                                                     label = u"Row")
        self.lbl_StartCoordinatesRow.Wrap(-1)
        self.lbl_StartCoordinatesRow.Enable(False)
        self.szr_StartCoordinates.Add(self.lbl_StartCoordinatesRow, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.txt_StartCoordinatesRow = wx.TextCtrl(self.pnl_Entries,
                                                   value = wx.EmptyString,
                                                   size = wx.Size(30,-1),
                                                   style = wx.TE_READONLY)
        self.txt_StartCoordinatesRow.Enable(False)
        self.szr_StartCoordinates.Add(self.txt_StartCoordinatesRow, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.dic_StartCoordinatesGUI = {"collabel":self.lbl_StartCoordinatesColumn,
                                        "coltext":self.txt_StartCoordinatesColumn,
                                        "rowlabel":self.lbl_StartCoordinatesRow,
                                        "rowtext":self.txt_StartCoordinatesRow}
        self.szr_Entries.Add(self.szr_StartCoordinates, 0, wx.ALL, 5)
        self.lin_Start = wx.StaticLine(self.pnl_Entries, 
                                       style = wx.LI_HORIZONTAL)
        self.szr_Entries.Add(self.lin_Start, 0, wx.EXPAND|wx.ALL, 5)
        # Stop ////
        self.lbl_TransfersStop = wx.StaticText(self.pnl_Entries,
                                               label = u"Find end of transfer entries by")
        self.lbl_TransfersStop.Wrap(-1)
        self.szr_Entries.Add(self.lbl_TransfersStop, 0, wx.ALL, 5)
        # Keyword
        self.szr_StopKeyword = wx.BoxSizer(wx.HORIZONTAL)
        self.rad_StopKeyword = wx.RadioButton(self.pnl_Entries,
                                              label = u"unique keyword",
                                              style = wx.RB_SINGLE)
        self.rad_StopKeyword.SetValue(True)
        self.szr_StopKeyword.Add(self.rad_StopKeyword, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.txt_StopKeyword = wx.TextCtrl(self.pnl_Entries,
                                           value = wx.EmptyString,
                                           style = wx.TE_READONLY)
        self.szr_StopKeyword.Add(self.txt_StopKeyword, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.txt_StopKeywordEditable = wx.TextCtrl(self.pnl_Entries,
                                                   value = wx.EmptyString)
        self.txt_StopKeywordEditable.Enable(False)
        self.txt_StopKeywordEditable.Show(False)
        self.szr_StopKeyword.Add(self.txt_StopKeywordEditable, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.lbl_StopKeywordColumn = wx.StaticText(self.pnl_Entries,
                                                   label = u"in column")
        self.lbl_StopKeywordColumn.Wrap(-1)
        self.szr_StopKeyword.Add(self.lbl_StopKeywordColumn, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.txt_StopKeywordColumn = wx.TextCtrl(self.pnl_Entries,
                                                 size = wx.Size(30,-1),
                                                 style = wx.TE_READONLY)
        self.szr_StopKeyword.Add(self.txt_StopKeywordColumn, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.szr_Entries.Add(self.szr_StopKeyword, 0, wx.ALL, 5)
        # Exact?
        self.szr_StopKeywordExact = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_StopKeywordExact.Add((10,0), 0, wx.ALL, 5)
        self.chk_StopKeywordExact = wx.CheckBox(self.pnl_Entries,
                                                 label = u"Keyword exactly like in example file.")
        self.chk_StopKeywordExact.SetValue(True)
        self.szr_StopKeywordExact.Add(self.chk_StopKeywordExact, 0, wx.ALL, 0)
        self.szr_Entries.Add(self.szr_StopKeywordExact, 0, wx.ALL, 5)
        self.dic_StopKeywordGUI = {"text":self.txt_StopKeyword,
                                   "text_editable":self.txt_StopKeywordEditable,
                                   "exact":self.chk_StopKeywordExact,
                                   "columnlabel":self.lbl_StopKeywordColumn,
                                   "columntext":self.txt_StopKeywordColumn}
        # Coordinates
        self.szr_StopCoordinates = wx.BoxSizer(wx.HORIZONTAL)
        self.rad_StopCoordinates = wx.RadioButton(self.pnl_Entries,
                                                  label = u"absolute coordinates:",
                                                  style = wx.RB_SINGLE)
        self.szr_StopCoordinates.Add(self.rad_StopCoordinates, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.lbl_StopCoordinatesColumn = wx.StaticText(self.pnl_Entries,
                                                       label = u"Column")
        self.lbl_StopCoordinatesColumn.Wrap(-1)
        self.lbl_StopCoordinatesColumn.Enable(False)
        self.szr_StopCoordinates.Add(self.lbl_StopCoordinatesColumn, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.txt_StopCoordinatesColumn = wx.TextCtrl(self.pnl_Entries,
                                                     size = wx.Size(30,-1),
                                                     style = wx.TE_READONLY)
        self.txt_StopCoordinatesColumn.Enable(False)
        self.szr_StopCoordinates.Add(self.txt_StopCoordinatesColumn, 0, wx.ALL, 5)
        self.lbl_StopCoordinatesRow = wx.StaticText(self.pnl_Entries, label = u"Row")
        self.lbl_StopCoordinatesRow.Wrap(-1)
        self.lbl_StopCoordinatesRow.Enable(False)
        self.szr_StopCoordinates.Add(self.lbl_StopCoordinatesRow, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.txt_StopCoordinatesRow = wx.TextCtrl(self.pnl_Entries,
                                                  size = wx.Size(30,-1),
                                                  style = wx.TE_READONLY)
        self.txt_StopCoordinatesRow.Enable(False)
        self.szr_StopCoordinates.Add(self.txt_StopCoordinatesRow, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.szr_Entries.Add(self.szr_StopCoordinates, 0, wx.ALL, 5)
        self.dic_StopCoordinatesGUI = {"collabel":self.lbl_StopCoordinatesColumn,
                                       "coltext":self.txt_StopCoordinatesColumn,
                                       "rowlabel":self.lbl_StopCoordinatesRow,
                                       "rowtext":self.txt_StopCoordinatesRow}
        # Empty row
        self.szr_StopEmptyLine = wx.BoxSizer(wx.HORIZONTAL)
        self.rad_StopEmptyLine = wx.RadioButton(self.pnl_Entries, 
                                                label = u"Empty row",
                                                style = wx.RB_SINGLE)
        self.szr_StopEmptyLine.Add(self.rad_StopEmptyLine, 0, wx.ALL, 5)
        self.szr_Entries.Add(self.szr_StopEmptyLine, 0, wx.ALL, 5)
        ################################################################################
        # All elements added to sizer
        self.pnl_Entries.SetSizer(self.szr_Entries)
        self.pnl_Entries.Layout()
        self.szr_Entries.Fit(self.pnl_Entries)
        # Add to simplebook #############################################################
        self.sbk_Wizard.AddPage(self.pnl_Entries, u"EntryOrganisation", False)
        self.dic_PageSaveFunctions["EntryOrganisation"] = self.save_entry_organisation
        #################################################################################
        
        """
        ##### #   #  #### ##### ####  ##### #  ###  #   #  ####
        #      # #  #     #     #   #   #   # #   # ##  # #
        ###     #   #     ###   ####    #   # #   # #####  ###
        #      # #  #     #     #       #   # #   # #  ##     #
        ##### #   #  #### ##### #       #   #  ###  #   # ####

        # Wizard Page: Exception Organisation ##########################################
        self.pnl_Exceptions = wx.ScrolledWindow(self.sbk_Wizard,
                                                style = wx.TAB_TRAVERSAL|wx.VSCROLL)
        self.pnl_Exceptions.SetScrollRate(5,5)
        self.pnl_Exceptions.SetBackgroundColour(self.pnlbgclr)
        self.szr_Exceptions = wx.BoxSizer(wx.VERTICAL)
        # Start ########################################################################
        self.lbl_ExceptStart = wx.StaticText(self.pnl_Exceptions,
                                             label = u"Find start of excaptions/error messages entries by")
        self.lbl_ExceptStart.Wrap(-1)
        self.szr_Exceptions.Add(self.lbl_ExceptStart, 0, wx.ALL, 5)
        # Keyword
        self.szr_ExceptKeyword = wx.BoxSizer(wx.HORIZONTAL)
        self.rad_ExceptKeyword = wx.RadioButton(self.pnl_Exceptions,
                                                label = u"unique keyword",
                                                style = wx.RB_SINGLE)
        self.rad_ExceptKeyword.SetValue(True)
        self.szr_ExceptKeyword.Add(self.rad_ExceptKeyword, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.txt_ExceptKeyword = wx.TextCtrl(self.pnl_Exceptions,
                                             style = wx.TE_READONLY)
        self.szr_ExceptKeyword.Add(self.txt_ExceptKeyword, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.txt_ExceptKeywordEditable = wx.TextCtrl(self.pnl_Exceptions,
                                                     style = wx.TE_READONLY)
        self.txt_ExceptKeywordEditable.Enable(False)
        self.txt_ExceptKeywordEditable.Show(False)
        self.szr_ExceptKeyword.Add(self.txt_ExceptKeywordEditable, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.lbl_ExceptKeywordColumn = wx.StaticText(self.pnl_Exceptions,
                                                     label = u"in column")
        self.lbl_ExceptKeywordColumn.Wrap(-1)
        self.szr_ExceptKeyword.Add(self.lbl_ExceptKeywordColumn, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.txt_ExceptKeywordColumn = wx.TextCtrl(self.pnl_Exceptions,
                                                   value = wx.EmptyString,
                                                   size = wx.Size(30,-1),
                                                   style = wx.TE_READONLY)
        self.szr_ExceptKeyword.Add(self.txt_ExceptKeywordColumn, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.szr_Exceptions.Add(self.szr_ExceptKeyword, 0, wx.ALL, 5)
        # Exact?
        self.szr_ExceptKeywordExact = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_ExceptKeywordExact.Add((10,0), 0, wx.ALL, 5)
        self.chk_ExceptKeywordExact = wx.CheckBox(self.pnl_Exceptions,
                                                 label = u"Keyword exactly like in example file.")
        self.chk_ExceptKeywordExact.SetValue(True)
        self.szr_ExceptKeywordExact.Add(self.chk_ExceptKeywordExact, 0, wx.ALL, 0)
        self.szr_Exceptions.Add(self.szr_ExceptKeywordExact, 0, wx.ALL, 5)
        self.dic_ExceptKeywordGUI = {"text":self.txt_ExceptKeyword,
                                    "text_editable":self.txt_ExceptKeywordEditable,
                                    "exact":self.chk_ExceptKeywordExact,
                                    "columnlabel":self.lbl_ExceptKeywordColumn,
                                    "columntext":self.txt_ExceptKeywordColumn}
        # Coordinates
        self.szr_ExceptCoordinates = wx.BoxSizer(wx.HORIZONTAL)
        self.rad_ExceptCoordinates = wx.RadioButton(self.pnl_Exceptions,
                                                   label = u"absolute coordinates:",
                                                   style = wx.RB_SINGLE)
        self.szr_ExceptCoordinates.Add(self.rad_ExceptCoordinates, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.lbl_ExceptCoordinatesColumn = wx.StaticText(self.pnl_Exceptions, label = u"Column")
        self.lbl_ExceptCoordinatesColumn.Wrap(-1)
        self.lbl_ExceptCoordinatesColumn.Enable(False)
        self.szr_ExceptCoordinates.Add(self.lbl_ExceptCoordinatesColumn, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.txt_ExceptCoordinatesColumn = wx.TextCtrl(self.pnl_Exceptions,
                                                      size = wx.Size(30,-1),
                                                      style = wx.TE_READONLY)
        self.txt_ExceptCoordinatesColumn.Enable(False)
        self.szr_ExceptCoordinates.Add(self.txt_ExceptCoordinatesColumn, 0, wx.ALL, 5)
        self.lbl_ExceptCoordinatesRow = wx.StaticText(self.pnl_Exceptions,
                                                     label = u"Row")
        self.lbl_ExceptCoordinatesRow.Wrap(-1)
        self.lbl_ExceptCoordinatesRow.Enable(False)
        self.szr_ExceptCoordinates.Add(self.lbl_ExceptCoordinatesRow, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.txt_ExceptCoordinatesRow = wx.TextCtrl(self.pnl_Exceptions,
                                                   size = wx.Size(30,-1),
                                                   style = wx.TE_READONLY)
        self.txt_ExceptCoordinatesRow.Enable(False)
        self.szr_ExceptCoordinates.Add(self.txt_ExceptCoordinatesRow, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.dic_ExceptCoordinatesGUI = {"collabel":self.lbl_ExceptCoordinatesColumn,
                                        "coltext":self.txt_ExceptCoordinatesColumn,
                                        "rowlabel":self.lbl_ExceptCoordinatesRow,
                                        "rowtext":self.txt_ExceptCoordinatesRow}
        self.szr_Exceptions.Add(self.szr_ExceptCoordinates, 0, wx.ALL, 5)
        ################################################################################
        # All elements added to sizer
        self.pnl_Exceptions.SetSizer(self.szr_Exceptions)
        self.pnl_Exceptions.Layout()
        self.szr_Exceptions.Fit(self.pnl_Exceptions)
        # Add to simplebook #############################################################
        self.sbk_Wizard.AddPage(self.pnl_Exceptions, u"Exceptions", False)
        self.dic_PageSaveFunctions["Exceptions"] = self.save_exceptions
        #################################################################################
        """

         ####  ###  #     #   # #   #  ####
        #     #   # #     #   # ## ## #
        #     #   # #     #   # #####  ###
        #     #   # #     #   # # # #     #
         ####  ###  #####  ###  #   # ####

        # Wizard Page: Columns #########################################################
        self.pnl_Columns = wx.ScrolledWindow(self.sbk_Wizard,
                                             style = wx.TAB_TRAVERSAL|wx.VSCROLL)
        self.pnl_Columns.SetScrollRate(5,5)
        self.pnl_Columns.SetBackgroundColour(self.pnlbgclr)
        self.szr_Columns = wx.BoxSizer(wx.VERTICAL)
        # Columns lbc ##################################################################
        self.szr_ColumnsPanel = wx.BoxSizer(wx.VERTICAL)
        self.szr_ColumnsListControls = wx.BoxSizer(wx.VERTICAL)
        self.lbl_Columns = wx.StaticText(self.pnl_Columns,
                                         label = u"Map columns of transfer file to BBQ data structures")
        self.szr_ColumnsListControls.Add(self.lbl_Columns, 0, wx.ALL, 5)
        self.lbl_MappingNotes = wx.StaticText(self.pnl_Columns,
                                              label = u"Drag and drop column from transfer file to BBQ data structure."
                                              + "\nUn-map a column by selecting it and pressing  the 'Delete' key on the keyboard or using the context menu on right click")
        self.lbl_MappingNotes.Wrap(390)
        self.szr_ColumnsListControls.Add(self.lbl_MappingNotes, 0, wx.ALL, 5)
        self.lbl_Transfer = wx.StaticText(self.pnl_Columns,
                                         label = u"Columns in transfer file:")
        self.szr_ColumnsListControls.Add(self.lbl_Transfer, 0, wx.ALL, 5)
        # List control for columns in transfer file:
        self.lbc_Transfer = dd.MyDragList(self.pnl_Columns,
                                          size = wx.Size(390,100),
                                          style = wx.LC_LIST)
        #self.lbc_Transfer.SetBackgroundColour(clr_TextBoxes)
        self.szr_ColumnsListControls.Add(self.lbc_Transfer, 1, wx.ALL, 5)
        self.lbl_BBQDataStructure = wx.StaticText(self.pnl_Columns,
                                         label = u"BBQ data structure:")
        self.szr_ColumnsListControls.Add(self.lbl_BBQDataStructure, 0, wx.ALL, 5)
        self.lbc_Columns = dd.MyDropTarget(self.pnl_Columns,
                                           size = wx.Size(390,300),
                                           style = wx.LC_REPORT)
        # List Control for columns we want to pair with entries:
        self.lbc_Columns.InsertColumn(0,"")
        self.lbc_Columns.SetColumnWidth(0, 15)
        self.lbc_Columns.InsertColumn(1,"Column Title")
        self.lbc_Columns.SetColumnWidth(1, 175)
        self.lbc_Columns.InsertColumn(2,"Mapped column")
        self.lbc_Columns.SetColumnWidth(2, 175)
        for col in self.rule_set["TransferFileColumns"].keys():
            if self.rule_set["TransferFileColumns"][col]["Required"] == True:
                req = u"*"
            else:
                req = u""
            self.lbc_Columns.InsertItem(self.lbc_Columns.GetItemCount(),req)
            self.lbc_Columns.SetItem(self.lbc_Columns.GetItemCount()-1,1,
                                     self.rule_set["TransferFileColumns"][col]["Name"])
            self.lbc_Columns.SetItem(self.lbc_Columns.GetItemCount()-1,2,"")
        self.szr_ColumnsListControls.Add(self.lbc_Columns, 0, wx.ALL, 5)
        self.szr_ColumnsPanel.Add(self.szr_ColumnsListControls, 0, wx.ALL, 0)
        self.txt_ColumnsHints = wx.TextCtrl(self.pnl_Columns,
                                            value = wx.EmptyString,
                                            size = wx.Size(390,60),
                                            style = wx.TE_READONLY|wx.TE_MULTILINE|wx.TE_WORDWRAP|wx.TE_NO_VSCROLL)
        self.szr_ColumnsPanel.Add(self.txt_ColumnsHints, 0, wx.ALL, 5)
        # All elements added to sizer
        self.pnl_Columns.SetSizer(self.szr_ColumnsPanel)
        self.pnl_Columns.Layout()
        self.szr_ColumnsPanel.Fit(self.pnl_Columns)
        # Add to simplebook #############################################################
        self.sbk_Wizard.AddPage(self.pnl_Columns, u"Columns", False)
        self.dic_PageSaveFunctions["Columns"] = self.save_columns
        #################################################################################

        # Add simplebook to main sizer ##############################################################################################################
        self.szr_Wizard.Add(self.sbk_Wizard, 1, wx.ALL, 5)

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

        # Finish Wizard Sizer
        self.szr_Surround.Add(self.pnl_Wizard, 0, wx.EXPAND, 5)

        # Transfer file grid ###########################################################
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
        self.grd_ExampleFile.SetDefaultCellAlignment(wx.ALIGN_LEFT, wx.ALIGN_TOP)
        self.szr_Surround.Add(self.grd_ExampleFile, 1, wx.ALL, 5)
        self.grd_ExampleFile.Show(False)
        ################################################################################
        
        self.SetSizer(self.szr_Surround)
        self.Layout()

        self.Centre(wx.BOTH)

        ####  # #   # ####  # #   #  ####
        #   # # ##  # #   # # ##  # #
        ####  # ##### #   # # ##### #  ##
        #   # # #  ## #   # # #  ## #   #
        ####  # #   # ####  # #   #  ####

        # Bindings ##################################################################################################################################
        self.fpk_TransferFile.Bind(wx.EVT_FILEPICKER_CHANGED, self.FileSelected)
        self.btn_ParseFile.Bind(wx.EVT_BUTTON, self.parse_transfer_file)
        # Verification keyword
        self.chk_Verification.Bind(wx.EVT_CHECKBOX, self.on_chk_verification)
        self.rad_VerificationKeywordRow.Bind(wx.EVT_RADIOBUTTON, self.on_rad_verificationkeywordrow)
        self.rad_VerificationKeywordColumn.Bind(wx.EVT_RADIOBUTTON, self.on_rad_verificationkeywordcolumn)
        self.chk_VerificationKeywordExact.Bind(wx.EVT_CHECKBOX, self.on_chk_verificationkeywordexact)
        #self.chk_Exceptions.Bind(wx.EVT_CHECKBOX, self.on_chk_exceptions)
        # Start and stop of transfer entries:
        self.rad_StartKeyword.Bind(wx.EVT_RADIOBUTTON, self.on_rad_startkeyword)
        self.chk_StartKeywordExact.Bind(wx.EVT_CHECKBOX, self.on_chk_startkeywordexact)
        self.rad_StartCoordinates.Bind(wx.EVT_RADIOBUTTON, self.on_rad_startcoordinates)
        self.chk_SolventTransfers.Bind(wx.EVT_CHECKBOX, self.on_chk_solventtransfers)
        self.rad_StopKeyword.Bind(wx.EVT_RADIOBUTTON, self.on_rad_stopkeyword)
        self.rad_StopCoordinates.Bind(wx.EVT_RADIOBUTTON, self.on_rad_stopcoordinates)
        self.chk_StopKeywordExact.Bind(wx.EVT_CHECKBOX, self.on_chk_stopkeywordexact)
        self.rad_StopEmptyLine.Bind(wx.EVT_RADIOBUTTON, self.on_rad_stopemptyline)
        # Exceptions
        #self.rad_ExceptKeyword.Bind(wx.EVT_RADIOBUTTON, self.on_rad_exceptkeyword)
        #self.chk_ExceptKeywordExact.Bind(wx.EVT_CHECKBOX, self.on_chk_exceptkeywordexact)
        #self.cbo_Wells.Bind(wx.EVT_COMBOBOX, self.OnWellCommbo)
        self.lbc_Columns.Bind(wx.EVT_MOTION, self.ColumnHint)
        self.lbc_Columns.Bind(wx.EVT_LEAVE_WINDOW, self.ColumnLeave)
        self.lbc_Columns.Bind(dd.EVT_TARGET_UPDATE, self.OnUpdateColumns)
        self.lbc_Transfer.Bind(wx.EVT_LIST_KEY_DOWN, self.on_key_press_bbqstructure)
        self.grd_ExampleFile.Bind(wx.grid.EVT_GRID_CELL_RIGHT_CLICK, self.on_right_click_grid)
        #self.btn_SaveRules.Bind(wx.EVT_BUTTON, self.SaveRuleset)

        # Wizard navigation buttons
        self.btn_WizardBack.Bind(wx.EVT_BUTTON, self.on_wzd_back)
        self.btn_WizardNext.Bind(wx.EVT_BUTTON, self.on_wzd_next)
        self.btn_WizardPrintRules.Bind(wx.EVT_BUTTON, self.PrintRulesAndColumns)

        #############################################################################################################################################

    def __del__(self):
        pass

    def populate_from_file(self, assay):
        """
        Populates this tab after an assay definition file has been
        loaded.
        """
        self.assay = assay
        pass

    ##### #   # ##### #   # #####    #   #  ###  #   # ####  #     ##### ####   ####
    #     #   # #     ##  #   #      #   # #   # ##  # #   # #     #     #   # #
    ###   #   # ###   #####   #      ##### ##### ##### #   # #     ###   ####   ###
    #      # #  #     #  ##   #      #   # #   # #  ## #   # #     #     #   #     #
    #####   #   ##### #   #   #      #   # #   # #   # ####  ##### ##### #   # ####

    # Event handlers for simple book pages ##########################################################################################################

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

    def OnWellCommbo(self,event):
        self.rule_set["DestinationPlateFormat"] = int(self.cbo_Wells.GetValue())

    def on_chk_verification(self, event):
        """
        Event handler.
        Updates UI elements and rule set entries for verification keyword.
        """
        bool_Verification = self.chk_Verification.GetValue()
        self.rule_set["UseVerificationKeyword"] = bool_Verification
        self.txt_VerificationKeyword.Enable(bool_Verification)
        self.lbl_VerificationKeywordColumn.Enable(bool_Verification)
        self.txt_VerificationKeywordColumn.Enable(bool_Verification)

    def on_rad_verificationkeywordrow(self, event):
        """
        Event handler.
        Updates ruleset with whether to use verification keyword row
        or not, based on radio box
        """
        self.rad_VerificationKeywordColumn.SetValue(False)
        self.rule_set["VerificationKeywordAxis"] = 0
        self.rule_set["VerificationKeywordRow"] = int(self.txt_VerificationKeywordRow.GetLineText(0))-1
        self.rule_set["VerificationKeywordColumn"] = None

    def on_rad_verificationkeywordcolumn(self, event):
        """
        Event handler.
        Updates ruleset with whether to use verification keyword column
        or not, based on radio box
        """
        self.rad_VerificationKeywordRow.SetValue(False)
        self.rule_set["VerificationKeywordAxis"] = 1
        self.rule_set["VerificationKeywordRow"] = None
        self.rule_set["VerificationKeywordColumn"] = 65 - ord(self.txt_VerificationKeywordColumn.GetLineText(0))

    def on_chk_verificationkeywordexact(self, event):
        """
        Event handler.
        Toggles option to use exact keyword for verification or partial match.
        """
        self.rule_set["VerificationKeywordExact"] = self.chk_VerificationKeywordExact.GetValue()

    def on_chk_exceptions(self, event):
        """
        Event handler.
        Toggles option to read exceptions/error messages from transfer file.
        """
        expt = self.chk_Exceptions.GetValue()
        self.pnl_Exceptions.Enable(expt)
        self.save_exceptions()

    def on_chk_solventtransfers(self, event):
        self.rule_set["CatchSolventTransfers"] = self.chk_SolventTransfers.GetValue()

    def on_rad_startkeyword(self,event):
        """
        Event handler.
        Enables ui elements for start keyword, disables ui elements
        for start coordinates. Calls save_entry_organisation to update ruleset
        accordingly.
        """
        self.rad_StartCoordinates.SetValue(False)
        for element in self.dic_StartKeywordGUI:
            self.dic_StartKeywordGUI[element].Enable(True)
        for element in self.dic_StartCoordinatesGUI:
            self.dic_StartCoordinatesGUI[element].Enable(False)        
        self.save_entry_organisation()

    def on_chk_startkeywordexact(self, event):
        """
        Event handler.
        Hides/shows TextCtrl for keyword/exact keyword based on value of
        check box. Sets rule "StartKeywordExact" accordingly.
        """
        exact = self.chk_StartKeywordExact.GetValue()
        self.txt_StartKeyword.Show(exact)
        self.txt_StartKeyword.Enable(exact)
        self.txt_StartKeywordEditable.Show(not exact)
        self.txt_StartKeywordEditable.Enable(not exact)
        self.szr_StartKeyword.Layout()
        self.rule_set["StartKeywordExact"] = exact

    def on_rad_startcoordinates(self, event):
        """
        Event handler.
        Enables ui elements for start coordinates, disables ui elements
        for start keyword. Calls save_entry_organisation to update ruleset
        accordingly.
        """
        self.rad_StartKeyword.SetValue(False)
        for element in self.dic_StartKeywordGUI:
            self.dic_StartKeywordGUI[element].Enable(False)
        self.rad_StartKeyword.SetValue(False)
        for element in self.dic_StartCoordinatesGUI:
            self.dic_StartCoordinatesGUI[element].Enable(True)
        self.save_entry_organisation()

    def on_rad_stopkeyword(self, event):
        """
        Event handler.
        Enables ui elements for stop keyword, disables ui elements
        for stop coordinates. Calls save_entry_organisation to update
        ruleset accordingly.
        """
        for element in self.dic_StopKeywordGUI:
            self.dic_StopKeywordGUI[element].Enable(True)
        self.rad_StopCoordinates.SetValue(False)
        for element in self.dic_StopCoordinatesGUI:
            self.dic_StopCoordinatesGUI[element].Enable(False)
        self.rad_StopEmptyLine.SetValue(False)
        self.save_entry_organisation()

    def on_rad_stopcoordinates(self, event):
        """
        Event handler.
        Enables ui elements for stop coordinates, disables ui elements
        for stop keyword. Calls save_entry_organisation to update ruleset
        accordingly.
        """
        
        for element in self.dic_StopKeywordGUI:
            self.dic_StopKeywordGUI[element].Enable(False)
        self.rad_StopKeyword.SetValue(False)
        for element in self.dic_StopCoordinatesGUI:
            self.dic_StopCoordinatesGUI[element].Enable(True)
        self.rad_StopEmptyLine.SetValue(False)
        self.save_entry_organisation()

    def on_chk_stopkeywordexact(self, event):
        """
        Event handler.
        Hides/shows TextCtrl for keyword/exact keyword based on value of
        check box. Sets rule "StopKeywordExact" accordingly.
        """
        exact = self.chk_StopKeywordExact.GetValue()
        self.txt_StopKeyword.Show(exact)
        self.txt_StopKeyword.Enable(exact)
        self.txt_StopKeywordEditable.Show(not exact)
        self.txt_StopKeywordEditable.Enable(not exact)
        self.szr_StopKeyword.Layout()
        self.rule_set["StopKeywordExact"] = exact

    def on_rad_stopemptyline(self, event):
        """
        Event handler.
        Disables UI elements for stop keyword/coordiates and updates ruleset
        accordingly.
        """
        for element in self.dic_StopKeywordGUI.keys():
            self.dic_StopKeywordGUI[element].Enable(False)
        self.rad_StopKeyword.SetValue(False)
        for element in self.dic_StopCoordinatesGUI.keys():
            self.dic_StopCoordinatesGUI[element].Enable(False)
        self.rad_StopCoordinates.SetValue(False)
        self.save_entry_organisation()

    def on_rad_exceptkeyword(self, event):
        """
        Event handler.
        Switches UI elements for start coordinates off (disables) and switches
        UI elements for start keyword on. Updates ruleset accordingly.
        """
        for element in self.dic_ExceptKeywordGUI.keys():
            self.dic_ExceptKeywordGUI[element].Enable(True)
        for element in self.dic_ExceptCoordinatesGUI.keys():
            self.dic_ExceptCoordinatesGUI[element].Enable(True)
        self.rad_ExceptCoordinates.SetValue(False)
        self.save_exceptions()

    def on_rad_exceptkeyword(self, event):
        """
        Event handler.
        Switches UI elements for start coordinates off (disables) and switches
        UI elements for start keyword on. Updates ruleset accordingly.
        """
        for element in self.dic_ExceptKeywordGUI.keys():
            self.dic_ExceptKeywordGUI[element].Enable(True)
        for element in self.dic_ExceptCoordinatesGUI.keys():
            self.dic_ExceptCoordinatesGUI[element].Enable(True)
        self.rad_ExceptCoordinates.SetValue(False)
        self.save_exceptions()

    def on_chk_exceptkeywordexact(self, event):
        """
        Event handler.
        Toggles between setting UI elements and rule set entries for use of
        exact keyword or partial match of keyword.
        """
        bool_CheckBox = self.chk_ExceptKeywordExact.GetValue()
        self.rule_set["StartKeywordExact"] = bool_CheckBox
        self.txt_ExceptKeyword.Show(bool_CheckBox)
        self.txt_ExceptKeyword.Enable(bool_CheckBox)
        self.txt_ExceptKeywordEditable.Show(not bool_CheckBox)
        self.txt_ExceptKeywordEditable.Enable(not bool_CheckBox)
        self.szr_ExceptKeyword.Layout()

    def on_right_click_grid(self, event):
        self.PopupMenu(GridContextMenu(self, event))

    def OnUpdateColumns(self,event):
        if len(event.return_items) > 0:
            for i in range(len(event.return_items)):
                self.lbc_Transfer.InsertItem(self.lbc_Transfer.GetItemCount()+1,event.return_items[i])
            #self.lbc_Transfer.ReSort()
        # Update dataframe for columns
        self.UpdateColumnsDataframe()

    def UpdateColumnsDataframe(self):
        """"
        Updates the columns dataframe/dictionary.
        """
        print("Updating")
        for row in range(self.lbc_Columns.GetItemCount()):
            col = str(row)
            col_name = self.lbc_Columns.GetItemText(row,2)
            print(col_name)
            if len(col_name) > 0:
                print(len(col_name))
                self.rule_set["TransferFileColumns"][col]["Mapped"] = self.lbc_Columns.GetItemText(row,2)
            else:
                self.rule_set["TransferFileColumns"][col]["Mapped"] = None

    def on_key_press_bbqstructure(self, event):
        """
        Event handler
        Catches key presses in lbc_Columns and un-maps columns if it is Delete or Backspace
        """
        # https://docs.wxpython.org/wx.KeyCode.enumeration.html
        idx_Column = self.lbc_Columns.GetFirstSelected()
        idx_Transfer = self.lbc_Transfer.GetFirstSelected()
        # If no item on either list is selected, go away
        if idx_Column == -1:
            event.Skip()
            return None

        # Key: Delete
        # Action: un-map the column
        if event.GetKeyCode() == wx.WXK_DELETE:
            if not len(self.lbc_Columns.GetItemText(idx_Column,2)) == 0:
                self.lbc_Transfer.InsertItem(self.lbc_Transfer.GetItemCount(),self.lbc_Columns.GetItemText(idx_Column,2))
                self.lbc_Columns.SetItem(idx_Column,2,"")
                self.UpdateColumnsDataframe()
        # Key: Backspace
        # Action: un-map the column
        elif event.GetKeyCode() == wx.WXK_BACK:
            if not len(self.lbc_Columns.GetItemText(idx_Column,2)) == 0:
                self.lbc_Transfer.InsertItem(self.lbc_Transfer.GetItemCount(),self.lbc_Columns.GetItemText(idx_Column,2))
                self.lbc_Columns.SetItem(idx_Column,2,"")
                self.UpdateColumnsDataframe()
        else:
            event.Skip()

    def ColumnHint(self, event):
        """
        Writes "Comment" from dfr_TransferFiles->Columns to text box under column list
        controls as an alternative to tool tips.
        """
        row = event.GetEventObject().HitTest(event.GetPosition())[0]
        if row > 0:
            col = str(row - 1)
            self.txt_ColumnsHints.SetValue(self.rule_set["TransferFileColumns"][col]["Comment"])

    def ColumnLeave(self, event):
        """
        Writes empty string
        """
        self.txt_ColumnsHints.SetValue("")

    def FileSelected(self, event):

        self.btn_ParseFile.Enable(True)

        str_FilePath = self.fpk_TransferFile.GetPath()
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

    def parse_transfer_file(self, event):
        """
        Reads transfer file and returns file  type and engine to use for parsing by calling DirectRead function.
        After getting the result, update rule_set and the relevant GUI elements.
        """
        self.Freeze()
        str_FilePath = self.fpk_TransferFile.GetPath()
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
        # DirectRead returns None for all three objects if the file can't be parsed. A real DataFrame would throw an error if compared to None,
        # so we test the next object in line.
        if str_FileType == None:
            return None

        # Update rule_set with results from file reading
        self.rule_set["Extension"] = str_Extension
        self.rule_set["FileType"] = str_FileType
        self.rule_set["Engine"] = str_Engine
        # We only need the worksheet if it is an excel file:
        if str_FileType == "xls":
            self.rule_set["Worksheet"] = self.cbo_Worksheet.GetString(self.cbo_Worksheet.GetCurrentSelection())
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

    def PrintRulesAndColumns(self, event):
        print("Rule set:")
        print(js.dumps(self.assay, sort_keys= False, indent = 2))

    def CheckRules(self):
        """
        Checks whether rules to parse transfer file are consistent
        """
        if self.rule_set["UseVerificationKeyword"] == True:
            if self.rule_set["VerificationKeyword"] == None or self.rule_set["VerificationKeyword"] == "":
                mb.info(self, "No keyword to verify the transfer file given.")
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
        if (self.rule_set["TransferFileColumns"]["Destination Plate Name"] == None and
            self.rule_set["TransferFileColumns"]["Destination Plate Barcode"] == None):
            mb.info(self, "Either 'Destination Plate Name' or 'Destination Plate Barcode' need to have a column assigned")
            return False
        if self.rule_set["TransferFileColumns"]["Destination Well"] == None:
            mb.info(self, "No 'Destination Well' column assigned.")
            return False
        if self.rule_set["TransferFileColumns"]["Destination Concentration"] == None:
            mb.info(self, "Needs at least a destination concentration or source concentration + transfer volume")
        if (self.rule_set["TransferFileColumns"]["Destination Concentration"] == None and
            self.rule_set["TransferFileColumns"]["Source Concentration"] == None):
            mb.info(self, "Needs at least a destination concentration or source concentration + transfer volume")
            return False
        return True

    def SaveRuleset(self, event):
        # First, check that everything has been filled out properly
        if self.CheckColumns() == False:
            return None
        if self.CheckRules() == False:
            return None

        # Get file path:
        with wx.FileDialog(self, "Save project file", wildcard="BBQ transfer rules files (*.transferrules)|*.transferrules",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as fileDialog:
            # Exit via returning nothing if the user changed their mind
            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return
            str_SaveFilePath = fileDialog.GetPath()
            # Prevent duplication of file extension
            if str_SaveFilePath.find(".transferrules") == -1:
                str_SaveFilePath = str_SaveFilePath + ".transferrules"
        # Create zip archive:
        try:
            zip_transferrules = zf.ZipFile(str_SaveFilePath, "w")
        except:
            return False

        # Check whether temporary directory exists and if so, delete. Create temporary directory.
        str_TempDir = os.path.join(Path.home(),"bbqtempdir")
        if os.path.isdir(str_TempDir) == True:
            shutil.rmtree(str_TempDir)
        os.mkdir(str_TempDir)
        
        # Write dataframes to csv and write them to the archive
        self.rule_set["TransferFileColumns"].to_csv(str_TempDir + r"\Columns.csv")
        zip_transferrules.write(str_TempDir + r"\Columns.csv", arcname="Columns.csv")
        self.rule_set.to_csv(str_TempDir + r"\Transferrules.csv")
        zip_transferrules.write(str_TempDir + r"\Transferrules.csv", arcname="Transferrules.csv")
        zip_transferrules.close()

        # Remove all the temporary files
        shutil.rmtree(str_TempDir)

    ####  #   # #     #####     ####  ###  #   # # #   #  ####
    #   # #   # #     #        #     #   # #   # # ##  # #
    ####  #   # #     ###       ###  ##### #   # # ##### #  ##
    #   # #   # #     #            # #   #  # #  # #  ## #   #
    #   #  ###  ##### #####    ####  #   #   #   # #   #  ####

    # Simplebook page saving functions ##############################################################################################################

    def fun_Dummy(self):
        return "Forward"

    def save_example_file(self):
        """
        Saves file type info and verification info to rule_set.
        """

        str_Return = "Backward"

        if self.has_dataframe() == True:
            self.rule_set["UseVerificationKeyword"] = self.chk_Verification.GetValue()
            if self.rule_set["UseVerificationKeyword"] == True:
                # Test if any fields are not filled out:
                if len(self.txt_VerificationKeyword.GetLineText(0)) > 0:
                    if self.chk_VerificationKeywordExact.GetValue() == True:
                        self.rule_set["VerificationKeyword"] = self.txt_VerificationKeyword.GetLineText(0)
                        self.rule_set["ExactVerificationKeyword"] = True
                    else:
                        self.rule_set["VerificationKeyword"] = self.txt_VerificationKeywordEditable.GetLineText(0)
                        self.rule_set["VerificationKeywordExact"] = False
                    if self.rad_VerificationKeywordColumn.GetValue() == True:
                        self.rule_set["VerificationKeywordAxis"] = 0
                    elif self.rad_VerificationKeywordRow.GetValue() == True:
                        self.rule_set["VerificationKeywordAxis"] = 1
                    str_Return +=  "Forward"
                    if self.rad_VerificationKeywordRow.GetValue() == True:
                        if len(self.txt_VerificationKeywordRow.GetLineText(0)) > 0:
                            # Remember: Human readable indexing shown in UI!
                            self.rule_set["VerificationKeywordRow"] = int(self.txt_VerificationKeywordRow.GetLineText(0))-1
                            str_Return +=  "Forward"
                        else:
                            str_Return += "Stop"
                    else:
                        self.rule_set["VerificationKeywordRow"] = None
                    if self.rad_VerificationKeywordColumn.GetValue() == True:
                        if len(self.txt_VerificationKeywordColumn.GetLineText(0)) > 0:
                            self.rule_set["VerificationKeywordColumn"] = 65 - ord(self.txt_VerificationKeywordColumn.GetLineText(0))
                            str_Return +=  "Forward"
                        else:
                            str_Return += "Stop"
                    else:
                        self.rule_set["VerificationKeyworColumn"] = None
                # Fields are not filled out
                else:
                    str_Return += "Stop"
            else:
                self.rule_set["VerificationKeyword"] = None
                self.rule_set["VerificationKeywordColumn"] = None
                self.rule_set["VerificationKeywordRow"] = None
                self.rule_set["VerificationKeywordAxis"] = None
                self.rule_set["VerificationKeywordExact"] = False
            #self.rule_set["CatchExceptions"] = self.chk_Exceptions.GetValue()
            self.rule_set["CatchSolventOnlyTransfers"] = self.chk_SolventTransfers.GetValue()
            str_Return += "Forward"
            #self.save_assay_definition()
        else:
            mb.info(self, "Dataframe for ruleset has not been created.")
            str_Return += "Stop"

        return str_Return

    def save_entry_organisation(self):
        """
        Saves info about top level of data organisation to rule_set.
        """

        str_Return = "Backward"

        if self.has_dataframe() == True:
            # Start keyword
            if self.rad_StartKeyword.GetValue() == True:
                self.rule_set["UseStartKeyword"] = True
                self.rule_set["UseStartCoordinates"] = False
                self.rule_set["StartKeywordExact"] = self.chk_StartKeywordExact.GetValue()
                if self.chk_StartKeywordExact.GetValue() == True:
                    self.rule_set["StartKeyword"] = self.txt_StartKeyword.GetLineText(0)
                else:
                    self.rule_set["StartKeyword"] = self.txt_StartKeywordEditable.GetLineText(0)
                if len(self.txt_StartKeywordColumn.GetLineText(0)) > 0:
                    self.rule_set["StartKeywordColumn"] = 65-ord(self.txt_StartKeywordColumn.GetLineText(0))
                    # 65 is the unicode for "A"
                else:
                    self.rule_set["StartKeywordColumn"] = None
                    str_Return += "Stop"
                self.rule_set["StartCoordinates"] = None
            else:
                self.rule_set["UseStartKeyword"] = False
                self.rule_set["StartKeywordExact"] = False
                self.rule_set["StartKeyword"] = None
                self.rule_set["UseStartCoordinates"] = True
                self.rule_set["StartKeywordColumn"] = None
                if len(self.txt_StartCoordinatesColumn.GetLineText(0)) > 0 and self.txt_StartCoordinatesRow.GetLineText(0):
                    self.rule_set["StartCoordinates"] = (int(self.txt_StartCoordinatesRow.GetLineText(0)),
                                                               65-ord(self.txt_StartCoordinatesColumn.GetLineText(0)))
                else:
                    self.rule_set["StartCoordinates"] = None
                    str_Return += "Stop"
            # Stop keyword
            if self.rad_StopKeyword.GetValue() == True:
                self.rule_set["UseStopKeyword"] = True
                self.rule_set["UseStopCoordinates"] = False
                self.rule_set["StopKeywordExact"] = self.chk_StopKeywordExact.GetValue()
                if self.chk_StopKeywordExact.GetValue() == True:
                    self.rule_set["StopKeyword"] = self.txt_StopKeyword.GetLineText(0)
                else:
                    self.rule_set["StopKeyword"] = self.txt_StopKeywordEditable.GetLineText(0)
                if len(self.txt_StopKeywordColumn.GetLineText(0)) > 0:
                    self.rule_set["StopKeywordColumn"] = 65-ord(self.txt_StopKeywordColumn.GetLineText(0))
                    # 65 is the unicode for "A"
                else:
                    self.rule_set["StopKeywordColumn"] = None
                    str_Return += "Stop"
                self.rule_set["UseStopEmptyLine"] = False
            elif self.rad_StopCoordinates.GetValue() == True:
                self.rule_set["UseStopKeyword"] = False
                self.rule_set["StopKeywordExact"] = False
                self.rule_set["UseStopCoordinates"] = True
                self.rule_set["StopKeywordColumn"] = None
                if len(self.txt_StopCoordinatesColumn.GetLineText(0)) > 0 and self.txt_StopCoordinatesRow.GetLineText(0):
                    self.rule_set["StopCoordinates"] = (int(self.txt_StopCoordinatesRow.GetLineText(0)),
                                                                  65-ord(self.txt_StopCoordinatesColumn.GetLineText(0)))
                else:
                    self.rule_set["StopCoordinates"] = None
                    str_Return += "Stop"
                self.rule_set["UseStopEmptyLine"] = False
            else:
                self.rule_set["UseStopKeyword"] = False
                self.rule_set["StopKeywordExact"] = False
                self.rule_set["UseStopCoordinates"] = False
                self.rule_set["StopKeywordColumn"] = None
                self.rule_set["StopCoordinates"] = None
                self.rule_set["UseStopEmptyLine"] = True 
            str_Return += "Forward"
            #self.save_assay_definition()
        else:
            mb.info(self, "Dataframe for ruleset has not been created.")
            str_Return += "Stop"

        return str_Return
    
    def save_exceptions(self):
        """
        Saves info aboutexceptions/error messages to rule_set.
        """

        str_Return = "Backward"

        if self.has_dataframe() == True:
            if self.chk_Exceptions.GetValue() == True:
                # We dp ise exceptions
                self.rule_set["CatchExceptions"] = True
                # Exceptions keyword
                if self.rad_ExceptKeyword.GetValue() == True:
                    self.rule_set["UseExceptionsKeyword"] = True
                    self.rule_set["UseExceptionsCoordinates"] = False
                    self.rule_set["ExceptionsKeywordExact"] = self.chk_ExceptKeywordExact.GetValue()
                    if self.chk_ExceptKeywordExact.GetValue() == True:
                        self.rule_set["ExceptionsKeyword"] = self.txt_ExceptKeyword.GetLineText(0)
                    else:
                        self.rule_set["ExceptionsKeyword"] = self.txt_ExceptKeywordEditable.GetLineText(0)
                    if len(self.txt_ExceptKeywordColumn.GetLineText(0)) > 0:
                        self.rule_set["ExceptionsKeywordColumn"] = 65-ord(self.txt_ExceptKeywordColumn.GetLineText(0))
                        # 65 is the unicode for "A"
                    else:
                        self.rule_set["ExceptionsKeywordColumn"] = None
                        str_Return += "Stop"
                    self.rule_set["ExceptionsCoordinates"] = None
                else:
                    self.rule_set["UseExceptionsKeyword"] = False
                    self.rule_set["ExceptionsKeywordExact"] = False
                    self.rule_set["UseExceptionsCoordinates"] = True
                    self.rule_set["ExceptionsKeywordColumn"] = None
                    if len(self.txt_ExceptCoordinatesColumn.GetLineText(0)) > 0 and self.txt_ExceptCoordinatesRow.GetLineText(0):
                        self.rule_set["ExceptionsCoordinates"] = (int(self.txt_ExceptCoordinatesRow.GetLineText(0)),
                                                                        65-ord(self.txt_ExceptCoordinatesColumn.GetLineText(0)))
                    else:
                        self.rule_set["ExceptionsCoordinates"] = None
                        str_Return += "Stop"
            else:
                # We don't use exceptions
                self.rule_set["CatchExceptions"] = False
                self.rule_set["UseExceptionsKeyword"] = False
                self.rule_set["ExceptionsKeywordExact"] = False
                self.rule_set["UseExceptionsCoordinates"] = False
                self.rule_set["ExceptionsKeywordColumn"] = None
                self.rule_set["ExceptionsCoordinates"] = None
            str_Return += "Forward"
            #self.save_assay_definition()
        else:
            mb.info(self, "Dataframe for ruleset has not been created.")
            str_Return += "Stop"

        return str_Return

    def save_columns(self):
        """
        Saves info about mapping transfer file data onto BBQ datastructure rule_set.
        """
        str_Return = "Backwards"

        for row in range(self.lbc_Columns.GetItemCount()):
            col = str(row)
            col_name = self.lbc_Columns.GetItemText(row,2)
            if len(col_name) > 0:
                self.rule_set["TransferFileColumns"][col]["Mapped"] = col_name
            else:
                self.rule_set["TransferFileColumns"][col]["Mapped"] = None

        str_Return += "Forward"

        #self.save_assay_definition()

        return str_Return

    def save_assay_definition(self):
        """
        Writes the ruleset to the assay definition dictionary
        """
        self.assay["TransferRules"] = copy.deepcopy(self.rule_set)

    def has_dataframe(self):
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

########################################################################################################
##                                                                                                    ##
##     #####   ####   ##  ##  ######  ######  ##  ##  ######      ##    ##  ######  ##  ##  ##  ##    ##
##    ##      ##  ##  ### ##    ##    ##       ####     ##        ###  ###  ##      ### ##  ##  ##    ##
##    ##      ##  ##  ######    ##    ####      ##      ##        ########  ####    ######  ##  ##    ##
##    ##      ##  ##  ## ###    ##    ##       ####     ##        ## ## ##  ##      ## ###  ##  ##    ##
##     #####   ####   ##  ##    ##    ######  ##  ##    ##        ##    ##  ######  ##  ##   ####     ##
##                                                                                                    ##
########################################################################################################

class GridContextMenu(wx.Menu):
    def __init__(self, parent, rightclick):
        super(GridContextMenu, self).__init__()
        """
        Context menu to define keywords, locations, etc. on grid.
        """
        #real_path = os.path.realpath(__file__)
        #dir_path = os.path.dirname(real_path)
        #str_MenuIconsPath = dir_path + r"\menuicons"

        self.parent = parent

        # Save EventObject in instance variable
        self.grid = rightclick.GetEventObject()
        self.row = rightclick.GetRow()
        self.col = rightclick.GetCol()

        # Verification Keyword ######################################################################################################################
        if self.parent.chk_Verification.GetValue() == True:
            self.mi_VerificationKeyword = wx.MenuItem(self, wx.ID_ANY, u"File verification keyword", wx.EmptyString, wx.ITEM_NORMAL)
            #self.mi_TransferKeyword.SetBitmap(wx.Bitmap(str_MenuIconsPath + r"\TickBoxTicked.ico"))
            self.Append(self.mi_VerificationKeyword)
            self.Bind(wx.EVT_MENU, lambda event: self.VerificationKeyword(event, self.row, self.col), self.mi_VerificationKeyword)

        # Start Keyword #############################################################################################################################
        if self.parent.rad_StartKeyword.GetValue() == True:
            self.mi_TransferStartKeyword = wx.MenuItem(self, wx.ID_ANY, u"Start keyword for transfers", wx.EmptyString, wx.ITEM_NORMAL)
            #self.mi_TransferKeyword.SetBitmap(wx.Bitmap(str_MenuIconsPath + r"\TickBoxTicked.ico"))
            self.Append(self.mi_TransferStartKeyword)
            self.Bind(wx.EVT_MENU, lambda event: self.TransferStartKeyword(event, self.row, self.col), self.mi_TransferStartKeyword)
        # Start Coordinates
        if self.parent.rad_StartCoordinates.GetValue() == True:
            self.mi_TransferStartCoordinates = wx.MenuItem(self, wx.ID_ANY, u"Start coordinates for Transfer", wx.EmptyString, wx.ITEM_NORMAL)
            self.Append(self.mi_TransferStartCoordinates)
            self.Bind(wx.EVT_MENU, lambda event: self.TransferStartCoordinates(event, self.row, self.col), self.mi_TransferStartCoordinates)
        # Stop Keyword
        if self.parent.rad_StopKeyword.GetValue() == True:
            self.mi_TransferStopKeyword = wx.MenuItem(self, wx.ID_ANY, u"Stop keyword for transfers", wx.EmptyString, wx.ITEM_NORMAL)
            #self.mi_TransferKeyword.SetBitmap(wx.Bitmap(str_MenuIconsPath + r"\TickBoxTicked.ico"))
            self.Append(self.mi_TransferStopKeyword)
            self.Bind(wx.EVT_MENU, lambda event: self.TransferStopKeyword(event, self.row, self.col), self.mi_TransferStopKeyword)
        # Stop Coordinates
        if self.parent.rad_StopCoordinates.GetValue() == True:
            self.mi_TransferStopCoordinates = wx.MenuItem(self, wx.ID_ANY, u"Stop coordinates for Transfer", wx.EmptyString, wx.ITEM_NORMAL)
            self.Append(self.mi_TransferStopCoordinates)
            self.Bind(wx.EVT_MENU, lambda event: self.TransferStopCoordinates(event, self.row, self.col), self.mi_TransferStopCoordinates)

        #self.AppendSeparator()

    def VerificationKeyword(self, event, row, col):
        # Update display
        self.parent.txt_VerificationKeyword.SetValue(self.grid.GetCellValue(row, col))
        self.parent.txt_VerificationKeywordColumn.SetValue(str(chr(col+65)))
        self.parent.txt_VerificationKeywordRow.SetValue(str(row+1))
        # Update ruleset
        self.parent.rule_set["VerificationKeyword"] = self.grid.GetCellValue(row, col)
        self.parent.rule_set["VerificationKeywordColumn"] = col
        self.parent.rule_set["VerificationKeywordRow"] = row

    def TransferStartKeyword(self, event, row, col):
        keyword = self.grid.GetCellValue(row, col)
        # Update display
        self.parent.txt_StartKeyword.SetValue(keyword)
        self.parent.txt_StartKeywordEditable.SetValue(keyword)
        self.parent.txt_StartKeywordColumn.SetValue(str(chr(col+65)))
        self.parent.txt_StartCoordinatesColumn.SetValue("")
        self.parent.txt_StartCoordinatesRow.SetValue("")
        # Update ruleset
        self.parent.rule_set["StartKeyword"] = self.grid.GetCellValue(row, col)
        self.parent.rule_set["StartKeywordColumn"] = col
        self.parent.rule_set["StartKeywordRow"] = row
        self.parent.rule_set["StartCoordinates"] = None
        # Update lists:
        self.populate_lists(row, col)

    def TransferStartCoordinates(self, event, row, col):
        # Update display
        self.parent.txt_StartKeyword.SetValue("")
        self.parent.txt_StartKeywordColumn.SetValue("")
        self.parent.txt_StartCoordinatesColumn.SetValue(chr(col+65))
        self.parent.txt_StartCoordinatesRow.SetValue(str(row+1))
        # Update ruleset
        self.parent.rule_set["StartKeyword"] = None
        self.parent.rule_set["StartKeywordColumn"] = None
        self.parent.rule_set["StartCoordinates"] = (row,col)
        # Update lists:
        self.populate_lists(row, col)

    def populate_lists(self, row, col):
        # Get available column titles:
        self.parent.dic_Available = {}
        lst_Available = []
        for i in range(self.parent.grd_ExampleFile.GetNumberCols()):
            if self.parent.grd_ExampleFile.GetCellValue(row,i) != "":
                lst_Available.append(self.parent.grd_ExampleFile.GetCellValue(row,i))
        # Update list controls required and available columns
        self.parent.lbc_Transfer.DeleteAllItems()
        for name in lst_Available:
            self.parent.lbc_Transfer.InsertItem(self.parent.lbc_Transfer.GetItemCount(),name)

    def TransferStopKeyword(self, event, row, col):
        # Update display
        self.parent.txt_StopKeyword.SetValue(self.grid.GetCellValue(row, col))
        self.parent.txt_StopKeywordColumn.SetValue(str(chr(col+65)))
        self.parent.txt_StopCoordinatesColumn.SetValue("")
        self.parent.txt_StopCoordinatesRow.SetValue("")
        # Update ruleset
        self.parent.rule_set["StopKeyword"] = self.grid.GetCellValue(row, col)
        self.parent.rule_set["StopKeywordColumn"] = col
        self.parent.rule_set["StopCoordinates"] = None

    def TransferStopCoordinates(self, event, row, col):
        # Update display
        self.parent.txt_StopKeyword.SetValue("")
        self.parent.txt_StopKeywordColumn.SetValue("")
        self.parent.txt_StopCoordinatesColumn.SetValue(chr(col+65))
        self.parent.txt_StopCoordinatesRow.SetValue(str(row+1))
        # Update ruleset
        self.parent.rule_set["StopKeyword"] = None
        self.parent.rule_set["StopKeywordColumn"] = None
        self.parent.rule_set["StopCoordinates"] = (row,col)

############################################################################################
##                                                                                        ##
##     ####   #####   #####   ##      ##  ##    #####   ##  ##  ##      ######   #####    ##
##    ##  ##  ##  ##  ##  ##  ##      ##  ##    ##  ##  ##  ##  ##      ##      ##        ##
##    ######  #####   #####   ##       ####     #####   ##  ##  ##      ####     ####     ##
##    ##  ##  ##      ##      ##        ##      ##  ##  ##  ##  ##      ##          ##    ##
##    ##  ##  ##      ##      ######    ##      ##  ##   ####   ######  ######  #####     ##
##                                                                                        ##
############################################################################################

class frm_ApplyTransferRules (wx.Frame):

    def __init__(self, parent):
        wx.Frame.__init__ (self, parent, id = wx.ID_ANY, title = wx.EmptyString, pos = wx.DefaultPosition, size = wx.Size(819,588),
                            style = wx.DEFAULT_FRAME_STYLE|wx.TAB_TRAVERSAL)

        self.SetSizeHints(wx.DefaultSize, wx.DefaultSize)

        self.OpenRuleset(None)

        self.str_FilePath = self.OpenFileToParse()

        bool_Success = False # Set default value.
        self.dfr_Layout, bool_Success = tf.TransferFileToLayout(self.rule_set, self.str_FilePath)

        if bool_Success == False:
            mb.info(self,
                        "Either start or stop of transfer entries could not be found.\nCheck your transfer file parsing rules for consistency.")
            return None

        self.int_Rows = self.dfr_Layout.iloc[0,0].shape[0]
        self.int_Columns = self.dfr_Layout.iloc[0,0].shape[1]
        self.lst_RowNames = self.dfr_Layout.iloc[0,0].index

        self.szr_Envelope = wx.BoxSizer(wx.HORIZONTAL)

        self.szr_Plates = wx.BoxSizer(wx.HORIZONTAL)

        # List Control - Plates
        self.lbc_Plates = wx.ListCtrl(self, 
                                      size = wx.Size(175,-1),
                                      style = wx.LC_REPORT|wx.LC_SINGLE_SEL)
        self.lbc_Plates.InsertColumn(0, "Plate")
        self.lbc_Plates.SetColumnWidth(0,40)
        self.lbc_Plates.InsertColumn(1,"Transfer file entry")
        self.lbc_Plates.SetColumnWidth(1, 120)
        self.szr_Plates.Add(self.lbc_Plates, 0, wx.ALL|wx.EXPAND, 5)

        # add destination plate entries
        for plate in self.dfr_Layout.index:
            self.lbc_Plates.InsertItem(self.lbc_Plates.GetItemCount(), str(self.lbc_Plates.GetItemCount()+1))
            self.lbc_Plates.SetItem(self.lbc_Plates.GetItemCount()-1, 1, plate)


        self.szr_Envelope.Add(self.szr_Plates, 0, wx.EXPAND, 5)

        self.nbk_Layout = wx.Notebook(self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, 0)
        # Add pages for all columns #################################################################################################################
        self.dic_NotebookPages = {}
        self.dic_NotebookSizers = {}
        self.dic_NotebookGrids = {}
        for col in self.dfr_Layout.columns:
            self.dic_NotebookPages[col] = wx.Panel(self.nbk_Layout, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL)
            self.dic_NotebookSizers[col] = wx.BoxSizer(wx.VERTICAL)
            self.dic_NotebookGrids[col] = wx.grid.Grid(self.dic_NotebookPages[col], wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, 0)
            # Grid
            self.dic_NotebookGrids[col].CreateGrid(self.int_Rows, self.int_Columns)
            self.dic_NotebookGrids[col].EnableEditing(False)
            self.dic_NotebookGrids[col].EnableGridLines(True)
            self.dic_NotebookGrids[col].EnableDragGridSize(False)
            self.dic_NotebookGrids[col].SetMargins(0, 0)
            # Columns
            self.dic_NotebookGrids[col].EnableDragColMove(False)
            self.dic_NotebookGrids[col].EnableDragColSize(False)
            self.dic_NotebookGrids[col].SetColLabelAlignment(wx.ALIGN_CENTER, wx.ALIGN_CENTER)
            for gridcol in range(self.dic_NotebookGrids[col].GetNumberCols()):
                self.dic_NotebookGrids[col].SetColLabelValue(gridcol, str(gridcol+1))
            # Rows
            self.dic_NotebookGrids[col].EnableDragRowSize(True)
            self.dic_NotebookGrids[col].SetRowLabelAlignment(wx.ALIGN_CENTER, wx.ALIGN_CENTER)
            for gridrow in range(self.dic_NotebookGrids[col].GetNumberRows()):
                self.dic_NotebookGrids[col].SetRowLabelValue(gridrow, self.lst_RowNames[gridrow])
            # Label Appearance
            # Cell Defaults
            self.dic_NotebookGrids[col].SetDefaultCellAlignment(wx.ALIGN_LEFT, wx.ALIGN_TOP)
            self.dic_NotebookSizers[col].Add(self.dic_NotebookGrids[col], 0, wx.ALL, 5)
            # Grid finished -> populate grid
            for gridrow in range(self.dfr_Layout.loc[self.dfr_Layout.index[0],col].shape[0]):
                for gridcol in range(self.dfr_Layout.loc[self.dfr_Layout.index[0],col].shape[1]):
                    self.dic_NotebookGrids[col].SetCellValue(gridrow,gridcol,
                                                            str(self.dfr_Layout.loc[self.dfr_Layout.index[0],col].iloc[gridrow,gridcol]))
            self.dic_NotebookPages[col].SetSizer(self.dic_NotebookSizers[col])
            self.dic_NotebookPages[col].Layout()
            self.dic_NotebookSizers[col].Fit(self.dic_NotebookPages[col])
            self.nbk_Layout.AddPage(self.dic_NotebookPages[col], col, True)
        #############################################################################################################################################
        
        self.szr_Envelope.Add(self.nbk_Layout, 1, wx.EXPAND |wx.ALL, 5)

        # Bindings ##################################################################################################################################
        self.lbc_Plates.Bind(wx.EVT_LIST_ITEM_SELECTED, self.DisplayPlate)


        self.SetSizer(self.szr_Envelope)
        self.Layout()

        self.Centre(wx.BOTH)

    def __del__(self):
        pass

    def OpenRuleset(self, event):
        with wx.FileDialog(self, "Open transfer file rule set", wildcard="BBQ transferrule files (*.transferrules)|*.transferrules",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as fileDialog:

            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return None     # the user changed their mind
            str_FilePath = fileDialog.GetPath()

        # Check whether temporary directory exists. if so, delete and make fresh
        str_TempDir = os.path.join(Path.home(),"bbqtempdir")
        if os.path.isdir(str_TempDir) == True:
            shutil.rmtree(str_TempDir)
        os.mkdir(str_TempDir)

        # Extract saved file to temporary directory
        with zf.ZipFile(str_FilePath, "r") as zip:
            zip.extractall(str_TempDir)

        # Read csv files into dataframes
        self.rule_set = pd.read_csv(str_TempDir + r"\Transferrules.csv", sep=",", header=0, index_col=0, engine="python")
        for key in self.rule_set.keys():
            if self.rule_set[key] == "True":
                self.rule_set[key] = True
            elif self.rule_set[key] == "False":
                self.rule_set[key] = False
            elif pd.isna(self.rule_set[key]) == True:
                self.rule_set[key] = None
        dfr_Columns = pd.read_csv(str_TempDir + r"\Columns.csv", sep=",", header=0, index_col=0, engine="python")
        for field in dfr_Columns.index:
            if dfr_Columns.loc[field] == "True":
                dfr_Columns.loc[field] = True
            elif dfr_Columns.loc[field] == "False":
                dfr_Columns.loc[field] = False
            elif pd.isna(dfr_Columns.loc[field]) == True:
                dfr_Columns.loc[field] = None

        self.rule_set["TransferFileColumns"] = None
        self.rule_set["TransferFileColumns"] = dfr_Columns

        # Delete temporary directory again
        shutil.rmtree(str_TempDir)

    def OpenFileToParse(self):
        with wx.FileDialog(self, "Open liquid handler transfer file", wildcard="Liquid handler transfer file (*.*)|*.*",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as fileDialog:

            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return None     # the user changed their mind
            return fileDialog.GetPath()

    def DisplayPlate(self, event):
        """
        Displays a plate layout's information.
        """
        plate = self.lbc_Plates.GetItemText(self.lbc_Plates.GetFirstSelected(),1)
        for grid in self.dic_NotebookGrids:
            self.dic_NotebookGrids[grid].ClearGrid()
            for gridrow in range(self.dfr_Layout.loc[plate,grid].shape[0]):
                for gridcol in range(self.dfr_Layout.loc[plate,grid].shape[1]):
                    self.dic_NotebookGrids[grid].SetCellValue(gridrow,gridcol,str(self.dfr_Layout.loc[plate,grid].iloc[gridrow,gridcol]))
                    