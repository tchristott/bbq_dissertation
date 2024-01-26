"""
Contains plate layout and sample ID menu for analysis setup.

    Classes:
        ScrollList
        PlateLayout
        PlateContextMenu
        SampleContextMenu

"""

import wx
import wx.xrc
import wx.grid
import os
import shutil

import lib_colourscheme as cs
import lib_platefunctions as pf
import lib_datafunctions as df
import lib_custombuttons as btn
import pandas as pd
import numpy as np

import zipfile as zf

######  ##  ##  ##  ##   #####  ######  ##   ####   ##  ##   #####
##      ##  ##  ### ##  ##        ##    ##  ##  ##  ### ##  ##
####    ##  ##  ######  ##        ##    ##  ##  ##  ######   ####
##      ##  ##  ## ###  ##        ##    ##  ##  ##  ## ###      ##
##       ####   ##  ##   #####    ##    ##   ####   ##  ##  #####

def edit_layouts(workflow):
    """
    Launches dialog to edit plate layouts. Sends dfr_Layout back.
    """
    plates = []
    no_plates = False
    if not workflow.details["GlobalLayout"] == True:
        if hasattr(workflow, "dfr_PlateAssignment"):
            if workflow.dfr_PlateAssignment.shape[0]> 0:
                for plate in workflow.dfr_PlateAssignment.index:
                    plates.append(workflow.dfr_PlateAssignment.loc[plate,"TransferEntry"])
            else:
                no_plates = True
        else:
            no_plates = True
        if no_plates == True:
            wx.MessageBox("You have not imported any destination/assay plates, yet.\nImport plates and try again.",
                          "No plates",
                          wx.OK|wx.ICON_INFORMATION)
            return None
        if workflow.dfr_Layout.shape[0] == 0:
            workflow.dfr_Layout = pd.DataFrame()
    
    # Get number of wells
    if workflow.details["AssayType"].find("96") != -1:
        wells = 96
    else:
        wells = 384

    # Launch editor
    editor = PlateLayout(workflow,
                         plates = plates,
                         dfr_Layout = workflow.dfr_Layout, 
                         wells = wells,
                         global_layout = workflow.details["GlobalLayout"],
                         plateids = workflow.bol_PlateID,
                         references = workflow.details["References"],
                         controls = workflow.details["Controls"],
                         sampleids = False)
    editor.ShowModal()
    editor.Destroy()

 #####   #####  #####    ####   ##      ##      ##      ##   #####  ######
##      ##      ##  ##  ##  ##  ##      ##      ##      ##  ##        ##
 ####   ##      #####   ##  ##  ##      ##      ##      ##   ####     ##
    ##  ##      ##  ##  ##  ##  ##      ##      ##      ##      ##    ##
#####    #####  ##  ##   ####   ######  ######  ######  ##  #####     ##

class ScrollList(wx.ScrolledWindow):
    """
    Window containing a list of items, e.g. for control compounds,
    proteins, or references.
    Derived from class wx.ScrolledWindow.

    Methods:
        add_entry
        delete_entry
        delete_all_entries
    """
    def __init__(self, parent, plm, defaultitem, use_zprime):
        """
        Initialises class attributes.
        
        Arguments:
            parent -> parent object for wxPython GUI building.
            plm -> plate layout menu, this owns the dfr_Layout
                   dataframe and has the functions to update it.
        """
        wx.ScrolledWindow.__init__ (self, parent = parent, id = wx.ID_ANY,
                                    pos = wx.DefaultPosition, size = wx.Size(225,91),
                                    style = wx.TAB_TRAVERSAL|wx.VSCROLL, name = wx.EmptyString)
        self.parent = parent
        self.SetMinSize(wx.Size(225,91))
        self.SetScrollRate(5, 5)
        self.SetBackgroundColour(cs.BgLight)
        self.szr_Surround = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.szr_Surround)
        self.family = {}
        self.highlit = 0
        self.plm = plm
        self.entries = 0
        self.use_zprime = use_zprime
        self.defaultitem = defaultitem

        self.add_entry(self.defaultitem + u" 1", "10", True, use_zprime)

    def add_entry(self, name, conc, zprime = False, use_zprime = True):
        """
        Adds entry to file list.

        Arguments:
            name -> string. Name/ID of the control compound
            conc -> string. Concentration in uM
            zprime -> boolean. Whether to use the control to calculate
                      Z' values
        """
        index = len(self.family)
        self.family[index] = ListEntry(self, index = index,
                                       name = name,
                                       conc = conc,
                                       zprime = zprime,
                                       plm = self.plm,
                                       use_zprime = use_zprime)
        self.family[index].highlight_entry()
        self.szr_Surround.Add(self.family[index],0,wx.ALL,0)
        self.entries += 1
        self.Layout()
        self.parent.Layout()

    def delete_entry(self, entry):
        """
        Deletes one entry.
        Arguments:
            entry -> integer. Index of the entry to be removed.
        """
        if self.entries > 1:
            self.family[entry].Destroy()
            self.family.pop(entry)
            self.Layout()
            self.parent.Layout()
            # We need to reset the entries
            reset = {}
            n = 0
            for key in self.family.keys():
                reset[n] = self.family[key]
                reset[n].index = n
                reset[n].lbl_Index.SetLabel(str(n+1))
                n += 1
            self.family = reset
            self.entries -= 1
        else:
            wx.MessageBox("There are no items to remove.",
                "No items", wx.OK|wx.ICON_INFORMATION)
            
    def delete_all_entries(self):
        """
        Removes all file entries from list.
        """
        for entry in self.family:
            self.family[entry].Destroy()
        self.family = {}
        self.entries = 0
        self.Layout()
        self.parent.Layout()

class ListEntry(wx.Panel):
    """
    Entry for file list.

    Methods:
        highlight_entry -> changes appearance of entry to "hihglighted"
        standard -> cahnges appearance of entry back to default, not highlighted.
        on_left_down -> event handler for mouse event
        on_left_up -> event handler for mouse event
        on_right_down -> event handler for mouse event
        on_right_up -> event handler for mouse event
        on_rad_zprime -> event handler for ZPrime radio button
        update_name -> updates name property of the entry and layout dataframe
        update_conc -> updates conc property of the entry and layout dataframe

    """
    def __init__(self, parent, index, name, conc, zprime, plm, use_zprime):
        """
        Initialises class attributes.
        
        Arguments:
            parent -> parent object for wxPython GUI building.
            index -> int. Index of the item to be added
            name -> string. Name/ID of the control compound
            conc -> string. Concentration in uM
            zprime -> boolean. Whether to use the control to calculate
                      Z' values
            plm -> plate layout menu, this owns the dfr_Layout
                   dataframe and has the functions to update it.
        """
        wx.Panel.__init__ (self, parent = parent, id = wx.ID_ANY,
                           pos = wx.DefaultPosition, size = wx.Size(205,25),
                           style = wx.TAB_TRAVERSAL, name = wx.EmptyString)

        self.SetBackgroundColour(cs.BgLight)
        self.SetForegroundColour(cs.White)
        self.parent = parent
        self.index = index
        self.name = str(name)
        self.conc = str(conc)
        if type(zprime) == str:
            if zprime == "True":
                self.zprime = True
            else:
                self.zprime = False
        else:
            self.zprime = zprime
        self.highlit = True
        self.plm = plm
        self.use_zprime = use_zprime

        # Start building the entry:
        self.szr_Outside = wx.BoxSizer(wx.VERTICAL)
        self.pnl_Button = wx.Panel(self, size = wx.Size(205,25), style = wx.TAB_TRAVERSAL)
        self.pnl_Button.SetBackgroundColour(cs.BgMedium)
        self.szr_Inside = wx.BoxSizer(wx.HORIZONTAL)
        self.lbl_Index = wx.StaticText(self.pnl_Button,
                                       label = str(self.index + 1),
                                       size = wx.Size(14,22))
        self.szr_Inside.Add(self.lbl_Index, 0, wx.ALL, 2)
        self.txt_Name = wx.TextCtrl(self.pnl_Button,
                                    value = self.name,
                                    size = wx.Size(110,22))
        self.szr_Inside.Add(self.txt_Name, 0, wx.ALL, 2)
        self.txt_Conc = wx.TextCtrl(self.pnl_Button,
                                    value = self.conc,
                                    size = wx.Size(50,22))
        self.szr_Inside.Add(self.txt_Conc, 0, wx.ALL, 2)
        if self.use_zprime == True:
            self.rad_ZPrime = wx.RadioButton(self.pnl_Button,
                                            size = wx.Size(20,22))                                     
            self.rad_ZPrime.SetValue(self.zprime)
            self.szr_Inside.Add(self.rad_ZPrime, 0, wx.ALL, 2)

        self.pnl_Button.SetSizer(self.szr_Inside)
        self.pnl_Button.Layout()
        self.szr_Inside.Fit(self.pnl_Button)
        self.szr_Outside.Add(self.pnl_Button,0,wx.ALL,0)
        self.pnl_Line = wx.Panel(self, size = wx.Size(205,1), style = wx.TAB_TRAVERSAL)
        self.pnl_Line.SetBackgroundColour(cs.White)
        self.szr_Outside.Add(self.pnl_Line,0,wx.ALL,0)
        self.SetSizer(self.szr_Outside)
        self.Layout()

        ####  # #   # ####  # #   #  ####
        #   # # ##  # #   # # ##  # #  
        ####  # ##### #   # # ##### #  ##
        #   # # #  ## #   # # #  ## #   #
        ####  # #   # ####  # #   #  ###  ###############################################

        if self.use_zprime == True:
            self.rad_ZPrime.Bind(wx.EVT_RADIOBUTTON, self.on_rad_zprime)
            self.rad_ZPrime.Bind(wx.EVT_LEFT_DOWN, self.on_left_down)

        self.pnl_Button.Bind(wx.EVT_LEFT_DOWN, self.on_left_down)
        self.lbl_Index.Bind(wx.EVT_LEFT_DOWN, self.on_left_down)
        self.txt_Name.Bind(wx.EVT_LEFT_DOWN, self.on_left_down)
        self.txt_Name.Bind(wx.EVT_TEXT, self.update_name)
        self.txt_Conc.Bind(wx.EVT_LEFT_DOWN, self.on_left_down)
        self.txt_Conc.Bind(wx.EVT_TEXT, self.update_conc)

    def highlight_entry(self, event = None):
        """
        Event handler on mouse over. Sets visual appearance
        to 'highlighted'.
        """
        self.pnl_Button.SetBackgroundColour(cs.BgMedium)
        self.highlit = True
        self.parent.highlit = self.index
        self.Refresh()
        for i in range(self.parent.entries):
            if not self.parent.family[i].index == self.index:
                self.parent.family[i].standard(None)

    def standard(self, event):
        """
        Event handler on mouse leaving. Sets visual appearance
        to 'standard'.
        """
        self.pnl_Button.SetBackgroundColour(cs.BgLight)
        self.highlit = False
        self.Refresh()

    def on_left_down(self, event):
        """
        Event handler to change appearance on left mouse down.
        """
        self.highlight_entry()
        self.Refresh()
        event.Skip()

    def on_left_up(self, event):
        """
        Event handler to change appearance on left mouse up.
        """
        self.pnl_Button.SetBackgroundColour(cs.BgDark)
        self.Refresh()

    def on_right_down(self, event):
        """
        Event handler for right mouse down. Passes.
        """
        pass
    
    def on_right_up(self, event):
        """
        Event handler for right mouse up. Opens context menu.
        """
        pass

    def on_rad_zprime(self, event):
        """
        Event handler for ZPrime radio button.
        Updates ZPrime status for controls.
        """

        if event.GetEventObject().GetValue() == True:
            self.zprime = True
            for key in self.parent.family.keys():
                if not self.parent.family[key].index == self.index:
                    self.parent.family[key].rad_ZPrime.SetValue(False)
                    self.parent.family[key].zprime = False
        self.plm.update_dataframe()

    def update_name(self, event):
        """
        Event handler. Updates "name" property of the entry and updates the
        layout dataframe.
        """
        self.name = self.txt_Name.GetValue()
        self.plm.update_dataframe()

    def update_conc(self, event):
        """
        Event handler. Updates "conc" property of the entry and updates the
        layout dataframe.
        """
        self.conc = self.txt_Conc.GetValue()
        self.plm.update_dataframe()
            

