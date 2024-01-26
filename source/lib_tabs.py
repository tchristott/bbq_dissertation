"""
Contains standardised pages for assay workflows.

Classes:

    ButtonBar
    AssayStepsNotebook
    CustomFilePicker
    FileSelection
    Review
    ELNPlots
    ExportTable
    PlateMapForDatabase (CMD specific)

Functions:

    on_key_press_grid
    process_data
    SingleSelection
    get_grid_selection
    get_date

"""
import os
import copy

# My own libraries
import lib_colourscheme as cs
import lib_transferdragndrop as tdnd
import lib_messageboxes as msg
import lib_datafunctions as df
import lib_resultreadouts as ro
import lib_customplots as cp
import lib_custombuttons as btn
import lib_platefunctions as pf
import lib_platelayoutmenus as plm

import wx
import pandas as pd
import math
import threading
import numpy as np
import openpyxl
from openpyxl import load_workbook
from datetime import datetime
from time import perf_counter, sleep
import functools as ft


####################################################################################
##                                                                                ##
##    #####   ##  ##  ######  ######   ####   ##  ##    #####    ####   #####     ##
##    ##  ##  ##  ##    ##      ##    ##  ##  ### ##    ##  ##  ##  ##  ##  ##    ##
##    #####   ##  ##    ##      ##    ##  ##  ######    #####   ######  #####     ##
##    ##  ##  ##  ##    ##      ##    ##  ##  ## ###    ##  ##  ##  ##  ##  ##    ##
##    #####    ####     ##      ##     ####   ##  ##    #####   ##  ##  ##  ##    ##
##                                                                                ##
####################################################################################

class ButtonBar(wx.Panel):

    """
    Button bar: Save, Save As, Cancel, Analyse Data
    """

    def __init__(self, tabname, id = wx.ID_ANY, pos = wx.DefaultPosition,
                 size = wx.DefaultSize, style = wx.TAB_TRAVERSAL, name = wx.EmptyString):
        """
        Initialises class attributes.
        
        Arguments:
            tabname -> gets assigned to self.tabname. Reference to the
                       pnl_Project instance above this object (contains
                       any functions that might need to be called, objects
                       controlled, etc).
        """
        wx.Panel.__init__ (self, parent = tabname, id = id,
                           pos = pos, size = size, style = style, name = "ButtonBar")

        self.tabname = tabname
        self.SetBackgroundColour(cs.BgMediumDark)
        self.SetForegroundColour(cs.White)
        self.szr_HeaderProject = wx.BoxSizer(wx.VERTICAL)
        # Banner with title
        self.szr_Banner = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_Banner.Add((20, 0), 0, wx.EXPAND, 0)
        self.szr_BannerLabel = wx.BoxSizer(wx.VERTICAL)
        self.lbl_Filename = wx.StaticText(self, label = u"[Filename goes here]")
        self.szr_BannerLabel.Add(self.lbl_Filename, 0, wx.ALL, 0)
        self.szr_Banner.Add(self.szr_BannerLabel, 1, wx.EXPAND, 0)
        self.szr_HeaderProject.Add(self.szr_Banner, 1, wx.EXPAND, 0)
        self.szr_HeaderProject.Add((0,5),0,wx.ALL,0)
        # Menu bar #####################################################################
        # Save + save as
        self.szr_ProjectMenuBar = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_ProjectMenuBar.Add((20, 30), 0, wx.EXPAND, 0)
        self.btn_HeaderSave = btn.CustomBitmapButton(self,
                                                     name = u"Save",
                                                     index = 1,
                                                     size = (100,30),
                                                     tooltip="Save the current project")
        self.btn_HeaderSave.Enable(False)
        self.szr_ProjectMenuBar.Add(self.btn_HeaderSave, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 0)
        self.szr_ProjectMenuBar.Add((3,0), 0, wx.ALL, 0)
        self.btn_HeaderSaveAs = btn.CustomBitmapButton(self,
                                                       name = u"SaveAs",
                                                       index = 1,
                                                       size = (100,30))
        self.btn_HeaderSaveAs.Enable(False)
        self.szr_ProjectMenuBar.Add(self.btn_HeaderSaveAs, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 0)
        self.szr_ProjectMenuBar.Add((3,0), 0, wx.ALL, 0)
        # Cancel
        self.sep_LineSeparator_01 = wx.StaticLine(self, wx.ID_ANY, wx.DefaultPosition,
                                                  wx.Size(-1,30), wx.LI_VERTICAL)
        self.szr_ProjectMenuBar.Add(self.sep_LineSeparator_01, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 0)
        self.szr_ProjectMenuBar.Add((3,0), 0, wx.ALL, 0)
        self.btn_HeaderCancel = btn.CustomBitmapButton(self,
                                                       name = "Cancel",
                                                       index = 1,
                                                       size = (100,30),
                                                       tooltip="Cancel the current project")
        self.btn_HeaderCancel.Enable(False)
        self.szr_ProjectMenuBar.Add(self.btn_HeaderCancel, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 0)
        self.szr_ProjectMenuBar.Add((3,0), 0, wx.ALL, 0)
        # Run analysis
        self.sep_LineSeparator_02 = wx.StaticLine(self, size = wx.Size(-1,30),
                                                  style = wx.LI_VERTICAL)
        self.szr_ProjectMenuBar.Add(self.sep_LineSeparator_02, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 0)
        self.szr_ProjectMenuBar.Add((3,0), 0, wx.ALL, 0)
        self.btn_HeaderAnalyse = btn.CustomBitmapButton(self,
                                                        name = u"AnalyseData",
                                                        index = 1,
                                                        size = (150,30),
                                                        tooltip = u"Analyse the data in the current project")
        self.btn_HeaderAnalyse.Enable(False)
        self.szr_ProjectMenuBar.Add(self.btn_HeaderAnalyse, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 0)
        self.szr_HeaderProject.Add(self.szr_ProjectMenuBar, 0, wx.EXPAND, 0)
        self.szr_HeaderProject.Add((0,15),0,wx.ALL,0)
        self.SetSizer(self.szr_HeaderProject)
        self.Layout()
        self.szr_HeaderProject.Fit(self)
        
        # Connect event handlers
        self.btn_HeaderSave.Bind(wx.EVT_BUTTON, self.tabname.save_file)
        self.btn_HeaderSaveAs.Bind(wx.EVT_BUTTON, self.tabname.save_file_as)
        self.btn_HeaderCancel.Bind(wx.EVT_BUTTON, self.tabname.parent.Cancel)
        self.btn_HeaderAnalyse.Bind(wx.EVT_BUTTON, self.tabname.parent.AnalyseData)

    def EnableButtons(self, bol_Enable):
        """
        Enables/Disables the buttons
        """
        self.btn_HeaderSave.Enable(bol_Enable)
        self.btn_HeaderSaveAs.Enable(bol_Enable)
        self.btn_HeaderCancel.Enable(bol_Enable)
        self.btn_HeaderAnalyse.Enable(bol_Enable)


##########################################################################
##                                                                      ##
##    ##  ##   ####   ######  ######  #####    ## #    ####   ##  ##    ##
##    ### ##  ##  ##    ##    ##      ##  ##  ##  ##  ##  ##  ##  ##    ##
##    ######  ##  ##    ##    #####   #####   ##  ##  ##  ##  #####     ##
##    ##  ##  ##  ##    ##    ##      ##  ##  ##  ##  ##  ##  ##  ##    ##
##    ##  ##   ####     ##    ######  #####    ####    ####   ##  ##    ##
##                                                                      ##
##########################################################################
    
class AssayStepsNotebook(wx.Panel):
    """
    Creates a fancier looking notebook with bitmap buttons for tab buttons
    and a simplebook w/o native tab buttons.
    """
    def __init__(self, parent, size = wx.DefaultSize):
        """
        Initialises class attributes.
        
        Arguments:
            parent -> parent object for wxPython GUI building.
            size -> wx.Size type.
        """
        wx.Panel.__init__ (self, parent = parent, id = wx.ID_ANY,
                           pos = wx.DefaultPosition, size = size,
                           style = wx.TAB_TRAVERSAL, name = wx.EmptyString)

        self.parent = parent # Required. This will be used by the btn.AnalysisTabButton 
                             # instances to call change_tab() from the project tab
        self.SetBackgroundColour(cs.BgMediumDark)
        self.SetForegroundColour(cs.White)

        self.lst_ButtonNames = []
        self.lst_ButtonIndices = []
        self.lst_Enabled = []
        self.dic_Buttons = {}

        self.szr_Notebook = wx.BoxSizer(wx.VERTICAL)

        self.pnl_TabButtons = wx.Panel(self,
                                       size =  wx.Size(-1,30),
                                       style = wx.TAB_TRAVERSAL)
        self.pnl_TabButtons.SetBackgroundColour(cs.BgMediumDark)
        self.pnl_TabButtons.SetForegroundColour(cs.White)
        self.szr_TabButtons = wx.BoxSizer(wx.HORIZONTAL)
        self.pnl_TabButtons.SetSizer(self.szr_TabButtons)
        self.szr_TabButtons.Fit(self)
        self.szr_Notebook.Add(self.pnl_TabButtons, 0, wx.ALL, 0)

        self.sbk_Notebook = wx.Simplebook(self, size = wx.Size(-1,-1))
        self.szr_Notebook.Add(self.sbk_Notebook, 1, wx.EXPAND|wx.ALL, 0)

        self.SetSizer(self.szr_Notebook)
        self.Layout()
        self.szr_Notebook.Fit(self)

    def EnableAll(self, bol_Enabled):
        """
        Enables/Disables all buttons on this button bar based on
        argument.

        Arguments:
            bol_Enabled -> Values is handed to each button's "IsEnabled"
                            function.
        """
        for key in self.dic_Buttons.keys():
            self.dic_Buttons[key].IsEnabled(bol_Enabled)

    def EnablePlateMap(self, bol_PlateMap):
        """
        Enables/Disables "Plate Map" button, if present

        Arguments:
            bol_Enabled -> Values is handed to each button's "IsEnabled"
                            function.

        """
        if "Plate Map" in self.dic_Buttons.keys():
            self.dic_Buttons["Plate Map"].IsEnabled(bol_PlateMap)
    
    def AddPage(self, pnl_Page, str_Name, bol_Enabled = True, bol_Selected = False):
        """
        Adds a new page to the notebook and corresponding button.
        
        Arguments:
            pnl_Page -> the wx.Panel to add as a new page
            str_Name -> string, name of the panel
            bol_Enabled -> boolean, sets the enabled attribute of
                            the page
            bol_Selected -> boolean, selects (or not) the page
        """
        # Add page to notebook:
        self.sbk_Notebook.AddPage(pnl_Page, str_Name, bol_Selected)
        # Add button:
        int_Index = len(self.lst_ButtonIndices)
        self.lst_ButtonNames.append(str_Name)
        self.lst_ButtonIndices.append(int_Index)
        self.lst_Enabled.append(bol_Enabled)
        self.dic_Buttons[str_Name] = btn.AnalysisTabButton(self.pnl_TabButtons, self.parent, str_Name, int_Index)
        self.dic_Buttons[str_Name].IsEnabled(self.lst_Enabled[int_Index])
        self.dic_Buttons[str_Name].Group = self.dic_Buttons
        self.dic_Buttons[str_Name].Notebook = self.sbk_Notebook
        self.szr_TabButtons.Add(self.dic_Buttons[str_Name], 0, wx.ALL, 0)
        self.pnl_TabButtons.Layout()
        self.pnl_TabButtons.Refresh()
        self.szr_TabButtons.Fit(self.pnl_TabButtons)
        self.szr_Notebook.Fit(self)
        self.szr_Notebook.Layout()
        self.Layout()
        self.Refresh()

    def SetSelection(self, int_Index):
        """
        Selects page at specified index and sets corresponding button.s
        current state to True

        Arguments:
            int_Index -> integer
        """
        self.sbk_Notebook.SetSelection(int_Index)
        self.dic_Buttons[self.lst_ButtonNames[int_Index]].IsCurrent(True)
    
    def GetSelection(self):
        """
        Returns index of currently selected page as integer.
        """
        return self.sbk_Notebook.GetSelection()

    def GetPageCount(self):
        """
        Returns page cound ot notebook as integer.
        """
        return self.sbk_Notebook.GetPageCount()

########################################################################################################
##                                                                                                    ##
##     ####    #####   #####   ####   ##  ##    #####   ######  ######   ####   ##  ##       #####    ##
##    ##  ##  ##      ##      ##  ##  ##  ##    ##  ##  ##        ##    ##  ##  ##  ##      ##        ##
##    ######   ####    ####   ######   ####     ##  ##  ####      ##    ######  ##  ##       ####     ##
##    ##  ##      ##      ##  ##  ##    ##      ##  ##  ##        ##    ##  ##  ##  ##          ##    ##
##    ##  ##  #####   #####   ##  ##    ##      #####   ######    ##    ##  ##  ##  ######  #####     ##
##                                                                                                    ##
########################################################################################################
    
class AssayDetails_Flex(wx.Panel):
    """
    Flexible, procedurally populated tab for assay details, class derived from wx.Panel
    """

    def __init__(self, notebook, workflow, columns):
        """
        Initialises class attributes.
        
        Arguments:
            notebook -> parent object for wxPython GUI building.In this
                        case, the notebook that this panel will reside in.
            workflow -> gets assigned to self.workflow. Reference to the
                       pnl_Project instance above this object (contains
                       any functions that might need to be called, objects
                       controlled, etc).
            columns -> dictionary with details to show on page, grouped in
                       columns
        """
        wx.Panel.__init__ (self, parent = notebook, id = wx.ID_ANY,
                           pos = wx.DefaultPosition, size = wx.DefaultSize,
                           style = wx.TAB_TRAVERSAL, name = wx.EmptyString)

        # Dictionary with all the available widgets for dynamic creation.
        widgets = {"ListBox":ListBox,
                   "Property":Property,
                   "Date Picker":DatePicker,
                   "Multi Line Text Box":MultiLineTextBox,
                   "Plate Layout":PlateLayout,
                   "RadioOptions":RadioOptions}
        
        self.get_detail = {} # holds reference to the object from which to retrieve a detail from

        self.workflow = workflow

        self.SetBackgroundColour(cs.BgUltraLight)
        self.clr_Panels = cs.BgLight
        self.clr_TextBoxes = cs.BgUltraLight

        self.szr_Surround = wx.BoxSizer(wx.VERTICAL)
        self.szr_Columns = wx.BoxSizer(wx.HORIZONTAL)


        self.col_sizers = {}
        self.dic_Details = {}
        self.dic_Panels = {}
        # Make columns of panels
        for col in columns.keys():
            self.col_sizers[col] = wx.BoxSizer(wx.VERTICAL)
            panels = columns[col]
            for pnl in panels.keys():
                # All widgets have same constructor
                self.dic_Panels[pnl] = widgets[panels[pnl]["Type"]](parent = self,
                                                                    label = pnl,
                                                                    widgets = panels[pnl],
                                                                    workflow = workflow,
                                                                    optional = panels[pnl]["Optional"])
                self.col_sizers[col].Add(self.dic_Panels[pnl],
                                         proportion = 0,
                                         flag = wx.ALL|wx.EXPAND,
                                         border = 5)
            self.szr_Columns.Add(self.col_sizers[col],
                                 proportion = 0,
                                 flag = wx.ALL,
                                 border = 0)
        # Populate with default details.
        for key in workflow.set_details.keys():
            if key in workflow.default_details.keys():
                    workflow.set_details[key](workflow.default_details[key])
        # Finalise
        self.szr_Surround.Add(self.szr_Columns, 0, wx.EXPAND, 20)
        self.SetSizer(self.szr_Surround)
        self.Layout()
        self.szr_Surround.Fit(self)

def get_text_width(label):

    font = wx.Font(10, family = wx.FONTFAMILY_DEFAULT, 
                   style = wx.FONTSTYLE_NORMAL,
                   weight = wx.FONTWEIGHT_BOLD,
                   underline = False,
                   faceName = wx.EmptyString)
    dc = wx.ScreenDC()
    dc.SetFont(font)
    wide, tall = dc.GetTextExtent(label)
    if len(label) > 10:
        wide = wide -10
    return wide


class ListBox(wx.Panel):
    """
    Based on wx.Panel.
    Holds list box with title (static text above)
    """

    def __init__(self, parent, label, widgets, optional, workflow):
        """
        Initialises the ListBox

        Arguments:
            parent -> wx object that this object belongs to
            label -> str. Label for panel
            widgets -> dictionary with instructions to build
                       this widget:
            workflow -> reference to workflow (i.e. the object
                        that represents the workflow tab)
        """
        wx.Panel.__init__ (self,
                           parent = parent,
                           id = wx.ID_ANY,
                           pos = wx.DefaultPosition,
                           size = wx.Size(220,-1),
                           style = wx.TAB_TRAVERSAL,
                           name = wx.EmptyString)
        
        self.workflow = workflow
    
        self.SetBackgroundColour(parent.clr_Panels)
        self.SetMaxSize(wx.Size(220,-1))

        self.optional = optional
        self.szr = wx.BoxSizer(wx.VERTICAL)
        if self.optional == True:
            self.lbl = wx.CheckBox(self,
                                   label = label)
            self.lbl.Bind(wx.EVT_CHECKBOX, self.toggle)
            # Shoudle widget be eNaBLed?
            self.nbl = False
        else: 
            self.lbl = wx.StaticText(self,
                                     label = label)
            self.lbl.Wrap(-1)
            # Shoudle widget be eNaBLed?
            self.nbl = True
        self.szr.Add(self.lbl, 0, wx.ALL, 5)
        self.lbx = wx.ListBox(self,
                              size = wx.Size(210,-1),
                              choices = list(workflow.default_details[widgets["Options"]].keys()))
        self.lbx.SetSelection(0)
        self.lbx.Enable(self.nbl)
        dtl = widgets["Detail"]
        workflow.get_details[dtl] = self.get_value
        workflow.set_details[dtl] = self.set_value
        workflow.wdg_details[dtl] = self
        self.dtl = copy.copy(widgets["Detail"])
        self.lbx.Bind(wx.EVT_LISTBOX, self.update_detail)
        self.lbx.SetBackgroundColour(parent.clr_TextBoxes)
        self.szr.Add(self.lbx, 1, wx.ALL, 5)
        # Finalise
        self.SetSizer(self.szr)
        self.Layout()
        self.szr.Fit(self)

    def toggle(self, event):
        """
        Event handler to toggle the enabled status of the widget
        """
        self.nbl = event.GetEventObject().GetValue()
        self.lbx.Enable(self.nbl)
        self.Refresh()

    def get_value(self):
        """
        Function to return selected value.
        """
        if self.nbl == True:
            sel = self.lbx.GetSelection()
            return self.lbx.GetString(sel)
        else:
            return np.nan
    
    def set_value(self, values):
        """
        Function to replace values in listbox
        Arguments:
            values -> some type of collection, most likely dictionary
        """
        # This should unpack it and repack it. If it's a dictionary, this
        # will be just the keys.
        return None
        # This is superfluous. Keep it in case changes are made in the future.
        values = [str(val) for val in values]
        self.lbx.Clear()
        self.lbx.AppendItems(values)
        self.lbx.SetSelection(0)
        self.Refresh()

    def update_detail(self, event):
        """
        Event handler.
        Updates the conntected detail in the workflow when clicking on a list item
        """
        self.workflow.details[self.dtl] = self.get_value()

    def get_index(self, value):
        """
        Get index of  given value, if in lbx:
        """
        for row in range(self.lbx.GetCount()):
            if self.lbx.GetString(row) == value:
                return row
        return -1
            
    def set_selection(self, idx):
        """
        Select item at index idx.
        Return False if idx is > GetCount
        """
        if idx + 1 > self.lbx.GetCount():
            return False
        else:
            self.lbx.SetSelection(idx)
            return True
        
    def get_choices(self):
        """
        Returns strings of all items in listbox
        """
        choices = []
        for row in range(self.lbx.GetCount()):
            choices.append(self.lbx.GetString(row))
        return choices


