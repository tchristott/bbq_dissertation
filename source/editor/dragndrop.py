import wx
import wx.lib.newevent
import pickle
import pandas as pd

# Create new event to handle updates of the lists:
TargetUpdateEvent, EVT_TARGET_UPDATE = wx.lib.newevent.NewEvent()

############################################################################################################
##
##  #####   #####    ####    ####           #####   #####    ####   #####
##  ##  ##  ##  ##  ##  ##  ##        ##    ##  ##  ##  ##  ##  ##  ##  ##
##  ##  ##  #####   ######  ## ###  ######  ##  ##  #####   ##  ##  #####
##  ##  ##  ##  ##  ##  ##  ##  ##    ##    ##  ##  ##  ##  ##  ##  ##
##  #####   ##  ##  ##  ##   ####           #####   ##  ##   ####   ##
##
############################################################################################################
## Based on first example in wxpython documentation here:
## https://wiki.wxpython.org/How%20to%20create%20a%20list%20control%20with%20drag%20and%20drop%20%28Phoenix%29
############################################################################################################
class MyDragList(wx.ListCtrl):
    def __init__(self, *arg, **kw):
        wx.ListCtrl.__init__(self, *arg, **kw)

        data = 1
        self.Bind(wx.EVT_LIST_BEGIN_DRAG, self.StartDrag)

        # We do not need to drop into this list
        #dt = MyListDrop(self)
        #self.SetDropTarget(dt)

    #-----------------------------------------------------------------------

    def GetItemInfo(self, idx):
        # Collect all relevant data of a listitem, and put it in a list.

        lst_Drag = []
        lst_Drag.append(idx) # We need the original index, so it is easier to eventualy delete it.
        lst_Drag.append(self.GetItemData(idx)) # Itemdata.
        lst_Drag.append(self.GetItemText(idx,0)) # Text first column.
        for i in range(1, self.GetColumnCount()): # Possible extra columns.
            lst_Drag.append(self.GetItem(idx, i).GetText())
        return lst_Drag

    def StartDrag(self, event):
        # Put together a data object for drag-and-drop _from_ this list.

        lst_Drag = []
        idx = -1
        while True: # Find all the selected items and put them in a list.
            idx = self.GetNextItem(idx, wx.LIST_NEXT_ALL, wx.LIST_STATE_SELECTED)
            if idx == -1:
                break
            lst_Drag.append(self.GetItemText(idx,0))

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
                pos = self.FindItem(0, lst_Drag[i])
                self.DeleteItem(pos)
    
    def ReSort(self):
        dfr_ToSort = pd.DataFrame(columns=["A","B"],index=range(self.GetItemCount()))
        for i in range(len(dfr_ToSort)):
            dfr_ToSort.loc[i,"A"] = self.GetItemText(i,0)
            dfr_ToSort.loc[i,"B"] = self.GetItemText(i,1)
        dfr_ToSort = dfr_ToSort.sort_values(by="A")
        self.DeleteAllItems()
        for i in range(len(dfr_ToSort)):
            self.InsertItem(i,dfr_ToSort.iloc[i,0])
            self.SetItem(i,1,dfr_ToSort.iloc[i,1])

class MyDropTarget(wx.ListCtrl):
    def __init__(self, *arg, **kw):
        wx.ListCtrl.__init__(self, *arg, **kw)

        #------------
        #self.Bind(wx.EVT_LIST_BEGIN_DRAG, self.StartDrag)
        #------------

        dt = MyListDrop(self)
        self.SetDropTarget(dt)

    def Insert(self, x, y, lst_Drag):

        idx_TargetColumn = 2

        # Insert text at given x, y coordinates --- used with drag-and-drop.

        # Find insertion point.
        idx, flags = self.HitTest((x, y))
        if idx == wx.NOT_FOUND: # User did not drop on list item
            if self.GetItemCount() > 0: # If there are items in the list
                if y <= self.GetItemRect(0).y: # User dropped above first item
                    idx = 0
                else:
                    # Change this to return to source list
                    idx = self.GetItemCount() + 1 # Append to end of list.
        else: # Clicked on an item.
            # Get bounding rectangle for the item the user is dropping over.
            rect = self.GetItemRect(idx)
        # Insert into target ListCtrl
        j = 0
        lst_Return = []
        for plate in lst_Drag: # Insert the item data.
            # My Change: Only set seconnd column to value. Add all dragged elements
            if idx+j < self.GetItemCount():
                if self.GetItemText(idx+j,idx_TargetColumn) != "":
                    lst_Return.append(self.GetItemText(idx+j,idx_TargetColumn))
                self.SetItem(idx+j,idx_TargetColumn,plate)
            else:
                lst_Return.append(plate)
            j += 1 # takes variable, adds 1 and returns it.
        #if len(lst_Return) > 0:
        #    for plate in lst_Return:
        #        dic_Source[0].InsertItem(dic_Source[0].GetItemCount(), plate)
        #    dic_Source[0].ReSort()

        # Create and post an event to update things
        event = TargetUpdateEvent(set_bool=True,return_items=lst_Return)
        wx.PostEvent(self,event)

#---------------------------------------------------------------------------

class MyListDrop(wx.DropTarget):

    # Drop target for simple lists.
    def __init__(self, source):
        """
        Arguments:
        source: source listctrl.
        """
        wx.DropTarget.__init__(self)

        #------------
        self.dv = source
        #------------

        # Specify the type of data we will accept.
        self.data = wx.CustomDataObject("ListCtrlItems")
        self.SetDataObject(self.data)

    #-----------------------------------------------------------------------

    # Called when OnDrop returns True.
    # We need to get the data and do something with it.
    def OnData(self, x, y, d):

        # Copy the data from the drag source to our data object.
        if self.GetData():
            # Convert it back to a list and give it to the viewer.
            ldata = self.data.GetData()
            l = pickle.loads(ldata)
            self.dv.Insert(x, y, l)

        # What is returned signals the source what to do
        # with the original data (move, copy, etc.)  In this
        # case we just return the suggested value given to us.
        return d