class PlateLayout(wx.Dialog):
    """
    Window to define plate layouts: well types (sample, reference,
    control), sample IDs, proteins, plate IDs.
    
    If user closes window via "Apply and Close", a dataframe with
    plates as index and the following columns is saved to the parent
    object: "PlateID",
            "ProteinNumerical",
            "ProteinID",
            "ProteinConcentration",
            "ControlNumerical",
            "ControlID",
            "ControlConcentration"
            "WellType",
            "SampleID"

    Methods:
        __init__
        change_tab
        on_mouse_move
        on_left_down
        on_left_up
        add_protein
        remove_protein
        add_control
        remove_control
        import_layout
        export_layout
        apply_and_close
        cancel
        context_menu_plate
        get_selection_plate
        on_mouseover_plate
        paint_sample
        paint_control
        paint_reference
        paint_blank
        clear_plate
        paint_cells
        write_protein
        get_well_type
        get_well_colour
        get_text_colour
        create_dataframe
        update_dataframe
        update_display
        update_plateid
        show_samples_context
        get_samples_selection
        on_wellchange_samples
        on_keypress_samples
        GetGridSelectionSamples
        GridCopy
        GridCut
        GridClear
        grid_paste
        SingleSelectionSamples

    """

    def __init__(self, parent, plates, dfr_Layout: pd.DataFrame, wells: int,
                 global_layout = True, plateids = False, proteins = True,
                 references = True, controls = False, sampleids = False):
        """
        Initialises class attributes

        Arguments:
            parent -> parent object in GUI.
            plates -> list of plate names.
            dfr_Layout -> pandas dataframe. If a plate layout has
                          already been defined, the contents of
                          this dataframe will be displayed.
            global_layout -> boolean. Whether this dialog is to set up
                         a single plate's layout or whether to
                         prepare multiple layouts.
            wells -> integer. Plate format in number of wells.
            plateid -> boolean. Whether plate IDs are used for
                       generating a platemap for the database.
                       Specific to our org.
            references -> boolean. Use reference wells.
            controls -> boolean. Use control compounds/wells.
        """

        self.bol_proteins = proteins
        self.bol_controls = controls
        self.bol_references = references
        self.bol_sampleids = sampleids
        if self.bol_proteins == True:
            self.show_in_cells = "proteins"
        elif self.bol_controls == True:
            self.show_in_cells = "controls"
        else:
            self.show_in_cells = None
        # Variables for sizing of elements ##############################################
        self.plateformat = wells
        self.PlateID = plateids
        if self.plateformat == 96:
            int_CellSize = 31
            int_XSizeModifier = 0
            int_YSizeModifier = +7
            int_SampleIDX = 402
            int_SampleIDY = 310
        elif self.plateformat == 384:
            int_CellSize = 17
            int_XSizeModifier = 24
            int_YSizeModifier = 0
            int_SampleIDX = 430
            int_SampleIDY = 320
        elif self.plateformat == 1536:
            int_CellSize = 9
            int_XSizeModifier = +35
            int_YSizeModifier = +10
            int_SampleIDX = 440
            int_SampleIDY = 330
        if self.PlateID == True:
            int_PlateIDOffset = 0
        else:
            int_PlateIDOffset = -7
        if global_layout == False:
            self.bol_MultiplePlates = True
            WindowSize = wx.Size(850 + int_XSizeModifier,
                                 445 + int_YSizeModifier + int_PlateIDOffset)
            int_Plates = len(plates)
        elif global_layout == True:
            self.bol_MultiplePlates = False
            WindowSize = wx.Size(680 + int_XSizeModifier,
                                 445 + int_YSizeModifier + int_PlateIDOffset)
            int_Plates = 1
        self.currentplate = 0

        # Initialise ####################################################################
        wx.Frame.__init__ (self, parent, id = wx.ID_ANY, title = wx.EmptyString,
                           pos = wx.DefaultPosition, size = WindowSize,
                           style = wx.TAB_TRAVERSAL)

        # Get the current directory and use that for the buttons
        real_path = os.path.realpath(__file__)
        dir_path = os.path.dirname(real_path)
        str_MenuIconsPath = dir_path + r"\menuicons"

        self.SetSizeHints(wx.DefaultSize, wx.DefaultSize)

        self.szr_Frame = wx.BoxSizer(wx.VERTICAL)
        self.pnl_Panel = wx.Panel(self)
        self.pnl_Panel.SetBackgroundColour(cs.BgMedium)

        self.szr_Surround = wx.BoxSizer(wx.VERTICAL)
        # TITLE BAR #####################################################################
        self.pnl_TitleBar = wx.Panel(self.pnl_Panel)
        self.pnl_TitleBar.SetBackgroundColour(cs.BgUltraDark)
        self.pnl_TitleBar.SetForegroundColour(cs.White)
        self.szr_TitleBar = wx.BoxSizer(wx.HORIZONTAL)
        self.lbl_Title = wx.StaticText(self.pnl_TitleBar, label= u"Define plate layout")
        self.lbl_Title.Wrap(-1)
        self.szr_TitleBar.Add( self.lbl_Title, 0, wx.ALL, 5 )
        self.szr_TitleBar.Add((0,0), 1, wx.EXPAND, 5)
        self.btn_X = btn.CustomBitmapButton(self.pnl_TitleBar,
                                        name = "small_x",
                                        index = 0,
                                        size = (25,25),
                                        pathaddendum = u"titlebar")
        self.szr_TitleBar.Add(self.btn_X,0,wx.ALL,0)
        self.pnl_TitleBar.SetSizer(self.szr_TitleBar)
        self.pnl_TitleBar.Layout()
        self.szr_Surround.Add(self.pnl_TitleBar, 0, wx.EXPAND, 5)

        self.szr_Contents = wx.BoxSizer(wx.HORIZONTAL)

        # Side panel for multiple plates
        if self.bol_MultiplePlates == True:
            self.pnl_PlateList = wx.Panel(self.pnl_Panel)
            self.pnl_PlateList.SetBackgroundColour(cs.BgLight)
            self.szr_PlateList = wx.BoxSizer(wx.VERTICAL)
            self.lbl_PlateList = wx.StaticText(self.pnl_PlateList, label = u"Plates:")
            self.lbl_PlateList.Wrap(-1)
            self.szr_PlateList.Add(self.lbl_PlateList, 0, wx.ALL, 5)
            self.lbx_PlateList = wx.ListBox(self.pnl_PlateList,
                                            size = wx.Size(150,280),
                                            choices = [])
            self.szr_PlateList.Add(self.lbx_PlateList, 1, wx.ALL, 5)
            self.pnl_PlateList.SetSizer(self.szr_PlateList)
            self.pnl_PlateList.Layout()
            self.szr_Contents.Add(self.pnl_PlateList, 1, wx.ALL, 5)
            self.lbx_PlateList.InsertItems(plates,0)
            self.lbx_PlateList.Select(0)
            self.lbx_PlateList.Bind(wx.EVT_LISTBOX, self.update_display)

        # PLATE MAP GRID
        self.szr_LayoutAndSamples = wx.BoxSizer(wx.VERTICAL)
        self.szr_PlateNoteBookButtons = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_PlateLayout = btn.MiniTabButton(self.pnl_Panel,
                                             change_tab_owner = self,
                                             label = u"Plate Layout",
                                             index = 0)
        self.btn_PlateLayout.IsCurrent(True)
        self.btn_SampleIDs = btn.MiniTabButton(self.pnl_Panel,
                                           change_tab_owner = self,
                                           label = u"Sample IDs",
                                           index = 1)
        self.btn_SampleIDs.IsEnabled(self.bol_sampleids)
        self.dic_PlateNoteBookButtons = {0:self.btn_PlateLayout,
                                         1:self.btn_SampleIDs}
        self.btn_PlateLayout.Group = self.dic_PlateNoteBookButtons
        self.btn_SampleIDs.Group = self.dic_PlateNoteBookButtons
        self.sbk_LayoutAndSamples = wx.Simplebook(self.pnl_Panel)
        self.btn_PlateLayout.Notebook = self.sbk_LayoutAndSamples
        self.btn_SampleIDs.Notebook = self.sbk_LayoutAndSamples
        self.szr_PlateNoteBookButtons.Add(self.btn_PlateLayout, 0, wx.ALL, 0)
        self.szr_PlateNoteBookButtons.Add(self.btn_SampleIDs, 0, wx.ALL, 0)
        self.szr_LayoutAndSamples.Add(self.szr_PlateNoteBookButtons, 0, wx.ALL, 0)

        # Simple book page: Plate Layout
        self.pnl_PlateMap = wx.Panel(self.sbk_LayoutAndSamples)
        self.pnl_PlateMap.SetBackgroundColour(cs.BgLight)
        self.szr_Grid = wx.BoxSizer(wx.VERTICAL)
        self.szr_PlateID = wx.BoxSizer(wx.HORIZONTAL)
        if proteins == True:
            cells_are = u"Cell labels: Proteins"
        elif controls == True:
            cells_are = u"Cell labels: Controls"
        self.lbl_Cells = wx.StaticText(self.pnl_PlateMap, label = cells_are)
        self.szr_PlateID.Add(self.lbl_Cells, 0, wx.ALL, 5)
        self.szr_PlateID.Add((-1,22), 1, wx.EXPAND, 5)
        if self.PlateID == True:
            self.lbl_PlateID = wx.StaticText(self.pnl_PlateMap,
                                             label = u"Plate ID:",
                                             size = wx.Size(-1,22))
            self.szr_PlateID.Add(self.lbl_PlateID, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
            self.txt_PlateID = wx.TextCtrl(self.pnl_PlateMap,
                                           value = u"X999A",
                                           size = wx.Size(55,22))
            self.txt_PlateID.SetBackgroundColour(cs.BgUltraLight)
            self.szr_PlateID.Add(self.txt_PlateID, 0, wx.ALL, 5)
        self.szr_Grid.Add(self.szr_PlateID, 1, wx.EXPAND, 0)
        self.grd_Plate = wx.grid.Grid(self.pnl_PlateMap)
        # Parameters for grid
        int_Columns = pf.plate_columns(self.plateformat)
        int_Rows = pf.plate_rows(self.plateformat)
        # Grid
        self.grd_Plate.CreateGrid(int_Rows, int_Columns)
        self.grd_Plate.EnableEditing(False)
        self.grd_Plate.EnableGridLines(True)
        self.grd_Plate.EnableDragGridSize(False)
        self.grd_Plate.SetMargins(0, 0)
        # Columns
        self.grd_Plate.SetColMinimalAcceptableWidth(int_CellSize)
        for i in range(int_Columns):
            self.grd_Plate.SetColSize(i, int_CellSize)
            self.grd_Plate.SetColLabelValue(i, str(i+1))
        self.grd_Plate.EnableDragColMove(False)
        self.grd_Plate.EnableDragColSize(False)
        self.grd_Plate.SetColLabelSize(int_CellSize)
        self.grd_Plate.SetColLabelAlignment(wx.ALIGN_CENTER, wx.ALIGN_CENTER)
        # Rows
        self.grd_Plate.SetRowMinimalAcceptableHeight(int_CellSize)
        for i in range(int_Rows):
            self.grd_Plate.SetRowSize(i, int_CellSize)
            self.grd_Plate.SetRowLabelValue(i, chr(65+i))
        self.grd_Plate.EnableDragRowSize(False)
        self.grd_Plate.SetRowLabelSize(int_CellSize)
        self.grd_Plate.SetRowLabelAlignment(wx.ALIGN_CENTER, wx.ALIGN_CENTER)
        # Label Appearance
        # Cell Defaults
        self.grd_Plate.SetDefaultCellAlignment(wx.ALIGN_CENTER, wx.ALIGN_CENTER)
        self.szr_Grid.Add(self.grd_Plate, 0, wx.ALL, 5)
        self.pnl_PlateMap.SetSizer(self.szr_Grid)
        self.sbk_LayoutAndSamples.AddPage(self.pnl_PlateMap, text = u"Plate Map",
                                          select = True)

        self.szr_LayoutAndSamples.Add(self.sbk_LayoutAndSamples, 0, wx.ALL, 0)

        # SimpleBook Page: Sample IDs
        self.pnl_SampleIDs = wx.Panel(self.sbk_LayoutAndSamples)
        self.pnl_SampleIDs.SetBackgroundColour(cs.BgLight)
        self.szr_SampleIDs = wx.BoxSizer(wx.VERTICAL)
        self.grd_SampleIDs = wx.grid.Grid(self.pnl_SampleIDs,
                                          size = wx.Size(int_SampleIDX,int_SampleIDY))
        # Parameters for grid
        int_CellSize = 20
        # Grid
        self.grd_SampleIDs.CreateGrid(self.plateformat, 2 )
        self.grd_SampleIDs.EnableEditing(True)
        self.grd_SampleIDs.EnableGridLines(True)
        self.grd_SampleIDs.EnableDragGridSize(False)
        self.grd_SampleIDs.SetMargins(0, 0)
        # Columns
        self.grd_SampleIDs.SetColMinimalAcceptableWidth(int_CellSize)
        self.grd_SampleIDs.SetColSize(0, 50)
        self.grd_SampleIDs.SetColLabelValue(0, "Well")
        self.grd_SampleIDs.SetColSize(1, int_SampleIDX - 100)
        self.grd_SampleIDs.SetColLabelValue(1, "Sample ID")
        self.grd_SampleIDs.EnableDragColMove(False)
        self.grd_SampleIDs.EnableDragColSize(False)
        self.grd_SampleIDs.SetColLabelSize(int_CellSize)
        self.grd_SampleIDs.SetColLabelAlignment(wx.ALIGN_CENTER, wx.ALIGN_CENTER)
        # Rows
        self.grd_SampleIDs.SetRowMinimalAcceptableHeight(int_CellSize)
        self.grd_SampleIDs.SingleSelection = (0,0)
        for i in range(self.plateformat):
            self.grd_SampleIDs.SetRowSize(i, int_CellSize)
            self.grd_SampleIDs.SetRowLabelValue(i, str(i+1))
        self.grd_SampleIDs.EnableDragRowSize(False)
        self.grd_SampleIDs.SetRowLabelSize(30)
        self.grd_SampleIDs.SetRowLabelAlignment(wx.ALIGN_CENTER, wx.ALIGN_CENTER)
        # Label Appearance
        # Cell Defaults
        self.grd_SampleIDs.SetDefaultCellAlignment(wx.ALIGN_CENTER, wx.ALIGN_CENTER)
        self.szr_SampleIDs.Add(self.grd_SampleIDs, 0, wx.ALL, 5)
        self.pnl_SampleIDs.SetSizer(self.szr_SampleIDs)
        self.pnl_SampleIDs.Layout()
        self.szr_SampleIDs.Fit(self.pnl_SampleIDs)
        self.sbk_LayoutAndSamples.AddPage(self.pnl_SampleIDs, text = u"Sample IDs",
                                          select = False)

        self.szr_Contents.Add(self.szr_LayoutAndSamples, 0, wx.ALL, 5)
        
        # Right Sizer ###################################################################
        self.szr_Right = wx.BoxSizer(wx.VERTICAL)
        
        self.szr_Definitions = wx.BoxSizer(wx.VERTICAL)
        self.szr_SimpleButtons = wx.BoxSizer(wx.HORIZONTAL)
        # Define simplebook now, add elements to it and add it
        # to the dialog later.
        self.sbk_Definitions = wx.Simplebook(self.pnl_Panel,
                                             size = wx.Size(235,-1))
        self.dic_DefinitionsButtons = {}

        # Proteins
        self.btn_Proteins = btn.MiniTabButton(self.pnl_Panel,
                                          change_tab_owner = self,
                                          label = u"Proteins",
                                          index = 0)
        self.dic_DefinitionsButtons["Proteins"] = self.btn_Proteins
        self.btn_Proteins.Notebook = self.sbk_Definitions
        self.btn_Proteins.Group = self.dic_DefinitionsButtons
        self.btn_Proteins.IsEnabled(self.bol_proteins)
        self.szr_SimpleButtons.Add(self.btn_Proteins, 0, wx.ALL, 0)
        # Prepare Protein list:
        self.pnl_ProteinList = wx.Panel(self.sbk_Definitions)
        self.pnl_ProteinList.SetBackgroundColour(cs.BgLight)
        self.szr_ProteinList = wx.BoxSizer(wx.VERTICAL)
        self.szr_ProteinTitleAndList = wx.BoxSizer(wx.VERTICAL)
        self.lbl_ProteinList = wx.StaticText(self.pnl_ProteinList, wx.ID_ANY,
                u"To add a new control, select wells on the plate map to the left and press \"Add new.\"")
        self.lbl_ProteinList.Wrap(225)
        self.szr_ProteinTitleAndList.Add(self.lbl_ProteinList, 0, wx.ALL, 0)
        self.szr_ProteinHeaders = wx.BoxSizer(wx.HORIZONTAL)
        self.lbl_Index = wx.StaticText(self.pnl_ProteinList,
                                       label = u"",
                                       size = wx.Size(14,22))
        self.szr_ProteinHeaders.Add(self.lbl_Index, 0, wx.ALL, 2)
        self.lbl_ProteinName = wx.StaticText(self.pnl_ProteinList,
                                    label = u"Name",
                                    size = wx.Size(110,22))
        self.szr_ProteinHeaders.Add(self.lbl_ProteinName, 0, wx.ALL, 2)
        self.lbl_ProteinConc = wx.StaticText(self.pnl_ProteinList,
                                    label = u"(uM)",
                                    size = wx.Size(50,22))
        self.szr_ProteinHeaders.Add(self.lbl_ProteinConc, 0, wx.ALL, 2)
        self.szr_ProteinTitleAndList.Add(self.szr_ProteinHeaders, 0, wx.ALL, 0)
        self.scr_ProteinList = ScrollList(self.pnl_ProteinList,
                                          self,
                                          defaultitem = u"Protein",
                                          use_zprime = False)
        self.szr_ProteinTitleAndList.Add(self.scr_ProteinList, 0, wx.ALL, 0)
        self.szr_ProteinList.Add(self.szr_ProteinTitleAndList, 0, wx.ALL, 5)
        # Buttons
        self.szr_ProteinButtons = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_ProteinButtons.Add((55, 0), 1, wx.ALL, 0)
        self.btn_AddProtein = btn.CustomBitmapButton(self.pnl_ProteinList, u"Add", 0, (75,30))
        self.szr_ProteinButtons.Add(self.btn_AddProtein, 0, wx.ALL, 0)
        self.szr_ProteinButtons.Add((5, 0), 1, wx.EXPAND, 0)
        self.btn_RemoveProtein = btn.CustomBitmapButton(self.pnl_ProteinList, u"Remove", 0, (90,30))
        self.szr_ProteinButtons.Add(self.btn_RemoveProtein, 0, wx.ALL, 0)
        self.szr_ProteinList.Add(self.szr_ProteinButtons, 0, wx.ALL, 5)
        self.pnl_ProteinList.SetSizer(self.szr_ProteinList)
        self.pnl_ProteinList.Layout()
        self.sbk_Definitions.AddPage(self.pnl_ProteinList,
                                     text = u"Protein",
                                     select = True)
        # Controls
        self.btn_Controls = btn.MiniTabButton(self.pnl_Panel,
                                          change_tab_owner = self,
                                          label = u"Controls",
                                          index = 1)
        self.dic_DefinitionsButtons["Controls"] = self.btn_Controls
        self.btn_Controls.IsEnabled(self.bol_controls)
        self.btn_Controls.Notebook = self.sbk_Definitions
        self.btn_Controls.Group = self.dic_DefinitionsButtons
        self.szr_SimpleButtons.Add(self.btn_Controls, 0, wx.ALL, 0)
        # Control List
        self.pnl_ControlList = wx.Panel(self.sbk_Definitions)
        self.pnl_ControlList.SetBackgroundColour(cs.BgLight)
        self.szr_ControlList = wx.BoxSizer(wx.VERTICAL)
        self.szr_CtrlTitleAndList = wx.BoxSizer(wx.VERTICAL)
        self.lbl_ControlList = wx.StaticText(self.pnl_ControlList, wx.ID_ANY,
                u"To add a new control, select wells on the plate map to the left and press \"Add new.\"")
        self.lbl_ControlList.Wrap(225)
        self.szr_CtrlTitleAndList.Add(self.lbl_ControlList, 0, wx.ALL, 0)
        self.szr_CtrlHeaders = wx.BoxSizer(wx.HORIZONTAL)
        self.lbl_Index = wx.StaticText(self.pnl_ControlList,
                                       label = u"",
                                       size = wx.Size(14,22))
        self.szr_CtrlHeaders.Add(self.lbl_Index, 0, wx.ALL, 2)
        self.lbl_Name = wx.StaticText(self.pnl_ControlList,
                                    label = u"Name",
                                    size = wx.Size(110,22))
        self.szr_CtrlHeaders.Add(self.lbl_Name, 0, wx.ALL, 2)
        self.lbl_Conc = wx.StaticText(self.pnl_ControlList,
                                    label = u"(uM)",
                                    size = wx.Size(50,22))
        self.szr_CtrlHeaders.Add(self.lbl_Conc, 0, wx.ALL, 2)
        self.lbl_ZPrime = wx.StaticText(self.pnl_ControlList,
                                         label = u"Z'",
                                         size = wx.Size(20,22))
        self.szr_CtrlHeaders.Add(self.lbl_ZPrime, 0, wx.ALL, 2)
        self.szr_CtrlTitleAndList.Add(self.szr_CtrlHeaders, 0, wx.ALL, 0)
        self.scr_ControlList = ScrollList(self.pnl_ControlList,
                                          self,
                                          defaultitem = u"Control",
                                          use_zprime = True)
        self.szr_CtrlTitleAndList.Add(self.scr_ControlList, 0, wx.ALL, 0)
        self.szr_ControlList.Add(self.szr_CtrlTitleAndList, 0, wx.ALL, 5)
        # Buttons
        self.szr_ControlButtons = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_ControlButtons.Add((55, 0), 1, wx.ALL, 0)
        self.btn_AddControl = btn.CustomBitmapButton(self.pnl_ControlList, u"Add", 0, (75,30))
        self.szr_ControlButtons.Add(self.btn_AddControl, 0, wx.ALL, 0)
        self.szr_ControlButtons.Add((5, 0), 1, wx.ALL, 0)
        self.btn_RemoveControl = btn.CustomBitmapButton(self.pnl_ControlList, u"Remove", 0, (90,30))
        self.szr_ControlButtons.Add(self.btn_RemoveControl, 0, wx.ALL, 0)
        self.szr_ControlList.Add(self.szr_ControlButtons, 0, wx.ALL, 5)
        self.pnl_ControlList.SetSizer(self.szr_ControlList)
        self.pnl_ControlList.Layout()
        self.sbk_Definitions.AddPage(self.pnl_ControlList,
                                     text = u"Control",
                                     select = True)
        # Initialise the simplebook:
        if self.bol_controls == True:
            self.btn_Proteins.IsCurrent(False)
            self.btn_Controls.IsCurrent(True)
            self.sbk_Definitions.SetSelection(1)
        if self.bol_proteins == True:
            self.btn_Proteins.IsCurrent(True)
            self.btn_Controls.IsCurrent(False)
            self.sbk_Definitions.SetSelection(0)

        self.szr_Definitions.Add(self.szr_SimpleButtons, 0, wx.ALL, 0)
        self.szr_Definitions.Add(self.sbk_Definitions, 0, wx.ALL, 0)

        self.szr_Right.Add(self.szr_Definitions, 0, wx.ALL, 5)

        # Samples and References
        self.pnl_SamplesAndReferences = wx.Panel(self.pnl_Panel,
                                                 size = wx.Size(245,-1))
        self.pnl_SamplesAndReferences.SetBackgroundColour(cs.BgLight)
        self.szr_SamplesAndReferences = wx.BoxSizer(wx.VERTICAL)
        self.lbl_SamplesAndReferences = wx.StaticText(self.pnl_SamplesAndReferences,
            label = u"Sample and reference wells:\n" 
            + u"To define sample and reference wells,\n"
            + u"select intended wells, right click, and select appropriate option.")
        self.lbl_SamplesAndReferences.Wrap(240)
        self.szr_SamplesAndReferences.Add(self.lbl_SamplesAndReferences, 0, wx.ALL, 5)
        self.szr_Legend = wx.BoxSizer(wx.HORIZONTAL)
        self.png_Sample = wx.StaticBitmap(self.pnl_SamplesAndReferences, 
                                          bitmap = wx.Bitmap(str_MenuIconsPath
                                                             + u"\GridSample.png",
                                                              wx.BITMAP_TYPE_ANY ))
        self.szr_Legend.Add(self.png_Sample, 0, wx.ALL, 0)
        self.lbl_Sample = wx.StaticText(self.pnl_SamplesAndReferences, 
                                        label = u" Sample  ")
        self.szr_Legend.Add(self.lbl_Sample, 0, wx.ALL, 0)
        if references == True:
            self.png_Reference = wx.StaticBitmap(self.pnl_SamplesAndReferences, 
                                                 bitmap = wx.Bitmap(str_MenuIconsPath
                                                                     + u"\GridReference.png",
                                                                     wx.BITMAP_TYPE_ANY ))
            self.szr_Legend.Add(self.png_Reference, 0, wx.ALL, 0)
            self.lbl_Reference = wx.StaticText(self.pnl_SamplesAndReferences,
                                               label = u" Reference  ")
            self.szr_Legend.Add(self.lbl_Reference, 0, wx.ALL, 0)
        if controls == True:
            self.png_Control = wx.StaticBitmap(self.pnl_SamplesAndReferences,
                                               bitmap = wx.Bitmap(str_MenuIconsPath
                                                                  + u"\GridControl.png",
                                                                  wx.BITMAP_TYPE_ANY ))
            self.szr_Legend.Add(self.png_Control, 0, wx.ALL, 0)
            self.lbl_Control = wx.StaticText(self.pnl_SamplesAndReferences,
                                             label = u" Control  ")
            self.szr_Legend.Add(self.lbl_Control, 0, wx.ALL, 0)
        self.szr_SamplesAndReferences.Add(self.szr_Legend, 0, wx.ALL, 5)
        self.pnl_SamplesAndReferences.SetSizer(self.szr_SamplesAndReferences)
        self.pnl_SamplesAndReferences.Layout()
        self.szr_Right.Add(self.pnl_SamplesAndReferences,0,wx.ALL,5)
        
        self.szr_Contents.Add(self.szr_Right, 0, wx.EXPAND, 5)
        self.szr_Surround.Add(self.szr_Contents, 0, wx.ALL, 0)

        
        # Dividing line #################################################################
        self.line = wx.StaticLine(self.pnl_Panel)
        self.szr_Surround.Add(self.line, 0, wx.EXPAND|wx.ALL, 5)

        # Button bar at bottom
        self.szr_ButtonBar = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_Import = btn.CustomBitmapButton(self.pnl_Panel, u"Import", 0, (100,30))
        self.szr_ButtonBar.Add(self.btn_Import, 0, wx.ALL, 5)
        self.btn_Export = btn.CustomBitmapButton(self.pnl_Panel, u"Export", 0, (100,30))
        self.szr_ButtonBar.Add(self.btn_Export, 0, wx.ALL, 5)
        self.szr_ButtonBar.Add( ( 0, 0), 1, wx.EXPAND, 5 )
        self.btn_Apply = btn.CustomBitmapButton(self.pnl_Panel, u"ApplyAndClose", 0, (100,30))
        self.szr_ButtonBar.Add(self.btn_Apply, 0, wx.ALL, 5)
        self.btn_Cancel = btn.CustomBitmapButton(self.pnl_Panel, u"Cancel", 0, (100,30))
        self.szr_ButtonBar.Add(self.btn_Cancel, 0, wx.ALL, 5)
        self.szr_Surround.Add(self.szr_ButtonBar, 0, wx.ALL|wx.EXPAND, 0)
    
        self.pnl_Panel.SetSizer(self.szr_Surround)
        self.pnl_Panel.Layout()
        self.szr_Frame.Add(self.pnl_Panel,0,wx.EXPAND,0)

        self.SetSizer( self.szr_Frame )
        self.Layout()
        self.Centre( wx.BOTH )

        # Populate:
        if len(dfr_Layout) == 0:
            self.dfr_Layout = pd.DataFrame(index=range(int_Plates),
                                           columns=["PlateID",
                                                    "Layout"])

            for plate in range(int_Plates):
                if self.PlateID == True:
                    self.dfr_Layout.loc[plate,"PlateID"] = self.txt_PlateID.GetValue()
                else:
                    self.dfr_Layout.loc[plate,"PlateID"] = "X999A"
                self.dfr_Layout.at[plate,"Layout"] = pd.DataFrame(index=range(self.plateformat),
                                                columns = ["WellType",
                                                           "ProteinNumerical",
                                                           "ProteinID",
                                                           "ProteinConcentration",
                                                           "ControlNumerical",
                                                           "ControlID",
                                                           "ControlConcentration",
                                                           "ZPrime",
                                                           "ReferenceNumerical",
                                                           "ReferenceID",
                                                           "ReferenceConcentration",
                                                           "SampleNumerical",
                                                           "SampleID",
                                                           "SampleConcentration"])
        else:
            self.dfr_Layout = dfr_Layout
            self.update_display()

        # Connect Events ################################################################
        self.grd_Plate.GetGridWindow().Bind(wx.EVT_MOTION, self.on_mouseover_plate)
        self.grd_Plate.Bind(wx.grid.EVT_GRID_CELL_RIGHT_CLICK, self.context_menu_plate)
        self.grd_SampleIDs.Bind(wx.grid.EVT_GRID_SELECT_CELL, self.SingleSelectionSamples)
        self.grd_SampleIDs.Bind(wx.grid.EVT_GRID_CELL_RIGHT_CLICK, self.show_samples_context)
        self.grd_SampleIDs.Bind(wx.EVT_KEY_DOWN, self.on_keypress_samples)
        self.grd_SampleIDs.Bind(wx.grid.EVT_GRID_CELL_CHANGED, self.on_wellchange_samples)
        self.btn_AddProtein.Bind(wx.EVT_BUTTON, self.add_protein)
        self.btn_RemoveProtein.Bind(wx.EVT_BUTTON, self.remove_protein)
        self.btn_AddControl.Bind(wx.EVT_BUTTON, self.add_control)
        self.btn_RemoveControl.Bind(wx.EVT_BUTTON, self.remove_control)
        self.sbk_Definitions.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.on_changed_definitions)
        if self.PlateID == True:
            self.txt_PlateID.Bind(wx.EVT_TEXT, self.update_plateid)
        self.btn_Import.Bind(wx.EVT_BUTTON, self.import_layout)
        self.btn_Export.Bind(wx.EVT_BUTTON, self.export_layout)
        self.btn_Apply.Bind(wx.EVT_BUTTON, lambda event: self.apply_and_close(parent, event))
        self.btn_Cancel.Bind(wx.EVT_BUTTON, self.cancel)
        self.btn_X.Bind(wx.EVT_BUTTON, self.cancel)

        # Required for window dragging:
        self.delta = wx.Point(0,0)
        self.pnl_TitleBar.Bind(wx.EVT_LEFT_DOWN, self.on_left_down)
        self.lbl_Title.Bind(wx.EVT_LEFT_DOWN, self.on_left_down)
        self.Bind(wx.EVT_LEFT_UP, self.on_left_up)
        self.Bind(wx.EVT_MOTION, self.on_mouse_move)
        self.dragging = False


    def __del__( self ):
        pass

    def change_tab(self, fnord):
        """
        Dummy function required when using btn.MiniTabButtons.
        Would normally perform chekcs to see whether changing
        tabs would be allowed.
        """
        return True
    
    def on_changed_definitions(self, event):
        """
        Event handler. Will update the display in the cells based on
        which definition tab (Proteins or Controls) is active.
        """
        event.Skip()
        self.Freeze()
        # Get plate index
        if self.bol_MultiplePlates == True and self.dfr_Layout.shape[0] > 1:
            plate = self.lbx_PlateList.GetSelection()
        else:
            plate = 0

        prows = pf.plate_rows(self.plateformat)
        pcols = pf.plate_columns(self.plateformat)
        
        notebook = event.GetEventObject()
        page = notebook.GetSelection()
        page_text = notebook.GetPageText(page)

        self.rewrite_all_cell_contents(page_text, plate, prows, pcols)
        self.lbl_Cells.SetLabel(f"Cell labels: {page_text}s")

        self.Thaw()

    # The following three function are taken from a tutorial on the wxPython Wiki: https://wiki.wxpython.org/How%20to%20create%20a%20customized%20frame%20-%20Part%201%20%28Phoenix%29
    # They have been modified if and where appropriate.

    def on_mouse_move(self, event):
        """
        Changes position of window based on mouse movement
        if left mouse button is down on titlebar.
        """
        if self.dragging == True:
            if event.Dragging() and event.LeftIsDown():
                x,y = self.ClientToScreen(event.GetPosition())
                newPos = (x - self.delta[0], y - self.delta[1])
                self.Move(newPos)
        else:
            return None

    def on_left_down(self, event):
        """
        Initiates all required properties for window dragging.
        """
        self.CaptureMouse()
        x, y = self.ClientToScreen(event.GetPosition())
        originx, originy = self.GetPosition()
        dx = x - originx
        dy = y - originy
        self.delta = [dx, dy]
        self.dragging = True

    def on_left_up(self, event):
        """
        Releases mouse capture and resets property for window
        dragging.
        """
        if self.HasCapture():
            self.ReleaseMouse()
        self.dragging = False

    def add_protein(self, event):
        """
        Adds a protein to the list and updates dataframe.
        Selecting wells on plate layout is required.
        """
        self.scr_ProteinList.add_entry(f"Protein {self.scr_ProteinList.entries+1}",
                                       conc = "10",
                                       use_zprime = False)

        # Only if the proteins tab is currently shown (i.e. the button is "Current")
        # and wells are indeed selected do we want to write the numerical ID onto
        # the plate layout.
        if self.btn_Proteins.Current == True:
            lst_Selection = self.get_selection_plate()
            if len(lst_Selection) > 0:
                for i in range(len(lst_Selection)):
                    self.grd_Plate.SetCellValue(lst_Selection[i][0],
                                                lst_Selection[i][1],
                                                str(self.scr_ProteinList.entries))
                    self.write_protein(None, None, self.scr_ProteinList.entries, False)
            else:
                wx.MessageBox("You have not selected any wells, could not assign protein to wells.\nSelect wells and try again.",
                    "No wells", wx.OK|wx.ICON_INFORMATION)

    def remove_protein(self, event):
        """
        Removes selected protein from protein list and
        clears all corresponding wells on plate layout,
        updates dataframe.
        """
        prot = self.scr_ProteinList.highlit
        self.scr_ProteinList.delete_entry(prot)
        self.update_dataframe()

        # Only if the proteins tab is currently shown (i.e. the button is "Current")
        # do we want to remove the numerical ID from the plate layout.
        if self.btn_Proteins.Current == True:
            for row in range(self.grd_Plate.GetNumberRows()):
                for col in range(self.grd_Plate.GetNumberCols()):
                    if self.grd_Plate.GetCellValue(row,col) == str(prot+1):
                        self.grd_Plate.SetCellValue(row,col,"")
                        self.grd_Plate.SetCellBackgroundColour(row,col,cs.White)
                    elif self.grd_Plate.GetCellValue(row,col) != "" and int(self.grd_Plate.GetCellValue(row,col)) > prot+1:
                        self.grd_Plate.SetCellValue(row,col,str(int(self.grd_Plate.GetCellValue(row,col))-1))

    def add_control(self, event):
        """
        Adds a control to the list and updates dataframe.
        """
        if self.scr_ControlList.entries == 0:
            zprime = True
        else:
            zprime = False
        self.scr_ControlList.add_entry(f"Control {self.scr_ControlList.entries+1}",
                                       conc = "10",
                                       zprime = zprime)
        
        # Only if the controls tab is currently shown (i.e. the button is "Current")
        # and wells are indeed selected do we want to write the numerical ID onto
        # the plate layout.
        if self.btn_Controls.Current == True:
            selection = self.get_selection_plate()
            if len(selection) > 0:
                for i in range(len(selection)):
                    self.grd_Plate.SetCellValue(selection[i][0],
                                                selection[i][1],
                                                str(self.scr_ControlList.entries))
                    self.paint_control(None, None, self.scr_ControlList.entries, 0)
            else:
                wx.MessageBox("You have not selected any wells, could not assign control to wells.\nSelect wells and try again.",
                    "No wells", wx.OK|wx.ICON_INFORMATION)

    def remove_control(self, event):
        """
        Removes selected control from control list and
        clears all corresponding wells on plate layout,
        updates dataframe.
        """
        ctrl = self.scr_ControlList.highlit
        self.scr_ControlList.delete_entry(ctrl)
        self.update_dataframe()

        # Only if the controls tab is currently shown (i.e. the button is "Current")
        # do we want to remove the numerical ID from the plate layout.
        if self.btn_Controls.Current == True:
            for row in range(self.grd_Plate.GetNumberRows()):
                for col in range(self.grd_Plate.GetNumberCols()):
                    if self.grd_Plate.GetCellValue(row,col) == str(ctrl+1):
                        self.grd_Plate.SetCellValue(row,col,"")
                        self.grd_Plate.SetCellBackgroundColour(row,col,cs.White)
                    elif self.grd_Plate.GetCellValue(row,col) != "" and int(self.grd_Plate.GetCellValue(row,col)) > ctrl+1:
                        self.grd_Plate.SetCellValue(row,col,str(int(self.grd_Plate.GetCellValue(row,col))-1))

    def test_for_control(self):
        """
        Tests if there is at least one control that is set to be used for
        ZPrime calculation.

        Returns True if condition is met.

        """
        int_Controls = 0
        if self.bol_controls == True:
            for key in self.scr_ControlList.family.keys():
                if self.scr_ControlList.family[key].zprime == True:
                    int_Controls += 1
                    break
            if int_Controls == 0:
                wx.MessageBox("You have not selected any controls for the Z prime calculation.\n"
                              + "Please select a control and try again.",
                              "No ZPrime",
                              wx.OK|wx.ICON_INFORMATION)
                return False
            else:
                return True
        else:
            return True

    def export_layout(self, event):
        """
        Exports layout dataframe to csv file with the file
        extension ".plf" (plate layout file)
        """
        # Test if there are any controls and if so, whether one is selected for ZPrime:
        if self.test_for_control() == False:
            return None

        with wx.FileDialog(self, "Export plate layout", wildcard="Plate layout files (*.plf)|*.plf",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as fileDialog:

            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return     # the user changed their mind
            str_SaveFilePath = fileDialog.GetPath()
            if str_SaveFilePath.find(".plf") == -1:
                str_SaveFilePath = str_SaveFilePath + ".plf"
            try:
                zip_PLF = zf.ZipFile(str_SaveFilePath, "w")
            except:
                return False
            HomePath = os.path.expanduser("~")
            str_TempDir = os.path.join(HomePath,"bbqtempdir")
            # Check whether temporary directory exists. if so, delete and make fresh
            if os.path.isdir(str_TempDir) == True:
                shutil.rmtree(str_TempDir)
            os.mkdir(str_TempDir)

            # Save Plate IDs
            self.dfr_Layout["PlateID"].to_csv(str_TempDir + r"\plates.csv")
            zip_PLF.write(str_TempDir + r"\plates.csv",
                          arcname="plates.csv")
            # Save individual layouts
            for plate in self.dfr_Layout.index:
                self.dfr_Layout.loc[plate,"Layout"].to_csv(str_TempDir + r"\layout.csv")
                zip_PLF.write(str_TempDir + r"\layout.csv",
                              arcname=str(plate) + r"\layout.csv")
                os.remove(os.path.join(str_TempDir, "layout.csv"))
            zip_PLF.close()
            # Remove all the temporary files
            shutil.rmtree(str_TempDir)

    def import_layout(self, event):
        """
        Imports a plate layout file. Reads contents to dataframe
        and updates all relevent widgets on dialog window.
        """
        with wx.FileDialog(self, "Open plate layout file", wildcard="Plate layout files (*.plf)|*.plf",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as fileDialog:

            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return     # the user changed their mind
            str_FilePath = fileDialog.GetPath()

            # Check whether temporary directory exists. if so, delete and make fresh
            HomePath = os.path.expanduser("~")
            str_TempDir = os.path.join(HomePath,"bbqtempdir")
            if os.path.isdir(str_TempDir) == True:
                shutil.rmtree(str_TempDir)
            os.mkdir(str_TempDir)
            # Extract saved file to temporary directory
            with zf.ZipFile(str_FilePath, "r") as zip:
                zip.extractall(str_TempDir)

            self.clear_plate(event = None)

            self.dfr_Layout = pd.read_csv(str_TempDir+r"\plates.csv",
                                          sep=",",
                                          header=0,
                                          index_col=0,
                                          engine="python")
            # Insert a column with contents, otherwise sub-dataframes cannot
            # be loaded,
            self.dfr_Layout.insert(1,"Layout","")

            for plate in self.dfr_Layout.index:
                layout = os.path.join(str_TempDir, str(plate), "layout.csv")
                self.dfr_Layout.at[plate,"Layout"] = pd.read_csv(layout,
                                                                 sep=",",
                                                                 header=0,
                                                                 index_col=0,
                                                                 engine="python")
                for col in self.dfr_Layout.loc[plate,"Layout"].columns:
                    if "Numerical" in col:
                        self.dfr_Layout.loc[plate,"Layout"][col] = self.dfr_Layout.loc[plate,"Layout"][col].apply(nodecimal)
 
            # Check whether the file is of the correct format (compare list length in dfr_Layout with number of wells on grid)
            if self.dfr_Layout.loc[0,"Layout"].shape[0] != self.plateformat:
                wx.MessageBox("The layout file you selected does not have the same plate format (number of wells) as the assay you have selected. Select a new file and try again.",
                    "Wrong plate format", wx.OK|wx.ICON_INFORMATION)
                return None # Easier to use this to skip all the rest of the function than to use if then else type wrapper around instructions.
            self.update_display()

            if self.bol_MultiplePlates == False and len(self.dfr_Layout) > 1:
                wx.MessageBox("You have imported a file with layouts for two plates or more," + "\n" +
                    "but have selected a global layout for all plates." + "\n" + "\n" +
                    "The first layout in the layout file will be applied to all plates.",
                    "Plate layouts reduced",
                    wx.OK|wx.ICON_INFORMATION)
    
    def apply_and_close(self, parent, event):
        """
        Apply and close. Writes layout dataframe to parent
        object's layout dataframe and closes the window.

        Arguments:
            parent -> parent object in GUI.
            event -> wx event.

        """
        # Test if there are any controls and if so, whether one is selected for ZPrime:
        if self.test_for_control() == False:
            return None
        # Check whether there is a plate without reference wells:
        lst_PlatesWithoutReferences = []
        for plate in self.dfr_Layout.index:
            if not "r" in self.dfr_Layout.loc[plate,"Layout"]["WellType"].tolist():
                lst_PlatesWithoutReferences.append(plate + 1)
        if len(lst_PlatesWithoutReferences) == 0:
            parent.dfr_Layout = self.dfr_Layout
            parent.bol_LayoutDefined = True
            self.EndModal(True)
        else:
            str_PlatesWithoutReferences = ""
            for i in range(len(lst_PlatesWithoutReferences)):
                if i < (len(lst_PlatesWithoutReferences) - 1):
                    str_Comma = ", "
                else:
                    str_Comma = ""
                str_PlatesWithoutReferences = str_PlatesWithoutReferences + str(lst_PlatesWithoutReferences[i]) + str_Comma
            dlg_Exit = wx.MessageDialog(None, "One or more plates have no reference wells:" + "\n" + 
                "Plate(s) " + str_PlatesWithoutReferences + "\n" + "\n" +
                "Data analysis is not possible without refrence wells.\n" + 
                "If you exit now, these plates cannot be analysed later (and might crash the program).\n" + 
                "Do you still want to exit?", "Missing reference wells", wx.YES_NO|wx.ICON_QUESTION)
            id_Exit = dlg_Exit.ShowModal()
            if id_Exit == wx.ID_YES:
                parent.dfr_Layout = self.dfr_Layout
                parent.bol_LayoutDefined = True
                self.EndModal(True)

    def cancel(self, event):
        """
        Closes window without changing parent object's
        layout dataframe.
        """
        event.Skip()
        self.EndModal(True)

    def context_menu_plate(self, event):
        """
        Event handler to show context menu for plate layout
        grid.
        """
        event.Skip()

        row = event.GetRow()
        col = event.GetCol()
        welltype = self.get_well_type(self.grd_Plate.GetCellBackgroundColour(row,col),True)
        if col >= 0 and col < self.grd_Plate.GetNumberCols() and row >= 0 and row < self.grd_Plate.GetNumberRows():
            self.PopupMenu(PlateContextMenu(self, event, welltype))

    def get_selection_plate(self):
        """
        Returns list of coordinates of all selected wells on
        plate layout grid.
        """
        # Selections are treated as blocks of selected cells
        lst_TopLeftBlock = self.grd_Plate.GetSelectionBlockTopLeft()
        lst_BotRightBlock = self.grd_Plate.GetSelectionBlockBottomRight()
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

    def on_mouseover_plate(self, event):
        """
        Event handler. Calculates where the mouse is pointing
        and then set the tooltip dynamically.
        """
        # Use CalcUnscrolledPosition() to get the mouse position
        # within the entire grid including what is offscreen
        x, y = self.grd_Plate.CalcUnscrolledPosition(event.GetX(),event.GetY())
        coords = self.grd_Plate.XYToCell(x, y)
        # you only need these if you need the value in the cell
        row = coords[0]
        col = coords[1]
        # Get plate
        plate = 0
        if (
            col >= 0 and col < self.grd_Plate.GetNumberCols()
            and row >= 0 and row < self.grd_Plate.GetNumberRows()
            ):
            # Get well coordiante:
            str_Well = pf.sortable_well(chr(row+65)+str(col+1),self.plateformat)
            idx_Well = pf.well_to_index(str_Well, self.plateformat)
            tooltip = str_Well + ": "
            # Get well type:
            welltype = self.get_well_type(self.grd_Plate.GetCellBackgroundColour(row,col),True)
            if not welltype == u"not assigned":
                # Add welltype to string:
                tooltip += u"\n" + welltype
                # Get sample ID if used:
                if self.bol_sampleids == True:
                    if welltype == "Sample":
                        sample = self.dfr_Layout.loc[plate,"Layout"].loc[idx_Well,"SampleID"]
                        tooltip += ": " + str(sample)
                # Get control ID if used
                if self.bol_controls == True:
                    if welltype == "Control":
                        control = self.dfr_Layout.loc[plate,"Layout"].loc[idx_Well,"ControlNumerical"]
                        if not control == "" and not pd.isna(control):
                            control = int(control)
                            tooltip += ": " + self.scr_ControlList.family[control].name
                            #self.grd_ControlList.GetCellValue(control,0)
                # Get protein ID if used:
                if self.bol_proteins == True:
                    protein = self.dfr_Layout.loc[plate,"Layout"].loc[idx_Well,"ProteinNumerical"]
                    if not protein == "" and not pd.isna(protein):
                        protein = int(protein)
                        tooltip += u"\nProtein: " + self.scr_ProteinList.family[protein].name
            else:
                tooltip += " Blank well"
            event.GetEventObject().SetToolTip(tooltip)
        event.Skip()

    def paint_sample(self, event, rightclick, update = True):
        """
        Event handler.
        Paints selected grid cell(s) and grid cells at rightclick
        coordinates yellow and sets cell type to "Sample".
        """
        selection = self.get_selection_plate()
        if rightclick != None:
            selection.append(rightclick)
        self.paint_cells(selection,"yellow")#,"s")
        if self.btn_Controls.Current == True:
            for i in range(len(selection)):
                self.grd_Plate.SetCellValue(selection[i][0],selection[i][1],"")
        if update == True:
            self.update_dataframe()

    def paint_control(self, event, rightclick, control, update = True):
        """
        Event handler.
        Paints selected grid cell(s) and grid cells at rightclick
        coordinates blue and sets cell type to "Control".
        """
        selection = self.get_selection_plate()
        if rightclick != None:
            selection.append(rightclick)
        if self.check_samples(selection) == False:
            return None
        self.paint_cells(selection,"blue")
        if self.btn_Controls.Current == True:
            for i in range(len(selection)):
                self.grd_Plate.SetCellValue(selection[i][0],selection[i][1],str(control))
        self.update_from_menu(selection, "control", control)

    def paint_reference(self, event, rightclick, name, update = True):
        """
        Event handler.
        Paints selected grid cell(s) and grid cells at rightclick
        coordinates red and sets cell type to "Reference".
        """
        selection = self.get_selection_plate()
        if rightclick != None:
            selection.append(rightclick)
        if self.check_samples(selection) == False:
            return None
        self.paint_cells(selection,"red")
        for i in range(len(selection)):
                self.grd_Plate.SetCellValue(selection[i][0],selection[i][1],"")
        self.update_from_menu(selection, "reference", 0)

    def paint_blank(self, event, rightclick, update = True):
        """
        Event handler.
        Paints selected grid cell(s) and grid cells at rightclick
        coordinates white and sets cell type to "not assigned".
        """
        selection = self.get_selection_plate()
        selection.append(rightclick)
        self.paint_cells(selection,"white")
        for i in range(len(selection)):
                self.grd_Plate.SetCellValue(selection[i][0],selection[i][1],"")
        self.update_from_menu(selection, "blank", 0)

    def check_samples(self, wells):
        """
        Checks if the wells in the list have a sample ID associated with them.
        Returns true or false.
        """
        proceed = wx.YES
        wells = [pf.col_row_to_index(w[0],w[1],self.plateformat) for w in wells]
        if self.bol_MultiplePlates == True:
            plate = self.lbx_PlateList.GetSelection()
        else:
            plate = 0
        for well in wells:
            if not pd.isna(self.dfr_Layout.loc[plate,"Layout"].loc[well,"SampleID"]) == True:
                proceed = wx.MessageBox(
                    "One or more of the selected cells have sample IDs associated with them."
                    + "\nDo you want to overwrite them?",
                    caption = "Sample IDs found",
                    style = wx.YES_NO|wx.ICON_WARNING)
                break
        if proceed == wx.NO:
            return False
        else:
            return True

    def clear_plate(self, event):
        """
        Clears contents of entire plate layout.
        """
        lst_Selection = []
        for y in range(24):
            for x in range(16):
                lst_Selection.append([x,y])
        self.grd_Plate.ClearGrid()
        self.paint_cells(lst_Selection,"white")#,"")
        self.update_from_menu(lst_Selection, "blank", 0)

    def paint_cells(self,selection,colour):
        """
        Changes background colour of selected cells and, if
        required, changes text colour for readability.
        """
        for i in range(len(selection)):
            self.grd_Plate.SetCellBackgroundColour(selection[i][0],selection[i][1],colour)
            if colour == "blue":
                self.grd_Plate.SetCellTextColour(selection[i][0],selection[i][1],"white")
            else:
                self.grd_Plate.SetCellTextColour(selection[i][0],selection[i][1],"black")
                #self.grd_Plate.SetCellValue(selection[i][0],selection[i][1],"")
        self.grd_Plate.ForceRefresh()
    
    def write_protein(self, event, rightclick, numerical, update = True):
        """
        writes number corresponding to protein's position
        in list into selected and clicked-on cells.
        """
        selection = self.get_selection_plate()
        selection.append(rightclick)
        if self.btn_Proteins.Current == True:
            for i in range(len(selection)):
                self.grd_Plate.SetCellValue(selection[i][0],selection[i][1],str(numerical + 1))
        self.update_from_menu(selection, "protein", numerical)

    def get_well_type(self, colour, long):
        """
        Takes background colour of cell and returns well type
        in short or long form.

        Arguments:
            colour -> list of RGBA values in integers.
            long -> boolean. Whether to return long or short
                    form well type, e.g. "Sample" or "s".
        """
        #if colour[0] == 255 and colour[1] == 255 and colour[2] == 255:
        #    # 255,255,255 = white
        #    str_WellType = "not assigned"
        if colour[0] == 255 and colour[1] == 255 and colour[2] == 0:
            # 255,255,0 = yellow
            if long == True:
                return "Sample"
            else:
                return "s"
        elif colour[0] == 255 and colour[1] == 0 and colour[2] == 0:
            # 255,0,0 = red
            if long == True:
                return "Reference well"
            else:
                return "r"
        elif colour[0] == 0 and colour[1] == 0 and colour[2] == 255:
            # 0,0,255 = blue
            if long == True:
                return "Control"
            else:
                return "c"
        else:
            if long == True:
                return "not assigned"
            else:
                return "na"

    def get_well_colour(self, well):
        """
        Takes the type of a well and returns the
        appropriate background colour for the cell/well.
        """
        if well == "r" or well == "Reference well":
            return "red"
        elif well == "s" or well == "Sample":
            return "yellow"
        elif well == "c" or well == "Control":
            return "blue"
        else:
            return "white"

    def get_text_colour(self, well):
        """
        Takes the type of a well and returns the
        appropriate text colour for the cell/well.
        """
        if well == "r" or well == "Reference well":
            return "white"
        elif well == "s" or well == "Sample":
            return "black"
        elif well == "c" or well == "Control":
            return "white"
        else:
            return "black"

    def create_dataframe(self, event = None):
        """
        Creates the plate dataframe with the current contents
        of the selected plate. Allows for dataframe expansion
        if there was previously only one entry (i.e. the user
        originally selected one layout for all plates but then
        later changed their mind)
        """
        # Get plate index
        if self.bol_MultiplePlates == True:
            plate = self.lbx_PlateList.GetSelection()
            # If neccessary, expand dataframe to reflect actual number of plates.
            if len(self.dfr_Layout) < self.lbx_PlateList.GetCount():
                int_Difference = self.lbx_PlateList.GetCount() - len(self.dfr_Layout)
                dfr_Addition = pd.DataFrame(index=range(int_Difference),
                                            columns=["PlateID",
                                                    "Layout"])
                for add in dfr_Addition.index:
                    if self.PlateID == True:
                        dfr_Addition.loc[add,"PlateID"] = self.txt_PlateID.GetValue()
                    else:
                        dfr_Addition.loc[add,"PlateID"] = "X999A"
                    self.dfr_Layout.at[add,"Layout"] = pd.DataFrame(index=range(self.plateformat),
                                            columns = ["WellType",
                                                       "ProteinNumerical",
                                                       "ProteinID",
                                                       "ProteinConcentration",
                                                       "ControlNumerical",
                                                       "ControlID",
                                                       "ControlConcentration",
                                                       "ZPrime",
                                                       "ReferenceNumerical",
                                                       "ReferenceID",
                                                       "ReferenceConcentration",
                                                       "SampleNumerical",
                                                       "SampleID",
                                                       "SampleConcentration"])
                self.dfr_Layout = self.dfr_Layout.append(dfr_Addition, ignore_index=True)
                wx.MessageBox("You have previously chosen to use one layout for all plates."
                              + "\nThe list of layouts has now been expanded."
                              + "\n\nCheck all plate entries to ensure correct layout.",
                              caption = "Layout expanded",
                              style = wx.OK|wx.ICON_INFORMATION)
        else:
            plate = 0

        # Update plate ID
        if self.PlateID == True:
            self.dfr_Layout.at[plate,"PlateID"] = self.txt_PlateID.GetValue()
        else:
            self.dfr_Layout.at[plate,"PlateID"] = "X999A"

        # Update well types
        lst_WellType = []
        for row in range(self.grd_Plate.GetNumberRows()):
            for col in range(self.grd_Plate.GetNumberCols()):
                lst_WellType.append(self.get_well_type(
                    self.grd_Plate.GetCellBackgroundColour(row,col),False))
        self.dfr_Layout.at[plate,"Layout"]["WellType"] = lst_WellType

        # Update proteins
        if self.bol_proteins == True:
            lst_ProteinIDs = []
            lst_ProtConcs = []
            lst_ProteinNumericals = []
            for row in range(self.grd_Plate.GetNumberRows()):
                for col in range(self.grd_Plate.GetNumberCols()):
                    numerical = self.grd_Plate.GetCellValue(row,col) # GetCellValue returns string
                    if numerical != "":
                        lst_ProteinNumericals.append(int(numerical))
                        key = int(numerical) -1
                        lst_ProteinIDs.append(
                            self.scr_ProteinList.family[key].name)
                        lst_ProtConcs.append(
                            self.scr_ProteinList.family[key].conc)
                    else:
                        lst_ProteinIDs.append("")
                        lst_ProtConcs.append("")
                        lst_ProteinNumericals.append("")
            # Write lists into dfr_Layout:
            self.dfr_Layout.at[plate,"Layout"]["ProteinNumerical"] = lst_ProteinNumericals
            self.dfr_Layout.at[plate,"Layout"]["ProteinID"] = lst_ProteinIDs
            self.dfr_Layout.at[plate,"Layout"]["ProteinConcentration"] = lst_ProtConcs
        else:
            self.dfr_Layout.at[plate,"Layout"]["ProteinNumerical"] = [""] * self.plateformat
            self.dfr_Layout.at[plate,"Layout"]["ProteinID"] = [""] * self.plateformat
            self.dfr_Layout.at[plate,"Layout"]["ProteinConcentration"] = [""] * self.plateformat

        # Update controls
        if self.bol_controls == True and self.scr_ControlList.entries > 0:
            lst_ControlIDs = []
            lst_ControlNumericals = []
            lst_ControlConcs = []
            lst_ZPrimes = []
            for row in range(self.grd_Plate.GetNumberRows()):
                for col in range(self.grd_Plate.GetNumberCols()):
                    numerical = self.grd_Plate.GetCellValue(row,col)
                    lst_ControlNumericals.append(numerical)
                    if numerical != "":
                        key = int(numerical) -1
                        lst_ControlIDs.append(
                            self.scr_ControlList.family[key].name)
                        lst_ControlConcs.append(
                            self.scr_ControlList.family[key].conc)
                        lst_ZPrimes.append(
                            self.scr_ControlList.family[key].zprime)
                    else:
                        lst_ControlIDs.append("")
                        lst_ControlConcs.append("")
                        lst_ZPrimes.append("")
            # Write lists into dfr_Layout:
            self.dfr_Layout.at[plate,"Layout"]["ControlNumerical"] = lst_ControlNumericals
            self.dfr_Layout.at[plate,"Layout"]["ControlID"] = lst_ControlIDs
            self.dfr_Layout.at[plate,"Layout"]["ControlConcentration"] = lst_ControlConcs
            self.dfr_Layout.at[plate,"Layout"]["ZPrime"] = lst_ZPrimes
        else:
            self.dfr_Layout.at[plate,"Layout"]["ControlNumerical"] = [""] * self.plateformat
            self.dfr_Layout.at[plate,"Layout"]["ControlID"] = [""] * self.plateformat
            self.dfr_Layout.at[plate,"Layout"]["ControlConcentration"] = [""] * self.plateformat
            self.dfr_Layout.at[plate,"Layout"]["ZPrime"] = [False] * self.plateformat

        # Write sample IDs to layout
        if self.bol_sampleids == True:
            for lrow in range(self.grd_SampleIDs.GetNumberRows()):
                if not self.grd_SampleIDs.GetCellValue(lrow,0) == "":
                    idx_Well = pf.well_to_index(self.grd_SampleIDs.GetCellValue(lrow,0), self.plateformat)
                    self.dfr_Layout.loc[plate,"Layout"].loc[idx_Well,"SampleID"] = self.grd_SampleIDs.GetCellValue(lrow,1)

    def update_from_menu(self, coords, welltype, typeindex):
        """
        Updates dataframe from context menu

        Arguments:
            coords -> collection. Coordinates of the wells to be updated
            welltype -> string. The type of well (sample, control, reference,
                        blank)
            typeindex -> integer. Index of the control 
        """
        indices = [pf.col_row_to_index(w[0],w[1],self.plateformat) for w in coords]
        if self.bol_MultiplePlates == True:
            plate = self.lbx_PlateList.GetSelection()
        else:
            plate = 0
        if welltype == "blank":
            for well in self.dfr_Layout.loc[plate,"Layout"].index:
                if well in indices:
                    for col in self.dfr_Layout.loc[plate,"Layout"].columns:
                        self.dfr_Layout.loc[plate,"Layout"].loc[well,col] = ""
                    self.dfr_Layout.loc[plate,"Layout"].loc[well,"WellType"] = "na"
        if welltype == "control":
            for well in self.dfr_Layout.loc[plate,"Layout"].index:
                if well in indices:
                    self.dfr_Layout.loc[plate,"Layout"].loc[well,"WellType"] = "c"
                    self.dfr_Layout.loc[plate,"Layout"].loc[well,"ControlID"] = self.scr_ControlList.family[typeindex].name
                    self.dfr_Layout.loc[plate,"Layout"].loc[well,"ControlNumerical"] = typeindex
                    self.dfr_Layout.loc[plate,"Layout"].loc[well,"ControlConcentration"] = self.scr_ControlList.family[typeindex].conc
                    self.dfr_Layout.loc[plate,"Layout"].loc[well,"ZPrime"] = self.scr_ControlList.family[typeindex].zprime
                    self.dfr_Layout.loc[plate,"Layout"].loc[well,"ReferenceID"] = ""
                    self.dfr_Layout.loc[plate,"Layout"].loc[well,"ReferenceNumerical"] = ""
                    self.dfr_Layout.loc[plate,"Layout"].loc[well,"ReferenceConcentration"] = ""
        elif welltype == "reference":
            for well in self.dfr_Layout.loc[plate,"Layout"].index:
                if well in indices:
                    self.dfr_Layout.loc[plate,"Layout"].loc[well,"WellType"] = "r"
                    self.dfr_Layout.loc[plate,"Layout"].loc[well,"ReferenceID"] = "DMSO"
                    self.dfr_Layout.loc[plate,"Layout"].loc[well,"ReferenceNumerical"] = typeindex
                    self.dfr_Layout.loc[plate,"Layout"].loc[well,"ReferenceConcentration"] = ""
                    self.dfr_Layout.loc[plate,"Layout"].loc[well,"ControlID"] = ""
                    self.dfr_Layout.loc[plate,"Layout"].loc[well,"ControlNumerical"] = ""
                    self.dfr_Layout.loc[plate,"Layout"].loc[well,"ControlConcentration"] = ""
                    self.dfr_Layout.loc[plate,"Layout"].loc[well,"ZPrime"] = ""
        elif welltype == "protein":
            for well in self.dfr_Layout.loc[plate,"Layout"].index:
                if well in indices:
                    self.dfr_Layout.loc[plate,"Layout"].loc[well,"ProteinID"] = self.scr_ProteinList.family[typeindex].name
                    self.dfr_Layout.loc[plate,"Layout"].loc[well,"ProteinNumerical"] = typeindex
                    self.dfr_Layout.loc[plate,"Layout"].loc[well,"ProteinConcentration"] = self.scr_ProteinList.family[typeindex].conc

    def update_dataframe(self, event = None):
        """
        Updates the plate dataframe with the current contents
        of the selected plate. Allows for dataframe expansion
        if there was previously only one entry (i.e. the user
        originally selected one layout for all plates but then
        later changed their mind)
        """
        # Get plate index
        if self.bol_MultiplePlates == True:
            plate = self.lbx_PlateList.GetSelection()
            # If neccessary, expand dataframe to reflect actual number of plates.
            if len(self.dfr_Layout) < self.lbx_PlateList.GetCount():
                int_Difference = self.lbx_PlateList.GetCount() - len(self.dfr_Layout)
                dfr_Addition = pd.DataFrame(index=range(int_Difference),
                                            columns=["PlateID",
                                                    "Layout"])
                for add in dfr_Addition.index:
                    if self.PlateID == True:
                        dfr_Addition.loc[add,"PlateID"] = self.txt_PlateID.GetValue()
                    else:
                        dfr_Addition.loc[add,"PlateID"] = "X999A"
                    self.dfr_Layout.at[add,"Layout"] = pd.DataFrame(index=range(self.plateformat),
                                            columns = ["WellType",
                                                       "ProteinNumerical",
                                                       "ProteinID",
                                                       "ProteinConcentration",
                                                       "ControlNumerical",
                                                       "ControlID",
                                                       "ControlConcentration",
                                                       "ZPrime",
                                                       "ReferenceNumerical",
                                                       "ReferenceID",
                                                       "ReferenceConcentration",
                                                       "SampleNumerical",
                                                       "SampleID",
                                                       "SampleConcentration"])
                self.dfr_Layout = self.dfr_Layout.append(dfr_Addition, ignore_index=True)
                wx.MessageBox("You have previously chosen to use one layout for all plates."
                              + "\nThe list of layouts has now been expanded."
                              + "\n\nCheck all plate entries to ensure correct layout.",
                              caption = "Layout expanded",
                              style = wx.OK|wx.ICON_INFORMATION)
        else:
            plate = 0

        # Update plate ID
        if self.PlateID == True:
            self.dfr_Layout.at[plate,"PlateID"] = self.txt_PlateID.GetValue()
        else:
            self.dfr_Layout.at[plate,"PlateID"] = "X999A"

        # Update well types
        lst_WellType = []
        for row in range(self.grd_Plate.GetNumberRows()):
            for col in range(self.grd_Plate.GetNumberCols()):
                lst_WellType.append(self.get_well_type(
                    self.grd_Plate.GetCellBackgroundColour(row,col),False))
        self.dfr_Layout.at[plate,"Layout"]["WellType"] = lst_WellType

        # Update proteins
        if self.bol_proteins == True:
            lst_ProteinIDs = []
            lst_ProtConcs = []
            lst_ProteinNumericals = []
            for row in range(self.grd_Plate.GetNumberRows()):
                for col in range(self.grd_Plate.GetNumberCols()):
                    cell = self.grd_Plate.GetCellValue(row,col)
                    if not cell == "":
                        cell = int(self.grd_Plate.GetCellValue(row,col)) - 1
                        lst_ProteinNumericals.append(cell)
                        lst_ProteinIDs.append(
                            self.scr_ProteinList.family[cell].name)
                        lst_ProtConcs.append(
                            self.scr_ProteinList.family[cell].conc)
                    else:
                        lst_ProteinIDs.append("")
                        lst_ProtConcs.append("")
                        lst_ProteinNumericals.append("")
            # Write lists into dfr_Layout:
            self.dfr_Layout.at[plate,"Layout"]["ProteinNumerical"] = lst_ProteinNumericals
            self.dfr_Layout.at[plate,"Layout"]["ProteinID"] = lst_ProteinIDs
            self.dfr_Layout.at[plate,"Layout"]["ProteinConcentration"] = lst_ProtConcs
        else:
            self.dfr_Layout.at[plate,"Layout"]["ProteinNumerical"] = [""] * self.plateformat
            self.dfr_Layout.at[plate,"Layout"]["ProteinID"] = [""] * self.plateformat
            self.dfr_Layout.at[plate,"Layout"]["ProteinConcentration"] = [""] * self.plateformat

        # Update controls
        if self.bol_controls == True and self.scr_ControlList.entries > 0:
            lst_ControlIDs = []
            lst_ControlNumericals = []
            lst_ControlConcs = []
            lst_ZPrimes = []
            for row in range(self.grd_Plate.GetNumberRows()):
                for col in range(self.grd_Plate.GetNumberCols()):
                    cell = self.grd_Plate.GetCellValue(row,col)
                    if cell != "":
                        cell = int(self.grd_Plate.GetCellValue(row,col))-1
                        lst_ControlIDs.append(
                            self.scr_ControlList.family[cell].name)
                        lst_ControlConcs.append(
                            self.scr_ControlList.family[cell].conc)
                        lst_ZPrimes.append(
                            self.scr_ControlList.family[cell].zprime)
                    else:
                        lst_ControlIDs.append("")
                        lst_ControlConcs.append("")
                        lst_ZPrimes.append("")
                    lst_ControlNumericals.append(cell)
            # Write lists into dfr_Layout:
            self.dfr_Layout.at[plate,"Layout"]["ControlNumerical"] = lst_ControlNumericals
            self.dfr_Layout.at[plate,"Layout"]["ControlID"] = lst_ControlIDs
            self.dfr_Layout.at[plate,"Layout"]["ControlConcentration"] = lst_ControlConcs
            self.dfr_Layout.at[plate,"Layout"]["ZPrime"] = lst_ZPrimes
        else:
            self.dfr_Layout.at[plate,"Layout"]["ControlNumerical"] = [""] * self.plateformat
            self.dfr_Layout.at[plate,"Layout"]["ControlID"] = [""] * self.plateformat
            self.dfr_Layout.at[plate,"Layout"]["ControlConcentration"] = [""] * self.plateformat
            self.dfr_Layout.at[plate,"Layout"]["ZPrime"] = [False] * self.plateformat

        # Write sample IDs to layout
        if self.bol_sampleids == True:
            for lrow in range(self.grd_SampleIDs.GetNumberRows()):
                if not self.grd_SampleIDs.GetCellValue(lrow,0) == "":
                    well = pf.well_to_index(self.grd_SampleIDs.GetCellValue(lrow,0), self.plateformat)
                    sample = self.grd_SampleIDs.GetCellValue(lrow,1)
                    self.dfr_Layout.loc[plate,"Layout"].loc[well,"SampleID"] = sample

    def update_display(self, event = None):
        """
        Updates the dialog box with the information from dfr_Layout.
        """
        # Take into consideration that the user might have previously selected
        # to use one layout for all, so the dataframe may have a length of 1,
        # as it has been previously been created. Getting the index from the
        # seleted item in lbx_PlateList could create indexing errors.

        self.Freeze()
        # Get plate index
        if self.bol_MultiplePlates == True and self.dfr_Layout.shape[0] > 1:
            plate = self.lbx_PlateList.GetSelection()
        else:
            plate = 0

        # Update well colours/types:
        for row in range(self.grd_Plate.GetNumberRows()):
            for col in range(self.grd_Plate.GetNumberCols()):
                idx_Well = col + row*self.grd_Plate.GetNumberCols()
                well = self.dfr_Layout.loc[plate,"Layout"].loc[idx_Well,"WellType"]
                self.grd_Plate.SetCellBackgroundColour(row,col,self.get_well_colour(well))
                self.grd_Plate.SetCellTextColour(row,col,self.get_text_colour(well))

        prows = pf.plate_rows(self.plateformat)
        pcols = pf.plate_columns(self.plateformat)

        # Update protein list
        if self.bol_proteins == True:
            # Before repopulating, first delete all but the first entry and set this one to blank.
            self.scr_ProteinList.delete_all_entries()
            if self.btn_Proteins.Current == True:
                for well in self.dfr_Layout.loc[plate,"Layout"].index:
                    numerical = self.dfr_Layout.loc[plate,"Layout"].loc[well,"ProteinNumerical"]
                    if self.display_this(numerical):
                        r, c = pf.index_to_row_col(int(well), prows, pcols)
                        self.grd_Plate.SetCellValue(r,c,
                                                    self.numbertext(numerical+1))
            dfr_Proteins = self.dfr_Layout.loc[plate,"Layout"][["ProteinNumerical","ProteinID","ProteinConcentration"]].dropna().drop_duplicates()
            if dfr_Proteins.shape[0] > 0:
                for prot in dfr_Proteins.index:
                    self.scr_ProteinList.add_entry(name = dfr_Proteins.loc[prot,"ProteinID"],
                                                   conc = dfr_Proteins.loc[prot,"ProteinConcentration"],
                                                   use_zprime = False)
        
        # Update control list
        if self.bol_controls == True:
            # Before repopulating, first delete all but the first entry and set this one to blank.
            self.scr_ControlList.delete_all_entries()
            dfr_Controls = self.dfr_Layout.loc[plate,"Layout"][["ControlNumerical","ControlID","ControlConcentration","ZPrime"]].dropna().drop_duplicates()
            if dfr_Controls.shape[0] > 0:
                for ctrl in dfr_Controls.index:
                    self.scr_ControlList.add_entry(name = dfr_Controls.loc[ctrl,"ControlID"],
                                                   conc = dfr_Controls.loc[ctrl,"ControlConcentration"],
                                                   zprime = dfr_Controls.loc[ctrl,"ZPrime"])

        # Populate grid with numerical IDs:
        page = self.sbk_Definitions.GetSelection()
        page_text = self.sbk_Definitions.GetPageText(page)
        self.rewrite_all_cell_contents(page_text, plate, prows, pcols)
        self.lbl_Cells.SetLabel(f"Cell labels: {page_text}s")
        self.grd_Plate.ForceRefresh()

        # Update Plate ID field:
        if self.PlateID == True:
            self.txt_PlateID.SetValue(self.dfr_Layout.at[plate,"PlateID"])

        # Update sample IDs:
        if self.bol_sampleids == True:
            # Initialise with empty cells:
            for lrow in range(self.grd_SampleIDs.GetNumberRows()):
                self.grd_SampleIDs.SetCellValue(lrow,0,"")
                self.grd_SampleIDs.SetCellValue(lrow,1,"")
            # Update with entries from dataframe:
            lrow = 0
            for well in self.dfr_Layout.loc[plate,"Layout"].index:
                if self.display_this(self.dfr_Layout.loc[plate,"Layout"].loc[well,"SampleID"]):
                    self.grd_SampleIDs.SetCellValue(lrow,0,pf.index_to_well(well+1,self.plateformat))
                    self.grd_SampleIDs.SetCellValue(lrow,1,self.numbertext(self.dfr_Layout.loc[plate,"Layout"].loc[well,"SampleID"]))
                    lrow += 1
        self.Thaw()

    def rewrite_all_cell_contents(self, with_what, plate, prows, pcols):
        """
        Rewrites the contents of all cells with what is defined.

        Argument:
            with_what -> str. Either "Protein" or "Control
            plate -> int. Index of plate in layout dataframe
            prows -> int. Number of rows on plate
            pcols -> int. Number of columns on plate
        """
        for well in self.dfr_Layout.loc[plate,"Layout"].index:
            numerical = self.dfr_Layout.loc[plate,"Layout"].loc[well,f"{with_what}Numerical"]
            r, c = pf.index_to_row_col(int(well), prows, pcols)
            if self.display_this(numerical):
                cell_value = self.numbertext(numerical+1)
            else:
                cell_value = ""
            self.grd_Plate.SetCellValue(r,c, cell_value)


    def display_this(self, this):
        """
        Wrapping function to check that an element to be written on the plate
        layout is NOT an empty string or nan or either the strings "NaN" or
        "nan
        """
        if this in ["", "nan", "NaN"] or pd.isna(this) == True:
            return False
        else:
            return True

    def numbertext(self, numerical):
        """
        Turns numerical value into string and removes anything
        after decimal point. Use for populating plate layout
        with numerical IDs of controls/references/proteins/etc.
        """
        numerical = str(numerical)
        if numerical.find(".") == -1:
            return numerical
        else:
            return numerical[:numerical.find(".")]

    def update_plateid(self, event):
        """
        Event handler. Updates plate ID after value in text control
        has been changed.
        """
        if self.bol_MultiplePlates == True:
            self.dfr_Layout.at[self.lbx_PlateList.GetSelection(),"PlateID"] = self.txt_PlateID.GetValue()
        else:
            self.dfr_Layout.at[0,"PlateID"] = self.txt_PlateID.GetValue()

    def show_samples_context( self, event ):
        """
        Event handler. Calls context menu for sample ID list.
        """
        event.Skip()
        self.PopupMenu(SampleContextMenu(self, event))

    def get_samples_selection(self):
        """
        Returns list of coordinates of all selected cells
        on sample ID grid.
        """
        # Selections are treated as blocks of selected cells
        lst_TopLeftBlock = self.grd_SampleIDs.GetSelectionBlockTopLeft()
        lst_BotRightBlock = self.grd_SampleIDs.GetSelectionBlockBottomRight()
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
    
    def on_wellchange_samples(self, event):
        """
        Event handler. Turns any well coordinate entered in cells
        in column 0 into sortable wells. Sets cell value to empty
        string if cell value is not convertable.
        """
        row = event.GetRow()
        col = event.GetCol()
        try:
            self.grd_SampleIDs.SetCellValue(row,col,pf.sortable_well(str(self.grd_SampleIDs.GetCellValue(row,col)),self.plateformat))
        except:
            self.grd_SampleIDs.SetCellValue(row,col,"")
        self.update_dataframe()

    def on_keypress_samples(self, event):
        """
        Event handler for key press events. Goves sample ID grid
        the behaviour windows users would expect, e.g. ctrl+c,
        ctrl+v, ctr+x etc will work.
        """
        # based on first answer here:
        # https://stackoverflow.com/questions/28509629/work-with-ctrl-c-and-ctrl-v-to-copy-and-paste-into-a-wx-grid-in-wxpython
        # by user Sinan Çetinkaya

        keycode = event.GetUnicodeKey()

        # Ctrl+C or Ctrl+Insert
        if event.ControlDown() and keycode in [67, 322]:
            self.GridCopy()

        # Ctrl+V
        elif event.ControlDown() and keycode == 86:
            self.grid_paste(self.grd_SampleIDs.SingleSelection[0],
                           self.grd_SampleIDs.SingleSelection[1])

        # DEL
        elif keycode == 127:
            self.GridClear()

        # Ctrl+A
        elif event.ControlDown() and keycode == 65:
            self.grd_SampleIDs.SelectAll()

        # Ctrl+X
        elif event.ControlDown() and keycode == 88:
            # Call delete method
            self.GridCut()

        # Ctrl+V or Shift + Insert
        elif (event.ControlDown() and keycode == 67) \
                or (event.ShiftDown() and keycode == 322):
            self.grid_paste(self.grd_SampleIDs.SingleSelection[0],
                           self.grd_SampleIDs.SingleSelection[1])

        # Tab
        elif keycode == 9:
            print("tab")
            print(self.grd_SampleIDs.GetGridCursorCoords())
        else:
            event.Skip()

    def GetGridSelectionSamples(self):
        """
        Returns all selected cells in sample IDs grid as list of
        coordinates.
        """
        # Selections are treated as blocks of selected cells
        lst_TopLeftBlock = self.grd_SampleIDs.GetSelectionBlockTopLeft()
        lst_BotRightBlock = self.grd_SampleIDs.GetSelectionBlockBottomRight()
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

    def GridCopy(self):
        """
        Creates dataframe with contents of selected cells on Sample IDs grid
        and writes it to clipboard.
        """
        lst_Selection = self.GetGridSelectionSamples()
        if len(lst_Selection) == 0:
            lst_Selection = [[self.grd_SampleIDs.SingleSelection[0], self.grd_SampleIDs.SingleSelection[1]]]
        dfr_Copy = pd.DataFrame()
        for i in range(len(lst_Selection)):
            dfr_Copy.at[lst_Selection[i][0],lst_Selection[i][1]] = self.grd_SampleIDs.GetCellValue(lst_Selection[i][0],lst_Selection[i][1])
        dfr_Copy.to_clipboard(header=None, index=False)

    def GridCut(self):
        """
        Creates dataframe with contents of selected cells on Sample IDs grid,
        writes it to clipboard and then deletes cells' contens on grid.
        """
        lst_Selection = self.GetGridSelectionSamples()
        if len(lst_Selection) == 0:
            lst_Selection = [[self.grd_SampleIDs.SingleSelection[0], self.grd_SampleIDs.SingleSelection[1]]]
        dfr_Copy = pd.DataFrame()
        for i in range(len(lst_Selection)):
            dfr_Copy.at[lst_Selection[i][0],lst_Selection[i][1]] = self.grd_SampleIDs.GetCellValue(lst_Selection[i][0],lst_Selection[i][1])
            self.grd_SampleIDs.SetCellValue(lst_Selection[i][0],lst_Selection[i][1],"")
        dfr_Copy.to_clipboard(header=None, index=False)
    
    def GridClear(self):
        """
        Clears contents of selected cells on sample IDs grid.
        """
        lst_Selection = self.GetGridSelectionSamples()
        if len(lst_Selection) == 0:
            lst_Selection = [[self.grd_SampleIDs.SingleSelection[0], self.grd_SampleIDs.SingleSelection[1]]]
        for i in range(len(lst_Selection)):
            if lst_Selection[i][1] > 0:
                self.grd_SampleIDs.SetCellValue(lst_Selection[i][0],lst_Selection[i][1],"")

    def grid_paste(self, row, col):
        """
        Pastes contens of clipboard onto sample IDs grid, starting at
        specified coordinates.
        """
        dfr_Paste = pd.read_clipboard(sep="\\t", header=None)
        int_Rows = len(dfr_Paste)
        int_Columns = len(dfr_Paste.columns)
        for i in range(int_Rows):
            for j in range(int_Columns):
                if pd.isna(dfr_Paste.iloc[i,j]) == False:
                    self.grd_SampleIDs.SetCellValue(i+row,j+col,str(dfr_Paste.iloc[i,j]))
                else:
                    self.grd_SampleIDs.SetCellValue(i+row,j+col,"")
        self.CheckWellAddressWholeColumn()
        self.update_dataframe()

    def SingleSelectionSamples(self, event):
        """
        Sets currently clicked on cell to grid's SingleSelection
        property to catch it as part of selected cells.
        """
        self.grd_SampleIDs.SingleSelection = (event.GetRow(), event.GetCol())

    def CheckWellAddressWholeColumn(self):
        """
        Tries to turn contents of each cell in column 0 of sample IDs
        grid into sortable well.
        """
        for row in range(self.grd_SampleIDs.GetNumberRows()):
            try:
                self.grd_SampleIDs.SetCellValue(row,
                                                0,
                                                pf.sortable_well(self.grd_SampleIDs.GetCellValue(row,0),
                                                                 self.plateformat))
            except:
                None

####  #      ####  ##### #####    #####  ####  #   # ##### ##### #   # #####   #   # ##### #   # #    #
#   # #     #    #   #   #       #      #    # ##  #   #   #      # #    #     ## ## #     ##  # #    #
####  #     ######   #   ###     #      #    # #####   #   ###     #     #     ##### ###   ##### #    #
#     #     #    #   #   #       #      #    # #  ##   #   #      # #    #     # # # #     #  ## #    #
#     ##### #    #   #   #####    #####  ####  #   #   #   ##### #   #   #     #   # ##### #   #  ####

class PlateContextMenu(wx.Menu):
    """
    Context menu to assign well type (sample or reference well; also clear assignment).
    This simply calls the functions of the dialog, which gets passed on as "parent" 

    Methods:
        set_to_sample
        set_to_reference
        set_to_control
        set_to_blank
        set_protein
    
    """
    def __init__(self, parent, rightclick, wtype):
        super(PlateContextMenu, self).__init__()
        """
        Initialises class attributes.

        Arguments:
            parent -> parent object in UI.
            rightclick -> wx mouse event.
            wtype -> type of well at clicked coordinates
        """
        lst_ClickedCoordinates = [rightclick.GetRow(), rightclick.GetCol()]
        # Get the current directory and use that for the buttons
        real_path = os.path.realpath(__file__)
        dir_path = os.path.dirname(real_path)
        self.str_MenuIconsPath = dir_path + r"\menuicons"

        self.parent = parent
        self.wtype = wtype

        self.men_WellType = wx.Menu()
        
        self.mi_Sample = wx.MenuItem(self, wx.ID_ANY, u"Sample", wx.EmptyString,
                                     wx.ITEM_NORMAL )
        self.mi_Sample.SetBitmap(wx.Bitmap(self.str_MenuIconsPath + u"\GridSample.png"))
        self.men_WellType.Append( self.mi_Sample )
        self.Bind(wx.EVT_MENU,
                  lambda event: self.set_to_sample(event, lst_ClickedCoordinates),
                  self.mi_Sample)

        self.mi_Reference = wx.MenuItem(self, wx.ID_ANY, u"Reference", wx.EmptyString,
                                        wx.ITEM_NORMAL )
        self.mi_Reference.SetBitmap(wx.Bitmap(self.str_MenuIconsPath + u"\GridReference.png"))
        self.men_WellType.Append(self.mi_Reference)
        self.Bind(wx.EVT_MENU, lambda event: self.set_to_reference(event, lst_ClickedCoordinates), self.mi_Reference)

        if self.parent.bol_controls == True:
            if self.parent.scr_ControlList.entries > 0:
                self.men_Control = wx.Menu()
                dic_ControlItems = {}
                count = 1
                for ctrl in self.parent.scr_ControlList.family.keys():
                    ctrl_id = str(ctrl+1)
                    if self.parent.scr_ControlList.family[ctrl].name != "":
                        dic_ControlItems["ctrl_"+ctrl_id]  = wx.MenuItem(self,
                            id = wx.ID_ANY,
                            text = f"{ctrl_id}: {self.parent.scr_ControlList.family[ctrl].name}")
                        self.Bind(wx.EVT_MENU,
                                lambda event: self.set_to_control(event, lst_ClickedCoordinates, ctrl),
                                dic_ControlItems["ctrl_"+ctrl_id])
                        count += 1
                        self.men_Control.Append(dic_ControlItems["ctrl_"+ctrl_id])
                self.AppendSubMenu(self.men_Control, u"Control")

        self.AppendSubMenu(self.men_WellType, u"Well type")

        if self.parent.bol_proteins == True:
            int_Proteins = self.parent.scr_ProteinList.entries
            if int_Proteins > 0:
                self.men_Protein = wx.Menu()
                dic_ProteinItems = {}
                count = 1
                for prot in range(int_Proteins):
                    if self.parent.scr_ProteinList.family[prot].name != "":
                        prot_id = str(prot+1)
                        dic_ProteinItems["prot_"+prot_id]  = wx.MenuItem(self,
                            id = wx.ID_ANY,
                            text = f"{prot_id}: {self.parent.scr_ProteinList.family[prot].name}")
                        self.Bind(wx.EVT_MENU,
                                lambda event: self.set_protein(event, lst_ClickedCoordinates, prot),
                                dic_ProteinItems["prot_"+prot_id])
                        count += 1
                        self.men_Protein.Append(dic_ProteinItems["prot_"+prot_id])
                self.AppendSubMenu(self.men_Protein, u"Protein")

        self.mi_Clear = wx.MenuItem(self, wx.ID_ANY, u"Clear", wx.EmptyString,
                                    wx.ITEM_NORMAL)
        self.Bind(wx.EVT_MENU,
                  lambda event: self.set_to_blank(event, lst_ClickedCoordinates),
                  self.mi_Clear)
        self.Append(self.mi_Clear)
    
    def set_to_sample(self, event, rightclick):
        """
        Event handler. Sets rightclicked well to sample.
        """
        self.parent.paint_sample(event, rightclick)

    def set_to_reference(self, event, rightclick):
        """
        Event handler. Sets rightclicked well to reference.
        """
        self.parent.paint_reference(event, rightclick, event.GetId())

    def set_to_control(self, event, rightclick, control):
        """
        Event handler. Sets rightclicked well to control.
        ID on the control is set to be 100 higher than it actually is to avoid
        confusion with other IDs.
        """
        self.parent.paint_control(event, rightclick, control)

    def set_to_blank(self, event, rightclick):
        """
        Event handler. Sets rightclicked well to blank/
        not assigned.
        """
        self.parent.paint_blank(event, rightclick)

    def set_protein(self, event, rightclick, protein):
        """
        Event handler. Writes portein's numerical identified
        into grid cell.
        """
        self.parent.write_protein(event, rightclick, protein)

    def RightclickToSelection(self, rightlick):
        pass

 ####   ####  #   # ####  #     #####  ####  ####  #   # ##### ##### #   # #####   #   # ##### #   # #   #
#      #    # ## ## #   # #     #     #     #    # ##  #   #   #      # #    #     ## ## #     ##  # #   #
 ####  ###### ##### ####  #     ###   #     #    # #####   #   ###     #     #     ##### ###   ##### #   #
     # #    # # # # #     #     #     #     #    # #  ##   #   #      # #    #     # # # #     #  ## #   #
 ####  #    # #   # #     ##### #####  ####  ####  #   #   #   ##### #   #   #     #   # ##### #   #  ###

class SampleContextMenu(wx.Menu):

    """
    Context menu to cut, copy, paste, clear and fill down from capillaries grid.

    Methods:
        FillDown
        Copy
        Cut
        Paste
        Clear
        GetGridSelection

    """

    def __init__(self, parent, rightclick):
        super(SampleContextMenu, self).__init__()
        """
        Initialises class attributes.

        Arguments:
            parent -> parent object in UI
            rightclick -> wx mouse event.
        """
        real_path = os.path.realpath(__file__)
        dir_path = os.path.dirname(real_path)
        str_MenuIconsPath = dir_path + r"\menuicons"

        row = rightclick.GetRow()
        col = rightclick.GetCol()

        self.grid = rightclick.GetEventObject()

        self.parent = parent

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
        self.Bind(wx.EVT_MENU, lambda event: self.clear(event,  row, col), self.mi_Clear)

        self.AppendSeparator()

        self.mi_FillDown = wx.MenuItem(self, wx.ID_ANY, u"Fill down", wx.EmptyString, wx.ITEM_NORMAL)
        self.mi_FillDown.SetBitmap(wx.Bitmap(str_MenuIconsPath + u"\FillDown.ico"))
        self.Append(self.mi_FillDown)
        self.Bind(wx.EVT_MENU, lambda event: self.FillDown(event, row, col), self.mi_FillDown)

    def FillDown(self, event, row, col):
        """
        Event handler.
        Takes contents of clicked-on cell and fills all cells
        below on same column with same contents.
        """
        filler = self.grid.GetCellValue(row,col)
        for i in range(row,self.grid.GetNumberRows(),1):
            self.grid.SetCellValue(i, col, filler)

    def Copy(self, event, row, col):
        """
        Event handler.
        Takes contents of all selected cells, writes them to clipboard.
        """
        lst_Selection = self.GetGridSelection()
        if len(lst_Selection) > 0:
            dfr_Copy = pd.DataFrame()
            for i in range(len(lst_Selection)):
                dfr_Copy.at[lst_Selection[i][0],lst_Selection[i][1]] = self.grid.GetCellValue(lst_Selection[i][0],lst_Selection[i][1])
            dfr_Copy.to_clipboard(header=None, index=False)

    def Cut(self, event, row, col):
        """
        Event handler.
        Takes contents of all selected cells, writes them to clipboard,
        then clears selected cells on grid.
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
        Event handler.
        Writes contents of clipboard to grid, starting
        at clicked-on cell
        """
        dfr_Paste = pd.read_clipboard(sep="\\t", header=None)
        int_Rows = len(dfr_Paste)
        int_Columns = len(dfr_Paste.columns)
        for i in range(int_Rows):
            for j in range(int_Columns):
                if pd.isna(dfr_Paste.iloc[i,j]) == False:
                    self.grid.SetCellValue(i+row,j+col,str(dfr_Paste.iloc[i,j]))
                else:
                    self.grid.SetCellValue(i+row,j+col,"")
        self.parent.update_dataframe()
        self.parent.CheckWellAddressWholeColumn()

    def clear(self, event, row, col):
        """
        Event handler. Clears contents of all selected cells.
        """
        self.grid.SetCellValue(row, col, "")
        lst_Selection = self.GetGridSelection()
        if len(lst_Selection) > 0:
            for i in range(len(lst_Selection)):
                if lst_Selection[i][1] > 0:
                    self.grid.SetCellValue(lst_Selection[i][0],lst_Selection[i][1],"")

    def GetGridSelection(self):
        """
        Returns list of coordinates of all selected cells
        on the grid.
        """
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

def nodecimal(number):
    try:
        number = str(number)
        where = number.find(".")
        if not where == -1:
            return int(number[:where])
        else:
            if number.isnumeric() == True:
                return int(number)
            else:
                return np.nan
    except:
        return np.nan
