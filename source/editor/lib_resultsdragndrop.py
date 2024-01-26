"""
Classes for drag and drop behaviour between two wx.ListCtrl instances.
Specifically tailored for the files tab of a typical BBQ workflow where
the dragged items get written into the third column of a wx.ListCtrl.

Based on example in wxpython documentation:

https://wiki.wxpython.org/How%20to%20create%20a%20list%20control%20with%20drag%20and%20drop%20%28Phoenix%29

Classes:
    MyDragList
    MyDropTarget
    MyListDrop

"""

import wx
import wx.lib.newevent
import wx.lib.mixins.listctrl as mxlc
import pickle
import pandas as pd

# Create new event to handle updates of the lists:
ResultsUpdateEvent, EVT_RESULTS_UPDATE = wx.lib.newevent.NewEvent()

class MyDragList(wx.ListCtrl):
    """
    Derived from wx.ListCtrl: Items can be dragged from this list.
    """
    def __init__(self, *arg, **kw):
        wx.ListCtrl.__init__(self, *arg, **kw)

        data = 1
        self.Bind(wx.EVT_LIST_BEGIN_DRAG, self.StartDrag)

        # We do not need to drop into this list
        self.dt = MyListDrop(self)
        self.SetDropTarget(self.dt)

    def GetItemInfo(self, idx: int):
        # Collect all relevant data of a listitem, and put it in a list.

        lst_Drag = []
        lst_Drag.append(idx) # We need the original index, so it is easier to eventualy delete it.
        lst_Drag.append(self.GetItemData(idx)) # Itemdata.
        lst_Drag.append(self.GetItemText(idx,0)) # Text first column.
        for i in range(1, self.GetColumnCount()): # Possible extra columns.
            lst_Drag.append(self.GetItem(idx, i).GetText())
        return lst_Drag

    def StartDrag(self, event):
        """
        Event handler for dragging list items.
        """
        # Put together a data object for drag-and-drop _from_ this list.

        lst_Drag = []
        idx = -1
        while True: # Find all the selected items and put them in a list.
            idx = self.GetNextItem(idx, wx.LIST_NEXT_ALL, wx.LIST_STATE_SELECTED)
            if idx == -1:
                break
            lst_Drag.append([self.Name, self.GetItemText(idx,0)])

        # Pickle the items list.
        itemdata = pickle.dumps(lst_Drag, 1)
        # Create our own data format and use it
        # in a Custom data object.
        ldata = wx.CustomDataObject("ListCtrlItems")
        ldata.SetData(itemdata)
        # Now make a data object for the  item list.
        data = wx.DataObjectComposite()
        data.Add(ldata)

        # Create drop source and begin drag-and-drop.
        dropSource = wx.DropSource(self)
        dropSource.SetData(data)
        res = dropSource.DoDragDrop(flags=wx.Drag_DefaultMove)

        # If move, we want to remove the item from this list.
        if res == wx.DragMove:
            # It is possible we are dragging/dropping from this list to this list.
            # In which case, the index we are removing may have changed...
            # Find correct position.
            lst_Drag.reverse() # Delete all the items, starting with the last item.
            for i in range(len(lst_Drag)):
                pos = self.FindItem(0, lst_Drag[i][1])
                self.DeleteItem(pos)
    
    def ReSort(self):
        """
        Re-sorts list after change.
        """
        dfr_ToSort = pd.DataFrame(columns=["A","B"],index=range(self.GetItemCount()))
        for i in range(len(dfr_ToSort)):
            dfr_ToSort.loc[i,"A"] = self.GetItemText(i,0)
            dfr_ToSort.loc[i,"B"] = self.GetItemText(i,1)
        dfr_ToSort = dfr_ToSort.sort_values(by="A")
        self.DeleteAllItems()
        for i in range(len(dfr_ToSort)):
            self.InsertItem(i,dfr_ToSort.iloc[i,0])
            self.SetItem(i,1,dfr_ToSort.iloc[i,1])