class Property(wx.Panel):
    """
    Panel with multiple text fields and optional units.
    """
    def __init__(self, parent, label, widgets, optional, workflow):
        """
        Initialises the Widget

        Arguments:
            parent -> wx object that this object belongs to
            label -> str. Label for panel
            widgets -> dictionary with instructions to build
                       this widget
            workflow -> reference to workflow (i.e. the object
                        that represents the workflow tab)
        """
        wx.Panel.__init__ (self,
                           parent = parent,
                           id = wx.ID_ANY,
                           pos = wx.DefaultPosition,
                           size = wx.DefaultSize,
                           style = wx.TAB_TRAVERSAL,
                           name = wx.EmptyString)
        
        self.SetBackgroundColour(parent.clr_Panels)
        #self.SetMinSize(wx.Size(220,-1))
        
        self.optional = optional
        self.szr = wx.BoxSizer(wx.VERTICAL)
        if self.optional == True:
            self.lbl = wx.CheckBox(self,
                                   label = label)
            self.lbl.Bind(wx.EVT_CHECKBOX, self.toggle)
            # Shoudle widget be eNaBLed?
            self.nbl = False
        else: 
            self.lbl = wx.StaticText(self,
                                     label = label)
            self.lbl.Wrap(-1)
            # Shoudle widget be eNaBLed?
            self.nbl = True
        self.szr.Add(self.lbl,
                     proportion = 0,
                     flag = wx.ALL,
                     border = 5)

        verify = {"float":self.verify_float,
                  "int":self.verify_int,
                  "str":self.verify_str}

        self.sizers = {}
        self.labels = {}
        self.inputs = {}
        self.units = {}
        for wdgt in widgets.keys():
            if not wdgt in ["Type", "Optional"]:
                dtl = widgets[wdgt]["Detail"]
                self.sizers[dtl] = wx.BoxSizer(wx.HORIZONTAL)
                self.labels[dtl] = wx.StaticText(self,
                                                  label = wdgt,
                                                  size = wx.Size(get_text_width(wdgt),-1))
                self.labels[dtl].Enable(self.nbl)
                self.sizers[dtl].Add(self.labels[dtl],
                                      proportion = 1,
                                      flag = wx.ALIGN_CENTER_VERTICAL|wx.ALL,
                                      border = 5)
                self.inputs[dtl] = wx.TextCtrl(self,
                                                value = u"",
                                                size = wx.Size(widgets[wdgt]["Size"],-1),
                                                style = 1)
                self.inputs[dtl].SetBackgroundColour(parent.clr_TextBoxes)
                self.inputs[dtl].Bind(wx.EVT_TEXT, verify[widgets[wdgt]["Allowed"]])
                self.inputs[dtl].Enable(self.nbl)
                # connect with workflow:
                workflow.get_details[dtl] = ft.partial(self.get_value, dtl)
                workflow.set_details[dtl] = ft.partial(self.set_value, dtl)
                workflow.wdg_details[dtl] = self.inputs[dtl]
                self.sizers[dtl].Add(self.inputs[dtl],
                                      proportion = 0,
                                      flag = wx.ALIGN_CENTER_VERTICAL|wx.ALL,
                                      border = 5)
                if widgets[wdgt]["Unit"]: # I love truthiness in python! If there is no unit, the value is False
                    self.units[dtl] = wx.StaticText(self,
                                                    label = widgets[wdgt]["Unit"])
                    self.units[dtl].Enable(self.nbl)
                    self.sizers[dtl].Add(self.units[dtl],
                                          proportion = 0,
                                          flag = wx.ALIGN_CENTER_VERTICAL|wx.ALL,
                                          border = 5)
                self.szr.Add(self.sizers[dtl],
                             proportion = 0,
                             flag = wx.ALL,
                             border = 0)
        
        self.SetSizer(self.szr)
        self.Layout()
        self.szr.Fit(self)

    def toggle(self, event):
        """
        Event handler to toggle the enabled status of the widget
        """
        self.nbl = event.GetEventObject().GetValue()
        for dtl in self.labels.keys():
            self.labels[dtl].Enable(self.nbl)
            self.inputs[dtl].Enable(self.nbl)
        # separate units out because not all fields might have units
        for dtl in self.units.keys():
            self.units[dtl].Enable(self.nbl)
        self.Refresh()

    def get_value(self, detail):
        """
        Function to retrieve value from a specific detail

        Arguments:
            detail => string. The detail to be retrieved.
        """
        if self.nbl == True:
            return self.inputs[detail].GetValue()
        else:
            return np.nan
    
    def set_value(self, detail, value):
        """
        Function to set the value of a specific detail.
        Uses .ChangeValue() to not trigger an event.

        Arguments:
            detail -> string. The detail that will have its
                      value changed
            value -> string. Value to set. If not string,
                     will be converted.
        """
        self.inputs[detail].ChangeValue(str(value))

    def verify_float(self, event):
        """
        Event handler.

        Checks whether text entered is alphanumeric
        """
        text = event.GetEventObject()
        value = text.GetValue()
        # Find insertion point
        insert = event.GetEventObject().GetInsertionPoint()
        # Check if string is emtpty
        if not value == "":
            # Get new character
            if insert == len(value):
                new = value[-1]
            else:
                new = value[insert-1:insert]
            # Check if alphanumeric
            if not new.isnumeric():
                if not new == ".":
                    # Reset text control
                    reset = value[:insert-1] + value[insert:]
                    text.ChangeValue(reset)
                    text.SetInsertionPoint(insert-1)

    def verify_int(self, event):
        """
        Event handler.

        Checks whether text entered is integer
        """
        text = event.GetEventObject()
        value = text.GetValue()
        # Find insertion point
        insert = event.GetEventObject().GetInsertionPoint()
        # Check if string is emtpty
        if not value == "":
            # Get new character
            if insert == len(value):
                new = value[-1]
            else:
                new = value[insert-1:insert]
            # Check if integer
            if not new.isnumeric():
                # Reset text control
                reset = value[:insert-1] + value[insert:]
                text.ChangeValue(reset)
                text.SetInsertionPoint(insert-1)
    
    def verify_str(self, event):
        pass


class DatePicker(wx.Panel):
    """
    Date picker panel
    """
    def __init__(self, parent, label, widgets, optional, workflow):
        """
        Initialises the DatePicker
        
        Arguments:
            parent -> wx object that this object belongs to
            label -> str. Label for panel
            widgets -> dictionary with instructions to build
                       this widget
            workflow -> reference to workflow (i.e. the object
                        that represents the workflow tab)
        """
        wx.Panel.__init__(self,
                          parent = parent,
                          id = wx.ID_ANY,
                          pos = wx.DefaultPosition,
                          size = wx.DefaultSize,
                          style = wx.TAB_TRAVERSAL,
                          name = wx.EmptyString)
        
        self.SetBackgroundColour(parent.clr_Panels)

        self.optional = optional
        self.szr = wx.BoxSizer(wx.VERTICAL)
        if self.optional == True:
            self.lbl = wx.CheckBox(self,
                                   label = label)
            self.lbl.Bind(wx.EVT_CHECKBOX, self.toggle)
            # Shoudle widget be eNaBLed?
            self.nbl = False
        else: 
            self.lbl = wx.StaticText(self,
                                     label = label)
            self.lbl.Wrap(-1)
            # Shoudle widget be eNaBLed?
            self.nbl = True
        self.szr.Add(self.lbl,
                     proportion = 0,
                     flag = wx.EXPAND|wx.ALL,
                     border = 5)
        self.szr_pck = wx.BoxSizer(wx.HORIZONTAL)
        self.how = wx.StaticText(self,
                                 label = u"Enter/select date:")
        self.szr_pck.Add(self.how,
                         proportion = 0,
                         flag = wx.ALIGN_CENTER_VERTICAL|wx.ALL,
                         border = 5)
        self.picker = wx.adv.DatePickerCtrl(self,
                                            style = wx.adv.DP_DEFAULT|wx.adv.DP_DROPDOWN)
        dtl = widgets["Detail"]
        workflow.get_details[dtl] = self.get_value
        workflow.set_details[dtl] = self.set_value
        workflow.wdg_details[dtl] = self
        self.picker.SetBackgroundColour(parent.clr_TextBoxes)
        self.szr_pck.Add(self.picker,
                         proportion = 0,
                         flag = wx.ALIGN_CENTER_VERTICAL|wx.ALL,
                         border = 5)
        self.szr.Add(self.szr_pck,
                     proportion = wx.EXPAND|wx.ALL,
                     flag = 0,
                     border = 0)
        self.SetSizer(self.szr)
        self.Layout()
        self.szr.Fit(self)

    def toggle(self, event):
        """
        Event handler to toggle the enabled status of the widget
        """
        self.nbl = event.GetEventObject().GetValue()
        self.picker.Enable(self.nbl)
        self.Refresh()

    def get_value(self):
        """
        Gets date from wxPython datepicker object and converts it
        into YYYY-MM-DD string.

        Returns:
            date as string.
        """
        if self.nbl == True:
            date = self.picker.GetValue()
            date = f"{date.GetYear()}-{date.GetMonth()+1}-{date.GetDay()}" # GetMonth is indexed from zero!!!!!
            return datetime.strptime(date,"%Y-%m-%d").strftime("%Y-%m-%d")
        else:
            return np.nan
    
    def set_value(self, value):
        """
        Converts date from string of format YYYY-MM-DD to wxDateTime
        object and sets the value of the date picker.

        Arguments:
            value -> string. Date in the format YYYY-MM-DD
        """
        if value: # is False per default!
            value = wx.DateTime(datetime.strptime(value, "%Y-%m-%d"))
            self.picker.SetValue(value)


class MultiLineTextBox(wx.Panel):
    """
    Panel with multiline wx.TextCtrl
    """
    def __init__(self, parent, label, widgets, optional, workflow):

        wx.Panel.__init__(self,
                          parent = parent,
                          id = wx.ID_ANY,
                          pos = wx.DefaultPosition,
                          size = wx.DefaultSize,
                          style = wx.TAB_TRAVERSAL,
                          name = wx.EmptyString)
        self.SetBackgroundColour(parent.clr_Panels)
        #self.SetMaxSize(wx.Size(220,-1))
        self.optional = optional
        self.szr = wx.BoxSizer(wx.VERTICAL)
        if self.optional == True:
            self.lbl = wx.CheckBox(self,
                                   label = label)
            self.lbl.Bind(wx.EVT_CHECKBOX, self.toggle)
            # Shoudle widget be eNaBLed?
            self.nbl = False
        else: 
            self.lbl = wx.StaticText(self,
                                     label = label)
            self.lbl.Wrap(-1)
            # Shoudle widget be eNaBLed?
            self.nbl = True
        self.szr.Add(self.lbl,
                     proportion = 0,
                     flag = wx.ALL,
                     border = 5)
        height = widgets["Lines"] * 18
        self.multi = wx.TextCtrl(self,
                                 value = u"Buffer",
                                 size = wx.Size(-1,height),
                                 style = wx.TE_MULTILINE|wx.TE_BESTWRAP)
        self.multi.SetBackgroundColour(parent.clr_TextBoxes)
        dtl = widgets["Detail"]
        workflow.get_details[dtl] = self.get_value
        workflow.set_details[dtl] = self.set_value
        workflow.wdg_details[dtl] = self
        self.szr.Add(self.multi,
                     proportion = 1,
                     flag = wx.ALL|wx.EXPAND,
                     border = 5)
        self.SetSizer(self.szr)
        self.Layout()
        self.szr.Fit(self)

    def toggle(self, event):
        """
        Event handler to toggle the enabled status of the widget
        """
        self.nbl = event.GetEventObject().GetValue()
        self.multi.Enable(self.nbl)
        self.Refresh()

    def get_value(self):
        """
        Function to return selected value.
        """
        if self.nbl == True:
            buffer = ""
            for lin in range(self.multi.GetNumberOfLines()):
                buffer += self.multi.GetLineText(lin)
            return buffer
        else:
            return np.nan
    
    def set_value(self, value):
        """
        Wrapper function to set the value.
        Arguments:
            value -> string.
        """
        self.multi.ChangeValue(value)


class PlateLayout(wx.Panel):
    """
    Panel to select one global plate layout or indiviaual layouts
    for plates.
    """
    def __init__(self, parent, label, widgets, optional, workflow):

        wx.Panel.__init__(self,
                          parent = parent,
                          id = wx.ID_ANY,
                          pos = wx.DefaultPosition,
                          size = wx.Size(270,-1),
                          style = wx.TAB_TRAVERSAL,
                          name = wx.EmptyString)

        self.workflow = workflow

        self.SetBackgroundColour(parent.clr_Panels)
        self.optional = optional
        self.szr = wx.BoxSizer(wx.VERTICAL)
        if self.optional == True:
            self.lbl = wx.CheckBox(self,
                                   label = label)
            self.lbl.Bind(wx.EVT_CHECKBOX, self.toggle)
            # Shoudle widget be eNaBLed?
            self.nbl = False
        else: 
            self.lbl = wx.StaticText(self,
                                     label = label)
            self.lbl.Wrap(-1)
            # Shoudle widget be eNaBLed?
            self.nbl = True
        self.szr.Add(self.lbl,
                     proportion = 0,
                     flag = wx.ALL,
                     border = 5)
        if widgets["PlateIDs"] == True:
            self.plate_id = wx.CheckBox(self,
                                           label = u"Use PlateID for database",
                                           size = wx.Size(-1,-1))
            self.plate_id.SetValue(True)
            self.szr.Add(self.plate_id, 0, wx.ALL, 5)
        self.rad_indi = wx.RadioButton(self,
                                    label = u"Individual layouts for each plate",
                                    style = wx.RB_SINGLE)
        self.rad_indi.Bind(wx.EVT_RADIOBUTTON, self.on_rad_indi)
        self.szr.Add(self.rad_indi,
                     proportion = 0,
                     flag = wx.ALL,
                     border = 5)
        self.szr_indi = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_indi.Add((25,24), 0, wx.EXPAND, 5)
        self.lbl_indi = wx.StaticText(self,
                                      label = u"If you select this option, you can specify layouts for each plate in the \"Transfer and Data Files\" tab after you have imported plates.")
        self.lbl_indi.Wrap(240)
        self.szr_indi.Add(self.lbl_indi,
                          proportion = 0,
                          flag = wx.EXPAND,
                          border = 5)
        self.lbl_indi.Enable(False)
        self.szr.Add(self.szr_indi,
                     proportion = 0,
                     flag = wx.EXPAND,
                     border = 5)
        self.rad_glbl = wx.RadioButton(self, 
                                       label = u"Same layout on all plates (e.g. large screen)",
                                       style = wx.RB_SINGLE)
        self.rad_glbl.Bind(wx.EVT_RADIOBUTTON, self.on_rad_glbl)
        self.szr.Add(self.rad_glbl,
                       proportion = 0,
                       flag = wx.ALL,
                       border = 5)
        self.rad_glbl.SetValue(True)
        self.returnvalue = True
        self.szr_glbl = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_glbl.Add((20,24), 0, wx.EXPAND, 5)
        self.btn_edit = btn.CustomBitmapButton(self,
                                               name = u"EditPlateLayout",
                                               index = 0,
                                               size = (125,25))
        self.szr_glbl.Add(self.btn_edit,
                          proportion = 0,
                          flag = wx.ALL,
                          border = 0)
        self.szr.Add(self.szr_glbl,
                     proportion = 0,
                     flag = wx.EXPAND,
                     border = 5)
        self.szr.Add((-1,10), 0, wx.ALL, 0)
        self.SetSizer(self.szr)
        self.Layout()
        self.szr.Fit(self)
        self.btn_edit.Bind(wx.EVT_BUTTON, self.edit_layouts)

        dtl = widgets["Detail"]
        workflow.get_details[dtl] = self.get_value
        workflow.set_details[dtl] = self.set_value
        workflow.wdg_details[dtl] = self

    def toggle(self, event):
        """
        Event handler to toggle the enabled status of the widget
        """
        self.nbl = event.GetEventObject().GetValue()
        for dtl in self.labels.keys():
            self.labels[dtl].Enable(self.nbl)
            self.inputs[dtl].Enable(self.nbl)
        # separate units out because not all fields might have units
        for dtl in self.units.keys():
            self.units[dtl].Enable(self.nbl)
        self.Refresh()

    def get_value(self):
        """
        Function to return selected value.
        """
        return self.returnvalue

    def set_value(self, value):

        self.rad_indi.SetValue(not value)
        self.rad_glbl.SetValue(value)
        self.returnvalue = value

    def on_rad_indi(self, event):
        self.rad_indi.SetValue(True)
        self.rad_glbl.SetValue(False)
        self.returnvalue = False
        self.btn_edit.Enable(False)
        self.lbl_indi.Enable(True)
        self.workflow.tab_Files.btn_EditLayouts.Enable(True)

    def on_rad_glbl(self, event):
        self.rad_indi.SetValue(False)
        self.rad_glbl.SetValue(True)
        self.returnvalue = True
        self.btn_edit.Enable(True)
        self.lbl_indi.Enable(False)
        self.workflow.tab_Files.btn_EditLayouts.Enable(False)
    
    def edit_layouts(self, event):
        plm.edit_layouts(self.workflow)
            
