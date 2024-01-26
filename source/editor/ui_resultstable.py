
"""
    In this module:
    
    User interface elements for building the results table

"""

# Imports ##############################################################################

import wx
import wx.xrc
import wx.grid

import pandas as pd
import numpy as np
import os
from pathlib import Path
import zipfile as zf
import copy

import json as js

import lib_messageboxes as mb
import lib_colourscheme as cs
import editor.lib_resultsdragndrop as rdnd
import lib_custombuttons as btn
import wx.lib.mixins.listctrl as mxlc

################################################################################################
##                                                                                            ##
##    #####   ######  ######  ##  ##  ##  ######    #####   ##  ##  ##      ######   #####    ##
##    ##  ##  ##      ##      ##  ### ##  ##        ##  ##  ##  ##  ##      ##      ##        ##
##    ##  ##  ####    ####    ##  ######  ####      #####   ##  ##  ##      ####     ####     ##
##    ##  ##  ##      ##      ##  ## ###  ##        ##  ##  ##  ##  ##      ##          ##    ##
##    #####   ######  ##      ##  ##  ##  ######    ##  ##   ####   ######  ######  #####     ##
##                                                                                            ##
################################################################################################

class ResultsTable (wx.Panel):
    """
    Panel for results table
    """
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

        self.assay["ResultsTable"] = CreateBlankRuleSet()
        self.rule_set = self.assay["ResultsTable"]
        # Associated variables:

        self.sizer = wx.BoxSizer(wx.HORIZONTAL)

        # Sidebar with all the options
        self.szr_PossibleColumns = wx.BoxSizer(wx.VERTICAL)
        self.szr_Instructions = wx.BoxSizer(wx.VERTICAL)
        self.lbl_PossibleColumns = wx.StaticText(self,
                                                 label = u"Preparing the results table:")
        self.szr_Instructions.Add(self.lbl_PossibleColumns, 0, wx.ALL, 5)
        self.lbl_Instructions = wx.StaticText(self,
                                              label = u"Create columns for the results table by selecting values from the lists below and dragging and dropping them into the list on the left. Every column needs a title assigned to it.")
        self.lbl_Instructions.Wrap(340)
        self.szr_Instructions.Add(self.lbl_Instructions, 0, wx.ALL, 5)
        self.szr_Instructions.Add((340,5), 0, wx.ALL, 5)
        self.szr_PossibleColumns.Add(self.szr_Instructions, 0, wx.ALL, 0)

        # Sizer With Buttons
        self.szr_SimpleBook = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_Buttons = wx.BoxSizer(wx.VERTICAL)

        self.btn_Meta = btn.ListBookButton(self,
                                          change_tab_owner = self,
                                          label = u"Meta Data",
                                          index = 0)
        self.btn_Meta.IsCurrent(True)
        self.szr_Buttons.Add(self.btn_Meta, 0, wx.ALL, 0)
        self.btn_Details = btn.ListBookButton(self,
                                             change_tab_owner = self,
                                             label = u"Assay Details",
                                             index = 1)
        self.szr_Buttons.Add(self.btn_Details, 0, wx.ALL, 0)
        self.btn_Reagents = btn.ListBookButton(self,
                                             change_tab_owner = self,
                                             label = u"Reagents",
                                             index = 2)
        self.szr_Buttons.Add(self.btn_Reagents, 0, wx.ALL, 0)
        self.btn_Transfer = btn.ListBookButton(self,
                                           change_tab_owner = self,
                                           label = u"Transfer File",
                                           index = 3)
        self.szr_Buttons.Add(self.btn_Transfer, 0, wx.ALL, 0)
        self.btn_Quality = btn.ListBookButton(self,
                                           change_tab_owner = self,
                                           label = u"Raw data plate quality",
                                           index = 4)
        self.szr_Buttons.Add(self.btn_Quality, 0, wx.ALL, 0)
        self.btn_Datapoints = btn.ListBookButton(self,
                                           change_tab_owner = self,
                                           label = u"Datapoints",
                                           index = 5)
        self.szr_Buttons.Add(self.btn_Datapoints, 0, wx.ALL, 0)
        self.btn_Model = btn.ListBookButton(self,
                                           change_tab_owner = self,
                                           label = u"Fitting Model",
                                           index = 6)
        self.szr_Buttons.Add(self.btn_Model, 0, wx.ALL, 0)
        self.dic_NoteBookButtons = {0:self.btn_Meta,
                                    1:self.btn_Details,
                                    2:self.btn_Reagents,
                                    3:self.btn_Transfer,
                                    4:self.btn_Quality,
                                    5:self.btn_Datapoints,
                                    6:self.btn_Model}
        self.btn_Meta.Group = self.dic_NoteBookButtons
        self.btn_Details.Group = self.dic_NoteBookButtons
        self.btn_Reagents.Group = self.dic_NoteBookButtons
        self.btn_Transfer.Group = self.dic_NoteBookButtons
        self.btn_Quality.Group = self.dic_NoteBookButtons
        self.btn_Datapoints.Group = self.dic_NoteBookButtons
        self.btn_Model.Group = self.dic_NoteBookButtons
        
        
        self.szr_SimpleBook.Add(self.szr_Buttons, 0, wx.ALL, 0)

        # Sizer with simplebook
        self.sbk_Columns = wx.Simplebook(self, size = wx.Size(200,400))
        self.btn_Meta.Notebook = self.sbk_Columns
        self.btn_Details.Notebook = self.sbk_Columns
        self.btn_Reagents.Notebook = self.sbk_Columns
        self.btn_Transfer.Notebook = self.sbk_Columns
        self.btn_Quality.Notebook = self.sbk_Columns
        self.btn_Datapoints.Notebook = self.sbk_Columns
        self.btn_Model.Notebook = self.sbk_Columns
        self.dic_ListCtrls = {}
        # Meta Data Page
        self.pnl_Meta = wx.Panel(self.sbk_Columns)
        self.szr_Meta = wx.BoxSizer(wx.VERTICAL)
        self.lbc_Meta = rdnd.MyDragList(self.pnl_Meta,
                                        size = wx.Size(200,400),
                                        style=wx.LC_LIST,
                                        name = u"Meta")
        self.lbc_Meta.table_name = "Meta"
        self.szr_Meta.Add(self.lbc_Meta, 0, wx.ALL, 0)
        self.pnl_Meta.SetSizer(self.szr_Meta)
        self.pnl_Meta.Layout()
        self.szr_Meta.Fit(self.pnl_Meta)
        self.sbk_Columns.AddPage(self.pnl_Meta, u"Meta Data", True)
        self.dic_ListCtrls["Meta"] = self.lbc_Meta
        # Assay details
        self.pnl_Details = wx.Panel(self.sbk_Columns)
        self.szr_Details = wx.BoxSizer(wx.VERTICAL)
        self.lbc_Details = rdnd.MyDragList(self.pnl_Details,
                                           size = wx.Size(200,400),
                                           style=wx.LC_LIST,
                                           name = u"Details")
        self.lbc_Details.table_name = "Details"
        self.szr_Details.Add(self.lbc_Details, 0, wx.ALL, 0)
        self.pnl_Details.SetSizer(self.szr_Details)
        self.pnl_Details.Layout()
        self.szr_Details.Fit(self.pnl_Details)
        self.sbk_Columns.AddPage(self.pnl_Details, u"Assay Details", True)
        self.dic_ListCtrls["Details"] = self.lbc_Details
        # Reagents
        self.pnl_Reagents = wx.Panel(self.sbk_Columns)
        self.szr_Reagents = wx.BoxSizer(wx.VERTICAL)
        self.lbc_Reagents = rdnd.MyDragList(self.pnl_Reagents,
                                            size = wx.Size(200,400),
                                            style=wx.LC_LIST,
                                            name = u"Reagents")
        self.lbc_Reagents.table_name = "Reagents"
        self.szr_Reagents.Add(self.lbc_Reagents, 0, wx.ALL, 0)
        self.pnl_Reagents.SetSizer(self.szr_Reagents)
        self.pnl_Reagents.Layout()
        self.szr_Reagents.Fit(self.pnl_Reagents)
        self.sbk_Columns.AddPage(self.pnl_Reagents, u"Reagents", True)
        self.dic_ListCtrls["Reagents"] = self.lbc_Reagents
        # Transfer File Entries
        self.pnl_Transfer = wx.Panel(self.sbk_Columns)
        self.szr_Transfer = wx.BoxSizer(wx.VERTICAL)
        self.lbc_Transfer = rdnd.MyDragList(self.pnl_Transfer,
                                           size = wx.Size(200,400),
                                           style=wx.LC_LIST,
                                           name = u"Transfer")
        self.lbc_Transfer.table_name = "Transfer"
        self.szr_Transfer.Add(self.lbc_Transfer, 0, wx.ALL, 0)
        self.pnl_Transfer.SetSizer(self.szr_Transfer)
        self.pnl_Transfer.Layout()
        self.szr_Transfer.Fit(self.pnl_Transfer)
        self.sbk_Columns.AddPage(self.pnl_Transfer, u"Transfer Entries", True)
        self.dic_ListCtrls["Transfer"] = self.lbc_Transfer
        # Assay Plate Quality
        self.pnl_Quality = wx.Panel(self.sbk_Columns)
        self.szr_Quality = wx.BoxSizer(wx.VERTICAL)
        self.lbc_Quality = rdnd.MyDragList(self.pnl_Quality,
                                           size = wx.Size(200,400),
                                           style=wx.LC_LIST,
                                           name = u"Quality")
        self.lbc_Quality.table_name = "Quality"
        self.szr_Quality.Add(self.lbc_Quality, 0, wx.ALL, 0)
        self.pnl_Quality.SetSizer(self.szr_Quality)
        self.pnl_Quality.Layout()
        self.szr_Quality.Fit(self.pnl_Quality)
        self.sbk_Columns.AddPage(self.pnl_Quality, u"Data Quality", True)
        self.dic_ListCtrls["Quality"] = self.lbc_Quality
        # Data points
        self.pnl_Datapoints = wx.Panel(self.sbk_Columns)
        self.szr_Datapoints = wx.BoxSizer(wx.VERTICAL)
        self.lbc_Datapoints = rdnd.MyDragList(self.pnl_Datapoints,
                                           size = wx.Size(200,400),
                                           style=wx.LC_LIST,
                                           name = u"Datapoints")
        self.lbc_Datapoints.table_name = "Datapoints"
        self.szr_Datapoints.Add(self.lbc_Datapoints, 0, wx.ALL, 0)
        self.pnl_Datapoints.SetSizer(self.szr_Datapoints)
        self.pnl_Datapoints.Layout()
        self.szr_Datapoints.Fit(self.pnl_Datapoints)
        self.sbk_Columns.AddPage(self.pnl_Datapoints, u"Datapoints", True)
        self.dic_ListCtrls["Datapoints"] = self.lbc_Datapoints
        # Data fitting Model
        self.pnl_Model = wx.Panel(self.sbk_Columns)
        self.szr_Model = wx.BoxSizer(wx.VERTICAL)
        self.lbc_Model = rdnd.MyDragList(self.pnl_Model,
                                           size = wx.Size(200,400),
                                           style=wx.LC_LIST,
                                           name = u"Model")
        self.lbc_Model.table_name = "Model"
        self.szr_Model.Add(self.lbc_Model, 0, wx.ALL, 0)
        self.pnl_Model.SetSizer(self.szr_Model)
        self.pnl_Model.Layout()
        self.szr_Model.Fit(self.pnl_Model)
        self.sbk_Columns.AddPage(self.pnl_Model, u"Fitting Model", True)
        self.dic_ListCtrls["Model"] = self.lbc_Model

        # MORE STUFF HERE
        self.szr_SimpleBook.Add(self.sbk_Columns, 0, wx.ALL, 0)
        self.sbk_Columns.SetSelection(0)
        self.szr_PossibleColumns.Add(self.szr_SimpleBook, 0, wx.ALL, 0)
        self.sizer.Add(self.szr_PossibleColumns, 0, wx.ALL, 5)

        # Actual results table here
        self.szr_ResultsTable = wx.BoxSizer(wx.VERTICAL)
        self.lbl_ResultsTable = wx.StaticText(self,
                                              label = u"Final Results table")
        self.szr_ResultsTable.Add(self.lbl_ResultsTable, 0, wx.ALL, 5)

        # Results Table
        self.lbc_ResultsTable = rdnd.MyDropTarget(self, size = wx.Size(500,300),
                                                  style = wx.LC_REPORT,
                                                  name = u"ResultsTable",
                                                  instance = self)
        self.lbc_ResultsTable.InsertColumn(0,"Table Column")
        self.lbc_ResultsTable.SetColumnWidth(0, 150)
        self.lbc_ResultsTable.InsertColumn(1,"Source")
        self.lbc_ResultsTable.SetColumnWidth(1, 100)
        self.lbc_ResultsTable.InsertColumn(2,"Name in source")
        self.lbc_ResultsTable.SetColumnWidth(2, 250)
        self.szr_ResultsTable.Add(self.lbc_ResultsTable, 0, wx.ALL, 5)

        self.sizer.Add(self.szr_ResultsTable, 0, wx.ALL, 5)

        # Fill the lists (lbc_ResultsTable needs to exist)
        meta_list = self.make_list_meta()
        for meta in meta_list:
            self.lbc_Meta.InsertItem(self.lbc_Meta.GetItemCount(), meta)
        details_list = self.make_list_details()
        for detail in details_list:
            self.lbc_Details.InsertItem(self.lbc_Details.GetItemCount(), detail)
        reagents_list = self.make_list_reagents()
        for reagent in reagents_list:
            self.lbc_Reagents.InsertItem(self.lbc_Reagents.GetItemCount(), reagent)
        transfer_list = self.make_list_transfer()
        for transfer in transfer_list:
            self.lbc_Transfer.InsertItem(self.lbc_Transfer.GetItemCount(), transfer)
        quality_list = self.make_list_quality()
        for qual in quality_list:
            self.lbc_Quality.InsertItem(self.lbc_Quality.GetItemCount(), qual)
        datapoints_list = self.make_list_datapoints()
        for point in datapoints_list:
            self.lbc_Datapoints.InsertItem(self.lbc_Datapoints.GetItemCount(), point)
        model_list = self.make_list_model()
        for model in model_list:
            self.lbc_Model.InsertItem(self.lbc_Model.GetItemCount(), model)

        self.SetSizer(self.sizer)
        self.Layout()
        self.sizer.Fit(self)

        self.Centre(wx.BOTH)

        ####  # #   # ####  # #   #  ####
        #   # # ##  # #   # # ##  # #
        ####  # ##### #   # # ##### #  ##
        #   # # #  ## #   # # #  ## #   #
        ####  # #   # ####  # #   #  ####

        # Bindings #####################################################################

        self.lbc_ResultsTable.Bind(rdnd.EVT_RESULTS_UPDATE, self.update_results_table)
        self.lbc_ResultsTable.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, self.on_right_click_lstctrl)

        # Results table

    def change_tab(self, fnord):
        """
        Dummy function required when using btn.MiniTabButtons.
        Would normally perform chekcs to see whether changing
        tabs would be allowed.
        """
        return True

    def update_results_table(self, event = None):
        """
        Updates the results table rule set
        Note: The event gets posted twice when the editor is closed. Not sure why.
        """
        # re-set:
        self.rule_set = {}
        # re-write:
        for row in range(self.lbc_ResultsTable.GetItemCount()):
            col = self.lbc_ResultsTable.GetItemText(row, 0)
            if not col == "":
                self.rule_set[col] = {"Source":self.lbc_ResultsTable.GetItemText(row, 1),
                                      "SourceName":self.lbc_ResultsTable.GetItemText(row, 2)}
        # Print for sanity check
        self.assay["ResultsTable"] = self.rule_set
        print("Rule Set")
        print(js.dumps(self.rule_set, sort_keys= False, indent = 2))
        print("Complete Assay Definition JSON")
        print(js.dumps(self.assay, sort_keys= False, indent = 2))

    def already_in_table(self, source):
        """
        Helper function to get what's already in the table.

        Arguments:
            source -> string. Which source we're collecting
        
        Returns list
        """

        in_table = []
        table = self.lbc_ResultsTable
        for row in range(table.GetItemCount()):
            if table.GetItemText(row, 1) == source:
                in_table.append(table.GetItemText(row, 2))
        return in_table
    
    def make_list_details(self):
        """
        Produces a list with all the assay details that will be
        available for the results table. This list is dynamically
        generated from the assay definition.
        """
        # Get details already in table:
        in_table = self.already_in_table("Details")
    
        # get list of all details:
        details = [key for key in self.assay["DefaultDetails"].keys()]

        # re-set
        self.deets = []
        for deet in details:
            if not deet in in_table:
                self.deets.append(deet)

        return self.deets

    def make_list_reagents(self):
        """
        Produces a list with all the reagents that will be
        available for the results table. This list is dynamically
        generated from the assay definition.
        """
        print("Reagents")
        # Get details already in table:
        in_table = self.already_in_table("Reagents")
        print(in_table)
    
        # get list of all details:
        reagents = [key for key in self.assay["Reagents"].keys()]
        print(reagents)

        # re-set
        self.reagents = []
        for reagent in reagents:
            if not reagent in in_table:
                self.reagents.append(reagent)

        return self.reagents

    def make_list_meta(self):
        """
        Produces a list with all the assay meta data/details that will be
        available for the results table. This list is static.
        """

        # Get meta data already in table:
        in_table = self.already_in_table("Meta")

        meta = ["Shorthand","FullName","DisplayTitle",
                "MainCategory","SecondaryCategory"]
        
        # re-set:
        self.meta = []
        for deet in meta:
            if not deet in in_table:
                self.meta.append(deet)

        return self.meta
    
    def make_list_quality(self):
        """
        Produces a list with parameters from plate quality
        """
        quality = ["ControlMean","BufferMean","SolventMean","ZPrime",
                   "ZPrimeRobust"]
        self.quality = quality
        return self.quality
    
    def make_list_datapoints(self):
        """
        Produces a list for the datapoints (concentration, mean value
        and error if desired)
        """
        max_points = self.assay["DataProcessing"]["MaxDatapoints"]
        if max_points == 0:
            return None

        self.datapoints = [f"Concentration {p+1}" for p in range(0, max_points)]
        self.datapoints += [f"MeanValue {p+1}" for p in range(0, max_points)]
        if self.assay["DataProcessing"]["ReplicateErrorCalculation"] == True:
            self.datapoints += [f"Error {p+1}" for p in range(0, max_points)]
        
        return self.datapoints

    def make_list_model(self):
        """
        Produces a list with all the data fitting parameters
        that will be available for the results table. This
        list is dynamically generated from the assay definition.
        """

        # Get parameters already in table:
        in_table = self.already_in_table("Model")

        # re-set
        self.model = []

        pars = [par for par in self.assay["DataProcessing"]["DataFitModel"]["Parameters"]]
        model = []
        for par in pars:
            model.append(par)
            model.append(f"{par}(95%CI)")
        
        # make the new list
        for par in model:
            if not par in in_table:
                self.model.append(par)
        self.model.append("Rsquare")

        return self.model
    
    def make_list_transfer(self):
        """
        Produces a list with all the assay details that will be
        available for the results table. This list is dynamically
        generated from the assay definition.
        """

        # Get details already in table:
        in_table = self.already_in_table("Transfer")

        # re-set
        self.transfer = []
        # re-populate
        columns = self.assay["TransferRules"]["TransferFileColumns"]
        transfer = []
        for col in columns.keys():
            if not pd.isna(columns[col]["Mapped"]):
                transfer.append(columns[col]["Name"])
        
        self.transfer = []
        for col in transfer:
            if not col in in_table:
                self.transfer.append(col)

        return self.transfer

    def update_columns(self):

        #for key in self.assay["DefaultDetails"].keys():
        #    self.deets.append(key)
        #    print(key)

        # Meta adata
        old_meta = copy.deepcopy(self.meta)
        self.meta = self.make_list_meta()
        for om in old_meta:
            if not om in self.meta:
                pass
        self.lbc_Meta.DeleteAllItems()
        for meta in self.make_list_meta():
            self.lbc_Meta.InsertItem(self.lbc_Meta.GetItemCount(), meta)

        old_deets = copy.deepcopy(self.deets)
        self.deets = self.make_list_details()
        for od in old_deets:
            if not od in self.deets:
                pass
        self.lbc_Details.DeleteAllItems()
        for deet in self.make_list_details():
            self.lbc_Details.InsertItem(self.lbc_Details.GetItemCount(), deet)

        old_reagents = copy.deepcopy(self.reagents)
        self.reagents = self.make_list_details()
        for old in old_reagents:
            if not old in self.reagents:
                pass
        self.lbc_Reagents.DeleteAllItems()
        for reagent in self.make_list_reagents():
            self.lbc_Reagents.InsertItem(self.lbc_Reagents.GetItemCount(), reagent)

        old_transfer = copy.deepcopy(self.transfer)
        self.transfer = self.make_list_transfer()
        for ot in old_transfer:
            if not ot in self.transfer:
                pass
        self.lbc_Transfer.DeleteAllItems()
        for transfer in self.make_list_transfer():
            self.lbc_Transfer.InsertItem(self.lbc_Transfer.GetItemCount(), transfer)

        old_pars = copy.deepcopy(self.model)
        self.model = self.make_list_model()
        for op in old_pars:
            if not op in self.model:
                pass
        self.lbc_Model.DeleteAllItems()
        for par in self.make_list_model():
            self.lbc_Model.InsertItem(self.lbc_Model.GetItemCount(), par)


    def add_column(self):
        """
        Adds column to rule set.

        Source will be the source dictionary used later, e.g. assay meta data
        (e.g. assay name), assay details (e.g. protein name, solvent, buffer...),
        fit parameters (if applicable), sample info (e.g. sample ID), etc.

        """

        col_name = "Column"
        col_source = "Meta"
        col_source_name = "SourceName"

        self.rule_set[col_name] = {"Source":col_source,
                                   "SourceName":col_source_name}


    ##### #   # ##### #   # #####    #   #  ###  #   # ####  #     ##### ####   ####
    #     #   # #     ##  #   #      #   # #   # ##  # #   # #     #     #   # #
    ###   #   # ###   #####   #      ##### ##### ##### #   # #     ###   ####   ###
    #      # #  #     #  ##   #      #   # #   # #  ## #   # #     #     #   #     #
    #####   #   ##### #   #   #      #   # #   # #   # ####  ##### ##### #   # ####

    # Event handlers for simple book pages #########################################
        
    def on_right_click_lstctrl(self, event):

        self.PopupMenu(ResultsTableContextMenu(self, event))
        