class MyDropTarget(wx.ListCtrl, mxlc.TextEditMixin):
    """
    wx.ListCtrl that can accept dropped data.
    """
    def __init__(self, parent, id = wx.ID_ANY, pos = wx.DefaultPosition,
                size = wx.DefaultSize, style = 0, name = u"", instance = None):
        wx.ListCtrl.__init__(self, parent, id=id, pos=pos, size=size, style=style,
                             validator=wx.DefaultValidator, name=name)
        mxlc.TextEditMixin.__init__(self)

        #------------
        # self.Bind(wx.EVT_LIST_BEGIN_DRAG, self.StartDrag)
        #------------
        self.instance = instance
        self.dt = MyListDrop(self)
        self.SetDropTarget(self.dt)
    
    def OnLeftDown(self, event=None):
        """
        Supercedes original OnLeftDown function from Mixins so
        that editor can only be opened on first column
        """
        x, y = event.GetX(), event.GetY()
        r, a, c = self.HitTestSubItem((x,y))
        if c == 0:
            return super().OnLeftDown(event)
        else:
            try:
                self.CloseEditor()
            except:
                None
            return None
        
    def CloseEditor(self, event=None):
        """
        Supercedes original CLoseEditor function to post custom event
        """
        event = ResultsUpdateEvent(set_bool=False,
                                   return_items=None)
        wx.PostEvent(self,event)
        super().CloseEditor()


    def Insert(self, x, y, lst_Drag):
        """
        Inserts dropped items (lst_Drag) at x, y coordintaes.
        """
        # Find insertion point.
        idx, flags = self.HitTest((x, y))
        bol_DroppedBelowTheList = False
        if idx == wx.NOT_FOUND or idx == -1: # User did not drop on list item
            if self.GetItemCount() > 0: # If there are items in the list
                if y <= self.GetItemRect(0).y: # User dropped above first item
                    idx = 0
                else: # User dropped below last item
                    idx = self.GetItemCount()
            else:
                # Change this to return to source list
                idx = 0 # Append to end of list.
                bol_DroppedBelowTheList = True
        else: # Clicked on an item.
            # Get bounding rectangle for the item the user is dropping over.
            print("Hit!")
            rect = self.GetItemRect(idx)
        # Insert into target ListCtrl and set global variables
        j = 0
        lst_Return = []
        if bol_DroppedBelowTheList == False:
            for src, col in lst_Drag: # Insert the item data.
                # My Change: Only set third column to value. Add all dragged elements
                if idx+j < self.GetItemCount():
                    if self.GetItemText(idx+j,1) != "":
                        lst_Return.append([self.GetItemText(idx+j,1),
                                           self.GetItemText(idx+j,2)])
                    self.SetItem(idx+j,1,src)
                    self.SetItem(idx+j,2,col)
                else:
                    self.InsertItem(idx+j,u"")
                    self.SetItem(idx+j,1,src)
                    self.SetItem(idx+j,2,col)
                j += 1 # takes variable, adds 1 and returns it.
        else:
            for src, col in lst_Drag: # Insert the item data.
                self.InsertItem(idx+j,"")
                self.SetItem(idx+j,1,src)
                self.SetItem(idx+j,2,col)
        #    lst_Return = lst_Drag
        if len(lst_Return) > 0:
            for src, col in lst_Return:
                listctrl = self.instance.dic_ListCtrls[src]
                listctrl.InsertItem(listctrl.GetItemCount(),col)

        # Create and post an event to update things
        event = ResultsUpdateEvent(set_bool=(not bol_DroppedBelowTheList),
                                   return_items=lst_Return)
        wx.PostEvent(self,event)


class MyListDrop(wx.DropTarget):
    """
    Drop target for simple lists.
    """
    
    def __init__(self, source):
        """
        Arguments:
            source -> listctrl
        """
        wx.DropTarget.__init__(self)

        #------------
        self.dv = source
        #------------

        # Specify the type of data we will accept.
        self.data = wx.CustomDataObject("ListCtrlItems")
        self.SetDataObject(self.data)

    def OnData(self, x, y, d):
        """
        Called when OnDrop returns True.  
        """

        # Copy the data from the drag source to our data object.
        if self.GetData():
            # Convert it back to a list and give it to the viewer.
            ldata = self.data.GetData()
            l = pickle.loads(ldata)
            self.dv.InsertItem(x, y, l)

        # What is returned signals the source what to do
        # with the original data (move, copy, etc.)  In this
        # case we just return the suggested value given to us.
        return d