class RadioOptions(wx.Panel):
    """
    Based on wx.Panel.
    Holds list of radio button options with title above.
    """
    def __init__(self, parent, label, widgets, optional, workflow):
        """
        Initialises the widget

        Arguments:
            parent -> wx object that this object belongs to
            label -> str. Label for panel
            widgets -> dictionary with instructions to build
                       this widget:
            workflow -> reference to workflow (i.e. the object
                        that represents the workflow tab)
        """
        wx.Panel.__init__(self,
                          parent = parent,
                          id = wx.ID_ANY,
                          pos = wx.DefaultPosition,
                          size = wx.DefaultSize,
                          style = wx.TAB_TRAVERSAL,
                          name = wx.EmptyString)
        self.SetBackgroundColour(parent.clr_Panels)
        self.optional = optional
        #self.SetMaxSize(wx.Size(220,-1))
        self.szr = wx.BoxSizer(wx.VERTICAL)
        if self.optional == True:
            self.lbl = wx.CheckBox(self,
                                   label = label)
            self.lbl.Bind(wx.EVT_CHECKBOX, self.toggle)
            # Shoudle widget be eNaBLed?
            self.nbl = False
        else: 
            self.lbl = wx.StaticText(self,
                                     label = label)
            self.lbl.Wrap(-1)
            # Shoudle widget be eNaBLed?
            self.nbl = True
        self.szr.Add(self.lbl,
                     proportion = 0,
                     flag = wx.ALL,
                     border = 5)
        self.rad = {}
        self.val = {}
        options = workflow.default_details[widgets["Options"]]
        for key in options.keys():
            self.rad[key] = wx.RadioButton(self,
                                           label = key,
                                           style = wx.RB_SINGLE)
            self.rad[key].Bind(wx.EVT_RADIOBUTTON, self.on_rad)
            self.val[key] = options[key]
            self.szr.Add(self.rad[key],
                         proportion = 0,
                         flag = wx.ALL,
                         border = 5)

        initial = list(self.rad.keys())[0] 
        self.rad[initial].SetValue(True)
        self.returnvalue = self.val[initial]

        dtl = widgets["Detail"]
        workflow.get_details[dtl] = self.get_value
        workflow.set_details[dtl] = self.set_value
        workflow.wdg_details[dtl] = self

        # Finalise
        self.SetSizer(self.szr)
        self.Layout()
        self.szr.Fit(self)

    def toggle(self, event):
        """
        Event handler to toggle the enabled status of the widget
        """
        self.nbl = event.GetEventObject().GetValue()
        for dtl in self.labels.keys():
            self.labels[dtl].Enable(self.nbl)
            self.inputs[dtl].Enable(self.nbl)
        # separate units out because not all fields might have units
        for dtl in self.units.keys():
            self.units[dtl].Enable(self.nbl)
        self.Refresh()

    def get_value(self):
        """
        Function to return selected value.
        """
        if self.nbl == True:
            return self.returnvalue
        else:
            return np.nan
            
    def set_value(self, value):

        for key in self.rad.keys():
            if value == self.val[key]:
                self.rad[key].SetValue(True)
                self.returnvalue = self.val[key]
            else:
                self.rad[key].SetValue(False)

    def on_rad(self, event):
        """
        Event handler for 
        """
        event.Skip()
        id = event.GetEventObject().GetId()
        for key in self.rad.keys():
            if id == self.rad[key].GetId():
                self.rad[key].SetValue(True)
                self.returnvalue = self.val[key]
            else:
                self.rad[key].SetValue(False)

##############################################
##                                          ##
##    ######  ##  ##      #######  #####    ##
##    ##      ##  ##      ##      ##        ##
##    #####   ##  ##      ####     ####     ##
##    ##      ##  ##      ##          ##    ##
##    ##      ##  ######  ######  #####     ##
##                                          ##
##############################################

