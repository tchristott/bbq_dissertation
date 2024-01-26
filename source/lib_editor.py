import os
import wx
import wx.grid
import wx.xrc
import pandas as pd
import json as js

import lib_platefunctions as pf
import lib_messageboxes as msg
import lib_colourscheme as cs
import lib_customplots as cp
import lib_custombuttons as btn
import copy as copy
import lib_tabs as tab

import editor.ui_datareader as dr
import editor.ui_transferreader as tr
import editor.ui_dataprocessing as dp
import editor.ui_details as dt
import editor.ui_resultstable as rt



def empty_assay():
    """
    Creates empty dictionary for assay definition
    """

    assay = {"Meta":{
                "Shorthand":None,
                "FullName":None,
                "DisplayTitle":None,
                "Timestamp":"01/01/1970",
                "Author":None,
                "AssayNameDB":None,
                "MainCategory":None,
                "SecondaryCategory":None,
                "OtherCategories":None
                },
             "DefaultDetails":{
                "Buffer": "20 mM HEPES, 100 mM NaCl, 2 mM TCEP, 0.5%(w/v) CHAPS, pH 7.5",
                "DateOfExperiment": "01/01/1970",
                "LIMS": "PAGE23-00271"},
             "Reagents":{},
             "Tabs":{
                "Details":{
                    "Column1":{},
                    "Column2":{},
                    "Column3":{},
                    "Column4":{}
                }
             },
             "RawDataRules":{},
             "TransferRules":{},
             "DataProcessing":{},
             "Results":{},
             "ResultsTable":{},
             "Database":{
                "UseDB":True,
                "DBTables":{}
             },
             }
    
    return assay

class TextField(wx.Panel):
    """
    Custom widget for meta data entry editor
    """
    def __init__(self,
                 parent,
                 entry_name,
                 title,
                 info,
                 char_limit = None,
                 force_case = False,
                 allowed = False):
        """
        Initialises class attributes

        Arguments:
            parent -> wx object. Parent object of this panel
            label -> str. What to display on the label
            entry_name -> str. Name of the meta data entry in the JSON file
            char_limit -> int. Max character length for the input text control
            force_case -> str or Bool(False). which case to force the value to
                be. Entries will be automatically converted. If False, upper and
                lower case are permitted.
            allowed -> str of False. Options are (combine and separate by underscore):
                alpha, num, und (underscore), dash (dash/hyphen), space
        """

        wx.Panel.__init__ (self, parent,
                           id = wx.ID_ANY,
                           pos = wx.DefaultPosition,
                           size = wx.DefaultSize,
                           style = wx.TAB_TRAVERSAL,
                           name = f"meta_{entry_name}")

        self.SetBackgroundColour(cs.BgLight)

        # Properties:
        self.entry = entry_name
        self.locked = False
        self.value = None
        self.char_limit = char_limit
        self.force_case = force_case
        self.allowed = allowed

        # Visible elements:
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.title = wx.StaticText(self,
                                   label = title)
        self.sizer.Add(self.title, 0, wx.ALL, 5)
        self.info = wx.StaticText(self,
                                  label = info)
        self.sizer.Add(self.info, 0, wx.ALL, 5)
        self.group = wx.BoxSizer(wx.HORIZONTAL)
        self.input = wx.TextCtrl(self, value = u"")
        if not char_limit is None:
            self.input.SetMaxLength(self.char_limit)
        self.group.Add(self.input, 0, wx.ALL, 0)
        self.group.Add((0,5), 0, wx.ALL, 0)
        self.clear = wx.Button(self, label=u"Clear")
        self.group.Add(self.clear, 0, wx.ALL, 0)
        self.group.Add((0,5), 0, wx.ALL, 0)
        self.lock = wx.Button(self, label="Un/Lock")
        self.group.Add(self.lock, 0, wx.ALL, 0)
        self.sizer.Add(self.group, 0, wx.ALL, 5)
        # Finish up:
        self.SetSizer(self.sizer)
        self.sizer.Fit(self)
        self.Layout()

        # Connect events to handlers:
        self.lock.Bind(wx.EVT_BUTTON, self.on_btn_lock)
        self.clear.Bind(wx.EVT_BUTTON, self.input.Clear())
        self.input.Bind(wx.EVT_TEXT, self.on_type)
        
    def on_btn_lock(self, event):
        """
        Event handler. Locks/unlocks the widget for editing.
        """
        self.input.Enable(self.locked)
        self.clear.Enable(self.locked)
        self.locked = not self.locked

    def on_clear(self, event):
        """
        Event handler. Clears the input text control.
        """
        self.input.Clear()

    def on_type(self, event):
        """
        Event handler for input text control
        """
        text_ctrl = event.GetEventObject()
        temp_value = text_ctrl.GetValue()
        new_value = copy.copy(temp_value)
        insertion = text_ctrl.GetInsertionPoint()

        if not new_value == "":
            # Get New Character:
            if insertion == len(new_value):
                new_chr = new_value[-1]
            else:
                new_chr = new_value[insertion-1:insertion]
            new_ord = ord(new_chr)

            # Check for allowed characters:
            all_ord = [] # holds decimal values of allowed Unicode characters
            if "alpha" in self.allowed:
                all_ord.extend(list(range(65,91))) # add upper case letters
                all_ord.extend(list(range(97,123))) # add lower case letters
            if "num" in self.allowed:
                all_ord.extend(list(range(48,58))) # add numbers
            if "und" in self.allowed:
                all_ord.append(94)
            if "dash" in self.allowed:
                all_ord.append(45)
            if "space" in self.allowed:
                all_ord.append(32)
            # Excise if not valid
            if not new_ord in all_ord:
                new_value = new_value[:insertion-1] + new_value[insertion:]

            # Check for forced case:
            if not self.force_case == False:
                if self.force_case == "lower":
                    new_value = new_value.lower()
                else:
                    new_value = new_value.upper()

            # And finally, set the new value
            text_ctrl.ChangeValue(new_value)
            if insertion < len(temp_value):
                insertion -= 1
            text_ctrl.SetInsertionPoint(insertion)

    def set_char_limit(self, char_limit):
        """
        Wrapper function. Sets character limit on input text control.

        Argument:
            char_limit -> int. Same behaviour as the built-in
                SetMaxLength. If char_limit is 0, the user can
                enter however many characters the widget natively
                supports.
        """
        self.input.SetMaxLength(char_limit)