def CreateBlankRuleSet():
    """
    Creates nested dictionary for columns to define results table.
    Just creates blank dictionary for now. This is only included for consistency
    with the other tabs in the editor.
    """
    return {}

class ResultsTableContextMenu(wx.Menu):
    def __init__(self, parent, rightclick):
        super(ResultsTableContextMenu, self).__init__()
        """
        Context menu to cut, copy, paste, clear and fill down from capillaries grid.
        """
        real_path = os.path.realpath(__file__)
        dir_path = os.path.dirname(real_path)
        str_MenuIconsPath = dir_path + r"\menuicons"

        self.listctrl = rightclick.GetEventObject()
        self.parent = parent
        row = rightclick.GetIndex()
        

        self.mi_Delete = wx.MenuItem(self, wx.ID_ANY, u"Delete", wx.EmptyString, wx.ITEM_NORMAL)
        #self.mi_Delete.SetBitmap(wx.Bitmap(str_MenuIconsPath + u"\Clear.ico"))
        self.Append(self.mi_Delete)
        self.Bind(wx.EVT_MENU, lambda event: self.Delete(event, row), self.mi_Delete)

        self.mi_Paste = wx.MenuItem(self, wx.ID_ANY, u"Paste", wx.EmptyString, wx.ITEM_NORMAL)
        #self.mi_Paste.SetBitmap(wx.Bitmap(str_MenuIconsPath + u"\Paste.ico"))
        self.Append(self.mi_Paste)
        self.Bind(wx.EVT_MENU, lambda event: self.Paste(event, row), self.mi_Paste)

        self.mi_PasteExtend = wx.MenuItem(self, wx.ID_ANY, u"Paste (extend)", wx.EmptyString, wx.ITEM_NORMAL)
        #self.mi_PasteExtend.SetBitmap(wx.Bitmap(str_MenuIconsPath + u"\PasteExtend.ico"))
        self.Append(self.mi_PasteExtend)
        self.Bind(wx.EVT_MENU, lambda event: self.PasteExtend(event, row), self.mi_PasteExtend)

        self.mi_Clear = wx.MenuItem(self, wx.ID_ANY, u"CLear 'Table Column", wx.EmptyString, wx.ITEM_NORMAL)
        #self.mi_Clear.SetBitmap(wx.Bitmap(str_MenuIconsPath + u"\Clear.ico"))
        self.Append(self.mi_Clear)
        self.Bind(wx.EVT_MENU, lambda event: self.Clear(event, row), self.mi_Clear)

        self.mi_MoveUp = wx.MenuItem(self, wx.ID_ANY, u"Move Up", wx.EmptyString, wx.ITEM_NORMAL)
        #self.mi_MoveUp.SetBitmap(wx.Bitmap(str_MenuIconsPath + u"\MoveUp.ico"))
        self.Append(self.mi_MoveUp)
        self.Bind(wx.EVT_MENU, lambda event: self.MoveUp(event,  row), self.mi_MoveUp)

        self.mi_MoveDown = wx.MenuItem(self, wx.ID_ANY, u"Move Down", wx.EmptyString, wx.ITEM_NORMAL)
        #self.mi_MoveDown.SetBitmap(wx.Bitmap(str_MenuIconsPath + u"\MoveDown.ico"))
        self.Append(self.mi_MoveDown)
        self.Bind(wx.EVT_MENU, lambda event: self.MoveDown(event,  row), self.mi_MoveDown)

    def Delete(self, event, row):
        """
        Deletes clicked on parameter: Writes all parameters except clicked
        on into new list, clears listctrl, inserts new lists, reassings
        colours and re-linters function.
        """
        # CBA right now to look up how to do it "properly", it's nearly 23h.
        lst_Reset = []
        lst_Return = []
        for line in range(self.listctrl.GetItemCount()):
            if not line == row:
                lst_Reset.append([self.listctrl.GetItemText(line,0),
                                  self.listctrl.GetItemText(line,1),
                                  self.listctrl.GetItemText(line,2)])
            else:
                lst_Return.append([self.listctrl.GetItemText(line,0),
                                   self.listctrl.GetItemText(line,1),
                                   self.listctrl.GetItemText(line,2)])
        # Return deleted items to original lists:
        if len(lst_Return) > 0:
            for col in range(len(lst_Return)):
                lbx = self.parent.dic_ListCtrls[lst_Return[col][1]]
                lbx.InsertItem(lbx.GetItemCount(),lst_Return[col][2])
        # Repopulate listctrl
        self.listctrl.DeleteAllItems()
        if len(lst_Reset) > 0:
            for col in range(len(lst_Reset)):
                self.listctrl.InsertItem(self.listctrl.GetItemCount(),lst_Reset[col][0])
                self.listctrl.SetItem(self.listctrl.GetItemCount()-1,1,lst_Reset[col][1])
                self.listctrl.SetItem(self.listctrl.GetItemCount()-1,2,lst_Reset[col][2])
        self.parent.update_results_table()

    def MoveUp(self, event, row):
        """
        Event handler.
        Moves the clicked-on row up
        """

        table = self.GetTable()
        new_table = []
        for lst in table:
            top = lst[0:row-1]
            down = lst[row-1]
            up = lst[row]
            bottom = lst[row+1:len(lst)]
            new_table.append([*top, up, down, *bottom])

        self.listctrl.DeleteAllItems()
        for row in range(len(new_table[0])):
            self.listctrl.InsertItem(row, new_table[0][row])
            self.listctrl.SetItem(row, 1, new_table[1][row])
            self.listctrl.SetItem(row, 2, new_table[2][row])
        self.parent.update_results_table()

    def MoveDown(self, event, row):
        """
        Event handler.
        Moves the clicked-on row down
        """
        table = self.GetTable()
        new_table = []
        for lst in table:
            top = lst[0:row]
            down = lst[row]
            up = lst[row+1]
            bottom = lst[row+2:len(lst)]
            new_table.append([*top, up, down, *bottom])

        self.listctrl.DeleteAllItems()
        for row in range(len(new_table[0])):
            self.listctrl.InsertItem(row, new_table[0][row])
            self.listctrl.SetItem(row, 1, new_table[1][row])
            self.listctrl.SetItem(row, 2, new_table[2][row])
        self.parent.update_results_table()

    def GetTable(self):
        """
        Get contents of results table as three columns
        """
        col = []
        src = []
        src_name = [] 

        for row in range(self.listctrl.GetItemCount()):
            col.append(self.listctrl.GetItemText(row, 0))
            src.append(self.listctrl.GetItemText(row, 1))
            src_name.append(self.listctrl.GetItemText(row, 2))

        return col, src, src_name

    def Paste(self, event, row):
        """
        Event handler.
        Writes contents of clipboard into first column, if there are
        rows in the table.
        """
        dfr_Paste = pd.read_clipboard(sep="\\t", header=None)
        
        all = self.listctrl.GetItemCount()
        row_range = range(row, all)

        pst = 0
        for col in row_range:
            self.listctrl.SetItem(col, 0, dfr_Paste.iloc[pst,0])
            pst += 1
            if pst > dfr_Paste.shape[0]:
                break
        self.parent.update_results_table()

    def PasteExtend(self, event, row):
        """
        Event handler.
        Writes contents of clipboard into first column, if there are
        rows in the table. If the end of the table is reached before
        the clipboard data has been written, the table will be extended.
        """
        dfr_Paste = pd.read_clipboard(sep="\\t", header=None)
        
        all = self.listctrl.GetItemCount()
        row_range = range(row, all)
        if dfr_Paste.shape[0] > len([*row_range]):
            add = dfr_Paste.shape[0] - len([*row_range])# - row
            while add > 0:
                self.listctrl.InsertItem(self.listctrl.GetItemCount(),"")
                add -= 1
        
        row_range = range(row, self.listctrl.GetItemCount())
        pst = 0
        for col in row_range:
            self.listctrl.SetItem(col, 0, dfr_Paste.iloc[pst,0])
            pst += 1
            if pst > dfr_Paste.shape[0]:
                break
        self.parent.update_results_table()

    def Clear(self, event, row):
        """
        Event handler. Clears the "Table Column" field of selected/clicked on
        rows of the table
        """

        self.listctrl.SetItem(row, 0, "")
        self.parent.update_results_table()