class CustomFilePicker(wx.Panel):
    """
    File or directory picker. Custom implementation to keep appearance
    consistent with BBQ GUI.
    """
    def __init__(self, parent, windowtitle, wildcard, size, what = "file"):
        """
        Initialises class attributes.
        
        Arguments:
            parent -> parent object for wxPython GUI building.
            windowtitle -> string. Window title for file/dir dialog
            wildcard -> string. Wildcard for file dialog
            size -> tupel of integers. Overall size of widget
        """
        wx.Panel.__init__ (self, parent, id = wx.ID_ANY, pos = wx.DefaultPosition,
                           size = wx.DefaultSize, style = wx.TAB_TRAVERSAL,
                           name = wx.EmptyString)
        self.parent = parent
        self.WindowTitle = windowtitle
        self.wildcard = wildcard
        self.what = what

        self.Function = None

        self.szr_FilePicker = wx.BoxSizer(wx.HORIZONTAL)
        self.txt_FilePicker = wx.TextCtrl(self, value = wx.EmptyString,
                                          size = wx.Size(size[0]-33,-1))
        self.szr_FilePicker.Add(self.txt_FilePicker, 0, wx.ALL, 0)
        self.szr_FilePicker.Add((3,-1),0,wx.EXPAND,0)
        self.btn_FilePicker = btn.CustomBitmapButton(self,
                                                     name = "Browse",
                                                     index = 1,
                                                     size = (30,25))
        self.szr_FilePicker.Add(self.btn_FilePicker, 0, wx.ALL, 0)
        self.SetSizer(self.szr_FilePicker)
        self.szr_FilePicker.Fit(self)
        self.Layout()

        self.btn_FilePicker.Bind(wx.EVT_BUTTON, self.action)

    def action(self, event):
        """
        Event handler to pick correct event based on whether files
        or directory are to be opened.
        """
        if self.what == "file":
            self.pick_file()
        elif self.what == "directory":
            self.pick_directory()

    def pick_file(self):
        """
        Open file dialog and write picked path into text field and
        do something with the path if a function is specified.
        """
        with wx.FileDialog(self, self.WindowTitle, wildcard=self.wildcard,
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as fileDialog:

            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return     # the user changed their mind
            self.txt_FilePicker.SetValue(fileDialog.GetPath())
            if not self.Function == None and not self.txt_FilePicker.Value == "":
                self.Function(fileDialog.GetPath())

    def pick_directory(self):
        """
        Open dir dialog and write picked path into text field and
        do something with the path if a function is specified.
        """
        with wx.DirDialog(self, self.WindowTitle,
            style=wx.FD_OPEN|wx.FD_FILE_MUST_EXIST) as directoryDialog:

            if directoryDialog.ShowModal() == wx.ID_CANCEL:
                return     # the user changed their mind
            self.txt_FilePicker.SetValue(directoryDialog.GetPath())
            if not self.Function == None and not self.txt_FilePicker.Value == "":
                self.Function(directoryDialog.GetPath())

    def Bind(self, function):
        """
        Assigns function
        """
        self.Function = function

    def set_path(self, str_Path):
        """
        Set path displayed in text box
        """
        if not type(str_Path) == str:
            str_Path = str(str_Path)
        self.txt_FilePicker.SetValue(str_Path)

    def get_path(self):
        return self.txt_FilePicker.GetValue()


class FileSelection(wx.Panel):
    """
    File selection tab. Derived from wx.Panel
    """

    def __init__(self, notebook, tabname, whattopick, extension, normalise, layouts):
        """
        Initialises class attributes.
        
        Arguments:
            notebook -> parent object for wxPython GUI building. In this
                        case, the notebook that this panel will reside in.
            tabname -> gets assigned to self.tabname. Reference to the
                       pnl_Project instance above this object (contains
                       any functions that might need to be called, objects
                       controlled, etc).
            whattopick -> string. Either "directory" or "file"
            extension -> string. Data file type extension, e.x. ".xlsx"
            normalise -> boolean. If true, display option to load reference
                         plate to normalise each plate against. Currently
                         not used.
            layouts -> boolean. If true, show option to define individual
                       layouts for each plate.
        """
        wx.Panel.__init__ (self, parent = notebook, id = wx.ID_ANY,
                           pos = wx.DefaultPosition, size = wx.DefaultSize,
                           style = wx.TAB_TRAVERSAL, name = wx.EmptyString)
        
        self.tabname = tabname

        self.SetBackgroundColour(cs.BgUltraLight)
        clr_Panels = cs.BgLight
        clr_TextBoxes = cs.BgUltraLight

        self.szr_Files = wx.BoxSizer(wx.VERTICAL)

        # 2. File assignment lists
        self.szr_Assignment = wx.FlexGridSizer(2,3,0,0)
        # 2.1 Transfer Files
        self.pnl_Transfer = wx.Panel(self, size = wx.Size(460,-1),
                                     style = wx.TAB_TRAVERSAL)
        self.pnl_Transfer.SetBackgroundColour(clr_Panels)
        self.pnl_Transfer.SetMaxSize(wx.Size(460,-1))
        self.szr_Transfer = wx.BoxSizer(wx.VERTICAL)
        # Show in case of "echo"
        self.pnl_Echo = wx.Panel(self.pnl_Transfer, size = wx.Size(460,-1),
                                 style = wx.TAB_TRAVERSAL)
        self.szr_Echo = wx.BoxSizer(wx.VERTICAL)
        self.lbl_Transfer = wx.StaticText(self.pnl_Echo, label = u"Select a transfer file:",
                                          size = wx.Size(450,20))
        self.lbl_Transfer.Wrap(-1)
        self.szr_Echo.Add(self.lbl_Transfer, 0, wx.ALL, 5)
        self.fpk_Transfer = CustomFilePicker(self.pnl_Echo,
                                             windowtitle = u"Select a transfer file",
                                             wildcard = u"*.csv",
                                             size = (450,-1),
                                             what = "file")
        self.szr_Echo.Add(self.fpk_Transfer, 0, wx.ALL, 5)
        self.fpk_Transfer.Bind(self.read_transfer)
        self.pnl_Echo.SetSizer(self.szr_Echo)
        self.pnl_Echo.Layout()
        self.szr_Echo.Fit(self.pnl_Echo)
        self.szr_Transfer.Add(self.pnl_Echo, 0, wx.ALL, 0)
        # Show in case of "lightcycler" or "well"
        self.pnl_Plates = wx.Panel(self.pnl_Transfer, size = wx.Size(460,70),
                                   style = wx.TAB_TRAVERSAL)
        self.szr_Plates = wx.BoxSizer(wx.VERTICAL)
        # Add Plate
        self.pnl_AddDestination = wx.Panel(self.pnl_Plates, size = wx.Size(450,25),
                                           style = wx.TAB_TRAVERSAL)
        self.szr_AddDestination = wx.BoxSizer(wx.HORIZONTAL)
        self.lbl_AddDestination = wx.StaticText(self.pnl_AddDestination,
                                                label = u"Add a plate to analyse:",
                                                size = wx.Size(-1,25))
        self.szr_AddDestination.Add(self.lbl_AddDestination, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 0)
        self.szr_AddDestination.Add((-1,25), 1, wx.EXPAND, 0)
        self.txt_AddDestination = wx.TextCtrl(self.pnl_AddDestination, 
                                              value = u"Plate 1",
                                              size = wx.Size(120,25))
        self.szr_AddDestination.Add(self.txt_AddDestination, 0, wx.EXPAND, 0)
        self.szr_AddDestination.Add((5,25), 0, wx.EXPAND, 0)
        if self.tabname.details["AssayCategory"] == "thermal_shift":
            lst_PlateFormat = [ u"96", u"384", u"1536" ]
        else:
            lst_PlateFormat = [ u"384", u"1536", u"96" ]
        self.cho_PlateFormat = wx.Choice(self.pnl_AddDestination, choices = lst_PlateFormat)
        self.cho_PlateFormat.SetSelection(0)
        self.szr_AddDestination.Add(self.cho_PlateFormat, 0, wx.EXPAND, 0)
        self.szr_AddDestination.Add((5,25), 0, wx.EXPAND, 0)
        self.btn_AddDestination = btn.CustomBitmapButton(self.pnl_AddDestination,
                                                         name = u"Plus",
                                                         index = 0,
                                                         size = (25,25))
        self.szr_AddDestination.Add(self.btn_AddDestination, 0, wx.EXPAND, 0)
        self.pnl_AddDestination.SetSizer(self.szr_AddDestination)
        self.pnl_AddDestination.Layout()
        self.szr_Plates.Add(self.pnl_AddDestination, 0, wx.ALL, 5)
        # Remove plate
        self.pnl_RemoveDestination = wx.Panel(self.pnl_Plates, size = wx.Size(450,25),
                                              style = wx.TAB_TRAVERSAL)
        self.szr_RemoveDestination = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_RemoveDestination.Add((-1,25), 1, wx.EXPAND, 0)
        self.lbl_RemoveDestination = wx.StaticText(self.pnl_RemoveDestination,
                                                   label = u"Remove selected plate(s)",
                                                   size = wx.Size(-1,25))
        self.szr_RemoveDestination.Add(self.lbl_RemoveDestination, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 0)
        self.szr_RemoveDestination.Add((5,25), 0, wx.ALL, 0)
        self.btn_RemoveDestination = btn.CustomBitmapButton(self.pnl_RemoveDestination,
                                                            name = u"Minus",
                                                            index = 0,
                                                            size = (25,25))
        self.szr_RemoveDestination.Add(self.btn_RemoveDestination, 0, wx.EXPAND, 5)
        self.pnl_RemoveDestination.SetSizer(self.szr_RemoveDestination)
        self.pnl_RemoveDestination.Layout()
        self.szr_RemoveDestination.Fit(self.pnl_RemoveDestination)
        self.szr_Plates.Add(self.pnl_RemoveDestination, 0, wx.ALL, 5)
        # Add to panel and fit
        self.pnl_Plates.SetSizer(self.szr_Plates)
        self.pnl_Plates.Layout()
        self.szr_Plates.Fit(self.pnl_Plates)
        self.szr_Transfer.Add(self.pnl_Plates, 0, wx.ALL, 0)
        self.lbc_Transfer = tdnd.MyDropTarget(self.pnl_Transfer, size = wx.Size(450,300),
                                            style = wx.LC_REPORT,
                                            name = u"TransferFileEntries",
                                            instance = self)
        self.lbc_Transfer.SetBackgroundColour(clr_TextBoxes)
        self.lbc_Transfer.InsertColumn(0,"Destination Plate Name")
        self.lbc_Transfer.SetColumnWidth(0, 150)
        self.lbc_Transfer.InsertColumn(1,"Wells")
        self.lbc_Transfer.SetColumnWidth(1, 50)
        self.lbc_Transfer.InsertColumn(2,"Raw Data Plate")
        self.lbc_Transfer.SetColumnWidth(2, 250)
        self.szr_Transfer.Add(self.lbc_Transfer, 0, wx.ALL, 5)
        self.pnl_Transfer.SetSizer(self.szr_Transfer)
        self.pnl_Transfer.Layout()
        self.szr_Assignment.Add(self.pnl_Transfer, 1, wx.ALL, 5)
        # 2.2 Assignment Buttons
        self.szr_AssignButtons = wx.BoxSizer(wx.VERTICAL)
        self.szr_AssignButtons.Add((0, 120), 0, wx.EXPAND, 5)
        self.lbl_Assign = wx.StaticText(self, label = u"Assign")
        self.lbl_Assign.Wrap(-1)
        self.szr_AssignButtons.Add(self.lbl_Assign, 0, wx.ALIGN_CENTER_HORIZONTAL, 5)
        self.btn_Assign = btn.CustomBitmapButton(self, "ArrowLeft", 1, (40,25))
        self.btn_Assign.Bind(wx.EVT_BUTTON, self.assign_plate)
        self.szr_AssignButtons.Add(self.btn_Assign, 0, wx.ALL, 5)
        self.btn_Remove = btn.CustomBitmapButton(self, "ArrowRight", 1, (40,25))
        self.szr_AssignButtons.Add(self.btn_Remove, 0, wx.ALL, 5)
        self.lbl_Remove = wx.StaticText(self, label = u"Remove")
        self.lbl_Remove.Wrap(-1)
        self.szr_AssignButtons.Add(self.lbl_Remove, 0, wx.ALIGN_CENTER_HORIZONTAL, 5)
        self.szr_Assignment.Add(self.szr_AssignButtons, 0, wx.EXPAND, 5)
        # 2.3 Data Files
        self.pnl_Data = wx.Panel(self, size = wx.Size(460,-1), 
                                 style = wx.TAB_TRAVERSAL)
        self.pnl_Data.SetBackgroundColour(clr_Panels)
        self.pnl_Data.SetMaxSize(wx.Size(460,-1))
        self.szr_Data = wx.BoxSizer(wx.VERTICAL)
        if whattopick == "directory":
            str_RawDataLabel = "Select the directory with the raw data:"
            windowtitle = "Select a folder"
        else:
            str_RawDataLabel = "Select a raw data file:"
            windowtitle = "Select a file"
        self.lbl_RawData = wx.StaticText(self.pnl_Data, label = str_RawDataLabel,
                                         size = wx.Size(450,20))
        self.szr_Data.Add(self.lbl_RawData, 0, wx.ALL, 5)
        self.pnl_Spacer = wx.Panel(self.pnl_Data, size = wx.Size(460,5),
                                   style = wx.TAB_TRAVERSAL)
        self.szr_Data.Add(self.pnl_Spacer, 0, wx.ALL, 0)
        self.fpk_Data = CustomFilePicker(self.pnl_Data,
                                         windowtitle = windowtitle,
                                         wildcard = f"*{extension}",
                                         size = (450,-1),
                                         what = whattopick)
        self.szr_Data.Add(self.fpk_Data, 0, wx.ALL, 5)
        self.lbc_Data = tdnd.MyDragList(self.pnl_Data,
                                      size = wx.Size(450,300),
                                      style = wx.LC_REPORT)
        self.lbc_Data.SetBackgroundColour(clr_TextBoxes)
        self.lbc_Data.InsertColumn(0,"Data Plate Name")
        self.lbc_Data.SetColumnWidth(0, 250)
        self.lbc_Data.InsertColumn(1,"Wells")
        self.lbc_Data.SetColumnWidth(1, 50)
        self.szr_Data.Add(self.lbc_Data, 0, wx.ALL, 5)
        self.pnl_Data.SetSizer(self.szr_Data)
        self.pnl_Data.Layout()
        self.szr_Assignment.Add(self.pnl_Data, 0, wx.ALL, 5)

        # 3. Normalisation
        #if normalise == True:
        #    self.pnl_Normalise = wx.Panel(self, wx.ID_ANY, wx.DefaultPosition, wx.Size(460,-1), wx.TAB_TRAVERSAL)
        #    self.pnl_Normalise.SetBackgroundColour(clr_Panels)
        #    self.pnl_Normalise.SetMaxSize(wx.Size(460,-1))
        #    self.szr_Normalise = wx.BoxSizer(wx.VERTICAL)
        #    self.chk_Normalise = wx.CheckBox(self.pnl_Normalise, wx.ID_ANY,  u"Normalise plates against a reference plate (e.g. Solvent only)", wx.DefaultPosition, wx.DefaultSize, 0)
        #    self.chk_Normalise.SetValue(False)
        #    self.szr_Normalise.Add(self.chk_Normalise, 0, wx.ALL, 5)
        #    self.fpk_Normalise = CustomFilePicker(self.pnl_Normalise, u"Select a file", u"*.*", (450,-1))
        #    self.szr_Normalise.Add(self.fpk_Normalise, 0, wx.ALL, 5)
        #    self.pnl_Normalise.SetSizer(self.szr_Normalise)
        #    self.pnl_Normalise.Layout()
        #    self.szr_Assignment.Add(self.pnl_Normalise, 0, wx.ALL, 5)
        # 4. Plate layouts
        if layouts == True:
            self.pnl_Layouts = wx.Panel(self, size = wx.Size(460,-1),
                                        style = wx.TAB_TRAVERSAL)
            self.pnl_Layouts.SetBackgroundColour(clr_Panels)
            self.pnl_Layouts.SetMaxSize(wx.Size(460,-1))
            self.szr_Layouts = wx.BoxSizer(wx.VERTICAL)
            self.btn_EditLayouts = btn.CustomBitmapButton(self.pnl_Layouts,
                                                          name = "EditIndividualPlateLayouts",
                                                          index = 0,
                                                          size = (186,25))
            self.szr_Layouts.Add(self.btn_EditLayouts, 0, wx.ALIGN_RIGHT|wx.ALL, 0)
            self.btn_EditLayouts.Enable(False)
            self.btn_EditLayouts.Bind(wx.EVT_BUTTON, lambda event: plm.edit_layouts(self.tabname))
            self.pnl_Layouts.SetSizer(self.szr_Layouts)
            self.pnl_Layouts.Layout()
            self.szr_Assignment.Add(self.pnl_Layouts, 0, wx.ALL, 5)
        # Finalise

        self.szr_Assignment.Add((-1,-1), 0, wx.EXPAND, 5)
        self.szr_Assignment.Add((-1,-1), 0, wx.EXPAND, 5)

        self.szr_Files.Add(self.szr_Assignment, 0, wx.EXPAND, 5)
        self.SetSizer(self.szr_Files)
        self.Layout()

        # Bindings
        self.lbc_Transfer.Bind(tdnd.EVT_TRANSFER_UPDATE, self.OnUpdateTransfer)
        self.fpk_Data.Bind(self.get_datafiles)
        self.btn_Remove.Bind(wx.EVT_BUTTON, self.remove_plate)
        self.btn_AddDestination.Bind(wx.EVT_BUTTON, self.add_plate)
        self.btn_RemoveDestination.Bind(wx.EVT_BUTTON, self.DeletePlate)

        if self.tabname.details["SampleSource"] == "echo":
            self.pnl_Echo.Show()
            self.lbl_RawData.SetSize(450,-1)
            self.pnl_Plates.Hide()
            self.pnl_Spacer.Hide()
            self.Layout()

    # 2.1 Load transfer file, get list of plates, write into list box
    def read_transfer(self, str_TransferFile):
        """
        Get list of destination plate entries in transfer file and populate
        list control with them.

        Arguments:
            str_TransferFile -> string
        """
        # Write transfer path (full path with with file name) into variable
        self.tabname.paths["TransferPath"] = str_TransferFile
        # use path with transfer functions to extract destination plates
        self.tabname.dfr_TransferFile, self.tabname.dfr_Exceptions = df.create_transfer_frame(str_TransferFile,
                                                                                              self.tabname.transfer_rules)
        # Include check to see if transfer file was processed correctly
        if self.tabname.dfr_TransferFile is None:
            msg.warn_not_transferfile()
            return None
        # If the dataframe is not None, we continue:
        dfr_DestinationPlates = df.get_destination_plates(self.tabname.dfr_TransferFile)
        # Clear list before inserting new items
        self.lbc_Transfer.DeleteAllItems()
        for i in range(len(dfr_DestinationPlates)):
            if dfr_DestinationPlates.iloc[i,0].find("Intermediate") == -1:
                # Write DestinationPlateName
                self.lbc_Transfer.InsertItem(i,str(dfr_DestinationPlates.iloc[i,0]))
                # Write number of wells
                self.lbc_Transfer.SetItem(i,1,str(dfr_DestinationPlates.iloc[i,2]))
                # write empty string tinto third column
                self.lbc_Transfer.SetItem(i,2,"")
        if not self.tabname.details["AssayCategory"] == "single_dose":
            # Write .xls files from same directory into tab_Files.lbc_Data list
            self.lbc_Data.DeleteAllItems()
            # Write transfer path (full path with with file name) into variable; chr(92) is "\"
            self.tabname.paths["Data"] = self.tabname.paths["TransferPath"][0:self.tabname.paths["TransferPath"].rfind(chr(92))+1]
            lst_DataFiles = os.listdir(self.tabname.paths["Data"])
            # Select correct file extension:
            for i in range(len(lst_DataFiles)):
                if lst_DataFiles[i].find(self.tabname.details["DataFileExtension"]) != -1: #and lst_DataFiles[i].find(".xlsx") == -1: # I am going to have to trust the 
                    self.lbc_Data.InsertItem(i,str(lst_DataFiles[i]))
            self.fpk_Data.set_path(self.tabname.paths["Data"])
        self.tabname.bol_TransferLoaded = True
    
    def CreateEmptyTransferFrame(self):
        """
        Creates enpty transfer dataframe when actual transfer file has ben
        loaded.
        """
        self.tabname.paths["TransferPath"] = None
        self.tabname.dfr_TransferFile = pd.DataFrame(columns=["SourceConcentration",
                                                     "Destination",
                                                     "DestinationPlateBarcode",
                                                     "DestinationPlateType",
                                                     "DestinationWell",
                                                     "SampleID",
                                                     "SampleName",
                                                     "DestinationConcentration",
                                                     "TransferVolume",
                                                     "ActualVolume"])
        
    def get_datafiles(self, datapath):
        """
        Get list of data files and populate list control with them.

        Arguments:
            datapath -> string
        """
        # Clear list
        self.lbc_Data.DeleteAllItems()
        # Write transfer path (full path with with file name) into variable
        self.tabname.paths["Data"] = datapath
        # Populate list depending on assay category. Only for single dose do we have
        # multiple plates per data file.
        if self.tabname.details["AssayCategory"] != "single_dose":
            lst_DataFiles = os.listdir(self.tabname.paths["Data"])
            for i in range(len(lst_DataFiles)):
                if lst_DataFiles[i].find(self.tabname.details["DataFileExtension"]) != -1:
                    self.lbc_Data.InsertItem(i,str(lst_DataFiles[i]))
        else:
            lst_Plates = ro.get_bmg_list_namesonly(self.tabname.paths["Data"])
            if len(lst_Plates) == 0:
                msg.warn_not_datafile()
            else:
                for i in range(len(lst_Plates)):
                    self.lbc_Data.InsertItem(i,str(lst_Plates[i]))

    def OnUpdateTransfer(self,event):
        """
        Event handler. Gets called when transfer file is updated. 
        Calls self.update_plate_assignment and updates data file entries
        in lbc_Data with entries from transfer file.
        """
        self.tabname.bol_DataFilesAssigned = event.set_bool
        self.tabname.bol_DataFilesUpdated = event.set_bool
        self.update_plate_assignment()
        if len(event.return_items) > 0:
            for i in range(len(event.return_items)):
                self.lbc_Data.InsertItem(self.lbc_Data.GetItemCount()+1,event.return_items[i])
            self.lbc_Data.ReSort()

    def assign_plate(self, event):
        """
        Event handler. Gets called when user assigns entry from data file
        list to transfer file entry. Assigned entry/ies from data file
        list is/are removed.
        """
        # Create lists to handle things:
        lst_Transfer_Selected = []
        lst_Data_Selected = []
        lst_Data_Return = []
        lst_Data_Delete = []
        # Count selected items in Transfer file list and write indices into list:
        for i in range(self.lbc_Transfer.ItemCount):
            if self.lbc_Transfer.IsSelected(i) == True:
                lst_Transfer_Selected.append(i)
        # Count selected items in Data file list and write indices into list:
        for i in range(self.lbc_Data.ItemCount):
            if self.lbc_Data.IsSelected(i) == True:
                lst_Data_Selected.append(i)
        # Assign data files:
        int_Data = len(lst_Data_Selected)
        int_Transfer = len(lst_Transfer_Selected)
        if int_Data > 0 and int_Transfer > 0:
            for i in range(int_Transfer):
                # Make sure we do not run out of selected data files:
                if i < int_Data:
                    # Check if a data file had been assigned previously
                    if not self.lbc_Transfer.GetItemText(i,2) == "":
                        lst_Data_Return.append(self.lbc_Transfer.GetItemText(i,2))
                    # Write data file in there
                    self.lbc_Transfer.SetItem(lst_Transfer_Selected[i],2,
                                              self.lbc_Data.GetItemText(lst_Data_Selected[i],0))
                    # Catch which items we want to delete from the data file list.
                    # If there are more data files selected than transfer file entries,
                    # these will not be added to this list and thus not be deleted from
                    # the data list.
                    lst_Data_Delete.append(lst_Data_Selected[i])
                    # update global change tracking variables
                    self.tabname.bol_DataFilesAssigned = True
                    self.tabname.bol_DataFilesUpdated = True
        # Delete items that have been assigned:
        if len(lst_Data_Delete) > 0:
            # Go from the end of the list so as to not change the indices when deleting items:
            for i in range(len(lst_Data_Delete),0,-1):
                self.lbc_Data.DeleteItem(lst_Data_Delete[i-1])
        # Return any items:
        if len(lst_Data_Return) > 0:
            for i in range(len(lst_Data_Return)):
                self.lbc_Data.InsertItem(self.lbc_Data.GetItemCount()+1,lst_Data_Return[i])
            self.lbc_Data.ReSort()
        # Update plate assignment
        self.update_plate_assignment()

    def remove_plate(self, event):
        """
        Event handler. Gets called when user removes data file entry from
        transfer file entry. Removed data file entry/ies get relisted on
        raw data file list control.
        """
        int_Selected = self.lbc_Transfer.GetSelectedItemCount()
        if int_Selected > 0:
            int_idx_Transfer = self.lbc_Transfer.GetFirstSelected()
            if int_idx_Transfer != -1:
                if not self.lbc_Transfer.GetItemText(int_idx_Transfer,2) == "":
                    self.lbc_Data.InsertItem(self.lbc_Data.GetItemCount()+1,
                                             self.lbc_Transfer.GetItemText(int_idx_Transfer,2))
                    self.lbc_Transfer.SetItem(int_idx_Transfer,2,"")
                    self.lbc_Data.ReSort()
                    self.tabname.bol_DataFilesAssigned = False
        if int_Selected > 1:
            for i in range(int_Selected-1):
                if not self.lbc_Transfer.GetNextSelected(i) and self.lbc_Transfer.GetItemText(self.lbc_Transfer.GetNextSelected(i),2) == "":
                    self.lbc_Data.InsertItem(self.lbc_Data.GetItemCount()+1,
                                             self.lbc_Transfer.GetItemText(self.lbc_Transfer.GetNextSelected(i),2))
                    self.lbc_Transfer.SetItem(self.lbc_Transfer.GetNextSelected(i),2,"")
                    self.lbc_Data.ReSort()
                    self.tabname.bol_DataFilesAssigned = False
        # Check if any data files remain assigned to destination plate entries
        # and set tracking varibles
        for i in range(self.lbc_Transfer.GetItemCount()-1):
            if not self.lbc_Transfer.GetItem(i,2) == "":
                self.tabname.bol_DataFilesAssigned = True
                self.tabname.bol_DataFilesUpdated = True
        # Update plate assignment
        self.update_plate_assignment()

    def update_plate_assignment(self):
        """
        Updates plate assignment dataframe with entries from transfer file
        list control.
        """
        # count how many assigned plates there are
        count = 0
        for i in range(self.lbc_Transfer.GetItemCount()):
            if not self.lbc_Transfer.GetItemText(i,2) == "":
                count += 1
        self.tabname.bol_DataFilesAssigned = False
        # Initialise plate assignment dataframe
        if count > 0:
            transfer = []
            wells = []
            data = []
            for i in range(self.lbc_Transfer.GetItemCount()):
                if not self.lbc_Transfer.GetItemText(i,2) == "":
                    transfer.append(self.lbc_Transfer.GetItemText(i,0))
                    wells.append(self.lbc_Transfer.GetItemText(i,1))
                    data.append(self.lbc_Transfer.GetItemText(i,2))
            self.tabname.dfr_PlateAssignment = pd.DataFrame(data={"TransferEntry":transfer,
                                                                  "DataFile":data,
                                                                  "Wells":wells})
            self.tabname.bol_DataFilesAssigned = True
        else:
            return None
        if self.tabname.bol_LayoutDefined == False:
            self.CreatePlateLayout()
    
    def CreatePlateLayout(self):
        """
        Creates a plate layout dataframe with metadata for each well
        of the plate. Meta data is taken from TxtCtrls
        """

        layout = {}
        layout["PlateID"] = []
        layout["Layout"] = []
        plates = self.tabname.dfr_PlateAssignment.index
        for plate in plates:
            layout["PlateID"].append("X999A")

            welltype = []
            protnum = []
            protid = []
            protconc = []
            ctrlnum = []
            ctrlid = []
            ctrlconc = []
            zprime = []
            refnum = []
            refid = []
            refconc = []
            smplnum = []
            smplid = []
            smplconc = []
            for well in range(int(self.tabname.dfr_PlateAssignment.loc[plate, "Wells"])):
                welltype.append("s")
                protnum.append(0)
                protid.append(self.tabname.details["PurificationID"])
                protconc.append(self.tabname.details["ProteinConc"])
                ctrlnum.append("")
                ctrlid.append("")
                ctrlconc.append("")
                zprime.append("")
                refnum.append("")
                refid.append("")
                refconc.append("")
                smplnum.append("")
                smplid.append("")
                smplconc.append("")
            layout["Layout"].append(pd.DataFrame(data = {"WellType":welltype,
                                                        "ProteinNumerical":protnum,
                                                        "ProteinID":protid,
                                                        "ProteinConcentration":protconc,
                                                        "ControlNumerical":ctrlnum,
                                                        "ControlID":ctrlid,
                                                        "ControlConcentration":ctrlconc,
                                                        "ZPrime":zprime,
                                                        "ReferenceNumerical":refnum,
                                                        "ReferenceID":refid,
                                                        "ReferenceConcentration":refconc,
                                                        "SampleNumerical":smplnum,
                                                        "SampleID":smplid,
                                                        "SampleConcentration":smplconc}))

        self.tabname.dfr_Layout = pd.DataFrame(data = layout)
        self.tabname.bol_LayoutDefined = True
    
    def SwitchSampleSource(self):
        """
        Writes data file entries in transfer listctrl back to data file
        listctrl and clears transfer lstctrl. Displays appropriate fields
        for selected sample source.
        """
        if self.lbc_Transfer.GetItemCount() > 0:
            for idx_List in range(self.lbc_Transfer.GetItemCount()):
                if not self.lbc_Transfer.GetItemText(idx_List,2) == "":
                    self.lbc_Data.InsertItem(self.lbc_Data.GetItemCount()+1,
                                             self.lbc_Transfer.GetItemText(idx_List,2))
            self.lbc_Transfer.DeleteAllItems()
        if self.tabname.details["SampleSource"] == "echo":
            self.pnl_Echo.Show()
            self.pnl_Plates.Hide()
            self.pnl_Spacer.Hide()
            self.Layout()
        elif self.tabname.details["SampleSource"] == "lightcycler":
            self.pnl_Echo.Hide()
            self.pnl_Plates.Show()
            self.pnl_Spacer.Show()
            self.Layout()
        elif self.tabname.details["SampleSource"] == "well":
            self.pnl_Echo.Hide()
            self.pnl_Plates.Show()
            self.pnl_Spacer.Show()
            self.Layout()

    def add_plate(self,event):
        """
        Adds entry to Transfer File dataframe if a new raw data
        entry is assigned to a transfer entry.
        """
        # Get text for Destination:
        int_PlateFormat = int(self.cho_PlateFormat.GetString(self.cho_PlateFormat.GetSelection()))
        str_Destination = self.txt_AddDestination.GetValue()
        # Check if it's already been added:
        if self.lbc_Transfer.GetItemCount() > 0:
            for idx_List in range(self.lbc_Transfer.GetItemCount()):
                if self.lbc_Transfer.GetItemText(idx_List,1) != str(int_PlateFormat):
                    msg.info_plateformat_mismatch()
                    return None
                if self.lbc_Transfer.GetItemText(idx_List,0) == str_Destination:
                    msg.ItemAlradyExists("Destination Plate")
                    return None
        # Check if we have a transfer data frame. If not, make one
        if not hasattr(self.tabname, "dfr_TransferFile"):
            self.CreateEmptyTransferFrame()
        dfr_Add = pd.DataFrame(columns=["SourceConcentration","DestinationPlateName",
                                        "DestinationPlateBarcode","DestinationPlateType",
                                        "DestinationWell","SampleID","SampleName",
                                        "DestinationConcentration","TransferVolume",
                                        "ActualVolume"], index=range(int_PlateFormat))
        # Write values into dafarame -> Use dummy values
        for i in range(int_PlateFormat):
            dfr_Add.loc[i,"SourceConcentration"] = 50 # Dummy value
            dfr_Add.loc[i,"DestinationPlateName"] = str_Destination
            dfr_Add.loc[i,"DestinationPlateBarcode"] = "Dummy"
            dfr_Add.loc[i,"DestinationPlateType"] = f"PCR_{int_PlateFormat}"
            dfr_Add.loc[i,"DestinationWell"] = pf.index_to_well(i,int_PlateFormat)
            dfr_Add.loc[i,"SampleID"] = pf.index_to_well(i,int_PlateFormat)
            dfr_Add.loc[i,"SampleName"] = pf.index_to_well(i,int_PlateFormat)
            dfr_Add.loc[i,"DestinationConcentration"] = 5
            dfr_Add.loc[i,"TransferVolume"] = 20 # Dummy value
            dfr_Add.loc[i,"ActualVolume"] = 20 # Dummy value
        # Combine/concatenate dataframes
        self.tabname.dfr_TransferFile = pd.concat([self.tabname.dfr_TransferFile, dfr_Add],
                                                  ignore_index=False)
        self.lbc_Transfer.InsertItem(self.lbc_Transfer.GetItemCount()+1,str_Destination)
        self.lbc_Transfer.SetItem(self.lbc_Transfer.GetItemCount()-1,1,str(int_PlateFormat))
        if self.lbc_Transfer.GetItemCount() > 0:
            self.btn_RemoveDestination.Enable(True)
        if len(self.tabname.dfr_TransferFile) > 0:
            self.tabname.bol_TransferLoaded = True
        else:
            self.tabname.bol_TransferLoaded = False

    def DeletePlate(self, event):
        """
        Removes entries in TransferFile dataframe is raw data entry is
        removed from transfer file ListCtrl.
        """
        int_Selected = self.lbc_Transfer.GetSelectedItemCount()
        if int_Selected > 0:
            str_DestinationPlate = self.lbc_Transfer.GetItemText(self.lbc_Transfer.GetFirstSelected(), 0)
            self.tabname.dfr_TransferFile = self.tabname.dfr_TransferFile.drop(self.tabname.dfr_TransferFile.index[self.tabname.dfr_TransferFile["Destination"]==str_DestinationPlate])
            self.lbc_Transfer.DeleteItem(self.lbc_Transfer.GetFirstSelected())
        if int_Selected > 1:
            for i in range(int_Selected - 1):
                str_DestinationPlate = self.lbc_Transfer.GetItemText(self.lbc_Transfer.GetNextSelected(0), 0)
                self.tabname.dfr_TransferFile = self.tabname.dfr_TransferFile.drop(self.tabname.dfr_TransferFile.index[self.tabname.dfr_TransferFile["Destination"]==str_DestinationPlate])
                self.lbc_Transfer.DeleteItem(self.lbc_Transfer.GetNextSelected(0))
        if self.lbc_Transfer.GetItemCount() == 0:
            self.btn_RemoveDestination.Enable(False)
        if len(self.tabname.dfr_TransferFile) > 0:
            self.tabname.bol_TransferLoaded = True
        else:
            self.tabname.bol_TransferLoaded = False

##########################################################
##                                                      ##
##    #####   ######  ##  ##  ##  ######  ##  ##  ##    ##
##    ##  ##  ##      ##  ##  ##  ##      ##  ##  ##    ##
##    #####   ####    ##  ##  ##  ####    ##  ##  ##    ##
##    ##  ##  ##       ####   ##  ##       ########     ##
##    ##  ##  ######    ##    ##  ######    ##  ##      ##
##                                                      ##
##########################################################

class Review(wx.Panel):

    """
    Panel to review plate data. Available plots: Heatmap (for raw data),
    Replicate correlation (scatter plot), Scatter plot (for simple data
    processing, e.g. single concentration screen)
    """

    def __init__(self, notebook, tabname, assaycategory, plots = [], xlabels = [],
                 ylabels= [], sidebar = []):
        """
        Initialises class attributes.
        
        Arguments:
            notebook -> parent object for wxPython GUI building. In this
                        case, the notebook that this panel will reside in.
            tabname -> gets assigned to self.tabname. Reference to the
                       pnl_Project instance above this object (contains
                       any functions that might need to be called, objects
                       controlled, etc).
            assaycategory -> short hand of the assay
            plots -> list of the plots to be displayed
            xlabels -> list x-axis labels for the plots
            ylabels -> list of y-axis labels for the plots
            sidebar -> list of parameters to be displayed on the plots'
                       sidebar
        """
        wx.Panel.__init__ (self, parent = notebook, id = wx.ID_ANY,
                           pos = wx.DefaultPosition, size = wx.DefaultSize,
                           style = wx.TAB_TRAVERSAL, name = wx.EmptyString)

        self.tabname = tabname
        self.Assaycategory = assaycategory

        self.SetBackgroundColour(cs.BgUltraLight)

        self.dic_PlotOptions = {"Heat Map": cp.HeatmapPanel,
                                "Replicate Correlation": cp.ReplicateCorrelation,
                                "Scatter Plot": cp.ScatterPlotPanel}
        self.dic_PlotUpdateFunctions = {"Heat Map": self.update_heatmap,
                                        "Replicate Correlation": self.UpdateReplicateCorrelation,
                                        "Scatter Plot": self.UpdateScatterPlot}
        self.dic_Plots = {}
        self.dic_TabButtons = {}
        self.lst_Plots = plots

        # Start Building
        self.szr_ReviewVertical = wx.BoxSizer(wx.VERTICAL)

        self.szr_ReviewHorizontal = wx.BoxSizer(wx.HORIZONTAL)

        # List Control - Plates
        self.lbc_Plates = wx.ListCtrl(self, size = wx.Size(310,-1),
                                      style = wx.LC_REPORT|wx.LC_SINGLE_SEL)
        self.lbc_Plates.SetBackgroundColour(cs.BgUltraLight)
        self.lbc_Plates.InsertColumn(0, "Plate")
        self.lbc_Plates.SetColumnWidth(0,40)
        self.lbc_Plates.InsertColumn(1,"Transfer file entry")
        self.lbc_Plates.SetColumnWidth(1, 120)
        self.lbc_Plates.InsertColumn(2,"Data file name")
        self.lbc_Plates.SetColumnWidth(2, 120)
        self.szr_ReviewHorizontal.Add(self.lbc_Plates, 0, wx.ALL|wx.EXPAND, 5)


        # Plot panel ###################################################################
        self.szr_Plots = wx.BoxSizer(wx.VERTICAL)
        # Create simplebook before adding it to its sizer so that it can be added as
        # .Notebook for IconTabButtons:
        self.sbk_Plots = wx.Simplebook(self, size = wx.Size(900,600))
        self.sbk_Plots.SetBackgroundColour(cs.BgUltraLight)
        self.szr_TabButtons = wx.BoxSizer(wx.HORIZONTAL)
        idx_Button = 0
        for plot in self.lst_Plots:
            self.dic_TabButtons[plot] = btn.IconTabButton(parent = self,
                                                          label = plot,
                                                          index = idx_Button,
                                                          path = self.tabname.AssayPath)
            self.dic_TabButtons[plot].Group = self.dic_TabButtons
            self.dic_TabButtons[plot].Notebook = self.sbk_Plots
            self.dic_TabButtons[plot].IsEnabled(True)
            self.szr_TabButtons.Add(self.dic_TabButtons[plot], 0, wx.ALL, 0)
            self.dic_Plots[plot] = self.dic_PlotOptions[plot](parent = self.sbk_Plots,
                                                             size = wx.Size(600,400),
                                                             tabname = self.tabname,
                                                             title = plot,
                                                             buttons = True)
            self.sbk_Plots.AddPage(self.dic_Plots[plot], plot, False)
            idx_Button += 1
        self.dic_TabButtons[self.lst_Plots[0]].IsCurrent(True)
        self.szr_Plots.Add(self.szr_TabButtons, 0, wx.ALL, 0)
        self.szr_Plots.Add(self.sbk_Plots, 0, wx.ALL, 0)

        self.szr_ReviewHorizontal.Add(self.szr_Plots, 0, wx.ALL, 5)
        self.szr_ReviewVertical.Add(self.szr_ReviewHorizontal, 0, wx.ALL, 5)

        self.SetSizer(self.szr_ReviewVertical)
        self.szr_ReviewVertical.Fit(self)
        self.Layout()

        # Binding
        self.lbc_Plates.Bind(wx.EVT_LIST_ITEM_SELECTED, self.UpdatePlots)

    def populate(self, noreturn = False):
        """
        Tries to populate the list control for the first time.

        Arguments:
            noreturn -> boolean. optional. Determines whether
                        to return success of populating as
                        boolean
        
        Returns:
            Boolean result of populating the tab.
        """
        try:
            self.lbc_Plates.DeleteAllItems()
            for i in self.tabname.assay_data.index:
                self.lbc_Plates.InsertItem(i,str(i+1))
                self.lbc_Plates.SetItem(i,1,
                        str(self.tabname.assay_data.loc[i,"Destination"]))
                self.lbc_Plates.SetItem(i,2,
                        str(self.tabname.assay_data.loc[i,"DataFile"]))
            # This will call UpdatePlots as it is bound to the selection event of the list
            self.lbc_Plates.Select(0)
            self.lbc_Plates.SetFocus()
            if noreturn == False:
                return True
        except:
            if noreturn == False:
                return False

    def UpdatePlots(self, event):
        """
        Event handler.
        General function to update the plots after clicking on an entry in lbc_Plates.
        Calls functions to update individual plots as required.

        Returns: -
        """
        # Get current selection
        plate = self.lbc_Plates.GetFirstSelected()
        if plate == -1:
            plate = 0
        # Check which plots are present and update accordingly
        for plot in self.lst_Plots:
            self.dic_PlotUpdateFunctions[plot](plate)

    def update_heatmap(self, plate):
        """
        Calls function in higher instance to prepare data for the plot.
        Also updates side panel with data quality metrics

        Arguments:
            plate -> integer type, index of the plate that has its data
                         represented by the heatmap.

        Returns: -
        """
        self.dic_Plots["Heat Map"].PlateIndex = plate
        self.dic_Plots["Heat Map"].data = self.tabname.prep_heatmap(plate)
        self.dic_Plots["Heat Map"].title = self.tabname.assay_data.iloc[plate,0]
        self.dic_Plots["Heat Map"].vmax = None
        self.dic_Plots["Heat Map"].vmin = None
        self.dic_Plots["Heat Map"].draw()

        references = self.tabname.assay_data.loc[plate,"References"]

        # Update plate details in plot's sidebar (Solvent, buffer and control well mean values):
        if pd.isna(references.loc["BufferMean",0]) == False:
            mean = round(references.loc["BufferMean",0],2)
            sem = round(references.loc["BufferSEM",0],2)
            self.dic_Plots["Heat Map"].lbl_BufferWells.SetLabel(f"{mean} {chr(177)} {sem}")
        else:
            self.dic_Plots["Heat Map"].lbl_BufferWells.SetLabel(u"N/A")
        if pd.isna(references.loc["SolventMean",0]) == False:
            mean = round(references.loc["SolventMean",0],2)
            sem = round(references.loc["SolventSEM",0],2)
            self.dic_Plots["Heat Map"].lbl_SolventWells.SetLabel(f"{mean} {chr(177)} {sem}")
        else:
            self.dic_Plots["Heat Map"].lbl_SolventWells.SetLabel(u"N/A")
        if pd.isna(references.loc["ControlMean",0]) == False:
            mean = round(references.loc["ControlMean",0],2)
            sem = round(references.loc["ControlSEM",0],2)
            self.dic_Plots["Heat Map"].lbl_ControlWells.SetLabel(f"{mean} {chr(177)} {sem}")
        else:
            self.dic_Plots["Heat Map"].lbl_ControlWells.SetLabel(u"N/A")
        if pd.isna(references.loc["ZPrimeMean",0]) == False:
            mean = round(references.loc["ZPrimeMean",0],3)
            median = round(references.loc["ZPrimeMedian",0],3)
            self.dic_Plots["Heat Map"].lbl_ZPrimeMean.SetLabel(f"{mean}")
            self.dic_Plots["Heat Map"].lbl_ZPrimeMedian.SetLabel(f"{median}")
            if pd.isna(references.loc["BufferMean",0]) == False:
                ratio = round(references.loc["BufferMean",0]/references.loc["ControlMean",0],2)
                self.dic_Plots["Heat Map"].lbl_BC.SetLabel(f"{ratio}")
            else:
                self.dic_Plots["Heat Map"].lbl_BC.SetLabel(u"N/A")
            if pd.isna(references.loc["SolventMean",0]) == False:
                ratio = round(references.loc["SolventMean",0]/references.loc["ControlMean",0],2)
                self.dic_Plots["Heat Map"].lbl_DC.SetLabel(f"{ratio}")
            else:
                self.dic_Plots["Heat Map"].lbl_DC.SetLabel(u"N/A")
        else:
            self.dic_Plots["Heat Map"].lbl_ZPrimeMean.SetLabel(u"N/A")
            self.dic_Plots["Heat Map"].lbl_ZPrimeMedian.SetLabel(u"N/A")
            self.dic_Plots["Heat Map"].lbl_BC.SetLabel(u"N/A")
            self.dic_Plots["Heat Map"].lbl_DC.SetLabel(u"N/A")

    def UpdateReplicateCorrelation(self, plate):
        """
        Calls function in higher instance to prepare data for the plot.

        Arguments:
            plate -> integer type, index of the plate that has its data
                         represented by the heatmap.

        Returns: -
        """
        self.dic_Plots["Replicate Correlation"].data = self.tabname.prep_scatterplot(plate)
        self.dic_Plots["Replicate Correlation"].draw()

    def UpdateScatterPlot(self, plate):
        """
        Calls function in higher instance to prepare data for the plot.

        Arguments:
            plate -> integer type, index of the plate that has its data
                         represented by the heatmap.

        Returns: -
        """
        self.dic_Plots["Scatter Plot"].data = self.tabname.prep_scatterplot(plate)
        self.dic_Plots["Scatter Plot"].draw()


##################################################
##                                              ##
##    #####   ##       ####   ######   #####    ##
##    ##  ##  ##      ##  ##    ##    ##        ##
##    #####   ##      ##  ##    ##     ####     ##
##    ##      ##      ##  ##    ##        ##    ##
##    ##      ######   ####     ##    #####     ##
##                                              ##
##################################################

class ELNPlots(wx.Panel):
    """
    Panel containing all plots for a page. Serves as summary figure for
    ELN page.
    """

    def __init__(self, notebook, tabname, shorthand):
        """
        Initialises class attributes.
        
        Arguments:
            notebook -> parent object for wxPython GUI building. In this
                        case, the notebook that this panel will reside in.
            tabname -> gets assigned to self.tabname. Reference to the
                       pnl_Project instance above this object (contains
                       any functions that might need to be called, objects
                       controlled, etc).
            shorthand -> string. Determines type of plot to use
        """
        wx.Panel.__init__ (self, parent = notebook, id = wx.ID_ANY,
                           pos = wx.DefaultPosition, size = wx.DefaultSize,
                           style = wx.TAB_TRAVERSAL, name = wx.EmptyString)

        self.tabname = tabname
        self.shorthand = shorthand

        self.SetBackgroundColour(cs.BgUltraLight)
        self.szr_ELNPlots = wx.BoxSizer(wx.VERTICAL)

        # Sizer to keep Scrolled Window
        self.szr_ELNPlots_Scroll = wx.BoxSizer(wx.VERTICAL)
        self.pnl_ELNPlots_Scroll = wx.ScrolledWindow(self, style = wx.HSCROLL|wx.VSCROLL)
        self.pnl_ELNPlots_Scroll.SetScrollRate(5, 5)

        self.szr_ELNPlots_Scroll.Add(self.pnl_ELNPlots_Scroll, 1, wx.ALL|wx.EXPAND, 5)
        self.szr_ELNPlots.Add(self.szr_ELNPlots_Scroll, 1, wx.EXPAND, 5)

        # Finalise
        self.SetSizer(self.szr_ELNPlots)
        self.Layout()
        # Fitting happens later.

    def populate(self, completecontainer):
        """
        Populates the tab with data from self.tabname.assay_data

        Arguments:
            completecontainer -> pandas dataframe. Contains all assay data.
        """
        #Cleanup if drawn before:
        for each in self.pnl_ELNPlots_Scroll.GetChildren():
            if each:
                each.Destroy()
        # Create lists and dictionaries to hold button/sizer/plot names and objects:
        int_Plates = len(completecontainer)
        self.lst_FigureNames = []
        lst_ClipNames = []
        lst_PNGNames = []
        lst_SzrNames = []
        lst_LineNames = []
        self.dic_Figures = {}
        self.dic_Clip = {}
        self.dic_PNG = {}
        self.dic_BtnSzrs = {}
        self.dic_Lines = {}
        for i in range(int_Plates):
            self.lst_FigureNames.append("fig_Plate_" + str(i+1))
            lst_ClipNames.append("btn_Clipboard_" + str(i+1))
            lst_PNGNames.append("btn_PNG_" + str(i+1))
            lst_SzrNames.append("szr_Plots_Btns_" + str(i+1))
            lst_LineNames.append("line_ELNPlots_" + str(i+1))
        # Create sizer in scroll window:
        self.szr_ELNPlots_Scroll = wx.BoxSizer(wx.VERTICAL)
        # Dimensions for plot: distance to top edge, height of subplots, distance between subplots in y direction:
        # Defaults:
        int_GridWidth = 4
        int_LabelSize = 8
        int_TitleSize = 10
        int_SuperTitleSize = 16
        distance_top_px = 90
        distance_supertitle_top_px = 20
        subplot_height_px = 90 #90
        subplot_distance_px = 92
        distance_bottom_px = 70
        dpi = 100
        # Change based on assay:
        if self.shorthand in ["NDSF","DSF","RATE"]:
            int_GridWidth = 6 # was 4
            int_LabelSize = 6
            int_TitleSize = 10
            int_SuperTitleSize = 16
            subplot_height_px = 70

        maximum = 0
        for plate in completecontainer.index:
            maximum += completecontainer.loc[plate,"Processed"].shape[0]

        self.dlg_progress = wx.ProgressDialog(title = u"Processing",
                                                      message = u"Drawing plots for ELN PAGE.",
                                                      maximum = maximum,
                                                      parent = self,
                                                      style = wx.PD_APP_MODAL|wx.PD_AUTO_HIDE)

        self.Freeze()
        count = 0
        for i in range(len(self.lst_FigureNames)):
            # Get Dimensions based on number of subplots:
            samples = completecontainer.loc[count,"Processed"].shape[0]
            int_GridHeight = int(math.ceil(samples/int_GridWidth))
            # Get absolute dimensions:
            total_height_px = distance_top_px + (int_GridHeight * subplot_height_px) + ((int_GridHeight - 1) * subplot_distance_px) + distance_bottom_px
            total_height_inch = total_height_px / dpi
            # Get relative dimesnions:
            hspace_ratio = subplot_height_px / total_height_px
            bottom_ratio = distance_bottom_px / total_height_px    
            top_ratio = 1 - (distance_top_px / total_height_px)
            supertitle_ratio = 1 - (distance_supertitle_top_px / total_height_px)
            # Create panel:
            self.dic_PlotType = {"EPDR":cp.PlotGridEPDR,"DSF":cp.PlotGridDSF,
                                 "AADR":cp.PlotGridEPDR,
                                 "NDSF":cp.PlotGridNDSF,"RATE":cp.PlotGridRATE,
                                 "DRTC":cp.PlotGridDRTC,"ERDR":cp.PlotGridDPandFit}
            self.dic_Figures[self.lst_FigureNames[i]] = self.dic_PlotType[self.shorthand](
                    self.pnl_ELNPlots_Scroll, total_height_px, total_height_inch, dpi)
            self.dic_Figures[self.lst_FigureNames[i]].draw(samples,completecontainer.loc[count,"Processed"],
                    completecontainer.loc[count,"Destination"],int_GridHeight,int_GridWidth,hspace_ratio,bottom_ratio,
                    top_ratio,total_height_px,int_SuperTitleSize,supertitle_ratio,int_TitleSize,int_LabelSize,self.dlg_progress)
            # Add panel to Plots sizer
            self.szr_ELNPlots_Scroll.Add(self.dic_Figures[self.lst_FigureNames[i]], 0, wx.ALL|wx.ALIGN_CENTER_HORIZONTAL, 5)
            # Create and add l
            self.dic_Lines[lst_LineNames[i]] = wx.StaticLine(self.pnl_ELNPlots_Scroll, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.LI_HORIZONTAL)
            self.szr_ELNPlots_Scroll.Add(self.dic_Lines[lst_LineNames[i]], 0, wx.ALL|wx.ALIGN_CENTER_HORIZONTAL, 5)
            # Create button bar sizer
            self.dic_BtnSzrs[lst_SzrNames[i]] = wx.BoxSizer(wx.HORIZONTAL)
            # Create clipboard button, bind command, add to button bar sizer
            self.dic_Clip[lst_ClipNames[i]] = btn.CustomBitmapButton(self.pnl_ELNPlots_Scroll,
                                                                     name = u"Clipboard",
                                                                     index = 5,
                                                                     size = (130,25))
            self.dic_Clip[lst_ClipNames[i]].myname = str(i) # add name to pass index on to function
            self.dic_Clip[lst_ClipNames[i]].Bind(wx.EVT_BUTTON, self.panelplot_to_clipboard)
            self.dic_BtnSzrs[lst_SzrNames[i]].Add(self.dic_Clip[lst_ClipNames[i]], 0, wx.ALL, 5)
            # Create PNG button, bind command, add to button bar sizer
            self.dic_PNG[lst_PNGNames[i]] = btn.CustomBitmapButton(self.pnl_ELNPlots_Scroll,
                                                                   name = u"ExportToFile",
                                                                   index = 5,
                                                                   size = (104,25))
            self.dic_PNG[lst_PNGNames[i]].myname = str(i) # add name to pass index on to function
            self.dic_PNG[lst_PNGNames[i]].Bind(wx.EVT_BUTTON, self.panelplot_to_png)
            self.dic_BtnSzrs[lst_SzrNames[i]].Add(self.dic_PNG[lst_PNGNames[i]], 0, wx.ALL, 5)
            # Add button bar sizer to plots sizer
            self.szr_ELNPlots_Scroll.Add(self.dic_BtnSzrs[lst_SzrNames[i]], 0, wx.ALIGN_RIGHT, 5)

            count += 1
            # DON'T UPDATE PROGRESS DIALOG HERE, IT GETS UPDATED IN THE
            # draw METHOD CALLED FOR EACH FIGURE
        self.dlg_progress.Pulse()
        self.pnl_ELNPlots_Scroll.SetSizer(self.szr_ELNPlots_Scroll)
        self.szr_ELNPlots_Scroll.Fit(self.pnl_ELNPlots_Scroll)
        #self.pnl_ELNPlots.Layout()
        self.Layout()
        self.Update()
        self.tabname.bol_ELNPlotsDrawn = True
        self.Thaw()
        self.dlg_progress.Destroy()

    # 5.2 Copy a plot to the clipboard
    def panelplot_to_clipboard(self,event):
        """
        Event handler. Calls plot's plot_to_clipboard function.
        """
        self.dic_Figures[self.lst_FigureNames[int(event.GetEventObject().myname)]].plot_to_clipboard()

    # 5.3 Save a plot as a PNG file 
    def panelplot_to_png(self,event):
        """
        Event handler. Calls plot's plot_to_png function.
        """
        self.dic_Figures[self.lst_FigureNames[int(event.GetEventObject().myname)]].plot_to_png()


##########################################################################
##                                                                      ##
##    #####    ####   ######   ####   #####    ####    #####  ######    ##
##    ##  ##  ##  ##    ##    ##  ##  ##  ##  ##  ##  ##      ##        ##
##    ##  ##  ######    ##    ######  #####   ######   ####   ####      ##
##    ##  ##  ##  ##    ##    ##  ##  ##  ##  ##  ##      ##  ##        ##
##    #####   ##  ##    ##    ##  ##  #####   ##  ##  #####   ######    ##
##                                                                      ##
##########################################################################

class ExportToFileMenu(wx.Menu):
    """
    Menu to select file type to export to
    """
    def __init__(self, parent):
        super(ExportToFileMenu, self).__init__()

        self.parent = parent

        real_path = os.path.realpath(__file__)
        dir_path = os.path.dirname(real_path)
        str_MenuIconsPath = dir_path + r"\menuicons"

        self.mi_Excel = wx.MenuItem(self, wx.ID_ANY, u"Excel (.xlsx)", wx.EmptyString, wx.ITEM_NORMAL)
        #self.mi_Excel.SetBitmap(wx.Bitmap(str_MenuIconsPath + u"\Excel.ico"))
        self.Append(self.mi_Excel)
        self.Bind(wx.EVT_MENU, self.export_excel, self.mi_Excel)
        self.mi_CSV = wx.MenuItem(self, wx.ID_ANY, u"Comma separated values (.csv)", wx.EmptyString, wx.ITEM_NORMAL)
        #self.mi_CSV.SetBitmap(wx.Bitmap(str_MenuIconsPath + u"\CSV.ico"))
        self.Append(self.mi_CSV)
        self.Bind(wx.EVT_MENU, self.export_csv, self.mi_CSV)
        if self.parent.tabname.details["Shorthand"] == "EPDR":
            self.AppendSeparator()
            self.mi_Dotmatics = wx.MenuItem(self, wx.ID_ANY, u"Dotmatics compatible (.xlsx)", wx.EmptyString, wx.ITEM_NORMAL)
            #self.mi_Dotmatics.SetBitmap(wx.Bitmap(str_MenuIconsPath + u"\Dotmatics.ico"))
            self.Append(self.mi_Dotmatics)
            self.Bind(wx.EVT_MENU, self.export_dotmatics, self.mi_Dotmatics)

    def export_excel(self, event):
        self.parent.export_to_excel()

    def export_csv(self, event):
        self.parent.export_to_csv()

    def export_dotmatics(self, event):
        self.parent.export_to_dotmatics()

class ExportTable(wx.Panel):
    """
    Panel with a wx.grid.Grid. Contains experimental data formatted for upload
    to database.
    """

    def __init__(self, notebook, tabname, use_db = False,
                 db_table = None,
                 db_dependencies = None):
        """
        Initialises class attributes.
        
        Arguments:
            notebook -> parent object for wxPython GUI building. In this
                        case, the notebook that this panel will reside in.
            tabname -> gets assigned to self.tabname. Reference to the
                       pnl_Project instance above this object (contains
                       any functions that might need to be called, objects
                       controlled, etc).
        """
        wx.Panel.__init__ (self, parent=notebook, id = wx.ID_ANY,
                           pos = wx.DefaultPosition, size = wx.DefaultSize,
                           style = wx.TAB_TRAVERSAL, name = wx.EmptyString)

        self.tabname = tabname

        self.SetBackgroundColour(cs.BgUltraLight)

        # Start Building
        self.szr_Export = wx.BoxSizer(wx.VERTICAL)
        self.szr_Grid = wx.BoxSizer(wx.VERTICAL)

        # Button Bar
        self.szr_Export_ButtonBar = wx.BoxSizer(wx.VERTICAL)
        self.szr_Export_Buttons = wx.BoxSizer(wx.HORIZONTAL)
        if use_db == True:
            #self.btn_Verify = wx.Button(self,
            #                            label = u"Verify")
            #self.btn_Verify.Bind(wx.EVT_BUTTON, self.verify_db)
            #self.szr_Export_Buttons.Add(self.btn_Verify, 0, wx.ALL, 5)
            self.btn_Upload = btn.CustomBitmapButton(self,
                                                    name = u"UploadToDatabase",
                                                    index = 0,
                                                    size = (142,25))
            self.btn_Upload.Bind(wx.EVT_BUTTON, lambda x: self.upload_to_db(x,
                                                                            True,
                                                                            db_table,
                                                                            db_dependencies))
            self.szr_Export_Buttons.Add(self.btn_Upload, 0, wx.ALL, 5)
        self.btn_Clipboard = btn.CustomBitmapButton(self,
                                                    name = u"Clipboard",
                                                    index = 0,
                                                    size = (130,25))
        self.btn_Clipboard.Bind(wx.EVT_BUTTON, self.copy_to_clipboard)
        self.szr_Export_Buttons.Add(self.btn_Clipboard, 0, wx.ALL, 5)
        self.btn_Export = btn.CustomBitmapButton(self,
                                                 name = u"ExportToFile",
                                                 index = 0,
                                                 size = (104,25))
        self.btn_Export.Bind(wx.EVT_BUTTON, self.export_to_file)
        self.szr_Export_Buttons.Add(self.btn_Export, 0, wx.ALL, 5)
        self.szr_Export_ButtonBar.Add(self.szr_Export_Buttons, 0, wx.ALIGN_LEFT, 5)
        self.szr_Export.Add(self.szr_Export_ButtonBar, 0, wx.EXPAND, 5)

        # Gridl - Database
        self.grd_Database = wx.grid.Grid(self)
        self.szr_Grid.Add(self.grd_Database, 1, wx.ALL|wx.EXPAND, 5)
        self.szr_Grid.Fit(self.grd_Database)
        self.szr_Export.Add(self.szr_Grid, 1, wx.EXPAND, 5)


        # Finalise
        self.SetSizer(self.szr_Export)
        self.Layout()

        # Binding
        self.grd_Database.Bind(wx.EVT_KEY_DOWN, on_key_press_grid)
        self.grd_Database.Bind(wx.grid.EVT_GRID_SELECT_CELL, SingleSelection)
        self.grd_Database.Bind(wx.grid.EVT_GRID_CELL_RIGHT_CLICK, self.OpenCopyOnlyContextMenu)

    def populate(self, dbf_function = None, noreturn = False, kwargs = {}):
        """
        Populates Export tab. Calls thread to do this so that progress
        bar dialog can be updated from within the thread.
        """
        self.dlg_progress = wx.ProgressDialog(title = u"Processing",
                                                      message = u"Populating results table for database upload.",
                                                      maximum = 100,
                                                      parent = self,
                                                      style = wx.PD_APP_MODAL|wx.PD_AUTO_HIDE)
        thd_PopulateDatabase = threading.Thread(target=self.populate_thread, args=(dbf_function, kwargs,), daemon=True)
        thd_PopulateDatabase.start()
        if noreturn == False:
            return True

    def populate_thread(self, dbf_function, kwargs):
        """
        Thread for populating the export tab.
        """
        colnames = kwargs["colnames"]
        self.tabname.dfr_Database = pd.DataFrame(columns=colnames)
        # Create Database dataframe in sections for each plate and append
        for plate in self.tabname.assay_data.index:
            dfr_Partial = dbf_function(plate,kwargs)
            frames = [self.tabname.dfr_Database, dfr_Partial]
            self.tabname.dfr_Database = pd.concat(frames, ignore_index=True)

        # Create grid:
        self.int_Samples = self.tabname.dfr_Database.shape[0]
        self.dlg_progress.SetRange(self.tabname.dfr_Database.shape[0])
        self.Freeze()

        if self.grd_Database.GetNumberRows() > 0:
            self.grd_Database.DeleteRows(0, self.grd_Database.GetNumberRows())
            self.grd_Database.AppendRows(self.int_Samples, True)
        else:
            self.grd_Database.CreateGrid(self.int_Samples, len(colnames))
            # Grid
            self.grd_Database.EnableEditing(False)
            self.grd_Database.EnableGridLines(True)
            self.grd_Database.EnableDragGridSize(False)
            self.grd_Database.SetMargins(0, 0)
            # Columns
            self.grd_Database.AutoSizeColumns()
            self.grd_Database.EnableDragColMove(False)
            self.grd_Database.EnableDragColSize(True)
            self.grd_Database.SetColLabelSize(20)
            for i in range(len(colnames)):
                self.grd_Database.SetColLabelValue(i,colnames[i])
            self.grd_Database.SetColLabelAlignment(wx.ALIGN_CENTER, wx.ALIGN_CENTER)
            # Rows
            self.grd_Database.EnableDragRowSize(True)
            self.grd_Database.SetRowLabelSize(30)
            self.grd_Database.SetRowLabelAlignment(wx.ALIGN_CENTER, wx.ALIGN_CENTER)
            # Label Appearance
            # Cell Defaults
            self.grd_Database.SetDefaultCellAlignment(wx.ALIGN_LEFT, wx.ALIGN_TOP)
            self.grd_Database.SetGridLineColour(cs.BgMediumDark)
            self.grd_Database.SetDefaultCellBackgroundColour(cs.BgUltraLight)
        # Populate grid:
        for row in range(self.grd_Database.GetNumberRows()):
            # colouring just takes too long for long data sets. But this is how you would do it.
            #if row % 2 == 0:
            #    clr_Background = cs.BgLight
            #else:
            #    clr_Background = cs.BgUltraLight
            for col in range(self.grd_Database.GetNumberCols()):
                cell = self.tabname.dfr_Database.iloc[row,col]
                if not pd.isna(cell):
                    self.grd_Database.SetCellValue(row,col,str(cell))
                else:
                    self.grd_Database.SetCellValue(row,col,"")
                #self.grd_Database.SetCellBackgroundColour(idx_Sample,col,clr_Background)
            self.dlg_progress.Update(row)

        self.grd_Database.AutoSizeColumns()
        self.grd_Database.Refresh()
        self.Thaw()
        self.dlg_progress.Destroy()
        self.tabname.bol_ExportPopulated = True

    def copy_to_clipboard(self, event):
        """
        Event handler. copies data in dfr_Database to clipboard.
        """
        self.tabname.dfr_Database.to_clipboard(header=None, index=False)

    def export_to_file(self, event = None):
        self.PopupMenu(ExportToFileMenu(self))

    def export_to_excel(self, event = None):
        """
        Event handler. Exports data in dfr_Database to Excel.
        """
        fdlg = wx.FileDialog(self, "Save results as",
                             wildcard="Excel workbook (*.xlsx)|*.xlsx",
                             style=wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT)
        if fdlg.ShowModal() == wx.ID_OK:
            str_SavePath = fdlg.GetPath()
            # Check if str_SavePath ends in .csv. If so, remove
            if str_SavePath[-1:-5] == ".xlsx":
                str_SavePath = str_SavePath[:len(str_SavePath)]
            try:
                self.tabname.dfr_Database.to_excel(str_SavePath)
                msg.info_save_success()
            except PermissionError:
                msg.warn_permission_denied()

    def export_to_csv(self, event = None):
        """
        Event handler. Exports data in dfr_Database to csv.
        """
        fdlg = wx.FileDialog(self, "Save results as",
                             wildcard="CSV (*.csv)|*.csv",
                             style=wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT)
        if fdlg.ShowModal() == wx.ID_OK:
            str_SavePath = fdlg.GetPath()
            # Check if str_SavePath ends in .csv. If so, remove
            if str_SavePath[-1:-5] == ".csv":
                str_SavePath = str_SavePath[:len(str_SavePath)]
            try:
                self.tabname.dfr_Database.to_csv(str_SavePath)
                msg.info_save_success()
            except PermissionError:
                msg.warn_permission_denied()

    def upload_to_db(self,
                     event = None,
                     main_thread = True,
                     db_table = None,
                     db_dependencies = None):
        """
        Upload processed results to database.
        Perform verification first if not done already.
        """
        if self.tabname.parent.db_connection is None:
            do_connect = msg.query_connect_db()
            if do_connect == True:
                self.tabname.parent.toggle_db_connection()
            else:
                # User chose to cancel
                return False
        
        if self.tabname.dfr_Upload.shape[0] > 0:
            # dfr_Upload can only have shape[0] > 0 if data has been
            # verified
            if self.tabname.uploaded == False:
                self.start_upload(main_thread, db_table)
            else:
                anyway = wx.MessageBox(message = u"The results you are trying to upload have been marked as uploaded previoysly."
                                                 + u"\n Would you like to upload them anyway?",
                                        caption = u"Previously uploaded",
                                        style = wx.YES_NO|wx.ICON_WARNING)
                if anyway == wx.YES:
                    self.start_upload(main_thread, db_table)
        else:
            self.verify_db(event = None,
                           uploadafter = True,
                           db_table = db_table,
                           db_dependencies = db_dependencies)

    def verify_db(self, event = None, uploadafter = False, db_table = None, db_dependencies = None):
        """
        Verifies whether database dataframe can be uploaded to database.
        Criteria may differ from assay to assay.
        """
        if self.tabname.parent.db_connection is None:
            do_connect = msg.query_connect_db()
            if do_connect == True:
                self.tabname.parent.toggle_db_connection()
            else:
                # User chose to cancel
                return False
    
        self.dlg_progress = wx.ProgressDialog(title = u"Processing records",
                                              message = u"Verifying connections to other records and tables in database.",
                                              parent = self,
                                              style = wx.PD_APP_MODAL)
        self.dlg_progress.Pulse()
        thd_verifying = threading.Thread(target = self.tabname.db_df_verify,
                                         args = (self,
                                                 self.tabname.parent.db_connection.conn,
                                                 db_table,
                                                 db_dependencies,
                                                 uploadafter,),
                                         daemon = True)
        thd_verifying.start()

    def verified(self, success, db_table = None, db_dependencies = None, uploadafter = False):
        """
        FNORD
        """                    
        if success == True:
            if uploadafter == True:
                self.upload_to_db(event = None,
                                  main_thread = False,
                                  db_table = db_table,
                                  db_dependencies = db_dependencies)
            else:
                msg.info_all_verified()
        else:
            msg.info_some_not_verified()
            if hasattr(self, "dlg_progress"):
                self.dlg_progress.Destroy()

    def start_upload(self, main_thread, db_table):
        """
        Calls the upload method in the tab.
        Takes into account that we might be within a thread already:
        verifying -> uploading

        Arguments:
            main_thread -> bool. Whether or not this is called from
                           within a thread that is not the main thread.
        """
        if main_thread == True:
            self.dlg_progress = wx.ProgressDialog(title = u"Processing records",
                                                  message = u"Uploading records into database. This may take a while.",
                                                  parent = self,
                                                  style = wx.PD_APP_MODAL)
            self.dlg_progress.Pulse()
            thd_uploading = threading.Thread(target = self.tabname.db_upload,
                                             args = (self,
                                                     self.tabname.parent.db_connection.conn,
                                                     db_table),
                                             daemon = True)
            thd_uploading.start()
        else:
            # progress dialog already exists in this condition
            self.dlg_progress.Update(value = 0, 
                                     newmsg = u"Uploading records into database. This may take a while.")
            self.dlg_progress.Pulse()
            self.tabname.db_upload(self,
                                   self.tabname.parent.db_connection.conn,
                                   db_table)

    def uploaded(self, upload):
        """
        Helperfunction to display outcome of upload attempt.
        """
        if type(upload) == str:
            msg.warn_upload_failure(upload)
        else:
            msg.info_upload_success(upload)

    def Clear(self):
        """
        Clears the entire grid.
        """
        self.grd_Database.ClearGrid()

    def OpenCopyOnlyContextMenu(self, event):
        """
        Event handler: launcehs context menu after right click on grid.
        """
        self.PopupMenu(CopyOnlyContextMenu(event, event.GetEventObject()))

    def export_to_dotmatics(self):
        """
        Special case to prepare data for clipboard for
        specific customer.
        """

        Date = datetime.now()

        lst_Minima = []
        lst_Maxima = []
        lst_pEC50 = []
        lst_Span = []
        lst_ZPrimeMean = []
        lst_ZPrimeRobust = []
        lst_BufferToControl = []
        lst_DmsoToControl = []
        lst_Concentration = []
        lst_Empty = []
        lst_Comment = []
        lst_Validation = []
        lst_Date = []
        for smpl in self.tabname.dfr_Database.index:
            lst_Inhibitions = [self.tabname.dfr_Database.iloc[smpl,28],
                               self.tabname.dfr_Database.iloc[smpl,31],
                               self.tabname.dfr_Database.iloc[smpl,34],
                               self.tabname.dfr_Database.iloc[smpl,37],
                               self.tabname.dfr_Database.iloc[smpl,40],
                               self.tabname.dfr_Database.iloc[smpl,43],
                               self.tabname.dfr_Database.iloc[smpl,46],
                               self.tabname.dfr_Database.iloc[smpl,49],
                               self.tabname.dfr_Database.iloc[smpl,52],
                               self.tabname.dfr_Database.iloc[smpl,55],
                               self.tabname.dfr_Database.iloc[smpl,58],
                               self.tabname.dfr_Database.iloc[smpl,61],
                               self.tabname.dfr_Database.iloc[smpl,64],
                               self.tabname.dfr_Database.iloc[smpl,67],
                               self.tabname.dfr_Database.iloc[smpl,70],
                               self.tabname.dfr_Database.iloc[smpl,73]]
            for inh in range(len(lst_Inhibitions)):
                if lst_Inhibitions[inh] == "":
                    lst_Inhibitions[inh] = np.nan
            lst_Minima.append(np.nanmin(lst_Inhibitions))
            lst_Maxima.append(np.nanmax(lst_Inhibitions))
            lst_pEC50.append((-1)*self.tabname.dfr_Database.iloc[smpl,13])
            lst_Span.append(float(self.tabname.dfr_Database.iloc[smpl,21]) - float(self.tabname.dfr_Database.iloc[smpl,20]))
            lst_Concentration.append(self.tabname.dfr_Database.iloc[smpl,27])
            lst_ZPrimeMean.append(self.tabname.dfr_Database.iloc[smpl,79])
            lst_ZPrimeRobust.append(self.tabname.dfr_Database.iloc[smpl,80])
            lst_BufferToControl.append(self.tabname.dfr_Database.iloc[smpl,81])
            lst_DmsoToControl.append(self.tabname.dfr_Database.iloc[smpl,82])
            lst_Empty.append("")
            if lst_Maxima[smpl] >= 80:
                lst_Comment.append("ACTMax >= 80%")
                lst_Validation.append("A")
            elif lst_Maxima[smpl] >= 50:
                lst_Comment.append("50% =< ACTMax < 80%")
                lst_Validation.append("A")
            else:
                lst_Comment.append("ACTMax < 50%")
                lst_Validation.append("NA")
            lst_Date.append(Date)

        df = pd.DataFrame(data={"Global Compound ID":self.tabname.dfr_Database.iloc[:,4],"Purification ID":self.tabname.dfr_Database.iloc[:,1],
            "Compound comments":lst_Concentration,"":lst_Empty,"Result_ID":lst_Empty,"Evotec Compound ID":lst_Empty,"Evotec Batch ID":lst_Empty,"Validation":lst_Validation,
            "ACTMin":lst_Minima,"ACTMax":lst_Maxima,"Operator":lst_Empty,"EC50":self.tabname.dfr_Database.iloc[:,15],"CI-Lower":self.tabname.dfr_Database.iloc[:,17],
            "CI-Upper":self.tabname.dfr_Database.iloc[:,16],"Operator negative":lst_Empty,"pEC50":lst_pEC50,"Bottom":self.tabname.dfr_Database.iloc[:,20],
            "Top":self.tabname.dfr_Database.iloc[:,21],"Hill Slope":self.tabname.dfr_Database.iloc[:,18],"Span":lst_Span,"R2":self.tabname.dfr_Database.iloc[:,22],"Comment":lst_Comment,
            "ZPrime":lst_ZPrimeMean,"ZPrimeRobust":lst_ZPrimeRobust,"BufferToControl":lst_BufferToControl,"DMSOToControl":lst_DmsoToControl,"DateOfReport":lst_Date})

        fdlg = wx.FileDialog(self,
                             "Save results as",
                             wildcard="Excel files (*.xlsx)|*.xlsx",
                             style=wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT)
        if fdlg.ShowModal() == wx.ID_OK:
            str_SavePath = fdlg.GetPath()
            str_SaveDir = fdlg.GetDirectory()
            # Check if str_SavePath ends in .csv. If so, remove
            if str_SavePath[-1:-5] == ".xlsx":
                str_SavePath = str_SavePath[:len(str_SavePath)]
            try:
                df.to_excel(str_SavePath)
                bol_SaveSuccesful = True
            except PermissionError:
                msg.warn_permission_denied()
                bol_SaveSuccesful = False
                return None
        else:
            return None

        if bol_SaveSuccesful == True:
            wbk_Export = load_workbook(str_SavePath)
            wks_Export = wbk_Export.active
            lst_Columns = df.columns.to_list()
            for cell in range(len(lst_Columns)):
                int_Letters = len(lst_Columns[cell])
                if cell < 25: # Account for +1 offset!
                    str_Column = chr(cell+65+1)
                else:
                    str_Column = "A" + chr(cell+65-26+1)
                if int_Letters > 0:
                    wks_Export.column_dimensions[str_Column].width = int_Letters*1.23
            # Column with dose response plot: Automatically get last column,
            # regardless of how many columns there are:
            int_PlotColumn = len(lst_Columns)
            if int_PlotColumn < 24: # Account for +1 offset!
                str_PlotColumn = chr(int_PlotColumn+65+1)
            else:
                str_PlotColumn = "A" + chr(int_PlotColumn+65-26+1)
            if self.tabname.details["AssayCategory"] == "dose_response":
                self.dlg_progress = wx.ProgressDialog(title = u"Processing records",
                                                      message = u"Preparing Dotmatics report for export..",
                                                      maximum = self.tabname.dfr_Database.shape[0],
                                                      parent = self,
                                                      style = wx.PD_APP_MODAL|wx.PD_AUTO_HIDE)
                self.Freeze()
                wks_Export.column_dimensions[str_PlotColumn].width = 84
                # Draw the plots
                int_XLRow = 2 # starts on second row
                count = 0
                lst_Temppaths = []
                for plate in self.tabname.assay_data.index:
                    for smple in self.tabname.assay_data.loc[plate,"Processed"].index:
                        # Export plot to temporary file
                        tempplot = cp.CurvePlotPanel(self, (600,450), self)
                        tempplot.data = self.tabname.assay_data.loc[plate,"Processed"].loc[smple]
                        tempplot.draw(virtualonly=True)
                        str_SamplePlot = str(count) + ".png"
                        str_Temppath = os.path.join(str_SaveDir,str_SamplePlot)
                        lst_Temppaths.append(str_Temppath)
                        # I had explored the idea of just writing the file into a PIL.Image object, but that threw an error. The below should work fast enough.
                        tempplot.figure.savefig(str_Temppath, dpi=None, facecolor="w",
                                                edgecolor="w", orientation="portrait",
                                                format=None, transparent=False,
                                                bbox_inches=None, pad_inches=0.1)
                        opxl_Plot_ImageObject = openpyxl.drawing.image.Image(str_Temppath)
                        wks_Export.add_image(opxl_Plot_ImageObject,str_PlotColumn+str(int_XLRow))
                        # Destroy tempplot and delete tempplot.png
                        tempplot.Destroy()
                        wks_Export.row_dimensions[int_XLRow].height = 340
                        int_XLRow += 1
                        count += 1
                        self.dlg_progress.Update(value = count)
                wbk_Export.save(str_SavePath)
                # Deleting temp files. Deleting temp files just after they've
                # been handed to add_image() or after saving the spreadsheet didn't
                # quite work. They need to be present so that the save function
                # can find them.
                for i in range(len(lst_Temppaths)):
                    if os.path.exists(lst_Temppaths[i]):
                        os.remove(lst_Temppaths[i])
                self.dlg_progress.Destroy()
                self.Thaw()
                msg.info_save_success()
                


################################################################################
##                                                                            ##
##    #####   ##       ####   ######  ######      ##    ##   ####   #####     ##
##    ##  ##  ##      ##  ##    ##    ##          ###  ###  ##  ##  ##  ##    ##
##    #####   ##      ######    ##    ####        ########  ######  #####     ##
##    ##      ##      ##  ##    ##    ##          ## ## ##  ##  ##  ##        ##
##    ##      ######  ##  ##    ##    ######      ##    ##  ##  ##  ##        ##
##                                                                            ##
################################################################################

class PlateMapForDatabase(wx.Panel):
    """
    Panel containing a table (Wx.grid.Grid) for the map of the assay plate.
    """
    def __init__(self, notebook, tabname):
        """
        Initialises class attributes.
        
        Arguments:
            notebook -> parent object for wxPython GUI building. In this
                        case, the notebook that this panel will reside in.
            tabname -> gets assigned to self.tabname. Reference to the
                       pnl_Project instance above this object (contains
                       any functions that might need to be called, objects
                       controlled, etc).
        """
        wx.Panel.__init__ (self, parent = notebook, id = wx.ID_ANY,
                           pos = wx.DefaultPosition, size = wx.DefaultSize,
                           style = wx.TAB_TRAVERSAL, name = wx.EmptyString)

        self.tabname = tabname

        self.SetBackgroundColour(cs.BgUltraLight)

        # Start Building
        self.szr_Export = wx.BoxSizer(wx.VERTICAL)
        self.szr_Grid = wx.BoxSizer(wx.VERTICAL)

        # Prepare grid to populate later
        self.grd_PlateMap = wx.grid.Grid(self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, 0)
        self.szr_Grid.Add(self.grd_PlateMap, 1, wx.ALL|wx.EXPAND, 5)
        self.szr_Grid.Fit(self.grd_PlateMap)
        self.szr_Export.Add(self.szr_Grid, 1, wx.EXPAND, 5)

        # Button Bar
        self.szr_Export_ButtonBar = wx.BoxSizer(wx.VERTICAL)
        self.szr_Export_Buttons = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_Clipboard = btn.CustomBitmapButton(self,
                                                    name = u"Clipboard",
                                                    index = 0,
                                                    size = (130,25))
        self.btn_Clipboard.Bind(wx.EVT_BUTTON, self.copy_to_clipboard)
        self.szr_Export_Buttons.Add(self.btn_Clipboard, 0, wx.ALL, 5)
        self.btn_Export = btn.CustomBitmapButton(self,
                                                 name = u"ExportToFile",
                                                 index = 0,
                                                 size = (104,25))
        self.btn_Export.Bind(wx.EVT_BUTTON, self.export_to_file)
        self.szr_Export_Buttons.Add(self.btn_Export, 0, wx.ALL, 5)
        self.szr_Export_ButtonBar.Add(self.szr_Export_Buttons, 0, wx.ALIGN_RIGHT, 5)
        self.szr_Export.Add(self.szr_Export_ButtonBar, 0, wx.EXPAND, 5)

        # Finalise
        self.SetSizer(self.szr_Export)
        self.Layout()

        # Binding
        self.grd_PlateMap.Bind(wx.EVT_KEY_DOWN, on_key_press_grid)
        self.grd_PlateMap.Bind(wx.grid.EVT_GRID_SELECT_CELL, SingleSelection)
        self.grd_PlateMap.Bind(wx.grid.EVT_GRID_CELL_RIGHT_CLICK, self.OpenCopyOnlyContextMenu)

    def export_to_file(self, event):
        """
        Event handler. Exports data in dfr_DatabasePlateMap to csv.
        """
        fdlg = wx.FileDialog(self, "Save results as",
                             wildcard="Comma separated files (*.csv)|*.csv",
                             style=wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT)
        if fdlg.ShowModal() == wx.ID_OK:
            str_SavePath = fdlg.GetPath()
            # Check if str_SavePath ends in .csv. If so, remove
            if str_SavePath[-1:-4] == ".csv":
                str_SavePath = str_SavePath[:len(str_SavePath)]
            try:
                self.tabname.dfr_DatabasePlateMap.to_csv(str_SavePath)
                msg.info_save_success()
            except PermissionError:
                msg.warn_permission_denied()

    def copy_to_clipboard(self, event):
        """
        Event handler. copies data in dfr_DatabasePlateMap to clipboard.
        """
        try:
            self.tabname.dfr_DatabasePlateMap.to_clipboard(header=None, index=False)
        except:
            msg.warn_clipboard_error()

    def populate(self):
        """
        Populates tab from dataframe(s) in higher instance.
        Does this via running a second function in a thread to enable
        a progress bar dialog.
        """
        self.dlg_progress = wx.ProgressDialog(title = u"Processing",
                                                      message = u"Populating plate map table.",
                                                      maximum = 100,
                                                      parent = self,
                                                      style = wx.PD_APP_MODAL|wx.PD_AUTO_HIDE)
        thd_PopulatePlateMap = threading.Thread(target=self.populate_thread, args=(), daemon=True)
        thd_PopulatePlateMap.start()

    def populate_thread(self):
        """
        Gathers data from dataframe(s) to populate the grid/table on
        this panel.
        """
        self.Freeze()
        self.tabname.dfr_DatabasePlateMap = pd.DataFrame(columns=self.tabname.lst_PlateMapHeaders)
        # Create Database dataframe in sections for each plate and append
        for plate in self.tabname.assay_data.index:
            dfr_Partial = df.create_Database_frame_DSF_Platemap(self.tabname.details,self.tabname.lst_PlateMapHeaders,
                self.tabname.assay_data.loc[plate,"Processed"],self.tabname.dfr_Layout.loc[plate])
            frames = [self.tabname.dfr_DatabasePlateMap, dfr_Partial]
            self.tabname.dfr_DatabasePlateMap = pd.concat(frames, ignore_index=False)
        self.dlg_progress.SetRange(self.tabname.dfr_DatabasePlateMap.shape[0])
        # Create grid:
        self.int_Samples = self.tabname.dfr_DatabasePlateMap.shape[0]
        #self.grd_PlateMap = wx.grid.Grid(self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, 0)
        # Grid
        self.grd_PlateMap.CreateGrid(self.int_Samples, len(self.tabname.lst_PlateMapHeaders))
        self.grd_PlateMap.EnableEditing(False)
        self.grd_PlateMap.EnableGridLines(True)
        self.grd_PlateMap.EnableDragGridSize(False)
        self.grd_PlateMap.SetMargins(0, 0)
        # Columns
        self.grd_PlateMap.AutoSizeColumns()
        self.grd_PlateMap.EnableDragColMove(False)
        self.grd_PlateMap.EnableDragColSize(True)
        self.grd_PlateMap.SetColLabelSize(20)
        for i in range(len(self.tabname.lst_PlateMapHeaders)):
            self.grd_PlateMap.SetColLabelValue(i,self.tabname.lst_PlateMapHeaders[i])
        self.grd_PlateMap.SetColLabelAlignment(wx.ALIGN_CENTER, wx.ALIGN_CENTER)
        # Rows
        self.grd_PlateMap.EnableDragRowSize(True)
        self.grd_PlateMap.SetRowLabelSize(30)
        self.grd_PlateMap.SetRowLabelAlignment(wx.ALIGN_CENTER, wx.ALIGN_CENTER)
        # Label Appearance
        # Cell Defaults
        self.grd_PlateMap.SetDefaultCellAlignment(wx.ALIGN_LEFT, wx.ALIGN_TOP)
        self.grd_PlateMap.SetGridLineColour(cs.BgMediumDark)
        self.grd_PlateMap.SetDefaultCellBackgroundColour(cs.BgUltraLight)
        # Populate grid:
        for smpl in range(self.grd_PlateMap.GetNumberRows()):
            for col in range(self.grd_PlateMap.GetNumberCols()):
                self.grd_PlateMap.SetCellValue(smpl,col,str(self.tabname.dfr_DatabasePlateMap.iloc[smpl,col]))
            self.dlg_progress.Update(smpl)

        self.grd_PlateMap.AutoSizeColumns()
        self.Thaw()
        self.dlg_progress.Destroy()
        self.tabname.bol_PlateMapPopulated = True

    def Clear(self):
        """
        Clears the entire grid.
        """
        self.grd_PlateMap.Clear()

    def OpenCopyOnlyContextMenu(self, event):
        """
        Event handler. Opens context menu after right click on grid.
        """
        self.PopupMenu(CopyOnlyContextMenu(event, event.GetEventObject()))

###########################


class CopyOnlyContextMenu(wx.Menu):
    """
    Context menu to copy from the event generating  grid.
    """
    def __init__(self, rightclick, grid):
        super(CopyOnlyContextMenu, self).__init__()

        real_path = os.path.realpath(__file__)
        dir_path = os.path.dirname(real_path)
        str_MenuIconsPath = dir_path + r"\menuicons"

        self.Grid = grid
        self.mi_Copy = wx.MenuItem(self, wx.ID_ANY, u"Copy", wx.EmptyString, wx.ITEM_NORMAL)
        self.mi_Copy.SetBitmap(wx.Bitmap(str_MenuIconsPath + u"\Copy.ico"))
        self.Append(self.mi_Copy)
        self.Bind(wx.EVT_MENU, self.Copy, self.mi_Copy)

    def Copy(self, event):
        """
        Event handler. Gets list of selected cells and copies the
        contents to clipboard.
        """
        lst_Selection = get_grid_selection(self.Grid)
        if len(lst_Selection) > 0:
            dfr_Copy = pd.DataFrame()
            for i in range(len(lst_Selection)):
                dfr_Copy.at[lst_Selection[i][0],lst_Selection[i][1]] = self.Grid.GetCellValue(lst_Selection[i][0],lst_Selection[i][1])
            dfr_Copy.to_clipboard(header=None, index=False)


################################################################################################################################
##                                                                                                                            ##
##     #####  ##  ##   ####   #####   ######  #####     ######  ##  ##  ##  ##   #####  ######  ##   ####   ##  ##   #####    ##
##    ##      ##  ##  ##  ##  ##  ##  ##      ##  ##    ##      ##  ##  ### ##  ##        ##    ##  ##  ##  ### ##  ##        ##
##     ####   ######  ######  #####   ####    ##  ##    ####    ##  ##  ######  ##        ##    ##  ##  ##  ######   ####     ##
##        ##  ##  ##  ##  ##  ##  ##  ##      ##  ##    ##      ##  ##  ## ###  ##        ##    ##  ##  ##  ## ###      ##    ##
##    #####   ##  ##  ##  ##  ##  ##  ######  #####     ##       ####   ##  ##   #####    ##    ##   ####   ##  ##  #####     ##
##                                                                                                                            ##
################################################################################################################################

def on_key_press_grid(event):
    # based on first answer here:
    # https://stackoverflow.com/questions/28509629/work-with-ctrl-c-and-ctrl-v-to-copy-and-paste-into-a-wx-grid-in-wxpython
    # by user Sinan Çetinkaya
    """
    Handles all key press events for the grids in this module.
    """
    # Ctrl+C or Ctrl+Insert
    obj_Grid = event.GetEventObject()
    if event.ControlDown() and event.GetKeyCode() in [67, 322]:
        lst_Selection = get_grid_selection(obj_Grid)
        if len(lst_Selection) == 0:
            lst_Selection = [[obj_Grid.SingleSelection[0], obj_Grid.SingleSelection[1]]]
        dfr_Copy = pd.DataFrame()
        for i in range(len(lst_Selection)):
            dfr_Copy.at[lst_Selection[i][0],lst_Selection[i][1]] = obj_Grid.GetCellValue(lst_Selection[i][0],lst_Selection[i][1])
        dfr_Copy.to_clipboard(header=None, index=False)

    # Ctrl+A
    elif event.ControlDown() and event.GetKeyCode() == 65:
        obj_Grid.SelectAll()
    else:
        event.Skip()

def SingleSelection(event):
    """
    Event handlder.
    Sets SingleSelection property of cell (not standard in wx)
    to clicked cell to ensure it is part of the selection even
    if nothing else is selected.
    """
    event.GetEventObject().SingleSelection = (event.GetRow(), event.GetCol())

def get_grid_selection(obj_Grid):
    """
    Collects all selected cells of a grid as a list of coordinates.

    Arguments:
        obj_Grid -> wx.grid.Grid. The grid containing the selected cells.

    Returns:
        lst_Selection -> list. List of coordinates of selected cells.
    """
    # Selections are treated as blocks of selected cells
    lst_TopLeftBlock = obj_Grid.GetSelectionBlockTopLeft()
    lst_BotRightBlock = obj_Grid.GetSelectionBlockBottomRight()
    lst_Selection = []
    for i in range(len(lst_TopLeftBlock)):
        # Nuber of columns:
        int_Columns = lst_BotRightBlock[i][1] - lst_TopLeftBlock[i][1] + 1 # add 1 because if just one cell/column is selected, subtracting the coordinates will be 0!
        # Nuber of rows:
        int_Rows = lst_BotRightBlock[i][0] - lst_TopLeftBlock[i][0] + 1 # add 1 because if just one cell/row is selected, subtracting the coordinates will be 0!
        # Get all cells:
        for x in range(int_Columns):
            for y in range(int_Rows):
                new = [lst_TopLeftBlock[i][0]+y,lst_TopLeftBlock[i][1]+x]
                if lst_Selection.count(new) == 0:
                    lst_Selection.append(new)
    return lst_Selection

def process_data(ProjectTab, dlg_progress):
    """
    This function processes the data.
    First, assay details are saved to variables again (in case of updates).
    If the transfer file has been loaded, plates will be assigned (i.e.
    raw data files/entries matched with transfer file entries)

    Any previously displayed data will then be erased.

    Function complete_container in the lib_datafiles(df) module then takes
    all the data and information to normalise data and
    perform the curve fitting. The returned dataframe (assay_data) contains
    all the data (raw data, analysed data, experimental meta data) and can
    be saved to file.
    """
    time_start = perf_counter()
    ProjectTab.details["Samples"] = 0
    ProjectTab.save_details(bol_FromTabChange=False)
    dlg_progress.lbx_Log.InsertItems(["Assay details saved"], dlg_progress.lbx_Log.Count)
    
    # Perform sequence of checks before beginning processing
    if ProjectTab.bol_TransferLoaded == False:
        dlg_progress.Destroy()
        ProjectTab.parent.Thaw()
        msg.warn_no_transfer()
        return None
    if ProjectTab.bol_LayoutDefined == False:
        dlg_progress.Destroy()
        ProjectTab.parent.Thaw()
        msg.warn_no_layout()
        return None
    if ProjectTab.bol_DataFilesAssigned == False:
        dlg_progress.Destroy()
        ProjectTab.parent.Thaw()
        msg.warn_missing_datafile()
        return None
    
    transfer, layout, success = df.parse_transfer(ProjectTab.assay["TransferRules"],
                                                  ProjectTab.paths["TransferPath"])

    # Build dataframe that holds everything
    dlg_progress.lbx_Log.InsertItems(["Start creating complete container dataframe"], dlg_progress.lbx_Log.Count)
    ProjectTab.assay_data = df.complete_container(ProjectTab,
                                                  dlg_progress)

    # Catch any errors in processing -> df.complete_container() returns None on any errors:
    if ProjectTab.assay_data is None:
        dlg_progress.lbx_Log.InsertItems(["==============================================================="], dlg_progress.lbx_Log.Count)
        dlg_progress.lbx_Log.InsertItems(["DATA PROCESSING CANCELLED"], dlg_progress.lbx_Log.Count)
        dlg_progress.btn_X.Enable(True)
        dlg_progress.btn_Close.Enable(True)
        return None

    ProjectTab.dfr_Layout = ProjectTab.assay_data[["PlateID","Layout"]]

    # Re-set bool variables in case an analysis has been performed previously
    ProjectTab.bol_DataAnalysed = False
    ProjectTab.bol_ReviewsDrawn = False
    ProjectTab.bol_ResultsDrawn = False
    ProjectTab.bol_ELNPlotsDrawn = False
    ProjectTab.bol_ExportPopulated = False

    # Clear all lists, fields, grids, plots to populate with (new) results
    if hasattr(ProjectTab, "tab_Review"):
        ProjectTab.tab_Review.lbc_Plates.DeleteAllItems()
    if hasattr(ProjectTab, "lbc_Samples"):
        ProjectTab.lbc_Samples.DeleteAllItems()
    if hasattr(ProjectTab, "tab_Export"):
        try: ProjectTab.tab_Export.Clear()
        except: None

    # Populate tabs if existing and enable buttons:
    if hasattr(ProjectTab, "tab_Review") == True:
        dlg_progress.lbx_Log.InsertItems(["Populating 'Review plates' tab"], dlg_progress.lbx_Log.Count)
        ProjectTab.tab_Review.populate(noreturn = True)
        if hasattr(ProjectTab, "lbc_Plates") == True:
            ProjectTab.lbc_Plates.Select(0)
        ProjectTab.bol_ReviewsDrawn = True
    if hasattr(ProjectTab, "tab_Results") == True:
        dlg_progress.lbx_Log.InsertItems(["Populating 'Results' tab"], dlg_progress.lbx_Log.Count)
        ProjectTab.populate_results_tab()
        ProjectTab.bol_ResultsDrawn = True
    ProjectTab.tabs_Analysis.EnableAll(True)
    ProjectTab.tabs_Analysis.EnablePlateMap(ProjectTab.bol_PlateID)

    # Final entries in progress dialog:
    dlg_progress.lbx_Log.InsertItems([""], dlg_progress.lbx_Log.Count)
    dlg_progress.lbx_Log.InsertItems(["==============================================================="], dlg_progress.lbx_Log.Count)
    dlg_progress.lbx_Log.InsertItems(["Data processing completed"], dlg_progress.lbx_Log.Count)
    dlg_progress.lbx_Log.InsertItems([""], dlg_progress.lbx_Log.Count)
    str_Duration = str(round(perf_counter()-time_start,0))
    dlg_progress.lbx_Log.InsertItems(["Time elapsed: " + str_Duration + "s"], dlg_progress.lbx_Log.Count)

    # Pop up notification if neither main window nor progress dialog are active window:
    if ProjectTab.parent.IsActive() == False and dlg_progress.IsActive() == False:
        try:
            # This should only work on Windows
            ProjectTab.parent.icn_Taskbar.ShowBalloon(title="BBQ",text="Analysis completed!",msec=1000)
        except:
            msg_Popup = wx.adv.NotificationMessage(title="BBQ", message="Analysis completed!")
            try: msg_Popup.SetIcon(ProjectTab.parent.BBQIcon)
            except: None
            msg_Popup.Show(timeout=wx.adv.NotificationMessage.Timeout_Auto)
    
    # Finish up
    ProjectTab.bol_DataAnalysed = True
    dlg_progress.btn_X.Enable(True)
    dlg_progress.btn_Close.Enable(True)

def get_date(datepicker):
    """
    Gets date from wxPython datepicker object and converts it
    into YYYY-MM-DD string.

    Arguments:
        datepicker -> wxPython datepicker object

    Returns:
        date as string.
    """
    date = datepicker.GetValue()
    date = str(date.GetYear()) + "-" + str(date.GetMonth()+1) + "-" + str(date.GetDay()) # GetMonth is indexed from zero!!!!!
    return datetime.strptime(date,"%Y-%m-%d").strftime("%Y-%m-%d")

def details_backwards(details, additions = {}, typechecks = {}):
    """
    Ensures an assay details dictionary is treated for backwards compatibility.
    E.g. shorter names for variables: PeptideConcentration -> PeptideConc

    Arguments:
        details -> ductionary
        additions -> dictionary. Keys+Value pairs to add to details
        typechecks -> dictionary. Key+Value pairs. Key is the key to test,
                      value is tuple of (type, newval). If value tested is of the 
                      specified type, the value in the tuple will be inserted instead.

    Returns:
        dictionary
    """
    
    # 1. Simplify all indices: "SomethingConcentration" -> "SomethinConc"
    newdetails = {}
    for key in details.keys():
        if "entration" in key:
            newkey = key[:key.find("entration")]
            newdetails[newkey] = details[key]
        else:
            newdetails[key] = details[key]

    # 2. Add any entries that might be missing:
    for key in additions.keys():
        if not key in details.keys():
            newdetails[key] = additions[key]

    # 3. Perform typechecks and substitutions:
    for key in typechecks.keys():
        if key in details.keys():
            if details[key] is typechecks[key][0]:
                newdetails[key] = typechecks[key][1]

    return newdetails

def container_backwards(container):
    """
    Ensures backwards compatibility with column names in the assay_data
    dataframe.

    Argument:
        container -> pandas dataframe with assay data

    """
    return container.rename(columns = {"ProcessedDataframe":"Processed",
                                       "DestinationPlateName":"Destination",
                                       "DataFileName":"DataFile",
                                       "RawDataFrame":"RawData"   
                                       })

def default_details(details, defaults):
    """
    Checks whether there are any default values in the assay details.
    If true, prompt user to confirm whether they want to go ahead
    with the default values (show on dialog)

    Arguments:
        details -> dictionary of details
        defaults -> dictionary of default values that are to be
                    checked
    """

    offenders = ""

    for key in defaults.keys():
        if details[key] == defaults[key]:
            offenders += u"\n" + key + ": " + str(defaults[key])

    if len(offenders) > 0:
        answer = wx.MessageBox(u"One or more assay details are set to default values:"
                               + offenders
                               + u"\nDo you still want to start the analysis?",
                               caption = "Default values found. Continue?",
                               style = wx.YES_NO|wx.NO_DEFAULT|wx.ICON_WARNING)
        if answer == wx.YES:
            return True
        else:
            return False
    else:
        return True

def load_layout(tempdir: str):
    """
    Load layouts when populating from file.

    Arguments:
        tempdir -> str. The temporary directory in which the projcect is
                   unpacked in
    """
    layout = pd.read_csv(tempdir + r"\plates.csv",
                         sep=",",
                         header=0,
                         index_col=0,
                         engine="python")
    # Insert a column with contents, otherwise sub-dataframes cannot
    # be loaded,
    layout.insert(1,"Layout","")

    for plate in layout.index:
        laydir = os.path.join(tempdir, "layout", str(plate), "layout.csv")
        layout.at[plate,"Layout"] = pd.read_csv(laydir,
                                                sep=",",
                                                header=0,
                                                index_col=0,
                                                engine="python")

        # Backwards compatibility issue: Some numerical IDs were
        # starting from 1 instead of 0, in human familiar fashion.
        for col in layout.loc[plate,"Layout"].columns:
            if "Numerical" in col:
                try:
                    minimum = np.nanmin(layout.loc[plate,"Layout"].loc[:,col])
                    if (minimum > 0 and not pd.isna(minimum)):
                        layout.loc[plate,"Layout"][col] = layout.loc[plate,"Layout"][col].apply(minusone)
                except:
                    None
    return layout

def minusone(v):
    try:
        return v - 1
    except:
        return v
    
def lbc_constructor(parent, columns, background):
    """
    Helper function to add columns to a wx.Python ListCtrl.

    Arguments:
        listctrl -> wx.ListCtrl where columns need to be added
        colums -> nested dictionary where first level keys are names
                  of columns. Second level has "width" (int values) and
                  "sortable" (bool values)
    """

    width = 20
    for key in columns.keys():
        width += columns[key]["width"]
    listctrl = wx.ListCtrl(parent,
                           size = wx.Size(width,-1),
                           style = wx.LC_REPORT|wx.LC_SINGLE_SEL)
    listctrl.SetBackgroundColour(background)
    listctrl.titles = {}
    keys = [*columns.keys()]
    for k in range(len(keys)):
        listctrl.titles[k] = [keys[k],
                              columns[keys[k]]["width"],
                              columns[keys[k]]["sortable"]]
        listctrl.InsertColumn(k, keys[k])
        listctrl.SetColumnWidth(k, columns[keys[k]]["width"])
    
    return listctrl