class MetaTab(wx.Panel):
    """
    Panel for assay meta data
    """

    def __init__(self, parent, asay_def, dic_meta):
        """
        Initialises class attributes.
        
        Arguments:
            parent -> wx object. Parent object of this panel.
            assay_def -> assay definition dictionary
            dic_meta -> dictionary with fields for meta data editor
        """
        wx.Panel.__init__ (self, parent, id = wx.ID_ANY,
                           pos = wx.DefaultPosition, size = wx.DefaultSize,
                           style = wx.TAB_TRAVERSAL, name = wx.EmptyString)

        self.SetBackgroundColour(cs.BgUltraLight)
        clr_Tabs = cs.BgUltraLight
        clr_Panels = cs.BgLight
        clr_TextBoxes = cs.BgUltraLight

        self.parent = parent

        # Meta data section
        # Required:
        #       Shorthand
        #       FullName
        #       DisplayTitle
        #       MainCategory
        #       SecondaryCategory
        #       Other Categories

        self.szr_Meta = wx.BoxSizer(wx.VERTICAL)
        self.wdg_Meta = {}
        for key in dic_meta.keys():
            self.wdg_Meta[key] = dic_meta[key]["widget"](self,
                                                         **dic_meta[key]["kwargs"])
            self.szr_Meta.Add(self.wdg_Meta[key], 0, wx.ALL, 5)

        self.SetSizer(self.szr_Meta)
        self.Layout()
        self.szr_Meta.Fit(self)

class InstructionTab(wx.Panel):
    """
    Introduction to editor
    """
    def __init__(self, parent, wkflw, asay_def):
        """
        Initialises class attributes
        
        Arguments:
            parent -> wx object. Parent object of this panel.
            assay_def -> assay definition dictionary
        """
        wx.Panel.__init__ (self, parent, id = wx.ID_ANY,
                           pos = wx.DefaultPosition, size = wx.DefaultSize,
                           style = wx.TAB_TRAVERSAL, name = wx.EmptyString)
        
        self.SetBackgroundColour(cs.BgUltraLight)

        self.szr_Surround = wx.BoxSizer(wx.HORIZONTAL)

        self.pnl_Wizard = wx.Panel(self)
        self.pnl_Wizard.SetBackgroundColour(cs.BgLight)
        self.pnl_Wizard.SetMaxSize(wx.Size(420,630))
        self.szr_Wizard = wx.BoxSizer(wx.VERTICAL)

        self.lbl_Welcome = wx.StaticText(self.pnl_Wizard,
                                        label = u"Welcome to the Workflow Editor")
        self.szr_Wizard.Add(self.lbl_Welcome, 0, wx.ALL, 5)

        self.pnl_Wizard.SetSizer(self.szr_Wizard)
        self.pnl_Wizard.Layout()
        self.szr_Surround.Fit(self.pnl_Wizard)

        self.szr_Surround.Add(self.pnl_Wizard, 0, wx.EXPAND, 5)
        self.SetSizer(self.szr_Surround)
        self.Layout()
        self.szr_Surround.Fit(self)

class ResultsTable(wx.Panel):
    """
    Panel for results table
    """
    def __init__(self, parent, assay_def):
        """
        Initialises class attributes.
        
        Arguments:
            parent -> wx object. Parent object of this panel.
            assay_def -> assay definition dictionary
        """
        wx.Panel.__init__ (self, parent, id = wx.ID_ANY,
                           pos = wx.DefaultPosition, size = wx.DefaultSize,
                           style = wx.TAB_TRAVERSAL, name = wx.EmptyString)

        self.assay_def = assay_def

        self.SetBackgroundColour(cs.BgUltraLight)
        self.parent = parent

        self.sizer = wx.BoxSizer(wx.HORIZONTAL)

        # Sidebar with all the options
        self.szr_possible_columns = wx.BoxSizer(wx.VERTICAL)

        # Assay meta data
        self.szr_Meta = wx.BoxSizer(wx.VERTICAL)
        self.lbl_Meta = wx.StaticText(self,
                                         label = u"Assay meta data")
        self.szr_Meta.Add(self.lbl_Meta, 0, wx.ALL, 5)

        self.lbx_Meta = wx.ListBox(self,
                                      size = wx.Size(200,100),
                                      choices = self.make_list_meta())
        self.szr_Meta.Add(self.lbx_Meta, 0, wx.ALL, 5)
        self.szr_possible_columns.Add(self.szr_Meta, 0, wx.ALL, 5)

        # Assay details
        self.szr_Details = wx.BoxSizer(wx.VERTICAL)
        self.lbl_Details = wx.StaticText(self,
                                         label = u"Assay details")
        self.szr_Details.Add(self.lbl_Details, 0, wx.ALL, 5)

        self.lbx_Details = wx.ListBox(self,
                                      size = wx.Size(200,200),
                                      choices = self.make_list_details())
        self.szr_Details.Add(self.lbx_Details, 0, wx.ALL, 5)
        self.szr_possible_columns.Add(self.szr_Details, 0, wx.ALL, 5)

        # MORE STUFF HERE
        self.sizer.Add(self.szr_possible_columns, 0, wx.ALL, 5)

        self.SetSizer(self.sizer)
        self.Layout()
        self.sizer.Fit(self)



    def make_list_details(self):
        self.deets = []
        for key in self.assay_def["DefaultDetails"].keys():
            self.deets.append(key)
        return self.deets
    
    def make_list_meta(self):
        self.meta = ["Shorthand","FullName","DisplayTitle",
                     "MainCategory","SecondaryCategory"]

        return self.meta

    def update_columns(self):

        for key in self.assay_def["DefaultDetails"].keys():
            self.deets.append(key)
            print(key)

        # Meta adata
        old_meta = copy.deepcopy(self.meta)
        self.meta = self.make_list_meta()
        for om in old_meta:
            if not om in self.meta:
                pass
        self.lbx_Meta.Clear()
        for deet in self.make_list_meta():
            self.lbx_Meta.Insert(deet, self.lbx_Meta.GetCount())

        old_deets = copy.deepcopy(self.deets)
        self.deets = self.make_list_details()
        for od in old_deets:
            if not od in self.deets:
                pass
        self.lbx_Details.Clear()
        for deet in self.make_list_details():
            self.lbx_Details.Insert(deet, self.lbx_Details.GetCount())




class DatabaseTab(wx.Panel):
    """
    Panel for database connection
    """

    def __init__(self, parent, wkflw, assay):
        """
        Initialises class attributes.
        
        Arguments:
            parent -> wx object. Parent object of this panel.
            assay -> assay definition dictionary
        """
        wx.Panel.__init__ (self, parent, id = wx.ID_ANY,
                           pos = wx.DefaultPosition, size = wx.DefaultSize,
                           style = wx.TAB_TRAVERSAL, name = wx.EmptyString)

        self.SetBackgroundColour(cs.BgUltraLight)
        self.parent = parent
        self.wkflw = wkflw
        self.assay = assay
        self.rule_set = self.assay["Database"]

        self.sizer = wx.BoxSizer(wx.HORIZONTAL)

        # Database Details
        self.szr_DBTDetails = wx.BoxSizer(wx.VERTICAL)
        self.chk_Database = wx.CheckBox(self,
                                        label = u"Include database connection for result upload")
        self.chk_Database.SetValue(True)
        self.szr_DBTDetails.Add(self.chk_Database, 0, wx.ALL, 5)
        self.lin_Database = wx.StaticLine()
        self.szr_DBTDetails.Add(self.lin_Database, 0, wx.ALL, 5)
        self.lbl_Database = wx.StaticText(self,
                                          label = u"Details of database connection")
        self.szr_DBTDetails.Add(self.lbl_Database, 0, wx.ALL, 5)

        # Database Host Name
        self.szr_DBHost = wx.BoxSizer(wx.HORIZONTAL)
        self.chk_DBHost = wx.CheckBox(self,
                                   label = u"Host Name:")
        self.szr_DBHost.Add(self.chk_DBHost, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 0)
        self.txt_DBHost = wx.TextCtrl(self)
        self.szr_DBHost.Add(self.txt_DBHost, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 0)
        self.szr_DBTDetails.Add(self.szr_DBHost, 0, wx.ALL, 5)

        # Database Service Name
        self.szr_DSN = wx.BoxSizer(wx.HORIZONTAL)
        self.chk_DSN = wx.CheckBox(self,
                                   label = u"Service Name:")
        self.szr_DSN.Add(self.chk_DSN, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 0)
        self.txt_DSN = wx.TextCtrl(self)
        self.szr_DSN.Add(self.txt_DSN, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 0)
        self.szr_DBTDetails.Add(self.szr_DSN, 0, wx.ALL, 5)

        # Database Host Name
        self.szr_DBPort = wx.BoxSizer(wx.HORIZONTAL)
        self.chk_DBPort = wx.CheckBox(self,
                                   label = u"Port:")
        self.szr_DBPort.Add(self.chk_DBPort, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 0)
        self.txt_DBPort = wx.TextCtrl(self)
        self.szr_DBPort.Add(self.txt_DBPort, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 0)
        self.szr_DBTDetails.Add(self.szr_DBPort, 0, wx.ALL, 5)


        self.sizer.Add(self.szr_DBTDetails, 0, wx.ALL, 5)

        # Database Table Columns
        self.szr_DBTGrid = wx.BoxSizer(wx.VERTICAL)
        # Datbase table title
        self.szr_DBTName = wx.BoxSizer(wx.HORIZONTAL)
        self.lbl_DBTName = wx.StaticText(self,
                                         label = u"Database table:")
        self.szr_DBTName.Add(self.lbl_DBTName, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 0)
        self.szr_DBTName.Add((5,-1), 0, wx.ALL, 0)
        self.txt_DBTName = wx.TextCtrl(self)
        self.szr_DBTName.Add(self.txt_DBTName, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 0)
        self.szr_DBTDetails.Add(self.szr_DBTName, 0, wx.ALL, 5)
        self.szr_DBTGrid.Add(self.szr_DBTName, 0, wx.ALL, 5)
        # DBTable column names:
        self.dic_columns = {"BBQ_NAME":"Display name in BBQ",
                            "DB_NAME":"Name on DB table",
                            "MAPPED":"Mapped to...",
                            "DEFAULT":"Default value",
                            "DTYPE":"Data Type",
                            "OBSOLETE":"Obsolete column"}
        self.dic_DataTypes = {"String":"str",
                              "Floating point number":"float",
                              "Integer":"int"}
        self.grd_DBTGrid = wx.grid.Grid(self)
        # Grid
        self.grd_DBTGrid.CreateGrid(20, 6)
        self.grd_DBTGrid.EnableEditing(False)
        self.grd_DBTGrid.EnableGridLines(True)
        self.grd_DBTGrid.EnableDragGridSize(False)
        self.grd_DBTGrid.SetMargins(0, 0)
        # Columns
        self.grd_DBTGrid.EnableDragColMove(False)
        self.grd_DBTGrid.EnableDragColSize(False)
        self.grd_DBTGrid.SetColLabelAlignment(wx.ALIGN_CENTER, wx.ALIGN_CENTER)
        c = 0
        for col in self.dic_columns.keys():
            lbl = self.dic_columns[col]
            wid = tab.get_text_width(lbl) + 5 # This only gives the minimum width for the title to be legible
            self.grd_DBTGrid.SetColLabelValue(c, lbl)
            self.grd_DBTGrid.SetColSize(c, wid)
            c += 1
        # Rows
        self.grd_DBTGrid.EnableDragRowMove(True)
        self.grd_DBTGrid.EnableDragRowSize(False)
        self.grd_DBTGrid.SetRowLabelSize(30)
        self.grd_DBTGrid.SetRowLabelAlignment(wx.ALIGN_CENTER, wx.ALIGN_CENTER)
        self.grd_DBTGrid.SetDefaultCellAlignment(wx.ALIGN_LEFT, wx.ALIGN_TOP)
        self.szr_DBTGrid.Add(self.grd_DBTGrid, 0, wx.ALL, 5)

        self.sizer.Add(self.szr_DBTGrid, 0, wx.ALL, 5)

        self.grd_DBTGrid.Bind(wx.grid.EVT_GRID_CELL_RIGHT_CLICK, self.on_grid_right_click)
        self.grd_DBTGrid.Bind(wx.grid.EVT_GRID_CELL_LEFT_CLICK, self.on_grid_left_click)
        self.grd_DBTGrid.Bind(wx.grid.EVT_GRID_SELECT_CELL, self.on_grid_select_cell)
        self.grd_DBTGrid.Bind(wx.EVT_KEY_DOWN, self.on_grid_key_press)
        self.chk_Database.Bind(wx.EVT_CHECKBOX, self.on_chk_database)

        self.SetSizer(self.sizer)
        self.Layout()
        self.sizer.Fit(self)

    def on_chk_database(self, event):
        db = event.GetEventObject().GetValue()

        self.lbl_Database.Enable(db)
        self.chk_DBHost.Enable(db)
        self.txt_DBHost.Enable(db)
        self.chk_DBPort.Enable(db)
        self.txt_DBPort.Enable(db)
        self.txt_DBHost.Enable(db)
        self.chk_DSN.Enable(db)
        self.txt_DSN.Enable(db)
        self.lbl_DBTName.Enable(db)
        self.txt_DBTName.Enable(db)
        self.grd_DBTGrid.Enable(db)

        self.rule_set["UseDB"] = db

    def on_grid_select_cell(self, event):
        """
        Event handler. Ensures onlye select cells/columns can be edited manually.
        """
        row = event.GetRow()
        col = event.GetCol()

        if col in [0,1,3]:
            self.grd_DBTGrid.EnableEditing(True)
        else:
            self.grd_DBTGrid.EnableEditing(False)
        event.Skip()

    def on_grid_key_press(self, event):
        """
        Event handler. Does many things
        """
        grd = self.grd_DBTGrid
        row = self.grd_DBTGrid.GetGridCursorRow()
        col = self.grd_DBTGrid.GetGridCursorCol()
        last_col = self.grd_DBTGrid.GetNumberCols() - 1
        last_row = self.grd_DBTGrid.GetNumberRows() - 1
        
        # Ctrl+C or Ctrl+Insert
        if event.ControlDown() and event.GetKeyCode() in [67, 322]:
            lst_Selection = tab.get_grid_selection(grd)
            if len(lst_Selection) == 0:
                lst_Selection = [[grd.SingleSelection[0], grd.SingleSelection[1]]]
            dfr_Copy = pd.DataFrame()
            for i in range(len(lst_Selection)):
                dfr_Copy.at[lst_Selection[i][0],lst_Selection[i][1]] = grd.GetCellValue(lst_Selection[i][0],lst_Selection[i][1])
            dfr_Copy.to_clipboard(header=None, index=False)
        # Ctrl+A
        elif event.ControlDown() and event.GetKeyCode() == 65:
            grd.SelectAll()
        # Tab
        elif event.GetKeyCode() == 9 and row < last_row and col == last_col:
            grd.SetGridCursor(row + 1, 0)
        # Cursor key up
        elif event.GetKeyCode() == 315 and row == 0 and col < last_col and col > 0:
            grd.SetGridCursor(last_row, col - 1)
        # Cursor key down
        elif event.GetKeyCode() == 317 and row == last_row and col < last_col:
            grd.SetGridCursor(0, col + 1)
        # Cursor key left
        elif event.GetKeyCode() == 314 and row > 0  and col == 0:
            grd.SetGridCursor(row - 1, last_col)
        # Cursor key right
        elif event.GetKeyCode() == 316 and row < last_row  and col == last_col:
            grd.SetGridCursor(row + 1, 0)
        
        event.Skip()
        

    def on_grid_right_click(self, event):
        self.PopupMenu(GridContextMenu(self, event))

    def on_grid_left_click(self, event):
        row = event.GetRow()
        col = event.GetCol()
        grd = event.GetEventObject()

        # Branch off for column-specific menus
        if col in [0,1,3]:
            self.grd_DBTGrid.EnableEditing(True)
        elif col == 4:
            self.PopupMenu(DataTypeMenu(self, row, col, grd))
            self.grd_DBTGrid.EnableEditing(False)
        else:
            self.grd_DBTGrid.EnableEditing(False)
        event.Skip()


class GridContextMenu(wx.Menu):

    """
    Context menu to cut, copy, paste, clear  grid.
    """

    def __init__(self, parent, rightclick):
        super(GridContextMenu, self).__init__()

        self.parent = parent
        self.grid = rightclick.GetEventObject()

        real_path = os.path.realpath(__file__)
        dir_path = os.path.dirname(real_path)
        str_MenuIconsPath = os.path.join(dir_path, "menuicons")

        row = rightclick.GetRow()
        col = rightclick.GetCol()

        self.mi_Cut = wx.MenuItem(self, wx.ID_ANY, u"Cut", wx.EmptyString, wx.ITEM_NORMAL)
        self.mi_Cut.SetBitmap(wx.Bitmap(str_MenuIconsPath + u"\Cut.ico"))
        self.Append(self.mi_Cut)
        self.Bind(wx.EVT_MENU, lambda event: self.Cut(event,  row, col), self.mi_Cut)

        self.mi_Copy = wx.MenuItem(self, wx.ID_ANY, u"Copy", wx.EmptyString, wx.ITEM_NORMAL)
        self.mi_Copy.SetBitmap(wx.Bitmap(str_MenuIconsPath + u"\Copy.ico"))
        self.Append(self.mi_Copy)
        self.Bind(wx.EVT_MENU, lambda event: self.Copy(event,  row, col), self.mi_Copy)

        self.mi_Paste = wx.MenuItem(self, wx.ID_ANY, u"Paste", wx.EmptyString, wx.ITEM_NORMAL)
        self.mi_Paste.SetBitmap(wx.Bitmap(str_MenuIconsPath + u"\Paste.ico"))
        self.Append(self.mi_Paste)
        self.Bind(wx.EVT_MENU, lambda event: self.Paste(event,  row, col), self.mi_Paste)

        self.mi_Clear = wx.MenuItem(self, wx.ID_ANY, u"Clear", wx.EmptyString, wx.ITEM_NORMAL)
        self.mi_Clear.SetBitmap(wx.Bitmap(str_MenuIconsPath + u"\Clear.ico"))
        self.Append(self.mi_Clear)
        self.Bind(wx.EVT_MENU, lambda event: self.Clear(event,  row, col), self.mi_Clear)

        self.mi_AddDBColumn = wx.MenuItem(self, wx.ID_ANY, u"Add DB Column", wx.EmptyString, wx.ITEM_NORMAL)
        self.Append(self.mi_AddDBColumn)
        self.Bind(wx.EVT_MENU, lambda event: self.Add(event,  row, col), self.mi_AddDBColumn)

        self.mi_RemoveDBColumn = wx.MenuItem(self, wx.ID_ANY, u"Remove DB Column", wx.EmptyString, wx.ITEM_NORMAL)
        self.Append(self.mi_RemoveDBColumn)
        self.Bind(wx.EVT_MENU, lambda event: self.Remove(event,  row, col), self.mi_AddDBColumn)

    def Copy(self, event, row, col):
        """
        Copies contents of selected cells
        """
        lst_Selection = self.GetGridSelection()
        if len(lst_Selection) > 0:
            dfr_Copy = pd.DataFrame()
            for i in range(len(lst_Selection)):
                dfr_Copy.at[lst_Selection[i][0],lst_Selection[i][1]] = self.grid.GetCellValue(lst_Selection[i][0],lst_Selection[i][1])
            dfr_Copy.to_clipboard(header=None, index=False)

    def Cut(self, event, row, col):
        """
        Cuts contents from selected cells
        """
        lst_Selection = self.GetGridSelection()
        if len(lst_Selection) > 0:
            dfr_Copy = pd.DataFrame()
            for i in range(len(lst_Selection)):
                dfr_Copy.at[lst_Selection[i][0],lst_Selection[i][1]] = self.grid.GetCellValue(lst_Selection[i][0],lst_Selection[i][1])
                self.grid.SetCellValue(lst_Selection[i][0],lst_Selection[i][1],"")
            dfr_Copy.to_clipboard(header=None, index=False)

    def Paste(self, event, row, col):
        """
        Writes content of clipboard into selected cells
        """
        dfr_Paste = pd.read_clipboard(sep="\\t", header=None)
        int_Rows = len(dfr_Paste)
        int_Columns = len(dfr_Paste.columns)
        for i in range(int_Rows):
            for j in range(int_Columns):
                if j <= 5:
                    self.grid.SetCellValue(i+row,j+col,str(dfr_Paste.iloc[i,j]))

    def Clear(self, event, row, col):
        """
        Deletes contents of selected cells.
        """
        self.grid.SetCellValue(row, col, "")
        lst_Selection = self.GetGridSelection()
        if len(lst_Selection) > 0:
            for i in range(len(lst_Selection)):
                if lst_Selection[i][1] > 0:
                    self.grid.SetCellValue(lst_Selection[i][0],lst_Selection[i][1],"")

    def Add(self, event, row, col):
        pass

    def Remove(self, event, row, col):
        pass

    def GetGridSelection(self):
        # Selections are treated as blocks of selected cells
        lst_TopLeftBlock = self.grid.GetSelectionBlockTopLeft()
        lst_BotRightBlock = self.grid.GetSelectionBlockBottomRight()
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

class DataTypeMenu(wx.Menu):

    """
    Pop-up menu for defining data types.
    """

    def __init__(self, parent, row, col, grid):
        super(DataTypeMenu, self).__init__()

        self.parent = parent
        self.grid = grid
        self.dtypes = self.parent.dic_DataTypes

        #real_path = os.path.realpath(__file__)
        #dir_path = os.path.dirname(real_path)
        #str_MenuIconsPath = os.path.join(dir_path, "menuicons")

        self.type_items = {}
        for key in self.dtypes.keys():
            self.type_items[key] = wx.MenuItem(self,
                                               wx.ID_ANY,
                                               key,
                                               wx.EmptyString,
                                               wx.ITEM_NORMAL)
            #self.type_items[key].SetBitmap(wx.Bitmap(f"{str_MenuIconsPath}\{dtype}.ico"))
            self.Append(self.type_items[key])
            self.Bind(wx.EVT_MENU,
                      lambda event, dtype = self.dtypes[key]: self.set(event, row, col, dtype),
                      self.type_items[key])

    def set(self, event, row, col, dtype):
        self.grid.SetCellValue(row, col, dtype)


class WEButtonBar(wx.Panel):
    """
    Button bar: Save, Save As, Cancel, Analyse Data
    """

    def __init__(self, parent, id = wx.ID_ANY, pos = wx.DefaultPosition,
                 size = wx.DefaultSize, style = wx.TAB_TRAVERSAL, name = wx.EmptyString):
        """
        Initialises class attributes.
        """
        wx.Panel.__init__ (self, parent = parent, id = id,
                           pos = pos, size = size, style = style, name = "ButtonBar")

        self.parent = parent
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
        self.btn_HeaderNew = btn.CustomBitmapButton(self,
                                                    name = u"New",
                                                    index = 0,
                                                    size = (82,30),
                                                    tooltip="Start a new workflow")
        self.btn_HeaderNew.Enable(False)
        self.szr_ProjectMenuBar.Add(self.btn_HeaderNew, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 0)
        self.szr_ProjectMenuBar.Add((3,0), 0, wx.ALL, 0)
        self.btn_HeaderOpen = btn.CustomBitmapButton(self,
                                                     name = u"Open",
                                                     index = 1,
                                                     size = (100,30),
                                                     tooltip="Open an existing workflow")
        self.btn_HeaderOpen.Enable(False)
        self.szr_ProjectMenuBar.Add(self.btn_HeaderOpen, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 0)
        self.szr_ProjectMenuBar.Add((3,0), 0, wx.ALL, 0)
        self.btn_HeaderSave = btn.CustomBitmapButton(self,
                                                     name = u"Save",
                                                     index = 2,
                                                     size = (100,30),
                                                     tooltip="Save the current project")
        self.btn_HeaderSave.Enable(False)
        self.szr_ProjectMenuBar.Add(self.btn_HeaderSave, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 0)
        self.szr_ProjectMenuBar.Add((3,0), 0, wx.ALL, 0)
        self.btn_HeaderSaveAs = btn.CustomBitmapButton(self,
                                                       name = u"SaveAs",
                                                       index = 3,
                                                       size = (100,30))
        self.btn_HeaderSaveAs.Enable(False)
        self.szr_ProjectMenuBar.Add(self.btn_HeaderSaveAs, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 0)
        self.szr_ProjectMenuBar.Add((3,0), 0, wx.ALL, 0)
        # Cancel
        self.sep_LineSeparator_01 = wx.StaticLine(self, wx.ID_ANY, wx.DefaultPosition,
                                                  wx.Size(-1,30), wx.LI_VERTICAL)
        self.szr_ProjectMenuBar.Add(self.sep_LineSeparator_01, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 0)
        self.szr_ProjectMenuBar.Add((3,0), 0, wx.ALL, 0)
        self.btn_HeaderReturn = btn.CustomBitmapButton(self,
                                                       name = u"ReturnToToolSelection",
                                                       index = 4,
                                                       size = (169,25))
        self.szr_ProjectMenuBar.Add(self.btn_HeaderReturn, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 0)
        self.szr_ProjectMenuBar.Add((3,0), 0, wx.ALL, 0)
        self.szr_HeaderProject.Add(self.szr_ProjectMenuBar, 0, wx.EXPAND, 0)
        self.szr_HeaderProject.Add((0,15),0,wx.ALL,0)
        self.SetSizer(self.szr_HeaderProject)
        self.Layout()
        self.szr_HeaderProject.Fit(self)
        
        # Connect event handlers
        self.btn_HeaderNew.Bind(wx.EVT_BUTTON, self.parent.new_workflow)
        self.btn_HeaderOpen.Bind(wx.EVT_BUTTON, self.parent.open_workflow)
        self.btn_HeaderSave.Bind(wx.EVT_BUTTON, self.parent.save_workflow)
        self.btn_HeaderSaveAs.Bind(wx.EVT_BUTTON, self.parent.save_workflow)
        self.btn_HeaderReturn.Bind(wx.EVT_BUTTON, self.parent.close_editor)

    def EnableButtons(self, bol_Enable):
        """
        Enables/Disables the buttons
        """
        self.btn_HeaderNew.Enable(bol_Enable)
        self.btn_HeaderOpen.Enable(bol_Enable)
        self.btn_HeaderSave.Enable(bol_Enable)
        self.btn_HeaderSaveAs.Enable(bol_Enable)
        self.btn_HeaderReturn.Enable(bol_Enable)

class WorkflowEditor(wx.Panel):
    """
    Workflow Editor
    """

    def __init__(self, parent, main_frame):
        """
        Initialises class attributes.
        
        Arguments:
            parent -> wx object. Parent object of this panel.
            main_frame -> wx object. The main wx object (Frame) of the class
        """
        wx.Panel.__init__ (self, parent,
                           id = wx.ID_ANY,
                           pos = wx.DefaultPosition,
                           size = wx.DefaultSize,
                           style = wx.TAB_TRAVERSAL,
                           name = "WorkflowEditor")

        self.SetBackgroundColour(cs.BgMediumDark)
        clr_Tabs = cs.BgUltraLight
        clr_Panels = cs.BgLight
        clr_TextBoxes = cs.BgUltraLight

        self.parent = parent
        self.main_frame = main_frame

        self.assay = empty_assay()

        self.szr_Editor = wx.BoxSizer(wx.VERTICAL)
        
        # Button Bar
        self.pnl_ButtonBar = WEButtonBar(self)
        self.pnl_ButtonBar.EnableButtons(True)
        self.szr_Editor.Add(self.pnl_ButtonBar, 0, wx.ALL, 5)
        # Notebook
        self.nbk_Editor = tab.AssayStepsNotebook(self,
                                                 size = wx.DefaultSize)

        self.tab_Instructions = InstructionTab(self.nbk_Editor.sbk_Notebook,
                                               self,
                                               self.assay)
        self.nbk_Editor.AddPage(self.tab_Instructions, u"Instructions", True)

        self.tab_Details = dt.AssayDetails(self.nbk_Editor.sbk_Notebook,
                                           self,
                                           self.assay)
        self.nbk_Editor.AddPage(self.tab_Details, u"Assay Details", True)

        self.tab_TransferFiles = tr.TransferRules(self.nbk_Editor.sbk_Notebook,
                                                  self,
                                                  self.assay)
        self.nbk_Editor.AddPage(self.tab_TransferFiles, u"Liquid Handler Transfer Files", True)

        self.tab_DataFiles = dr.RawDataRules(self.nbk_Editor.sbk_Notebook,
                                             self,
                                             self.assay)
        self.nbk_Editor.AddPage(self.tab_DataFiles, u"Raw Data Files", True)

        self.tab_DataProcessing = dp.DataProcessing(self.nbk_Editor.sbk_Notebook,
                                                    self,
                                                    self.assay)
        self.nbk_Editor.AddPage(self.tab_DataProcessing, u"Data Processing", True)

        self.tab_ResultsTable = rt.ResultsTable(self.nbk_Editor.sbk_Notebook,
                                                self,
                                                self.assay)
        self.nbk_Editor.AddPage(self.tab_ResultsTable, u"Results Table", True)

        self.tab_Database = DatabaseTab(self.nbk_Editor.sbk_Notebook,
                                        self,
                                        self.assay)
        self.nbk_Editor.AddPage(self.tab_Database, u"Database connection", True)

        self.szr_Editor.Add(self.nbk_Editor, 1, wx.EXPAND|wx.ALL, 0)
        self.nbk_Editor.SetSelection(0)

        self.SetSizer(self.szr_Editor)
        self.Layout()
        self.szr_Editor.Fit(self)

    def change_tab(self, caller):
        """
        This function is normally to check whether the notebook
        is allowed to change tabs. In this case, there are no
        conditions to be met, so it shall always return True.
        """
        label = caller.Label

        if label == "Results Table":
            self.tab_ResultsTable.update_columns()

        return True
    
    def new_workflow(self, event):
        pass

    def open_workflow(self, event):
        
        with wx.FileDialog(self, "Open JSON file", wildcard="JSON files (*.json)|*.json",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as fileDialog:

            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return None     # the user changed their mind
            # Proceed loading the file chosen by the user
            self.assay = js.load(open(fileDialog.GetPath(), "r"))
            self.tab_Details.populate_from_file(self.assay)
        
            


    def save_workflow(self, saveas = False):
        """
        Saves workflow as JSON file.
        """
        verified = True
        previously = False

        if verified == True:
            if previously == False or saveas == True:
                with wx.FileDialog(self, "Save project file",
                                   wildcard = "JSON files (*.json)|*.json",
                                   style = wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT) as fileDialog:
                    # Exit via returning nothing if the user changed their mind
                    if fileDialog.ShowModal() == wx.ID_CANCEL:
                        return
                    str_SaveFilePath = fileDialog.GetPath()
                    # Prevent duplication of file extension
                    if str_SaveFilePath.find(".json") == -1:
                        str_SaveFilePath = str_SaveFilePath + ".json"
                    with open(str_SaveFilePath, 'w') as f:
                        js.dump(self.assay, f, indent=4)

    def close_editor(self, event = None):
        """
        Event handler.
        Closes the workflow and resets the notebook in the main frame
        of BBQ
        """
        if msg.query_discard_changes() == True:
            self.main_frame.CloseActiveTool(event = None)