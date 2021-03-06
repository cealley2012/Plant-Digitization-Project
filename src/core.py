#!/usr/bin/env python
"""
    Implements the core pandastable classes.
    Created Jan 2014
    Copyright (C) Damien Farrell

    This program is free software; you can redistribute it and/or
    modify it under the terms of the GNU General Public License
    as published by the Free Software Foundation; either version 3
    of the License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program; if not, write to the Free Software
    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""

from __future__ import absolute_import, division, print_function
try:
    from tkinter import *
    from tkinter.ttk import *
    from tkinter import filedialog, messagebox, simpledialog
    from tkinter import font
except:
    from Tkinter import *
    from ttk import *
    import tkFileDialog as filedialog
    import tkSimpleDialog as simpledialog
    import tkMessageBox as messagebox
# general imports
import math, time
import os, types
import string, copy
import numpy as np
import pandas as pd
# pandastable imports
from data import TableModel
from headers import ColumnHeader, RowHeader, IndexHeader, RowWidgetColumn
from prefs import Preferences
from dialogs import ImportDialog
import images, util
from dialogs import *
# pd added imports
from catalogOfLife import *
from locality import *
from printLabels import *
import webbrowser


class Table(Canvas):
    """A tkinter class for providing table functionality.

    Args:
        parent: parent Frame
        model: a TableModel with some data
        dataframe: a pandas DataFrame
        width: width of frame
        height: height of frame
        rows: number of rows if creating empty table
        cols: number of columns if creating empty table
        showtoolbar: whether to show the toolbar, default False
        showstatusbar: whether to show the statusbar
    """

    def __init__(self, parent=None, model=None, dataframe=None,
                   width=None, height=None,
                   rows=20, cols=5, showtoolbar=False, showstatusbar=False,
                   **kwargs):

        Canvas.__init__(self, parent, bg='white',
                         width=width, height=height,
                         relief=GROOVE,
                         scrollregion=(0,0,300,200))
        self.parentframe = parent

        #get platform into a variable
        self.ostype = util.checkOS()
        self.platform = platform.system()

        self.width = width
        self.height = height
        self.filename = None
        self.showtoolbar = showtoolbar
        self.showstatusbar = showstatusbar
        self.set_defaults()

        self.currentpage = None
        self.navFrame = None
        # indicates the current row of the Table object
        self.currentrow = 0
        self.currentcol = 0
        self.reverseorder = 0
        self.startrow = self.endrow = None
        self.startcol = self.endcol = None
        self.allrows = False
        self.multiplerowlist=[]
        self.multiplecollist=[]
        self.col_positions=[]
        self.mode = 'normal'
        self.editable = True
        self.filtered = False
        self.child = None
        self.queryrow = 4
        self.childrow = 5
        self.loadPrefs()
        self.currentdir = os.path.expanduser('~')
        #set any options passed in kwargs to overwrite defaults and prefs
        for key in kwargs:
            self.__dict__[key] = kwargs[key]

        if dataframe is not None:
            self.model = TableModel(dataframe=dataframe)
        elif model != None:
            self.model = model
        else:
            self.model = TableModel(rows=rows,columns=cols)

        self.rows = self.model.getRowCount()
        self.cols = self.model.getColumnCount()
        self.tablewidth = (self.cellwidth)*self.cols
        self.doBindings()

        #column specific actions, define for every column type in the model
        #when you add a column type you should edit this dict
        self.columnactions = {'text' : {"Edit":  'drawCellEntry' },
                              'number' : {"Edit": 'drawCellEntry' }}
        self.setFontSize()
        self.importpath = None
        self.prevdf = None

        # List of Initial Column order
        self.column_order = [
            'site#',
            '-',
            'specimen#',
            'eventDate',
            'scientificName',
            'scientificNameAuthorship',
            'genericcolumn1',
            'locality',
            'associatedTaxa',
            'recordedBy',
            'associatedCollectors',
            'samplingEffort',
            'locationRemarks',
            'occurrenceRemarks',
            'genericcolumn2',
            'substrate',
            'habitat',
            'individualCount',
            'reproductiveCondition',
            'establishmentMeans',
            'decimalLatitude',
            'decimalLongitude',
            'coordinateUncertaintyInMeters',
            'minimumElevationInMeters',
            'country',
            'stateProvince',
            'county',
            'municipality',
            'path',
            'catalogNumber',
            'identifiedBy',
            'dateIdentified',
            'otherCatalogNumbers',
            ]
        
        return

    def set_defaults(self):
        """Set default settings"""

        self.cellwidth = 120
        self.maxcellwidth=300
        self.mincellwidth = 30
        self.rowheight=30
        self.horizlines=1
        self.vertlines=1
        self.autoresizecols = 1
        self.inset=2
        self.x_start=0
        self.y_start=1
        self.linewidth=1.0
        self.rowheaderwidth=50
        #self.rowwidgetcolumn = 50
        self.showkeynamesinheader=False
        self.thefont = ('Arial',14)
        self.cellbackgr = '#F4F4F3'
        self.entrybackgr = 'white'
        self.grid_color = '#ABB1AD'
        self.rowselectedcolor = '#E4DED4'
        self.multipleselectioncolor = '#E0F2F7'
        self.boxoutlinecolor = '#084B8A'
        self.colselectedcolor = '#e4e3e4'
        self.floatprecision = 0
        self.columncolors = {}
        self.rowcolors = pd.DataFrame()
        self.bg = Style().lookup('TLabel.label', 'background')
        #Collection data entry bar defaults
        self.collName = ''
        self.detName = ''
        self.useDetDate = 0
        #Catalog number data entry bar defaults
        self.catPrefix = ''
        self.catDigits = 0
        self.catStart = 0
        #Student Collection entry bar defaults
        self.stuCollVerifyBy = ''
        self.stuCollCheckBox = 0
        return

    def setFontSize(self):
        """Set font size to match font, we need to get rid of `size as
            a separate variable?"""

        if hasattr(self, 'thefont') and type(self.thefont) is tuple:
            self.fontsize = self.thefont[1]
        return

    def mouse_wheel(self, event):
        """Handle mouse wheel scroll for windows"""

        if event.num == 5 or event.delta == -120:
            event.widget.yview_scroll(1, UNITS)
            self.rowheader.yview_scroll(1, UNITS)
        if event.num == 4 or event.delta == 120:
            if self.canvasy(0) < 0:
                return
            event.widget.yview_scroll(-1, UNITS)
            self.rowheader.yview_scroll(-1, UNITS)
        self.redrawVisible()
        return

    def doBindings(self):
        """Bind keys and mouse clicks, this can be overriden"""

        self.bind("<Button-1>",self.handle_left_click)
        self.bind("<Double-Button-1>",self.handle_double_click)
        self.bind("<Control-Button-1>", self.handle_left_ctrl_click)
        self.bind("<Shift-Button-1>", self.handle_left_shift_click)

        self.bind("<ButtonRelease-1>", self.handle_left_release)
        # For mac we bind Shift, left-click to right click
        ## Test this on Mac OSX machines
        if self.ostype=='mac':
            self.bind("<Button-2>", self.handle_right_click)
            self.bind('<Shift-Button-1>',self.handle_right_click)
        else:
            self.bind("<Button-3>", self.handle_right_click)

        self.bind('<B1-Motion>', self.handle_mouse_drag)
        #self.bind('<Motion>', self.handle_motion)

        self.bind("<Control-c>", self.copy)
        #self.bind("<Control-x>", self.deleteRow)
        #self.bind_all("<Control-n>", self.addRow)
        self.bind("<Delete>", self.clearData)
        self.bind("<Control-v>", self.paste)
        self.bind("<Control-z>", self.undo)
        self.bind("<Control-a>", self.selectAll)

        self.bind("<Right>", self.handle_arrow_keys)
        self.bind("<Left>", self.handle_arrow_keys)
        self.bind("<Up>", self.handle_arrow_keys)
        self.bind("<Down>", self.handle_arrow_keys)
        self.parentframe.master.bind_all("<KP_8>", self.handle_arrow_keys)
        self.parentframe.master.bind_all("<Return>", self.handle_arrow_keys)
        self.parentframe.master.bind_all("<Tab>", self.handle_arrow_keys)
        #if 'windows' in self.platform:
        self.bind("<MouseWheel>", self.mouse_wheel)
        self.bind('<Button-4>', self.mouse_wheel)
        self.bind('<Button-5>', self.mouse_wheel)
        self.focus_set()
        return

    def show(self, callback=None):
        """Adds column header and scrollbars and combines them with
           the current table adding all to the master frame provided in constructor.
           Table is then redrawn."""

        #Add the table and header to the frame
        self.rowheader = RowHeader(self.parentframe, self, width=self.rowheaderwidth)
        self.tablecolheader = ColumnHeader(self.parentframe, self)
        self.rowindexheader = IndexHeader(self.parentframe, self)
        self.Yscrollbar = AutoScrollbar(self.parentframe,orient=VERTICAL,command=self.set_yviews)
        self.Yscrollbar.grid(row=4,column=3,rowspan=1,sticky='news',pady=0,ipady=0)
        self.Xscrollbar = AutoScrollbar(self.parentframe,orient=HORIZONTAL,command=self.set_xviews)
        self.Xscrollbar.grid(row=5,column=2,columnspan=1,sticky='news')
        self['xscrollcommand'] = self.Xscrollbar.set
        self['yscrollcommand'] = self.Yscrollbar.set 
        self.tablecolheader['xscrollcommand'] = self.Xscrollbar.set
        self.rowheader['yscrollcommand'] = self.Yscrollbar.set
        self.parentframe.rowconfigure(4,weight=1)
        self.parentframe.columnconfigure(2,weight=1)

        self.rowindexheader.grid(row=3,column=1,rowspan=1,sticky='news')
        self.tablecolheader.grid(row=3,column=2,rowspan=1,sticky='news')
        self.rowheader.grid(row=4,column=1,rowspan=1,sticky='news')
        
        self.grid(row=4,column=2,rowspan=1,sticky='news',pady=0,ipady=0)

        self.adjustColumnWidths()
        self.parentframe.bind("<Configure>", self.redrawVisible)
        self.tablecolheader.xview("moveto", 0)
        self.xview("moveto", 0)
        if self.showtoolbar == True:
            self.toolbar = ToolBar(self.parentframe, self)
            self.toolbar.grid(row=0,column=0,columnspan=3,sticky='ew')
        if self.showstatusbar == True:
            self.statusbar = statusBar(self.parentframe, self)
            self.statusbar.grid(row=3,column=0,columnspan=3,sticky='ew')

        self.collectiondataentrybar = CollectionDataEntryBar(self.parentframe,self)
        self.collectiondataentrybar.grid(row=1, column=0, columnspan=3, sticky='we')

        self.catnumberbar = CatNumberBar(self.parentframe,self)
        self.catnumberbar.grid(row=2, column=0, columnspan=3, sticky='we')
        
        self.redraw(callback=callback)
        if hasattr(self, 'pf'):
            self.pf.updateData()
        return

    def remove(self):
        """Close table frame"""

        if hasattr(self, 'parenttable'):
            self.parenttable.child.destroy()
            self.parenttable.child = None
        self.parentframe.destroy()
        return

    def getVisibleRegion(self):
        """Get visible region of canvas"""

        x1, y1 = self.canvasx(0), self.canvasy(0)
        #w, h = self.winfo_width(), self.winfo_height()
        #if w <= 1.0 or h <= 1.0:
        w, h = self.master.winfo_width(), self.master.winfo_height()
        x2, y2 = self.canvasx(w), self.canvasy(h)
        return x1, y1, x2, y2

    def getRowPosition(self, y):
        """Set row position"""

        h = self.rowheight
        y_start = self.y_start
        row = (int(y)-y_start)/h
        if row < 0:
            return 0
        if row > self.rows:
            row = self.rows
        return int(row)

    def getColPosition(self, x):
        """Get column position at coord"""

        x_start = self.x_start
        w = self.cellwidth
        i=0
        col=0
        for c in self.col_positions:
            col = i
            if c+w>=x:
                break
            i+=1
        return int(col)

    def getVisibleRows(self, y1, y2):
        """Get the visible row range"""

        start = self.getRowPosition(y1)
        end = self.getRowPosition(y2)+1
        if end > self.rows:
            end = self.rows
        return start, end

    def getVisibleCols(self, x1, x2):
        """Get the visible column range"""

        start = self.getColPosition(x1)
        end = self.getColPosition(x2)+1
        if end > self.cols:
            end = self.cols
        return start, end

    def redrawVisible(self, event=None, callback=None):
        """Redraw the visible portion of the canvas. This is the core redraw
        method. Refreshes all table elements. Called by redraw() method as shorthand.

        Args:
            event: tkinter event to trigger method, default None
            callback: function to be called after redraw, default None
        """

        model = self.model
        self.delete('addSpecimenWidget')
        self.rows = len(self.model.df.index)
        self.cols = len(self.model.df.columns)
        if self.cols == 0 or self.rows == 0:
            self.delete('entry')
            self.delete('rowrect','colrect')
            self.delete('currentrect','fillrect')
            self.delete('gridline','text')
            self.delete('multicellrect','multiplesel')
            self.delete('colorrect')
            self.setColPositions()
            if self.cols == 0:
                self.tablecolheader.redraw()
            if self.rows == 0:
                self.visiblerows = []
                self.rowheader.redraw()
            return
        self.tablewidth = (self.cellwidth) * self.cols
        self.configure(bg=self.cellbackgr)
        self.setColPositions()

        #are we drawing a filtered subset of the recs?
        if self.filtered == True:
            self.delete('colrect')

        self.rowrange = list(range(0,self.rows))
        self.configure(scrollregion=(0,0, self.tablewidth+self.x_start,
                        self.rowheight*self.rows+10))

        x1, y1, x2, y2 = self.getVisibleRegion()
        startvisiblerow, endvisiblerow = self.getVisibleRows(y1, y2)
        self.visiblerows = list(range(startvisiblerow, endvisiblerow))
        startvisiblecol, endvisiblecol = self.getVisibleCols(x1, x2)
        self.visiblecols = list(range(startvisiblecol, endvisiblecol))

        self.drawGrid(startvisiblerow, endvisiblerow)
        align = self.align
        self.delete('fillrect')
        bgcolor = self.cellbackgr
        df = self.model.df

        #st=time.time()
        def set_precision(x, p):
            if not pd.isnull(x):
                if x<1:
                    x = '{:.{}g}'.format(x, p)
                else:
                    x = '{:.{}f}'.format(x, p)
            return x

        prec = self.floatprecision
        rows = self.visiblerows

        self.model.resetIndex()
        for col in self.visiblecols:
            coldata = df.iloc[rows,col]
            if prec != 0:
                if coldata.dtype == 'float64':
                    coldata = coldata.apply(lambda x: set_precision(x, prec), 1)
            coldata = coldata.astype(object).fillna('')
            offset = rows[0]

            for row in self.visiblerows:
                text = coldata.iloc[row-offset]
                
                if self.model.df.columns[col] == 'specimen#':       #If it is a site record add a widget to generate specimens from it.                  
                    if self.model.getValueAt(row, col) == '!AddSITE':
                        self.drawAddSpecimenWidget(row,col)
                        self.setRowColors(row,'#f9e66b')#set site level row to yellow
                    else:
                        self.drawText(row, col, text, align)
                        self.setRowColors(row,'#baec6d') #set specimen level row to green
                else:
                    self.drawText(row, col, text, align)
            colname = df.columns[col]

        self.colorColumns()
        self.colorRows()
        self.tablecolheader.redraw()
        self.rowheader.redraw(align=self.align)
        self.rowindexheader.redraw()
        self.drawSelectedRow()
        self.drawSelectedRect(self.currentrow, self.currentcol)
        if len(self.multiplerowlist)>1:
            self.rowheader.drawSelectedRows(self.multiplerowlist)
            self.drawMultipleRows(self.multiplerowlist)
            self.drawMultipleCells()
            
        self.tableChanged()  #is it excessive we set table changes every redraw?
        self.refreshSpecimenSiteNums(df)

        return
    def getOnlySpecimenRecords(self):
        """Returns a list of indices which are specimen records. Use it as such:
        self.parentapp.model.df.iloc[self.parentapp.getOnlySpecimenRecords(),:]
        or perhaps, depending on the tkinter frames:
        self.model.df.iloc[self.parentapp.getOnlySpecimenRecords(),:]
        Also see the function called:  self.parentapp.model.df.get_loc('catalogNumber') for use case."""
        listToReturn = [i for i, x in enumerate(self.model.df['specimen#']) if x != '!AddSITE']
        return listToReturn
        


    def redraw(self, event=None, callback=None):
        """Redraw table"""
        self.redrawVisible(event, callback)
        self.saveBarPrefs() # is it excessive to save this every redraw? are we writing way too often?
        if hasattr(self, 'statusbar'):
            self.statusbar.update()
        return

    def redrawCell(self, row=None, col=None, recname=None, colname=None):
        """Redraw a specific cell only"""

        text = self.model.getValueAt(row,col)
        self.delete('celltext'+str(col)+'_'+str(row))
        self.drawText(row, col, text)
        return

    def setColumnColors(self, cols=None, clr=None):
        """Set a column color and store it"""

        if clr is None:
            clr = self.getaColor('#dcf1fc')
        if clr == None:
            return
        if cols == None:
            cols = self.multiplecollist
        colnames = self.model.df.columns[cols]
        for c in colnames:
            self.columncolors[c] = clr
        self.redraw()
        return

    def colorColumns(self, cols=None, color='gray'):
        """Color visible columns"""

        if cols is None:
            cols = self.visiblecols
        self.delete('colorrect')
        for c in cols:
            colname = self.model.df.columns[c]
            if colname in self.columncolors:
                clr = self.columncolors[colname]
                self.drawSelectedCol(c, delete=0, color=clr, tag='colorrect')
        return

    def setColorByMask(self, col, mask, clr):
        """Color individual cells in a column using a mask."""

        df = self.model.df
        if len(self.rowcolors) == 0:
            self.rowcolors = pd.DataFrame(index=range(len(df)))
        rc = self.rowcolors
        if col not in rc.columns:
            rc[col] = pd.Series()
        rc[col] = rc[col].where(-mask, clr)
        #print (rc)
        return

    def colorRows(self):
        """Color individual cells in column(s). Requires that the rowcolors
         dataframe has been set. This needs to be updatedif the index is reset"""

        df = self.model.df
        rc = self.rowcolors
        rows = self.visiblerows
        offset = rows[0]
        idx = df.index[rows]
        for col in self.visiblecols:
            colname = df.columns[col]
            if colname in list(rc.columns):
                colors = rc[colname].ix[idx]
                for row in rows:
                    clr = colors.iloc[row-offset]
                    if not pd.isnull(clr):
                        self.drawRect(row, col, color=clr, tag='colorrect', delete=1)
        return

    def setRowColors(self, rows=None, clr=None):
        """Set rows color from menu"""
        if clr is None:
            clr = self.getaColor('#dcf1fc')
        if clr == None:
            return
        if rows == None:
            rows = self.multiplerowlist

        df = self.model.df
        idx = df.index[rows]
        rc = self.rowcolors
        colnames = df.columns
        for c in colnames:
            if c not in rc.columns:
                rc[c] = pd.Series(np.nan,index=df.index)
        try:
            rc.iloc[idx] = clr
        except IndexError: 
            self.rowcolors = self.rowcolors.append(pd.Series(), ignore_index=True)
            rc = self.rowcolors
            rc.iloc[idx] = clr
        #self.redraw() #recrusive since we've added it elsewhere
        return

    def setColorbyValue(self):
        """Set row colors in a column by values"""

        import pylab as plt
        cmaps = sorted(m for m in plt.cm.datad if not m.endswith("_r"))
        cols = self.multiplecollist
        d = MultipleValDialog(title='color by value',
                                initialvalues=[cmaps,1.0],
                                labels=['colormap:','alpha:'],
                                types=['combobox','string'],
                                parent = self.parentframe)
        if d.result == None:
            return
        cmap = d.results[0]
        alpha =float(d.results[1])
        df = self.model.df
        for col in cols:
            colname = df.columns[col]
            x = df[colname]
            clrs = self.values_to_colors(x, cmap, alpha)
            clrs = pd.Series(clrs,index=df.index)
            rc = self.rowcolors
            rc[colname] = clrs
        self.redraw()
        return

    def getScale(self):
        """Scales font """
        try:
            fontsize = self.thefont[1]
        except:
            fontsize = self.fontsize
        scale = 10.5 * float(fontsize)/9
        return scale

    def adjustColumnWidths(self):
        """Optimally adjust col widths to accomodate the longest entry
            in each column - usually only called on first redraw"""

        try:
            fontsize = self.thefont[1]
        except:
            fontsize = self.fontsize
        scale = self.getScale()
        for col in range(self.cols):
            colname = self.model.getColumnName(col)
            if colname == 'site#':
                l = 4
            if colname == '-':
                l = 1
            if colname == 'specimen#':
                l = 6
            elif colname in self.model.columnwidths:
                w = self.model.columnwidths[colname]
                l = self.model.getlongestEntry(col)
            else:
                w = self.cellwidth
                l = self.model.getlongestEntry(col)
                if l < 5:
                    l = 5
            txt = ''.join(['X' for i in range(l+1)])
            tw,tl = util.getTextLength(txt, self.maxcellwidth,
                                       font=self.thefont)
            #print (col,txt,l,tw)
            if colname not in ['site#','-','specimen#']:
                if tw >= self.maxcellwidth:
                    tw = self.maxcellwidth
                elif tw < self.cellwidth:
                    tw = self.cellwidth
            self.model.columnwidths[colname] = tw
        return

    def autoResizeColumns(self):
        """Automatically set nice column widths and draw"""

        self.adjustColumnWidths()
        self.redraw()
        return

    def setColPositions(self):
        """Determine current column grid positions"""

        df = self.model.df
        self.col_positions=[]
        w = self.cellwidth
        x_pos = self.x_start
        self.col_positions.append(x_pos)
        for col in range(self.cols):
            colname = str(df.columns[col])
            if colname in self.model.columnwidths:
                x_pos = x_pos+self.model.columnwidths[colname]
            else:
                x_pos = x_pos+w
            self.col_positions.append(x_pos)
        self.tablewidth = self.col_positions[len(self.col_positions)-1]
        return

    def sortTable(self, columnIndex=None, ascending=1, index=False):
        """Set up sort order dict based on currently selected field"""
        
        df = self.model.df
        if columnIndex == None:
            columnIndex = self.multiplecollist
        if isinstance(columnIndex, int):
            columnIndex = [columnIndex]
        #assert len(columnIndex) < len(df.columns)
        if index == True:
            df.sort_index(inplace=True)
        else:
            colnames = list(df.columns[columnIndex])
            try:
                df.sort_values(by=colnames, inplace=True, ascending=ascending)
                
            except TypeError:                   #If mixed int/str column probably result of filling NaN with ''
                def tempConvertForSort(v):      #Handle it by creating temp columns and fill '' with negative values which to sort by
                    if v == '':
                        return int(-9999)
                    else:
                        return v                    
                tempColNames = []
                for colName in colnames:
                    df['tempSort_{}'.format(colName)] = df[colName].apply(lambda x: tempConvertForSort(x))
                    tempColNames.append('tempSort_{}'.format(colName))
                df.sort_values(by=tempColNames, inplace=True, ascending= True)
                df.drop(tempColNames, axis = 1, inplace = True)     #Drop temporary helper columns
                       
            except Exception as e:
                       print('core.py error in function "sortTable", error: {}'.format(e))
                
        self.redraw()
        return

    def sortColumnIndex(self):
        """Sort the column header by the current rows values"""

        cols = self.model.df.columns
        #get only sortable cols
        temp = self.model.df.convert_objects(convert_numeric=True)
        temp = temp.select_dtypes(include=['int','float'])
        rowindex = temp.index[self.currentrow]
        row = temp.ix[rowindex]
        #add unsortable cols to end of new ordered ones
        newcols = list(temp.columns[row.argsort()])
        a = list(set(cols) - set(newcols))
        newcols.extend(a)
        self.model.df = self.model.df.reindex(columns=newcols)
        self.redraw()
        return

    def groupby(self, colindex):
        """Group by"""

        grps = self.model.groupby(colindex)
        return

    def setindex(self):
        """Set indexes"""

        cols = self.multiplecollist
        self.model.setindex(cols)
        if self.model.df.index.name is not None:
            self.showIndex()
        self.setSelectedCol(0)
        self.update_rowcolors()
        self.redraw()
        self.drawSelectedCol()
        if hasattr(self, 'pf'):
            self.pf.updateData()
        return

    def resetIndex(self):
        """Reset index and redraw row header"""

        self.model.resetIndex()
        self.update_rowcolors()
        self.redraw()
        self.drawSelectedCol()
        if hasattr(self, 'pf'):
            self.pf.updateData()
        return

    def copyIndex(self):
        """Copy index to a column"""

        self.model.copyIndex()
        self.redraw()
        return

    def renameIndex(self, ):
        """Rename the row index"""

        n = self.model.df.index.name
        name = simpledialog.askstring("New index name",
                                      "New name:",initialvalue=n,
                                       parent=self.parentframe)
        if name:
            self.model.df.index.name = name
            self.rowindexheader.redraw()
        return

    def showIndex(self):
        """Show the row index"""

        self.rowheader.showindex = True
        return

    def update_rowcolors(self):
        """Update row colors if present"""

        df = self.model.df
        if len(self.rowcolors) == len(df):
            self.rowcolors.set_index(df.index, inplace=True)
        return

    def set_xviews(self,*args):
        """Set the xview of table and col header"""

        self.xview(*args)
        self.tablecolheader.xview(*args)
        self.redrawVisible()
        return

    def set_yviews(self,*args):
        """Set the yview of table and row header
        Example usage: self.set_yviews('moveto', y-0.01)"""

        self.yview(*args)
        self.rowheader.yview(*args)
        self.redrawVisible()
        return

    def addRowFromSite(self, event=None):
        """Helper function to pass row to addRowFromSite
           in data.py"""

        self.storeCurrent()
        row = self.getSelectedRow()
        siteData = self.model.df.loc[row].to_dict() #occasional error, this func adds incorrect site Num row

        # open a dialog box to ASK for some necessary values upon adding the specimen
        # uses pandastables dialogs.py helpers
        d = MultipleValDialog(title='New Specimen',
                                initialvalues=('', CollectionDataEntryBar.detNameVar.get()),
                                labels=('Scientific name: ','Determined by: '),
                                types=('string','string'),
                                parent = self.parentframe)
        if d.result == None:
            return
        else:
            siteData['scientificName'] = d.results[0]
            siteData['identifiedBy'] = d.results[1]

        oldOtherSiteNum = siteData.get('site#')
        siteData.pop('specimen#', None)
        specimenNumbers = self.model.df['specimen#'].tolist()
        try:
            nextSpecimenNumber = max([int(y) for y in[x for x in specimenNumbers if isinstance(x, int)]]) + 1
        except ValueError:
            nextSpecimenNumber = 1
        newOtherCatNumber = str(oldOtherSiteNum) + '-' + str(nextSpecimenNumber)
        siteData['otherCatalogNumbers'] = newOtherCatNumber
        df = self.model.df
        a, b = df[:row], df[row:]
        a = a.append(siteData, ignore_index=True)
        self.model.df = pd.concat([a,b], ignore_index=True)
        self.model.resetIndex()
        self.refreshSpecimenSiteNums(self.model.df)
        self.sortTable([self.model.df.columns.get_loc('site#'),self.model.df.columns.get_loc('specimen#')])
        self.setSelectedRow(row)
        self.redraw()
        return

    def addSite(self):
        """Inserts a "Site" row at the required index by append/concat"""

        self.storeCurrent()
        rowindex = self.getSelectedRow()
        a, b = self.model.df[:rowindex], self.model.df[rowindex:]
        
        def siteNumExtract(catNum):
            """ input a field number formatted as "siteNumber-SpecimenNumber" (ie: 04-124)
            In the case of site only data, use "siteNumber-#" (ie: 05-#) returns the first "site number" value.
            Using this method instead of calling defined function in core.py for simplicity.
            There may be a cleaner way to do this."""
    
            try:
                result = catNum.split('-')[0]
                if result.isdigit():
                    return int(result)
                else:
                    return 0
            except: #an open exception catcher may be unwise.
                return 0
        maxSiteNum = max(self.model.df['otherCatalogNumbers'].apply(lambda x: siteNumExtract(x)))
        newSiteData = {'otherCatalogNumbers':'{}-#'.format(maxSiteNum + 1), '-':'-'}
        a = a.append(pd.Series(newSiteData), ignore_index=1)
        self.model.df = pd.concat([a,b])
        self.refreshSpecimenSiteNums(self.model.df)
        self.sortTable([self.model.df.columns.get_loc('site#'),self.model.df.columns.get_loc('specimen#')])
        self.model.resetIndex()
        self.setSelectedRow(self.model.df.shape[0] - 1)
        self.drawSelectedRow()
        self.movetoSelectedRow(self.getSelectedRow())
        self.redraw()
        return

    def addRow(self):
        """Insert a new row"""

        row = self.getSelectedRow()
        key = self.model.addRow(row)
        self.redraw()
        return

    def addRows(self, num=None):
        """Add new rows"""

        if num == None:
            num = simpledialog.askinteger("Now many rows?",
                                            "Number of rows:",initialvalue=1,
                                             parent=self.parentframe)
        if not num:
            return
        self.storeCurrent()
        keys = self.model.autoAddRows(num)
        self.redraw()
        return

    def addColumn(self, newname=None):
        """Add a new column"""

        if newname == None:
            coltypes = ['object','float64']
            d = MultipleValDialog(title='New Column',
                                    initialvalues=(coltypes, ''),
                                    labels=('Column Type','Name'),
                                    types=('combobox','string'),
                                    parent = self.parentframe)
            if d.result == None:
                return
            else:
                dtype = d.results[0]
                newname = d.results[1]

        df = self.model.df
        if newname != None:
            if newname in self.model.df.columns:
                messagebox.showwarning("Name exists",
                                        "Name already exists!",
                                        parent=self.parentframe)
            else:
                self.storeCurrent()
                self.model.addColumn(newname, dtype)
                self.parentframe.configure(width=self.width)
                self.redraw()
                
        return

    def deleteRow(self):
        """Delete a row"""
        if len(self.multiplerowlist)>1:
            n = messagebox.askyesno("Delete",
                                      "Delete selected rows?",
                                      parent=self.parentframe)
            if n == True:
                self.storeCurrent()
                rows = self.multiplerowlist
                self.model.deleteRows(rows)
                self.setSelectedRow(0)
                self.clearSelected()
                self.model.resetIndex()
                self.redraw()
        else:
            n = messagebox.askyesno("Delete",
                                      "Delete this row?",
                                      parent=self.parentframe)
            if n:
                self.storeCurrent()
                row = self.getSelectedRow()
                self.model.deleteRows([row])
                self.setSelectedRow(row-1)
                self.clearSelected()
                self.redraw()
        return

    def deleteColumn(self):
        """Delete currently selected column(s)"""

        n =  messagebox.askyesno("Delete",
                                   "Delete Column(s)?",
                                   parent=self.parentframe)
        if not n:
            return
        self.storeCurrent()
        cols = self.multiplecollist
        self.model.deleteColumns(cols)
        self.setSelectedCol(0)
        self.redraw()
        self.drawSelectedCol()
        return

    def tableChanged(self):
        """Callback to be used when dataframe changes so that other
            widgets and data can be updated"""
        self.updateFunctions()
        if hasattr(self, 'pf'):
            self.pf.updateData()
        return

    def storeCurrent(self):
        """Store current version of the table before a major change is made"""

        self.prevdf = self.model.df.copy()
        return

    def undo(self, event=None):
        """Undo last major table change"""

        if self.prevdf is None:
            return
        self.model.df = self.prevdf
        self.redraw()
        self.prevdf = None
        self.storeCurrent()
        return

    def deleteCells(self, rows, cols, answer=None):
        """Clear the cell contents"""

        if answer == None:
            answer =  messagebox.askyesno("Clear Confirm",
                                    "Clear this data?",
                                    parent=self.parentframe)
        if not answer:
            return
        self.storeCurrent()
        self.model.deleteCells(rows, cols)
        self.redraw()
        return

    def clearData(self, evt=None):
        """Delete cells from gui event"""

        if self.allrows == True:
            self.deleteColumn()
            return
        rows = self.multiplerowlist
        cols = self.multiplecollist
        self.deleteCells(rows, cols)
        return

    def clearTable(self):
        """Make an empty table"""
        n =  messagebox.askyesno("Clear Confirm",
                                   "This will clear the entire table.\nAre you sure?",
                                   parent=self.parentframe)
        if not n:
            return
        self.storeCurrent()
        model = TableModel(pd.DataFrame())
        self.updateModel(model)
        self.redraw()
        return

    def autoAddColumns(self, numcols=None):
        """Automatically add x number of cols"""

        if numcols == None:
            numcols = simpledialog.askinteger("Auto add rows.",
                                                "How many empty columns?",
                                                parent=self.parentframe)
        self.model.auto_AddColumns(numcols)
        self.parentframe.configure(width=self.width)
        self.redraw()
        return

    # may not need
    ## should probably customize rather than delete
    def setColumnType(self):
        """Change the column dtype"""

        df = self.model.df
        col = df.columns[self.currentcol]
        coltypes = ['object','str','int','float64','category']
        curr = df[col].dtype
        d = MultipleValDialog(title='current type is %s' %curr,
                                initialvalues=[coltypes],
                                labels=['Type:'],
                                types=['combobox'],
                                parent = self.parentframe)
        if d.result == None:
            return
        t = d.results[0]
        try:
            self.model.df[col] = df[col].astype(t)
            self.redraw()
        except:
            print('failed')
        return

    # may not need
    def cleanData(self):
        """Deal with missing data"""

        df = self.model.df
        cols = df.columns
        fillopts = ['','fill scalar','ffill','bfill','interpolate']
        d = MultipleValDialog(title='Clean Data',
                                initialvalues=(fillopts,'-','10',0,0,['any','all'],0,0,0),
                                labels=('Fill missing method:',
                                        'Fill symbol:',
                                        'Limit gaps:',
                                        'Drop columns with null data:',
                                        'Drop rows with null data:',
                                        'Drop method:',
                                        'Drop duplicate rows:',
                                        'Drop duplicate columns:',
                                        'Round numbers:'),
                                types=('combobox','string','string','checkbutton',
                                       'checkbutton','combobox','checkbutton','checkbutton','string'),
                                parent = self.parentframe)
        if d.result == None:
            return
        self.storeCurrent()
        method = d.results[0]
        symbol = d.results[1]
        limit = int(d.results[2])
        dropcols = d.results[3]
        droprows = d.results[4]
        how = d.results[5]
        dropdups = d.results[6]
        dropdupcols = d.results[7]
        rounddecimals = int(d.results[8])
        if method == '':
            pass
        elif method == 'fill scalar':
            df = df.fillna(symbol)
        elif method == 'interpolate':
            df = df.interpolate()
        else:
            df = df.fillna(method=method, limit=limit)
        if dropcols == 1:
            df = df.dropna(axis=1,how=how)
        if droprows == 1:
            df = df.dropna(axis=0,how=how)
        if dropdups == 1:
            df = df.drop_duplicates()
        if dropdupcols == 1:
            df = df.loc[:,~df.columns.duplicated()]
        if rounddecimals != 0:
            df = df.round(rounddecimals)
        self.model.df = df
        self.redraw()
        return

    # may not need
    def resample(self):
        """table resampling dialog"""

        df = self.model.df
        if not isinstance(df.index, pd.DatetimeIndex):
            messagebox.showwarning("No datetime index", 'Index should be a datetime',
                                   parent=self.parentframe)
            return

        conv = ['start','end']
        freqs = ['M','W','D','H','min','S','Q','A','AS','L','U']
        funcs = ['mean','sum','count','max','min','std','first','last']
        d = MultipleValDialog(title='Resample',
                                initialvalues=(freqs,1,funcs,conv),
                                labels=('Frequency:','Periods','Function'),
                                types=('combobox','string','combobox'),
                                tooltips=('Unit of time e.g. M for months',
                                          'How often to group e.g. every 2 months',
                                          'Function to apply'),
                                parent = self.parentframe)
        if d.result == None:
            return
        freq = d.results[0]
        period = d.results[1]
        func = d.results[2]
        #conv = d.results[3]

        rule = str(period)+freq
        new = df.resample(rule).apply(func)
        self.createChildTable(new, index=True)
        #df.groupby(pd.TimeGrouper(freq='M'))
        return

    def _callFunction(self, df, funcname):
        """Get function from a string as a module level or dataframe method and
        apply it to the dataframe. Pops up a dialog allowing entry of arguments as some
        functions will not run without non kw args. This is meant to be a general
        solution to applying functions without the need to custom dialogs.
        Returns the new DataFrame"""

        col = df.columns[0]
        import inspect
        if hasattr(pd, funcname):
            func = getattr(pd, funcname)
            obj = pd
        elif hasattr(df, funcname):
            func = getattr(df, funcname)
            obj = df
        elif hasattr(df[col].str, funcname):
            #string methods object
            func = getattr(df[col].str, funcname)
            obj = df[col].str
        else:
            return

        a = inspect.getfullargspec(func)
        args = a.args
        if a.defaults is None:
            p={}
        else:
            defaults = list(a.defaults)
            print (args[0])
            if args[0] not in ['values','self','data']:
                defaults.insert(0,a.varargs)
            print(defaults)
            labels = a.args[-len(defaults):]
            types=[]
            for d in defaults:
                if isinstance(d, bool):
                    t='checkbutton'
                elif isinstance(d, int):
                    t='int'
                else:
                    t='string'
                types.append(t)

            #print(labels)
            print(types)
            #auto populate a dialog with function parameters
            d = MultipleValDialog(title='Parameters',
                                  initialvalues=defaults,
                                  labels=labels,
                                  types=types,
                                  parent = self.parentframe)
            p = d.getResults(null='')
            print(p)

        #print (obj)
        if obj is pd:
            new = df.apply(func, **p)
        elif obj is df:
            new = func(**p)
        else:
            new = func(**p)
        return new

    # could leverage this to format dates to fit Symbiota dbase
    ## check import error to see desired format
    def convertDates(self):
        """Convert single or multiple columns into datetime"""

        df = self.model.df
        cols = list(df.columns[self.multiplecollist])
        if len(cols) == 1:
            colname = cols[0]
            temp = df[colname]
        else:
            colname = '-'.join(cols)
            temp = df[cols]

        if len(cols) == 1 and temp.dtype == 'datetime64[ns]':
            title = 'Date->string extract'
        else:
            title = 'String->datetime convert'
        timeformats = ['infer','%d%m%Y','%Y%m%d']
        props = ['day','month','minute','second','year',
                 'dayofyear','weekofyear','quarter']
        d = MultipleValDialog(title=title,
                                initialvalues=['',timeformats,props,True],
                                labels=['Column name:','Convert to date:',
                                        'Extract from datetime:','In place:'],
                                types=['string','combobox','combobox','checkbutton'],
                                parent = self.parentframe)

        if d.result == None:
            return
        self.storeCurrent()
        newname = d.results[0]
        if newname != '':
            colname = newname
        fmt = d.results[1]
        prop = d.results[2]
        inplace = d.results[3]
        if fmt == 'infer':
            fmt = None

        if len(cols) == 1 and temp.dtype == 'datetime64[ns]':
            if newname == '':
                colname = prop
            df[colname] = getattr(temp.dt, prop)
        else:
            try:
                df[colname] = pd.to_datetime(temp, format=fmt, errors='coerce')
            except Exception as e:
                messagebox.showwarning("Convert error", e,
                                        parent=self.parentframe)
        if inplace == False or len(cols)>1:
            #print (cols[-1])
            self.placeColumn(colname, cols[-1])

        self.redraw()
        return

    def showAll(self):
        """Re-show unfiltered"""

        if hasattr(self, 'dataframe'):
            self.model.df = self.dataframe
        self.filtered = False
        self.redraw()
        return

    # def statsViewer(self):
    #     """Show model fitting dialog"""

    #     from .stats import StatsViewer
    #     if StatsViewer._doimport() == 0:
    #         messagebox.showwarning("no such module",
    #                                 "statsmodels is not installed.",
    #                                 parent=self.parentframe)
    #         return

    #     if not hasattr(self, 'sv') or self.sv == None:
    #         sf = self.statsframe = Frame(self.parentframe)
    #         sf.grid(row=self.queryrow+1,column=0,columnspan=3,sticky='news')
    #         self.sv = StatsViewer(table=self,parent=sf)
    #     return self.sv

    def getRowsFromIndex(self, idx=None):
        """Get row positions from index values"""

        df = self.model.df
        if idx is not None:
            return [df.index.get_loc(i) for i in idx]
        return []

    def getRowsFromMask(self, mask):
        df = self.model.df
        if mask is not None:
            idx = df.ix[mask].index
        return self.getRowsFromIndex(idx)

    # may not need
    def query(self, evt=None):
        """Do query"""

        self.qframe.query()
        return

    # may not need
    def queryBar(self, evt=None):
        """Query/filtering dialog"""

        if hasattr(self, 'qframe') and self.qframe != None:
            return
        self.qframe = QueryDialog(self)
        self.qframe.grid(row=self.queryrow,column=0,columnspan=3,sticky='news')
        return

    def _eval(self, df, ex):
        """Evaluate an expression using numexpr"""

        #uses assignments to globals() - check this is ok
        import numexpr as ne
        for c in df:
            globals()[c] = df[c].as_matrix()
        a = ne.evaluate(ex)
        return a

    def evalFunction(self, evt=None):
        """Apply a string based function to create new columns"""

        self.convertNumeric()
        s = self.evalvar.get()

        if s=='':
            return
        df = self.model.df
        vals = s.split('=')
        if len(vals)==1:
            ex = vals[0]
            n = ex
        else:
            n, ex = vals
        if n == '':
            return
        #evaluate
        try:
            df[n] = self._eval(df, ex)
            self.functionentry.configure(style="White.TCombobox")
        except Exception as e:
            print ('function parse error')
            print (e)
            self.functionentry.configure(style="Red.TCombobox")
            return
        #keep track of which cols are functions?
        self.formulae[n] = ex

        if self.placecolvar.get() == 1:
            cols = df.columns
            self.placeColumn(n,cols[0])
        if self.recalculatevar.get() == 1:
            self.recalculateFunctions(omit=n)
        else:
            self.redraw()
        #update functions list in dropdown
        funclist = ['='.join(i) for i in self.formulae.items()]
        self.functionentry['values'] = funclist
        return

    def recalculateFunctions(self, omit=None):
        """Re evaluate any columns that were derived from functions
        and dependent on other columns (except self derived?)"""

        df = self.model.df
        for n in self.formulae:
            if n==omit: continue
            ex = self.formulae[n]
            #need to check if self calculation here...
            try:
                df[n] = self._eval(df, ex)
            except:
                print('could not calculate %s' %ex)
        self.redraw()
        return

    def updateFunctions(self):
        """Remove functions if a column has been deleted"""

        if not hasattr(self, 'formulae'):
            return
        df = self.model.df
        cols = list(df.columns)
        for n in list(self.formulae.keys()):
            if n not in cols:
                del(self.formulae[n])
        return

    def resizeColumn(self, col, width):
        """Resize a column by dragging"""

        colname = self.model.getColumnName(col)
        self.model.columnwidths[colname] = width
        self.setColPositions()
        self.delete('colrect')
        #self.drawSelectedCol(self.currentcol)
        self.redraw()
        return

    def get_row_clicked(self, event):
        """Get row where event on canvas occurs"""

        h=self.rowheight
        #get coord on canvas, not window, need this if scrolling
        y = int(self.canvasy(event.y))
        y_start=self.y_start
        rowc = int((int(y)-y_start)/h)
        return rowc

    def get_col_clicked(self,event):
        """Get column where event on the canvas occurs"""

        w = self.cellwidth
        x = int(self.canvasx(event.x))
        x_start = self.x_start
        for colpos in self.col_positions:
            try:
                nextpos = self.col_positions[self.col_positions.index(colpos)+1]
            except:
                nextpos = self.tablewidth
            if x > colpos and x <= nextpos:
                #print 'x=', x, 'colpos', colpos, self.col_positions.index(colpos)
                return self.col_positions.index(colpos)
        return

    def setSelectedRow(self, row):
        """Set currently selected row and reset multiple row list"""

        self.currentrow = row
        self.multiplerowlist = []
        self.multiplerowlist.append(row)
        return

    def setSelectedCol(self, col):
        """Set currently selected column"""

        self.currentcol = col
        self.multiplecollist = []
        self.multiplecollist.append(col)
        return

    def setSelectedCells(self, startrow, endrow, startcol, endcol):
        """Set a block of cells selected"""

        self.currentrow = startrow
        self.currentcol = startcol
        if startrow < 0 or startcol < 0:
            return
        if endrow > self.rows or endcol > self.cols:
            return
        for r in range(startrow, endrow):
            self.multiplerowlist.append(r)
        for c in range(startcol, endcol):
            self.multiplecollist.append(c)
        return

    def getSelectedRow(self):
        """Get currently selected row"""
        return self.currentrow

    def getSelectedColumn(self):
        """Get currently selected column"""
        return self.currentcol

    def selectAll(self, evt=None):
        """Select all rows and cells"""

        self.startrow = 0
        self.endrow = self.rows
        self.multiplerowlist = list(range(self.startrow,self.endrow))
        self.drawMultipleRows(self.multiplerowlist)
        self.startcol = 0
        self.endcol = self.cols
        self.multiplecollist = list(range(self.startcol, self.endcol))
        self.drawMultipleCells()
        return

    def selectNone(self):
        """Deselect current, called when table is redrawn with
        completely new cols and rows e.g. after model is updated."""

        self.multiplecollist = []
        self.multiplerowlist = []
        self.startrow = self.endrow = 0
        self.delete('multicellrect','multiplesel','colrect')
        return

    def getCellCoords(self, row, col):
        """Get x-y coordinates to drawing a cell in a given row/col"""

        colname=self.model.getColumnName(col)
        if colname in self.model.columnwidths:
            w=self.model.columnwidths[colname]
        else:
            w=self.cellwidth
        h=self.rowheight
        x_start=self.x_start
        y_start=self.y_start

        #get nearest rect co-ords for that row/col
        x1=self.col_positions[col]
        y1=y_start+h*row
        x2=x1+w
        y2=y1+h
        return x1,y1,x2,y2

    def getCanvasPos(self, row, col):
        """Get the cell x-y coords as a fraction of canvas size"""

        if self.rows==0:
            return None, None
        x1,y1,x2,y2 = self.getCellCoords(row,col)
        cx=float(x1)/self.tablewidth
        cy=float(y1)/(self.rows*self.rowheight)
        return cx, cy

    def isInsideTable(self,x,y):
        """Returns true if x-y coord is inside table bounds"""

        if self.x_start < x < self.tablewidth and self.y_start < y < self.rows*self.rowheight:
            return 1
        else:
            return 0
        return answer

    def setRowHeight(self, h):
        """Set the row height"""
        self.rowheight = h
        return

    def clearSelected(self):
        """Clear selections"""

        self.delete('rect')
        self.delete('entry')
        self.delete('tooltip')
        self.delete('searchrect')
        self.delete('colrect')
        self.delete('multicellrect')
        return

    def gotoprevRow(self):
        """Programmatically set previous row - eg. for button events"""

        self.clearSelected()
        current = self.getSelectedRow()
        self.setSelectedRow(current-1)
        self.startrow = current-1
        self.endrow = current-1
        #reset multiple selection list
        self.multiplerowlist=[]
        self.multiplerowlist.append(self.currentrow)
        self.drawSelectedRect(self.currentrow, self.currentcol)
        self.drawSelectedRow()
        # coltype = self.model.getColumnType(self.currentcol)
        # if coltype == 'text' or coltype == 'number':
        #     self.drawCellEntry(self.currentrow, self.currentcol)
        return

    def gotonextRow(self):
        """Programmatically set next row - eg. for button events"""

        self.clearSelected()
        current = self.getSelectedRow()
        self.setSelectedRow(current+1)
        self.startrow = current+1
        self.endrow = current+1
        #reset multiple selection list
        self.multiplerowlist=[]
        self.multiplerowlist.append(self.currentrow)
        self.drawSelectedRect(self.currentrow, self.currentcol)
        self.drawSelectedRow()
        # coltype = self.model.getColumnType(self.currentcol)
        # if coltype == 'text' or coltype == 'number':
        #     self.drawCellEntry(self.currentrow, self.currentcol)
        return

    def handle_left_click(self, event):
        """Respond to a single press"""

        self.clearSelected()
        self.allrows = False
        #which row and column is the click inside?
        rowclicked = self.get_row_clicked(event)
        colclicked = self.get_col_clicked(event)
        if colclicked == None:
            return
        self.focus_set()

        if hasattr(self, 'cellentry'):
            self.cellentry.destroy()
        #ensure popup menus are removed if present
        if hasattr(self, 'rightmenu'):
            self.rightmenu.destroy()
        if hasattr(self.tablecolheader, 'rightmenu'):
            self.tablecolheader.rightmenu.destroy()

        self.startrow = rowclicked
        self.endrow = rowclicked
        self.startcol = colclicked
        self.endcol = colclicked
        #reset multiple selection list
        self.multiplerowlist=[]
        self.multiplerowlist.append(rowclicked)
        if 0 <= rowclicked < self.rows and 0 <= colclicked < self.cols:
            self.setSelectedRow(rowclicked)
            self.setSelectedCol(colclicked)
            self.drawSelectedRect(self.currentrow, self.currentcol)
            self.drawSelectedRow()
            self.rowheader.drawSelectedRows(rowclicked)
            self.tablecolheader.delete('rect')
        if hasattr(self, 'cellentry'):
            self.cellentry.destroy()
        return

    def handle_left_release(self,event):
        self.endrow = self.get_row_clicked(event)
        return

    def handle_left_ctrl_click(self, event):
        """Handle ctrl clicks for multiple row selections"""

        rowclicked = self.get_row_clicked(event)
        colclicked = self.get_col_clicked(event)
        if 0 <= rowclicked < self.rows and 0 <= colclicked < self.cols:
            if rowclicked not in self.multiplerowlist:
                self.multiplerowlist.append(rowclicked)
            else:
                self.multiplerowlist.remove(rowclicked)
            self.drawMultipleRows(self.multiplerowlist)
            if colclicked not in self.multiplecollist:
                self.multiplecollist.append(colclicked)
            self.drawMultipleCells()
        return

    def handle_left_shift_click(self, event):
        """Handle shift click, for selecting multiple rows"""

        self.handle_mouse_drag(event)
        return

    def handle_mouse_drag(self, event):
        """Handle mouse moved with button held down, multiple selections"""

        if hasattr(self, 'cellentry'):
            self.cellentry.destroy()
        rowover = self.get_row_clicked(event)
        colover = self.get_col_clicked(event)
        if colover == None or rowover == None:
            return

        if rowover >= self.rows or self.startrow > self.rows:
            return
        else:
            self.endrow = rowover
        #do columns
        if colover > self.cols or self.startcol > self.cols:
            return
        else:
            self.endcol = colover
            if self.endcol < self.startcol:
                self.multiplecollist=list(range(self.endcol, self.startcol+1))
            else:
                self.multiplecollist=list(range(self.startcol, self.endcol+1))
            #print self.multiplecollist
        #draw the selected rows
        if self.endrow != self.startrow:
            if self.endrow < self.startrow:
                self.multiplerowlist=list(range(self.endrow, self.startrow+1))
            else:
                self.multiplerowlist=list(range(self.startrow, self.endrow+1))
            self.drawMultipleRows(self.multiplerowlist)
            self.rowheader.drawSelectedRows(self.multiplerowlist)
            #draw selected cells outline using row and col lists
            self.drawMultipleCells()
        else:
            self.multiplerowlist = []
            self.multiplerowlist.append(self.currentrow)
            if len(self.multiplecollist) >= 1:
                self.drawMultipleCells()
            self.delete('multiplesel')
        return

    def handle_arrow_keys(self, event):
        """Handle arrow keys press"""
        #print event.keysym

        row = self.get_row_clicked(event)
        col = self.get_col_clicked(event)
        x,y = self.getCanvasPos(self.currentrow, 0)
        if x == None:
            return

        if event.keysym == 'Up':
            if self.currentrow == 0:
                return
            else:
                #self.yview('moveto', y)
                #self.rowheader.yview('moveto', y)
                self.currentrow  = self.currentrow -1
        elif event.keysym == 'Down':
            if self.currentrow >= self.rows-1:
                return
            else:
                #self.yview('moveto', y)
                #self.rowheader.yview('moveto', y)
                self.currentrow  = self.currentrow +1
        elif event.keysym == 'Right' or event.keysym == 'Tab':
            if self.currentcol >= self.cols-1:
                if self.currentrow < self.rows-1:
                    self.currentcol = 0
                    self.currentrow  = self.currentrow +1
                else:
                    return
            else:
                self.currentcol  = self.currentcol +1
        elif event.keysym == 'Left':
            self.currentcol  = self.currentcol -1
        self.drawSelectedRect(self.currentrow, self.currentcol)
        coltype = self.model.getColumnType(self.currentcol)
        #if coltype == 'text' or coltype == 'number':
        #    self.delete('entry')
        #    self.drawCellEntry(self.currentrow, self.currentcol)
        return

    def handle_double_click(self, event):
        """Do double click stuff. Selected row/cols will already have
           been set with single click binding"""

        row = self.get_row_clicked(event)
        col = self.get_col_clicked(event)
        self.drawCellEntry(self.currentrow, self.currentcol)
        return

    def handle_right_click(self, event):
        """respond to a right click"""

        self.delete('tooltip')
        self.rowheader.clearSelected()
        if hasattr(self, 'rightmenu'):
            self.rightmenu.destroy()
        rowclicked = self.get_row_clicked(event)
        colclicked = self.get_col_clicked(event)
        if colclicked == None:
            self.rightmenu = self.popupMenu(event, outside=1)
            return

        if (rowclicked in self.multiplerowlist or self.allrows == True) and colclicked in self.multiplecollist:
            self.rightmenu = self.popupMenu(event, rows=self.multiplerowlist, cols=self.multiplecollist)
        else:
            if 0 <= rowclicked < self.rows and 0 <= colclicked < self.cols:
                self.clearSelected()
                self.allrows = False
                self.setSelectedRow(rowclicked)
                self.setSelectedCol(colclicked)
                self.drawSelectedRect(self.currentrow, self.currentcol)
                self.drawSelectedRow()
            if self.isInsideTable(event.x,event.y) == 1:
                self.rightmenu = self.popupMenu(event,rows=self.multiplerowlist, cols=self.multiplecollist)
            else:
                self.rightmenu = self.popupMenu(event, outside=1)
        return

    def placeColumn(self, col1, col2):
        """Move col2 next to col1, useful for placing a new column
        made from the first one next to it so user can see it easily"""

        ind1 = self.model.df.columns.get_loc(col1)
        ind2 = self.model.df.columns.get_loc(col2)
        self.model.moveColumn(ind1, ind2+1)
        self.redraw()
        return

    def gotonextCell(self):
        """Move highlighted cell to next cell in row or a new col"""

        if hasattr(self, 'cellentry'):
            self.cellentry.destroy()
        self.currentrow = self.currentrow+1
        #if self.currentcol >= self.cols-1:
        #    self.currentcol = self.currentcol+1
        self.drawSelectedRect(self.currentrow, self.currentcol)
        return

    def movetoSelectedRow(self, row=None, recname=None):
        """Move to selected row, updating table"""
        #row=self.model.getRecordIndex(recname)
        self.setSelectedRow(row)
        self.drawSelectedRow()
        x,y = self.getCanvasPos(row, 0)
        self.set_yviews('moveto', y-0.01)
        
        return

    def copyTable(self, event=None):
        """Copy from the clipboard"""

        df = self.model.df.copy()
        #flatten multi-index
        df.columns = df.columns.get_level_values(0)
        df.to_clipboard(sep=',')
        return

    def pasteTable(self, event=None):
        """Paste a new table from the clipboard"""

        self.storeCurrent()
        try:
            df = pd.read_clipboard(sep=',',error_bad_lines=False)
        except Exception as e:
            messagebox.showwarning("Could not read data", e,
                                    parent=self.parentframe)
            return
        if len(df) == 0:
            return
        df = pd.read_clipboard(sep=',', index_col=0, error_bad_lines=False)
        model = TableModel(df)
        self.updateModel(model)
        return

    def paste(self, row=None, column=None):
        """Paste contents from clipboard"""

        self.storeCurrent()
        df = pd.read_clipboard()
        dfList = df.astype(list)
        copiedValue = ''
        for elem in dfList:
            copiedValue = copiedValue + str(elem) + ' '
        if isinstance(row, list):
            self.model.setValueAt(copiedValue,row[0],column[0])
        else:
            row = self.getSelectedRow()
            column = self.getSelectedColumn()
            self.model.setValueAt(copiedValue,row,column)
        self.redraw()
        return

    def copy(self, rows, cols=None):
        """Copy cell contents to clipboard"""

        data = self.getSelectedDataFrame()
        try:
            if len(data) == 1 and len(data.columns) == 1:
                data.to_clipboard(index=False,header=False)
            else:
                data.to_clipboard()
        except:
            messagebox.showwarning("Warning",
                                   "No clipboard software.\nInstall xclip",
                                   parent=self.parentframe)
        return

    # don't need this
    # def transpose(self):
    #     """Transpose table"""

    #     self.model.transpose()
    #     self.updateModel(self.model)
    #     self.setSelectedRow(0)
    #     self.redraw()
    #     return

    
    # def transform(self):
    #     """Apply element-wise transform"""

    #     df = self.model.df
    #     cols = list(df.columns[self.multiplecollist])
    #     rows = self.multiplerowlist
    #     funcs = ['log','exp','log10','log2',
    #              'round','floor','ceil','trunc',
    #              'subtract','divide','mod',
    #              'negative','power',
    #              'sin','cos','tan','degrees','radians']

    #     d = MultipleValDialog(title='Apply Function',
    #                             initialvalues=(funcs,1,False),
    #                             labels=('Function:','Constant:','Use Selected'),
    #                             types=('combobox','string','checkbutton'),
    #                             tooltips=(None,'value to apply with arithmetic operations',
    #                                       'apply to selected data only'),
    #                             parent = self.parentframe)
    #     if d.result == None:
    #         return
    #     self.storeCurrent()
    #     funcname = d.results[0]
    #     func = getattr(np, funcname)
    #     const = float(d.results[1])
    #     use_sel = float(d.results[2])

    #     if funcname in ['round']:
    #         const = int(const)

    #     if funcname in ['subtract','divide','mod','power','round']:
    #         if use_sel == True:
    #             df.ix[rows, cols] = df.ix[rows, cols].applymap(lambda x: func(x, const))
    #         else:
    #             df = df.applymap( lambda x: func(x, const))
    #     else:
    #         if use_sel == True:
    #             df.ix[rows, cols] = df.ix[rows, cols].applymap(func)
    #         else:
    #             df = df.applymap(func)

    #     self.model.df = df
    #     self.redraw()
    #     return

    # may not need this
    def aggregate(self):
        """Show aggregate dialog"""

        df = self.model.df
        from .dialogs import AggregateDialog
        dlg = AggregateDialog(self, df=self.model.df)
        g = dlg.result
        if g is None:
            return
        replace = False
        #replace or make new table
        if replace == True:
            self.model.df = g
            self.showIndex()
            self.redraw()
        else:
            self.createChildTable(g, 'aggregated', index=True)
        return


    def doCombine(self):
        """Do combine/merge operation"""

        if self.child == None:
            return
        self.storeCurrent()
        from .dialogs import CombineDialog
        cdlg = CombineDialog(self, df1=self.model.df, df2=self.child.model.df)
        #df = cdlg.merged
        #if df is None:
        #    return
        #model = TableModel(dataframe=df)
        #self.updateModel(model)
        #self.redraw()
        return

    # probably don't need this
    def merge(self, table):
        """Merge with another table."""

        df1 = self.model.df
        df2 = table.model.df
        new = pd.merge(df1,df2,left_on=c1,right_on=c2,how=how)
        model = TableModel(new)
        self.updateModel(model)
        self.redraw()
        return

    def describe(self):
        """Create table summary"""

        g = self.model.df.describe()
        self.createChildTable(g)
        return

    def convertColumnNames(self, s='_'):
        """Convert col names so we can use numexpr"""

        d = MultipleValDialog(title='Convert col names',
                                initialvalues=['','','',0,0],
                                labels=['replace','with:',
                                        'add symbol to start:',
                                        'make lowercase','make uppercase'],
                                types=('string','string','string','checkbutton','checkbutton'),
                                parent = self.parentframe)
        if d.result == None:
            return
        pattern = d.results[0]
        repl = d.results[1]
        start = d.results[2]
        lower = d.results[3]
        upper = d.results[4]
        df = self.model.df
        if start != '':
            df.columns = start + df.columns
        if pattern != '':
            df.columns = [i.replace(pattern,repl) for i in df.columns]
        if lower == 1:
            df.columns = df.columns.str.lower()
        elif upper == 1:
            df.columns = df.columns.str.upper()
        self.redraw()
        return

    def convertNumeric(self):
        """Convert cols to numeric if possible"""

        df = self.model.df
        self.model.df = df.convert_objects(convert_numeric='force')
        self.redraw()
        return

    # def corrMatrix(self):
    #     """Correlation matrix"""

    #     df = self.model.df
    #     corr = df.corr()
    #     self.createChildTable(corr)
    #     return

    def createChildTable(self, df, title=None, index=False, out=False):
        """Add the child table"""

        self.closeChildTable()
        if out == True:
            win = Toplevel()
            x,y,w,h = self.getGeometry(self.master)
            win.geometry('+%s+%s' %(int(x+w/2),int(y+h/2)))
            if title != None:
                win.title(title)
        else:
            win = Frame(self.parentframe)
            win.grid(row=self.childrow,column=0,columnspan=2,sticky='news')
        self.childframe = win
        newtable = self.__class__(win, dataframe=df, showtoolbar=0, showstatusbar=1)
        newtable.parenttable = self
        newtable.adjustColumnWidths()
        newtable.show()
        toolbar = ChildToolBar(win, newtable)
        toolbar.grid(row=0,column=3,rowspan=2,sticky='news')
        self.child = newtable
        if hasattr(self, 'pf'):
            newtable.pf = self.pf
        if index==True:
            newtable.showIndex()
        return

    def closeChildTable(self):
        """Close the child table"""

        if self.child != None:
            self.child.destroy()
        if hasattr(self, 'childframe'):
            self.childframe.destroy()
        return

    def tableFromSelection(self):
        """Create a new table from the selected cells"""

        df = self.getSelectedDataFrame()
        if len(df) <=1:
            df = pd.DataFrame()
        self.createChildTable(df, 'selection')
        return

    # def pasteChildTable(self):
    #     """Paste child table back into main one"""

    #     answer =  messagebox.askyesno("Confirm",
    #                             "This will overwrite the main table.\n"+\
    #                             "Are you sure?",
    #                             parent=self.parentframe)
    #     if not answer:
    #         return
    #     table = self.parenttable
    #     model = TableModel(self.model.df)
    #     table.updateModel(model)
    #     return

    def showInfo(self):
        """Show dataframe info"""

        df = self.model.df
        import io
        buf = io.StringIO()
        df.info(verbose=True,buf=buf,memory_usage=True)
        from .dialogs import SimpleEditor
        w = Toplevel(self.parentframe)
        w.grab_set()
        w.transient(self)
        ed = SimpleEditor(w, height=25)
        ed.pack(in_=w, fill=BOTH, expand=Y)
        ed.text.insert(END, buf.getvalue())
        return

    def get_memory(self, ):
        """memory usage of current table"""

        df = self.model.df
        return df.memory_usage()

    def showasText(self):
        """Get table as formatted text - for printing"""

        d = MultipleValDialog(title='Table to Text',
                                initialvalues=(['left','right'],1,1,0,'',0,0),
                                labels=['justify:','header ','include index:',
                                        'sparsify:','na_rep:','max_cols','use selected'],
                                types=('combobox','checkbutton','checkbutton',
                                       'checkbutton','string','int','checkbutton'),
                                parent = self.parentframe)
        if d.result == None:
            return
        justify = d.results[0]
        header = d.results[1]
        index = d.results[2]
        sparsify = d.results[3]
        na_rep = d.results[4]
        max_cols = d.results[5]
        selected = d.results[6]

        if max_cols == 0:
            max_cols=None
        if selected == True:
            df = self.getSelectedDataFrame()
        else:
            df = self.model.df
        s = df.to_string(justify=justify,header=header,index=index,
                         sparsify=sparsify,na_rep=na_rep,max_cols=max_cols)
        #from tkinter.scrolledtext import ScrolledText
        from .dialogs import SimpleEditor
        w = Toplevel(self.parentframe)
        w.grab_set()
        w.transient(self)
        ed = SimpleEditor(w)
        ed.pack(in_=w, fill=BOTH, expand=Y)
        ed.text.insert(END, s)
        return

    # --- Some cell specific actions here ---

    def popupMenu(self, event, rows=None, cols=None, outside=None):
        """Add left and right click behaviour for canvas, should not have to override
            this function, it will take its values from defined dicts in constructor"""

        defaultactions = {
                        "Copy" : lambda: self.copy(rows, cols),
                        "Undo" : lambda: self.undo(event),
                        "Paste" : lambda: self.paste(rows, cols),
                        "Fill Down" : lambda: self.fillDown(rows, cols), # could potentially be removed
                        "Fill Right" : lambda: self.fillAcross(cols, rows), # could potentially be removed
                        "Add Row(s)" : lambda: self.addRows(),
                        "Add Site" : lambda: self.addSite(),                        
                        "Delete Row(s)" : lambda: self.deleteRow(),
                        "Add Column(s)" : lambda: self.addColumn(),
                        "Delete Column(s)" : lambda: self.deleteColumn(),
                        "Clear Data" : lambda: self.deleteCells(rows, cols),
                        "Select All" : self.selectAll,
                        "Auto Fit Columns" : self.autoResizeColumns,
                        "Table Info" : self.showInfo, # could potentially be removed
                        "Set Color" : self.setRowColors,
                        "Show as Text" : self.showasText,
                        "Filter Rows" : self.queryBar, # could potentially be removed
                        "New": self.new,
                        "Load": self.load,
                        "Save": self.save,
                        "Save as": self.saveAs,
                        "Import csv": lambda: self.importCSV(),
                        "Export": self.doExport,
                        "Preferences" : self.showPrefs,
                        "Table to Text" : self.showasText, # could potentially be removed
                        "Clean Data" : self.cleanData, # could potentially be removed
                        "Clear Formatting" : self.clearFormatting} # could potentially be removed

        main = ["Copy", "Paste", "Undo", "Clear Data"]
        general = ["Select All", "Preferences"]

        filecommands = ['New','Import csv','Save','Save as']
        # tablecommands = ['Table to Text','Clean Data','Clear Formatting']

        def createSubMenu(parent, label, commands):
            menu = Menu(parent, tearoff = 0)
            popupmenu.add_cascade(label=label,menu=menu)
            for action in commands:
                menu.add_command(label=action, command=defaultactions[action])
            applyStyle(menu)
            return menu

        def add_commands(fieldtype):
            """Add commands to popup menu for column type and specific cell"""
            functions = self.columnactions[fieldtype]
            for f in list(functions.keys()):
                func = getattr(self, functions[f])
                popupmenu.add_command(label=f, command= lambda : func(row,col))
            return

        popupmenu = Menu(self, tearoff = 0)
        def popupFocusOut(event):
            popupmenu.unpost()

        if outside == None:
            #if outside table, just show general items
            row = self.get_row_clicked(event)
            col = self.get_col_clicked(event)
            coltype = self.model.getColumnType(col)
            def add_defaultcommands():
                """now add general actions for all cells"""
                for action in main:
                    if action == 'Fill Down' and (rows == None or len(rows) <= 1):
                        continue
                    if action == 'Fill Right' and (cols == None or len(cols) <= 1):
                        continue
                    if action == 'Undo' and self.prevdf is None:
                        continue
                    else:
                        popupmenu.add_command(label=action, command=defaultactions[action])
                return

            if coltype in self.columnactions:
                add_commands(coltype)
            add_defaultcommands()

        for action in general:
            popupmenu.add_command(label=action, command=defaultactions[action])

        popupmenu.add_separator()
        createSubMenu(popupmenu, 'File', filecommands)
        # createSubMenu(popupmenu, 'Table', tablecommands)
        popupmenu.bind("<FocusOut>", popupFocusOut)
        popupmenu.focus_set()
        popupmenu.post(event.x_root, event.y_root)
        applyStyle(popupmenu)
        return popupmenu

    # --- spreadsheet type functions ---

    def fillDown(self, rowlist, collist):
        """Fill down a column, or multiple columns"""

        self.storeCurrent()
        df = self.model.df
        val = df.iloc[rowlist[0],collist[0]]
        #remove first element as we don't want to overwrite it
        rowlist.remove(rowlist[0])
        df.iloc[rowlist,collist] = val
        self.redraw()
        return

    def fillAcross(self, collist, rowlist):
        """Fill across a row, or multiple rows"""

        self.storeCurrent()
        model = self.model
        frstcol = collist[0]
        collist.remove(frstcol)
        self.redraw()
        return

    def getSelectionValues(self):
        """Get values for current multiple cell selection"""

        if len(self.multiplerowlist) == 0 or len(self.multiplecollist) == 0:
            return None
        rows = self.multiplerowlist
        cols = self.multiplecollist
        model = self.model
        if len(rows)<1 or len(cols)<1:
            return None
        #if only one row selected we plot whole col
        if len(rows) == 1:
            rows = self.rowrange
        lists = []

        for c in cols:
            x=[]
            for r in rows:
                #absr = self.get_AbsoluteRow(r)
                val = model.getValueAt(r,c)
                if val == None or val == '':
                    continue
                x.append(val)
            lists.append(x)
        return lists

    def getSelectedDataFrame(self):
        """Return a sub-dataframe of the selected cells"""
        df = self.model.df
        rows = self.multiplerowlist
        if not type(rows) is list:
            rows = list(rows)
        if len(rows)<1 or self.allrows == True:
            rows = list(range(self.rows))
        cols = self.multiplecollist
        try:
            data = df.iloc[list(rows),cols]
        except Exception as e:
            print ('error indexing data')
            return pd.DataFrame()
        return data
    
    def getSelectedLabelDict(self):
        """Returns a list of dictionaries from selected rows."""

        df = self.model.df
        rows = self.multiplerowlist
        if not type(rows) is list:
            rows = list(rows)
        if len(rows)<1 or self.allrows == True:
            rows = list(range(self.rows))
        cols = self.multiplecollist
        try:
            data = df.iloc[rows,:]
        except Exception as e:
            print ('error indexing data')
            return pd.DataFrame()
        data = data.fillna(' ')
        data = data.to_dict(orient = 'records')
        labelDicts = []
        for datum in data:
            datum = {key: value.strip() for key, value in datum.items() if isinstance(value,str)} #dict comprehension!
            if datum.get('specimen#') not in ['#','!AddSITE']:   #keep out the site level records!
                labelDicts.append(datum)
        return labelDicts
    
    #--- Drawing stuff ---

    def drawGrid(self, startrow, endrow):
        """Draw the table grid lines"""

        self.delete('gridline','text')
        rows=len(self.rowrange)
        cols=self.cols
        w = self.cellwidth
        h = self.rowheight
        x_start=self.x_start
        y_start=self.y_start
        x_pos=x_start

        if self.vertlines==1:
            for col in range(cols+1):
                x=self.col_positions[col]
                self.create_line(x,y_start,x,y_start+rows*h, tag='gridline',
                                     fill=self.grid_color, width=self.linewidth)
        if self.horizlines==1:
            for row in range(startrow, endrow+1):
                y_pos=y_start+row*h
                self.create_line(x_start,y_pos,self.tablewidth,y_pos, tag='gridline',
                                    fill=self.grid_color, width=self.linewidth)
        return

    def drawRowHeader(self):
        """User has clicked to select a cell"""

        self.delete('rowheader')
        x_start=self.x_start
        y_start=self.y_start
        h=self.rowheight
        rowpos=0
        for row in self.rowrange:
            x1,y1,x2,y2 = self.getCellCoords(rowpos,0)
            self.create_rectangle(0,y1,x_start-2,y2,
                                      fill='gray75',
                                      outline='white',
                                      width=1,
                                      tag='rowheader')
            self.create_text(x_start/2,y1+h/2,
                                      text=row+1,
                                      fill='black',
                                      font=self.thefont,
                                      tag='rowheader')
            rowpos+=1
        return

    def drawSelectedRect(self, row, col, color=None):
        """User has clicked to select a cell"""

        if col >= self.cols:
            return
        self.delete('currentrect')
        #bg = self.selectedcolor
        if color == None:
            color = 'gray25'
        w=2
        x1,y1,x2,y2 = self.getCellCoords(row,col)
        rect = self.create_rectangle(x1+w/2+1,y1+w/2+1,x2-w/2,y2-w/2,
                                  outline=color,
                                  width=w,
                                  tag='currentrect')
        #raise text above all
        self.lift('celltext'+str(col)+'_'+str(row))
        return

    def drawRect(self, row, col, color=None, tag=None, delete=1):
        """Cell is colored"""

        if delete==1:
            self.delete('cellbg'+str(row)+str(col))
        if color==None or color==self.cellbackgr:
            return
        else:
            bg=color
        if tag==None:
            recttag='fillrect'
        else:
            recttag=tag
        w=1
        x1,y1,x2,y2 = self.getCellCoords(row,col)
        rect = self.create_rectangle(x1+w/2,y1+w/2,x2-w/2,y2-w/2,
                                  fill=bg,
                                  outline=bg,
                                  width=w,
                                  tag=(recttag,'cellbg'+str(row)+str(col)))
        self.lower(recttag)
        return

    def handleCellEntry(self, row, col):
        """Callback for cell entry"""

        value = self.cellentryvar.get()
        self.model.setValueAt(value,row,col)
        self.drawText(row, col, value, align=self.align)
        self.delete('entry')
        self.gotonextCell()
        return

    def drawCellEntry(self, row, col, text=None):
        """
        When the user single/double clicks on a text/number cell,
        bring up entry window and allow edits. Also, call
        storeCurrent to store the dataframe state prior to a cell edit.
        """

        if self.editable == False:
            return
        # storeCurrent df before cell edit
        self.storeCurrent()
        h = self.rowheight
        model = self.model
        text = self.model.getValueAt(row, col)
        if pd.isnull(text):
            text = ''
        x1,y1,x2,y2 = self.getCellCoords(row,col)
        w=x2-x1
        self.cellentryvar = txtvar = StringVar()
        txtvar.set(text)

        self.cellentry = Entry(self.parentframe,width=20,
                        textvariable=txtvar,
                        takefocus=1,
                        font=self.thefont)
        self.cellentry.icursor(END)
        self.cellentry.bind('<Return>', lambda x: self.handleCellEntry(row,col))
        self.cellentry.focus_set()
        self.entrywin = self.create_window(x1,y1,
                                width=w,height=h,
                                window=self.cellentry,anchor='nw',
                                tag='entry')
        return

    def checkDataEntry(self,event=None):
        """do validation checks on data entry in a widget"""

        value=event.widget.get()
        if value!='':
            try:
                value=re.sub(',','.', value)
                value=float(value)
            except ValueError:
                event.widget.configure(bg='red')
                return 0
        elif value == '':
            return 1
        return 1

    def drawAddSpecimenWidget(self, row, col):
        """Draw the Addspecimen Widget in Cell """
        
        self.delete('addSpecimenWidget'+str(col)+'_'+str(row))
        h = self.rowheight
        x1,y1,x2,y2 = self.getCellCoords(row,col)
        w=x2-x1
        wrap = False
        pad=5
        y=y1+h/2
        def addRowFromSiteHelper(r):
            self.setSelectedRow(r)
            self.addRowFromSite()
        addSpecimenButton = Button(self,  text="Add Specimen", command=lambda r=row: addRowFromSiteHelper(r)) #Note have to assign r within lambda or else command is always final site#
        length = len("Add Specimen")
        addSpecimenWidget = self.create_window(x1+w/2,y,window=addSpecimenButton, tag=('addSpecimenWidget','addSpecimenWidget'+str(col)+'_'+str(row)))


    def drawText(self, row, col, celltxt, align=None):
        """Draw the text inside a cell area"""

        self.delete('addSpecimenWidget'+str(col)+'_'+str(row))
        self.delete('celltext'+str(col)+'_'+str(row))
        h = self.rowheight
        x1,y1,x2,y2 = self.getCellCoords(row,col)
        w=x2-x1
        wrap = False
        pad=5
        #if type(celltxt) is np.float64:
        #    celltxt = np.round(celltxt,3)
        celltxt = str(celltxt)
        length = len(celltxt)
        if length == 0:
            return

        if w<=10:
            return
        if w < 18:
            celltxt = '.'
            return

        fgcolor = 'black'
        if align == None:
            align = 'center'
        elif align == 'w':
            x1 = x1-w/2+pad
        elif align == 'e':
            x1 = x1+w/2-pad

        tw,newlength = util.getTextLength(celltxt, w-pad, font=self.thefont)
        width=0
        celltxt = celltxt[0:int(newlength)]
        y=y1+h/2
        rect = self.create_text(x1+w/2,y,
                                  text=celltxt,
                                  fill=fgcolor,
                                  font=self.thefont,
                                  anchor=align,
                                  tag=('text','celltext'+str(col)+'_'+str(row)),
                                  width=width)
        return

    def drawSelectedRow(self):
        """Draw a highlight rect for the currently selected rows"""

        self.delete('rowrect')
        row = self.currentrow
        x1,y1,x2,y2 = self.getCellCoords(row,0)
        x2 = self.tablewidth
        rect = self.create_rectangle(x1,y1,x2,y2,
                                  fill=self.rowselectedcolor,
                                  outline=self.rowselectedcolor,
                                  tag='rowrect')
        self.lower('rowrect')
        self.lower('fillrect')
        self.lower('colorrect')
        self.rowheader.drawSelectedRows(self.currentrow)
        return

    def drawSelectedCol(self, col=None, delete=1, color=None, tag='colrect'):
        """Draw a highlight rect for the current column selection"""

        if color == None:
            color = self.colselectedcolor
        if delete == 1:
            self.delete(tag)
        if len(self.model.df.columns) == 0:
            return
        if col == None:
            col = self.currentcol
        w=2
        x1,y1,x2,y2 = self.getCellCoords(0,col)
        y2 = self.rows * self.rowheight
        rect = self.create_rectangle(x1+w/2,y1+w/2,x2,y2+w/2,
                                     width=w,fill=color,outline='',
                                     tag=tag)
        self.lower('rowrect')
        self.lower('colrect')
        return

    def drawMultipleRows(self, rowlist):
        """Draw more than one row selection"""

        self.delete('multiplesel')
        self.delete('rowrect')
        cols = self.visiblecols
        for col in cols:
            colname = self.model.df.columns[col]
            #if col is colored we darken it
            if colname in self.columncolors:
                clr = self.columncolors[colname]
                clr = util.colorScale(clr, -30)
            else:
                clr = self.rowselectedcolor
            for r in rowlist:
                if r not in self.visiblerows or r > self.rows-1:
                    continue
                x1,y1,x2,y2 = self.getCellCoords(r,col)
                #x2 = self.tablewidth
                rect = self.create_rectangle(x1,y1,x2,y2,
                                          fill=clr,
                                          outline=self.rowselectedcolor,
                                          tag=('multiplesel','rowrect'))

        self.lower('multiplesel')
        self.lower('fillrect')
        self.lower('colorrect')
        return

    def drawMultipleCols(self):
        """Draw multiple column selections"""

        for c in self.multiplecollist:
            self.drawSelectedCol(c, delete=False)
        return

    def drawMultipleCells(self):
        """Draw an outline box for multiple cell selection"""

        self.delete('currentrect')
        self.delete('multicellrect')
        rows = self.multiplerowlist
        cols = self.multiplecollist
        if len(rows) == 0 or len(cols) == 0:
            return
        w=2
        x1,y1,a,b = self.getCellCoords(rows[0],cols[0])
        c,d,x2,y2 = self.getCellCoords(rows[len(rows)-1],cols[len(cols)-1])
        rect = self.create_rectangle(x1+w/2,y1+w/2,x2,y2,
                             outline=self.boxoutlinecolor, width=w,
                             tag='multicellrect')
        return

    def setcellbackgr(self):
        """set cell background color"""

        clr = self.getaColor(self.cellbackgr)
        if clr != None:
            self.cellbackgr = clr
        return

    def setgrid_color(self):
        """set grid color"""

        clr = self.getaColor(self.grid_color)
        if clr != None:
            self.grid_color = clr
        return

    def setrowselectedcolor(self):
        """Set selected row color"""

        clr = self.getaColor(self.rowselectedcolor)
        if clr != None:
            self.rowselectedcolor = clr
        return

    def getaColor(self, oldcolor):
        """get a color"""

        import tkinter.colorchooser
        ctuple, newcolor = tkinter.colorchooser.askcolor(title='pick a color',
                                                         initialcolor=oldcolor,
                                                         parent=self.parentframe)
        if ctuple == None:
            return None
        return str(newcolor)

    #--- Preferences stuff ---

    def showPrefs(self, prefs=None):
        """Show table options dialog using an instance of prefs"""

        if self.prefs == None:
            self.loadPrefs()
        self.prefswindow=Toplevel()
        x,y,w,h = self.getGeometry(self.master)
        #self.prefswindow.geometry('+%s+%s' %(x+w/2,y+h/2))
        self.prefswindow.title('Preferences')
        self.prefswindow.resizable(width=FALSE, height=FALSE)
        self.prefswindow.grab_set()
        self.prefswindow.transient(self)

        frame1=Frame(self.prefswindow)
        frame1.pack(side=LEFT)
        frame2=Frame(self.prefswindow)
        frame2.pack()
        
        def close_prefsdialog():
            self.prefswindow.destroy()
        row=0
        Checkbutton(frame1, text="Show horizontal lines", variable=self.horizlinesvar,
                    onvalue=1, offvalue=0).grid(row=row,column=0, columnspan=2, sticky='news')
        row=row+1
        Checkbutton(frame1, text="Show vertical lines", variable=self.vertlinesvar,
                    onvalue=1, offvalue=0).grid(row=row,column=0, columnspan=2, sticky='news')
        row=row+1
        Checkbutton(frame1, text="Auto resize columns", variable=self.autoresizecolsvar,
                    onvalue=1, offvalue=0).grid(row=row,column=0, columnspan=2, sticky='news')
        row=row+1
        lblrowheight = Label(frame1,text='Row Height:')
        lblrowheight.grid(row=row,column=0,padx=3,pady=2)
        rowheightentry = Scale(frame1,from_=12,to=50,resolution=1,orient='horizontal',
                            variable=self.rowheightvar)
        rowheightentry.configure(fg='black', bg=self.bg)
        rowheightentry.grid(row=row,column=1)
        row=row+1
        lblcellwidth = Label(frame1,text='Cell Width:')
        lblcellwidth.grid(row=row,column=0,padx=3,pady=2)
        cellwidthentry = Scale(frame1,from_=20,to=500,resolution=10,orient='horizontal',
                            variable=self.cellwidthvar)
        cellwidthentry.configure(fg='black', bg=self.bg)
        cellwidthentry.grid(row=row,column=1)
        row=row+1

        lbllinewidth = Label(frame1,text='Line Width:')
        lbllinewidth.grid(row=row,column=0,padx=3,pady=2)
        linewidthentry = Scale(frame1,from_=0,to=10,resolution=1,orient='horizontal',
                            variable=self.linewidthvar)
        linewidthentry.configure(fg='black', bg=self.bg)
        linewidthentry.grid(row=row,column=1)
        row=row+1

        rowhdrwidth=Label(frame1,text='Row Header Width:')
        rowhdrwidth.grid(row=row,column=0,padx=3,pady=2)
        rowhdrentry = Scale(frame1,from_=0,to=300,resolution=10,orient='horizontal',
                                    variable=self.rowheaderwidthvar)
        rowhdrentry.configure(fg='black', bg=self.bg)
        rowhdrentry.grid(row=row,column=1)
        row=row+1

        #fonts
        fts = self.getFonts()
        Label(frame2,text='font').grid(row=row,column=0)
        fb = Combobox(frame2, values=fts,
                       textvariable=self.fontvar)
        #currfont = self.prefs.get('celltextfont')
        fb.grid(row=row,column=1, columnspan=2, sticky='nes', padx=3,pady=2)
        row=row+1

        lblfontsize = Label(frame2,text='Text Size:')
        lblfontsize.grid(row=row,column=0,padx=3,pady=2)
        fontsizeentry = Scale(frame2,from_=6,to=50,resolution=1,orient='horizontal',
                                variable=self.celltextsizevar)
        fontsizeentry.configure(fg='black', bg=self.bg)
        fontsizeentry.grid(row=row,column=1, sticky='wens',padx=3,pady=2)
        row=row+1

        #cell alignment
        lbl=Label(frame2,text='Alignment:')
        lbl.grid(row=row,column=0,padx=3,pady=2)

        alignments=['center','w','e']
        alignentry_button = Combobox(frame2, values=alignments,
                              textvariable=self.cellalignvar)
        alignentry_button.grid(row=row,column=1, sticky='nes', padx=3,pady=2)
        row=row+1

        #float precision
        lbl=Label(frame2,text='Float precision:')
        lbl.grid(row=row,column=0,padx=3,pady=2)
        fpentry = Entry(frame2, textvariable=self.floatprecvar, width=10)
        fpentry.grid(row=row,column=1, sticky='nes', padx=3,pady=2)
        row=row+1

        #colors
        style = Style()
        style.configure("cb.TButton", background=self.cellbackgr)
        cellbackgrbutton = Button(frame2, text='table background',style="cb.TButton",
                                  command=self.setcellbackgr)

        cellbackgrbutton.grid(row=row,column=0,columnspan=2, sticky='news')
        row=row+1
        style = Style()
        style.configure("gc.TButton", background=self.grid_color)
        grid_colorbutton = Button(frame2, text='grid color', style="gc.TButton",
                                command=self.setgrid_color)
        grid_colorbutton.grid(row=row,column=0,columnspan=2, sticky='news')
        row=row+1
        style = Style()
        style.configure("rhc.TButton", background=self.rowselectedcolor)
        rowselectedcolorbutton = Button(frame2, text='row highlight color', style="rhc.TButton",
                                command=self.setrowselectedcolor)
        rowselectedcolorbutton.grid(row=row,column=0,columnspan=2, sticky='news')
        row=row+1

        frame=Frame(self.prefswindow)
        frame.pack(fill=BOTH,expand=1)
        # Apply Button
        b = Button(frame, text="Apply Settings", command=self.applyPrefs)
        b.pack(side=LEFT,expand=1)

        # Close button
        c=Button(frame,text='Close', command=close_prefsdialog)
        c.pack(side=LEFT,expand=1)
        self.prefswindow.focus_set()
        self.prefswindow.grab_set()
        self.prefswindow.wait_window()
        return self.prefswindow

    def getFonts(self):
        """get fonts available"""

        fonts = set(list(font.families()))
        fonts = sorted(list(fonts))
        return fonts

    def loadPrefs(self, prefs=None):
        """Load table specific prefs from the prefs instance used
           if they are not present, create them."""

        if prefs==None:
            prefs=Preferences('Table',{'check_for_update':1})
        self.prefs = prefs
        defaultprefs = {'horizlines':self.horizlines, 'vertlines':self.vertlines,
                        'rowheight':self.rowheight,
                        'cellwidth':120,
                        'autoresizecols': self.autoresizecols,
                        'align': 'w',
                        'floatprecision': self.floatprecision,
                        'celltextsize':14, 'celltextfont':'Arial',
                        'cellbackgr': self.cellbackgr, 'grid_color': self.grid_color,
                        'linewidth' : self.linewidth,
                        'rowselectedcolor': self.rowselectedcolor,
                        'rowheaderwidth': self.rowheaderwidth,
                        #CollectionDataEntryBar stuff
                        'collName': self.collName,
                        'detName':self.detName,
                        'useDetDate':self.useDetDate,
                        #CatNumberBar stuff
                        'catPrefix':self.catPrefix,
                        'catDigits':self.catDigits,
                        'catStart':self.catStart,
                        #student collection status stuff
                        'stuCollVerifyBy': self.stuCollVerifyBy,
                        'stuCollCheckBox': self.stuCollCheckBox
                        }
     

        for prop in list(defaultprefs.keys()):
            try:
                self.prefs.get(prop);
            except:
                self.prefs.set(prop, defaultprefs[prop])
        self.defaultprefs = defaultprefs

        #Create tkvars for dialog
        self.fontvar = StringVar()
        self.fontvar.set(self.prefs.get('celltextfont'))
        self.rowheightvar = IntVar()
        self.rowheightvar.set(self.prefs.get('rowheight'))
        self.rowheight = self.rowheightvar.get()
        self.cellwidthvar = IntVar()
        self.cellwidthvar.set(self.prefs.get('cellwidth'))
        self.cellwidth = self.cellwidthvar.get()
        self.cellalignvar = StringVar()
        self.cellalignvar.set(self.prefs.get('align'))
        self.align = self.cellalignvar.get()
        self.floatprecvar = IntVar()
        self.floatprecvar.set(self.prefs.get('floatprecision'))
        self.linewidthvar = StringVar()
        self.linewidthvar.set(self.prefs.get('linewidth'))
        self.horizlinesvar = IntVar()
        self.horizlinesvar.set(self.prefs.get('horizlines'))
        self.vertlinesvar = IntVar()
        self.vertlinesvar.set(self.prefs.get('vertlines'))
        self.autoresizecolsvar = IntVar()
        self.autoresizecolsvar.set(self.prefs.get('autoresizecols'))
        self.celltextsizevar = IntVar()
        self.celltextsizevar.set(self.prefs.get('celltextsize'))
        self.cellbackgr = self.prefs.get('cellbackgr')
        self.grid_color = self.prefs.get('grid_color')
        self.rowselectedcolor = self.prefs.get('rowselectedcolor')
        self.fontsize = self.celltextsizevar.get()
        # self.thefont = (self.prefs.get('celltextfont'), self.prefs.get('celltextsize'))
        self.rowheaderwidthvar = IntVar()
        self.rowheaderwidthvar.set(self.prefs.get('rowheaderwidth'))
        self.rowheaderwidth = self.rowheaderwidthvar.get()
        
        #Collection data entry bar defaults
        CollectionDataEntryBar.collNameVar = StringVar()
        CollectionDataEntryBar.collNameVar.set(self.prefs.get('collName'))
        CollectionDataEntryBar.detNameVar = StringVar()
        CollectionDataEntryBar.detNameVar.set(self.prefs.get('detName'))
        CollectionDataEntryBar.useDetDateVar = IntVar()
        CollectionDataEntryBar.useDetDateVar.set(self.prefs.get('useDetDate'))

        #Catalog number data entry bar defaults
        CatNumberBar.catPrefixVar = StringVar()
        CatNumberBar.catPrefixVar.set(self.prefs.get('catPrefix'))
        CatNumberBar.catDigitsVar = IntVar()
        CatNumberBar.catDigitsVar.set(self.prefs.get('catDigits'))
        CatNumberBar.catStartVar = IntVar()
        CatNumberBar.catStartVar.set(self.prefs.get('catStart'))

        #Student collection
        # box for the "verified by" name
        CatNumberBar.stuCollVerifyByVar = StringVar()
        CatNumberBar.stuCollVerifyByVar.set(self.prefs.get('stuCollVerifyBy'))
        # checkbox for the "Student collection" status.
        CatNumberBar.stuCollCheckBoxVar = IntVar()
        CatNumberBar.stuCollCheckBoxVar.set(self.prefs.get('stuCollCheckBox'))
        return

    def savePrefs(self):
        """Save and set the prefs"""

        try:
            self.prefs.set('horizlines', self.horizlinesvar.get())
            self.horizlines = self.horizlinesvar.get()
            self.prefs.set('vertlines', self.vertlinesvar.get())
            self.vertlines = self.vertlinesvar.get()
            self.prefs.set('autoresizecols', self.autoresizecolsvar.get())
            self.autoresizecols = self.autoresizecolsvar.get()
            self.prefs.set('rowheight', self.rowheightvar.get())
            self.rowheight = self.rowheightvar.get()
            self.prefs.set('cellwidth', self.cellwidthvar.get())
            self.cellwidth = self.cellwidthvar.get()
            self.prefs.set('align', self.cellalignvar.get())
            self.align = self.cellalignvar.get()
            self.floatprecision = self.floatprecvar.get()
            self.prefs.set('floatprecision', self.floatprecvar.get())
            self.prefs.set('linewidth', self.linewidthvar.get())
            self.linewidth = self.linewidthvar.get()
            self.prefs.set('celltextsize', self.celltextsizevar.get())
            self.prefs.set('celltextfont', self.fontvar.get())
            self.prefs.set('cellbackgr', self.cellbackgr)
            self.prefs.set('grid_color', self.grid_color)
            self.prefs.set('rowselectedcolor', self.rowselectedcolor)
            self.prefs.set('rowheaderwidth', self.rowheaderwidth)
            self.rowheaderwidth = self.rowheaderwidthvar.get()
            # self.thefont = (self.prefs.get('celltextfont'), self.prefs.get('celltextsize'))
            self.fontsize = self.prefs.get('celltextsize')
        except ValueError as e:
            print('prefs error: ', e)
            pass
        self.prefs.save_prefs()
        return

    def applyPrefs(self):
        """Apply prefs to the table by redrawing"""

        self.savePrefs()
        self.autoResizeColumns()
        self.show()
        self.redraw()
        return

    def show_progressbar(self,message=None):
        """Show progress bar window for loading of data"""

        progress_win=Toplevel() # Open a new window
        progress_win.title("Please Wait")
        #progress_win.geometry('+%d+%d' %(self.parentframe.rootx+200,self.parentframe.rooty+200))
        #force on top
        progress_win.grab_set()
        progress_win.transient(self.parentframe)
        if message==None:
            message='Working'
        lbl = Label(progress_win,text=message,font='Arial 16')

        lbl.grid(row=0,column=0,columnspan=2,sticky='news',padx=6,pady=4)
        progrlbl = Label(progress_win,text='Progress:')
        progrlbl.grid(row=1,column=0,sticky='news',padx=2,pady=4)
        import ProgressBar
        self.bar = ProgressBar.ProgressBar(progress_win)
        self.bar.frame.grid(row=1,column=1,columnspan=2,padx=2,pady=4)

        return progress_win

    def updateModel(self, model):
        """Should call this method when a new table model is loaded.
           Recreates widgets and redraws the table."""

        self.model = model
        self.rows = self.model.getRowCount()
        self.cols = self.model.getColumnCount()
        self.tablewidth = (self.cellwidth)*self.cols
        if hasattr(self, 'tablecolheader'):
            self.tablecolheader.destroy()
            self.rowheader.destroy()
            #self.rowwidgetcolumn.destroy()
            self.selectNone()
        self.show()
        return

    def new(self):
        """Clears all the data and makes a new table"""

        if messagebox.askyesno('New Data', 'Load a blank data set? (any unsaved progress will be lost)'):
            newDFDict = {
            'otherCatalogNumbers':['1-#','1-1'],
            'family':['',''],
            'scientificName':['',''],
            'genus':['',''],
            'scientificNameAuthorship':['',''],
            'taxonRemarks':['',''],
            'identifiedBy':['',''],
            'dateIdentified':['',''],
            'identificationReferences':['',''],
            'identificationRemarks':['',''],
            'collector':['',''],
            'collectorNumber':['',''],
            'associatedCollectors':['',''],
            'eventDate':['',''],
            'verbatimEventDate':['',''],
            'habitat':['',''],
            'substrate':['',''],
            'occurrenceRemarks':['',''],
            'informationWithheld':['',''],
            'associatedOccurrences':['',''],
            'dataGeneralizations':['',''],
            'associatedTaxa':['',''],
            'dynamicProperties':['',''],
            'description':['',''],
            'reproductiveCondition':['',''],
            'cultivationStatus':['',''],
            'establishmentMeans':['',''],
            'lifeStage':['',''],
            'sex':['',''],
            'individualCount':['',''],
            'country':['',''],
            'stateProvince':['',''],
            'county':['',''],
            'municipality':['',''],
            'locality':['',''],
            'localitySecurity':['',''],
            'decimalLatitude':['',''],
            'decimalLongitude':['',''],
            'geodeticDatum':['',''],
            'coordinateUncertaintyInMeters':['',''],
            'verbatimCoordinates':['',''],
            'minimumElevationInMeters':['',''],
            'maximumElevationInMeters':['',''],
            'verbatimElevation':['',''],
            'duplicateQuantity':['',''],
            'labelProject':['','']}

        newDF = pd.DataFrame.from_dict(newDFDict)
        newDF['-'] = '-' # add in the little "-" seperator.
        newDF.fillna('') # make any nans into empty strings.
        self.refreshSpecimenSiteNums(newDF)
        model = TableModel(dataframe=newDF)
        self.updateModel(model)
        self.sortTable([self.model.df.columns.get_loc('site#'),self.model.df.columns.get_loc('specimen#')])
        self.adjustColumnWidths()
        #this solves addressing errors related to index at row 1 = 1 on import, and various functions later properly reset the index to 0
        self.model.resetIndex()
        self.redraw()
        self.setSelectedRow(0)
        self.drawSelectedRow()
        self.drawSelectedRect(0,0)

        return

    # runs through table automatically
    # calls genLocality and genScientificName
    def processRecords(self):
        """Process records in table. Deals specifically with
        scientific name and locality strings. This function calls
        genLocality and genScientificName which use web API calls
        to update the given scientific name as well as fill locality
        fields from GPS coordinates."""

        currentRow = self.currentrow
        localityColumn = self.findColumnIndex('locality')
        catalogNumColumn = self.findColumnIndex('otherCatalogNumbers')
        recordedByColumn = self.findColumnIndex('recordedBy')
        assCollectorColumn = self.findColumnIndex('associatedCollectors')
        scientNameColumn = self.findColumnIndex('scientificName')
        authorshipColumn = self.findColumnIndex('scientificNameAuthorship')
        assocTaxaColumn = self.findColumnIndex('associatedTaxa')
        associatedTaxa = []
        # an indication of record processing
        self.parentframe.master.title("PD-Desktop (Processing Records...)")
        
        while currentRow < int(self.model.getRowCount()):
            try:
                currentRow = self.currentrow
                if self.model.getValueAt(currentRow, self.findColumnIndex('specimen#')) in ['#','!AddSITE']:
                    self.gotonextRow()
                    currentRow = self.currentrow
                    self.redraw()
                    continue
                #Clean duplicate primary collector names out of associated collectors. Presuming they're split with a " , ".
                associatedCollectors = self.model.getValueAt(currentRow, assCollectorColumn).split(',')
                recordedBy = self.model.getValueAt(currentRow, recordedByColumn)
                #use all uppercase names to check for duplicates.
                associatedCollectors = ', '.join([x.strip() for x in associatedCollectors if x.strip().upper() != recordedBy.strip().upper()])
                self.model.setValueAt(associatedCollectors, currentRow, assCollectorColumn)
                resultLocality = self.genLocality(currentRow)
                # missing gps coordinates
                if resultLocality in ["loc_error_no_gps","loc_apierr_no_retry"]:
                    #if fails to generate locality from GPS coords, try with local fields
                    # TODO This could probably use a try except block for whatever imaginable errors?
                    resultLocality = self.genLocalityNoAPI(currentRow)
                    self.model.setValueAt(resultLocality, currentRow, localityColumn)
                    self.redraw()
                elif resultLocality == "user_set_gps":
                    self.parentframe.master.title("PD-Desktop")
                    self.redraw()
                    return
                # modify to set value here
                else:
                    self.model.setValueAt(resultLocality, currentRow, localityColumn)
                    self.redraw()
                catNum = self.model.getValueAt(currentRow, catalogNumColumn)
                resSci = self.genScientificName(currentRow)
                # missing scientific name
                if resSci == "user_set_sciname":
                    self.parentframe.master.title("PD-Desktop")
                    self.redraw()
                    return
                else:
                    if isinstance(resSci, tuple):
                        self.model.setValueAt(resSci[0], currentRow, scientNameColumn)
                        # getting more weird authorship return values? add them here!
                        if resSci[1] != 'None':
                            self.model.setValueAt(resSci[1], currentRow, authorshipColumn)
                        associatedTaxa.append([currentRow, catNum, resSci[0]])
                        self.redraw()
                    else:
                        self.model.setValueAt(resSci, currentRow, scientNameColumn)
                        associatedTaxa.append([currentRow, catNum, resSci])
                        self.redraw()
                        
                self.gotonextRow()
                self.redraw()
            except IndexError:
                self.parentframe.master.title("PD-Desktop")
                self.redraw()

        self.model.df = self.model.df.groupby('site#').apply(self.genAssociatedTaxa).reset_index(drop=True)#group by 'site#', apply genAssociatedTaxa groupwise
        #this loop fixes the scientific name's presence also being in associated Taxa. It would be ideal to do this in associatedTaxa
        for recordRow in range(self.model.getRowCount()):
            recordAssociatedTaxa = self.model.getValueAt(recordRow, assocTaxaColumn) # identify associated taxa cell
            recordAssociatedTaxa = recordAssociatedTaxa.split(',') # split it into a list of strings on ','
            recordAssociatedTaxa = [x.strip() for x in recordAssociatedTaxa]
            if self.model.getValueAt(recordRow,scientNameColumn) in recordAssociatedTaxa:
                recordAssociatedTaxa.remove(self.model.getValueAt(recordRow,scientNameColumn))
              
            recordAssociatedTaxa = ', '.join(recordAssociatedTaxa).strip().strip(', ')
            self.model.setValueAt(recordAssociatedTaxa, recordRow, assocTaxaColumn)

        self.parentframe.master.title("PD-Desktop")
        self.setSelectedRow(0)
        self.redraw()

    def genAssociatedTaxa(self, siteGroup):
        """Generate Associated Taxa gets all associated taxa
        for a given record (specimen)."""
        
        associatedTaxaList = [] #start with empty list
#first generate a list of every item already in associatedTaxa (user entered)
        for recordAssociatedTaxa in siteGroup['associatedTaxa'].tolist():  #get the exising associated taxa from each row in the group
            if isinstance(recordAssociatedTaxa, str):                       #check that it exists
                recordAssociatedTaxa = recordAssociatedTaxa.split(',')      #if exists, try to split by commas
                recordAssociatedTaxa = [x.strip(' ') for x in recordAssociatedTaxa] #strip extra space from each item.
                associatedTaxaList = associatedTaxaList + recordAssociatedTaxa #Add each item individually to a list
        
        associatedTaxaList = list(dict.fromkeys(associatedTaxaList)) # remove duplicate entries, while preserving the order.
                
#then generate a list of all scientificNames in the group which are not already present in the associatedTaxaList.
        cleanGroupSciNameList = [str(x) for x in siteGroup['scientificName'].tolist() if str(x) not in ['', 'nan']]

        groupScientificNameList = [y.strip(' ') for y in cleanGroupSciNameList if y not in associatedTaxaList]
        #groupScientificNameList = [y.strip(' ') for y in siteGroup['scientificName'].tolist() if y not in associatedTaxaList]
        groupScientificNameList = sorted(list(set(groupScientificNameList)),key=str.lower) #clean and sort the list
#join the lists keeping user entered fields at the start of the list.
        groupAssociatedTaxa = associatedTaxaList + groupScientificNameList
        groupAssociatedTaxa = ', '.join(groupAssociatedTaxa).strip().replace(', , ', ', ')
        siteGroup['associatedTaxa'] = groupAssociatedTaxa #Update associated taxa according to the group with the final list.
        return siteGroup    #Return the groups with modified associatedTaxa Fields.
        
    def genLocalityNoAPI(self, currentRowArg):
        """ Attempts to improve the locality string using existing geography data.
        This function complains more than the inlaws."""
# both locality functions would benefit from some systemic method of determining when to add italics to binomial (scientific) names.
# such the italic tags "<i> and </i>" would need to be stripped before exporting for database submission.
        currentRow = currentRowArg
        pathColumn = self.findColumnIndex('path')
        localityColumn = self.findColumnIndex('locality')
        municipalityColumn = self.findColumnIndex('municipality')
        countyColumn = self.findColumnIndex('county')
        stateColumn = self.findColumnIndex('stateProvince')
        countryColumn = self.findColumnIndex('country')
        try:
            currentLocality = self.model.getValueAt(currentRow, localityColumn)
            #Gen list of locality value locations
            localityFields = [self.model.getValueAt(currentRow,x) for x in [countryColumn, stateColumn, countyColumn, municipalityColumn, pathColumn, localityColumn]]
            #Clean nans and empty fields out of the list
            localityFields = [x for x in localityFields if str(x) not in['','nan']]
            #combine values from each item remaining in localityFields
            newLocality = [x for x in localityFields if x.lower() not in currentLocality.lower()]
            #join the list into a single string
            newLocality = ', '.join(newLocality)
            userWarnedAboutGeo = False # set a trigger to restrict the amount of times we complain about their slack gps data.
            for geoGeographyField in [stateColumn, countyColumn]:
                if self.model.getValueAt(currentRow, geoGeographyField) in['','nan']:
                    messagebox.showinfo('LIMITED Location data at row {}'.format(currentRow+1), 'Row {} is missing important geographic data!\nYou may need to manually enter data into location fields (such as State, and County).'.format(currentRow+1))
                    userWarnedAboutGeo = True
                    break
            if not userWarnedAboutGeo:
                if newLocality != currentLocality: # if we actually changed something give the user a heads up the methods were sub-par.
                    newLocality = '{}, {}'.format(newLocality,currentLocality).rstrip(', ').lstrip(', ')
                    messagebox.showinfo('LIMITED Location data at row {}'.format(currentRow+1), 'Locality at row {} was generated using limited methods'.format(currentRow+1))
                else:# if we could infer nothing from existing geographic fields, AND we have no GPS values then they have work to do!
                    messagebox.showinfo('LIMITED Location data at row {}'.format(currentRow+1), 'Row {} is missing important geographic data!\nYou may need to manually enter data into location fields (such as State, and County).'.format(currentRow+1))
                    return newLocality
            return newLocality

        except ValueError:
            #if some lookup fails, toss value error and return empty
            messagebox.showinfo('Location ERROR at row {}'.format(currentRow+1), "Offline Locality generation requires atleast a column named locality.")
            return

    def genLocality(self, currentRowArg):
        """ Generate locality fields, uses API call to get
        country, state, city, etc. from GPS coordinates."""
# both locality functions would benefit from some systemic methid of determining when to add italics to binomial (scientific) names.
# such the italic tags "<i> and </i>" would need to be stripped before exporting for database submission.

        currentRow = currentRowArg
        pathColumn = self.findColumnIndex('path')
        localityColumn = self.findColumnIndex('locality')
        municipalityColumn = self.findColumnIndex('municipality')
        countyColumn = self.findColumnIndex('county')
        stateColumn = self.findColumnIndex('stateProvince')
        countryColumn = self.findColumnIndex('country')
        latitudeColumn = self.findColumnIndex('decimalLatitude')
        longitudeColumn = self.findColumnIndex('decimalLongitude')
        coordUncertaintyColumn = self.findColumnIndex('coordinateUncertaintyInMeters')
        
        if localityColumn != '':
            currentLocality = self.model.getValueAt(currentRow, localityColumn)
            try:
                latitude = (self.model.getValueAt(currentRow, latitudeColumn))
                longitude = (self.model.getValueAt(currentRow, longitudeColumn))
                if latitude == '' or longitude == '':
                    raise ValueError("Latitude/Longitude have no values")
            except ValueError:
                if messagebox.askyesno('MISSING GPS at row {}'.format(currentRow+1), 'Would you like to halt record processing to add GPS coordinates for row {}?'.format(currentRow+1)):
                    self.setSelectedRow(currentRow)
                    self.setSelectedCol(latitudeColumn)
                    return "user_set_gps"
                else:
                    return "loc_error_no_gps"
            address = reverseGeoCall(latitude, longitude)
            if isinstance(address, list):
                newLocality = []
                for addressComponent in address:
                    if addressComponent['types'][0] == 'route':
                        # path could be Unamed Road
                        # probably don't want this as a result?
                        
                        #Testing the idea of excluding the "path" if the coord uncertainty is over a threshold.
                        #the threshold of 200 meters was chosen arbitrarily and should be reviewed.
                        coordUncertainty = (self.model.getValueAt(currentRow, coordUncertaintyColumn))
                        try:
                            coordUncertainty = int(coordUncertainty)
                            if coordUncertainty < 200:
                                path = 'near {}'.format(addressComponent['long_name'])
                                newLocality.append(path)
                                self.model.setValueAt(path, currentRow, pathColumn)
                        except ValueError:
                            pass
                    if addressComponent['types'][0] == 'administrative_area_level_1':
                        stateProvince = addressComponent['long_name']
                        newLocality.append(stateProvince)
                        self.model.setValueAt(stateProvince, currentRow, stateColumn)
                    if addressComponent['types'][0] == 'administrative_area_level_2':
                        county = addressComponent['long_name']
                        newLocality.append(county)
                        self.model.setValueAt(county, currentRow, countyColumn)
                    if addressComponent['types'][0] == 'locality':
                        municipality = addressComponent['long_name']
                        newLocality.append(municipality)
                        self.model.setValueAt(municipality, currentRow, municipalityColumn)
                    if addressComponent['types'][0] == 'country':
                        country = addressComponent['short_name']
                        newLocality.append(country)
                        self.model.setValueAt(country, currentRow, countryColumn)
                newLocality = ', '.join(newLocality[::-1]) # build it in reverse order because the list is oddly being built incorrectly.
                if newLocality not in currentLocality:
                    newLocality = newLocality + ', ' + currentLocality
                    newLocality = newLocality.rstrip() #clean up the string
                    if newLocality.endswith(','):   #if it ends with a comma, strip the final one out.
                        newLocality = newLocality.rstrip(',').lstrip(', ')
                    return newLocality
                else:
                    return currentLocality
            # Google API call returned error/status string
            else:
                apiErrorMessage = address
                messagebox.showinfo('MISSING GPS at row {}'.format(currentRow+1), 'Location lookup error at row {}:\nGoogle reverse Geolocate service responded with: "{}"/nThis may be internet connection problems, or invalid GPS values.'.format(currentRow+1,str(apiErrorMessage)))
#Commenting out for now, not sure we want people clicking yes retry repeatedly
#                if messagebox.askyesno("Locality Error", "This function requires an internet connection, would you like to retry?"):
#                    self.genLocality(currentRow)
#                else:
#                    return "loc_apierr_no_retry"
                return "loc_apierr_no_retry"
        else:
            messagebox.showinfo('Location ERROR at row {}'.format(currentRow+1), "Locality generation requires GPS coordinates, and a column named locality.")
            return
        return

    def genScientificName(self, currentRowArg):
        """Generate scientific name calls Catalog of Life to get
        most up-to-date scientific name for the specimen in question."""
        currentRow = currentRowArg
        sciNameColumn = self.findColumnIndex('scientificName')
        authorColumn = self.findColumnIndex('scientificNameAuthorship')
        sciNameAtRow = self.model.getValueAt(currentRow, sciNameColumn)
        sciNameList = sciNameAtRow.split(' ')
        sciNameToQuery = sciNameAtRow
        sciAuthorAtRow = str(self.model.getValueAt(currentRow, authorColumn))
        sciNameSuffix = ''
        if sciNameAtRow != '':
            exclusionWordList = ['sp.','sp','spp','spp.','ssp','ssp.','var','var.']
            #this intends to exclude only those instances where the final word is one from the exclusion list.
            if sciNameList[-1].lower() in exclusionWordList:    #If an excluded word is in scientific name then modify.
                sciNameToQuery = sciNameList
                sciNameSuffix = str(' ' + sciNameToQuery[-1])       #store excluded word incase the user only has genus and wants Sp or the like included.
                sciNameToQuery.pop()
                if len(sciNameToQuery) < 1:                     #If the name has more than 1 word after excluded word was removed then forget the excluded word.
                    return sciNameAtRow
                sciNameToQuery = ' '.join(sciNameToQuery)
            #elif ((len(sciNameList) == 4) & (sciNameList[2].lower() in exclusionWordList)): # handle infraspecific abbreviations by trusting user input.
            elif len(sciNameList) == 4:
                if sciNameList[2].lower() in exclusionWordList: # handle infraspecific abbreviations by trusting user input.
                    infraSpecificAbbreviation = sciNameList[2]
                    sciNameList.remove(infraSpecificAbbreviation)
                    sciNameToQuery = ' '.join(sciNameList)
            results = colNameSearch(sciNameToQuery)
            if isinstance(results, tuple):
                if results[0] == 'ERROR':
                    messagebox.showinfo('Name ERROR at row {}'.format(currentRow+1), 'Name Verification Error at row {}:\nWhen asked about "{}",\nCatalog of Life responded with: "{}."\nName unverified! (probably a typo)'.format(currentRow+1,sciNameAtRow,results[1]))
                    return sciNameAtRow

                sciName = str(results[0])
                auth = str(results[1])
                try:
                    if isinstance(infraSpecificAbbreviation, str):
                        sciName = sciName.split()
                        if len(sciName) > 2:
                            sciName.insert(-1, infraSpecificAbbreviation)
                        sciName = ' '.join(sciName)
                except NameError:
                    pass # if we fail to check infraSpecificAbbreviation, it must not exist. Probably a nicer way to do this.
    
                if sciNameAtRow != sciName:   #If scientific name needs updating, ask. Don't ask about new authority in this case.
                    if messagebox.askyesno('Scientific name at row {}'.format(currentRow+1), 'Would you like to change {} to {} and update the authority?'.format(sciNameAtRow,sciName)):
                        return (sciName, auth)
                    else:
                        return (sciNameAtRow + sciNameSuffix, sciAuthorAtRow) #if user declines the change return the old stuff.

                elif sciAuthorAtRow == '':  #if author is empty, update it without asking.
                    return (sciNameAtRow + sciNameSuffix, auth)
                elif sciAuthorAtRow != auth:  #If only Author needs updating, ask and keep origional scientific name (we've covered if it is wrong already)
                    if messagebox.askyesno('Authority at row {}'.format(currentRow+1), 'Would you like to update the authorship for {} from {} to {}?'.format(sciNameAtRow,sciAuthorAtRow,auth)):
                        return (sciNameAtRow + sciNameSuffix, auth)
                    else:
                        return (sciNameAtRow + sciNameSuffix, sciAuthorAtRow) #if user declines the change return the old stuff.
                else:
                    return (sciNameAtRow + sciNameSuffix, sciAuthorAtRow)
                    
            elif isinstance(results, str):
         #       if results == 'not_accepted_or_syn':
         #           messagebox.showinfo("Scientific Name Error", "No scientific name update!")
         #           return currentSciName
                if results == 'empty_string':
                    #messagebox.showinfo("Scientific name error", "Row " + str(currentRow+1) + " has no scientific name.") # 2 dialog boxes is sort of rude.
                    if messagebox.askyesno('MISSING Name at row {}'.format(currentRow+1), "Would you like to halt record processing to add a Scientific Name to row {}?".format(currentRow+1)):
                        self.setSelectedRow(currentRow)
                        self.setSelectedCol(sciNameColumn)
                        return "user_set_sciname"
                elif results == 'http_Error':
                     messagebox.showinfo('Name ERROR at row {}'.format(currentRow+1, "Catalog of Life, the webservice might be down. Try again later, if this issue persists please contact us: plantdigitizationprojectutc@gmail.com"))
        else: # Can this ever catch anything?
            if messagebox.askyesno('MISSING Name at row {}'.format(currentRow+1), "Would you like to halt record processing to add a Scientific Name to row {}?".format(currentRow+1)):
                self.setSelectedRow(currentRow)
                self.setSelectedCol(sciNameColumn)
                return "user_set_sciname"
            return sciNameAtRow

    def genLabelPDF(self):
        """Generate Label PDF. Print specimen labels
        for physical plant records.
        # causes a pdf to be saved (uses dialog to get save name.
        # causes a pdf to be opened with default pdf reader.
        # if inproper data passed, returns empty return.
        # expects a dataframe or a series
        # a data row(record) should be a series
        # getSelectedDataFrame(self) should be a dataframe
        # http://pandastable.readthedocs.io/en/latest/_modules/pandastable/core.html#Table.getSelectedDataFrame
        """

        toPrintDataFrame = self.getSelectedLabelDict()  #function returns a list of dicts (one for each record to print)
        labelsToPrint = len(toPrintDataFrame)
        if labelsToPrint > 0:
            for record in toPrintDataFrame:   
                if CatNumberBar.stuCollCheckBoxVar.get() == 1: # for each dict, if it is student collection
                    record['verifiedBy'] = CatNumberBar.stuCollVerifyByVar.get() #then add the verified by name to the dict.

                associatedTaxaItems = record.get('associatedTaxa').split(', ') #for each dict, verify that the associatedTaxa string does not consist of >15 items.
                if len(associatedTaxaItems) > 15:   #if it is too large, trunicate it at 15, and append "..." to indicate trunication.
                    record['associatedTaxa'] = ', '.join(associatedTaxaItems[:15])+' ...'   

            pdfFileName = self.filename.replace('.csv', '.pdf').split('/')[-1] # prep the default file name
            genPrintLabelPDFs(toPrintDataFrame, pdfFileName)     #sent modified list of dicts to the printLabelPDF module without editing actual data fields.
        else:
            messagebox.showwarning("No Labels to Make", "No specimen records (green rows) selected.")
        return

    
    def findColumnIndex(self, columnLabel):
        """Find Column Index, gets the column index
        number for a given column header."""
        
        columnIndex = ''
        for column in range(0,self.model.getColumnCount()):
            # convert self.model.getColumnName(column) to lower case before comparison
            lowerCaseLabel = columnLabel.lower()
            lowerCaseCName = self.model.getColumnName(column).lower()
            if lowerCaseCName == lowerCaseLabel:
                columnIndex = column
        return columnIndex

    def load(self, filename=None):
        """load from a file"""

        if filename == None:
            filename = filedialog.askopenfilename(parent=self.master,
                                                      defaultextension='.mpk',
                                                      initialdir=os.getcwd(),
                                                      filetypes=[("msgpack","*.mpk"),
                                                                 ("pickle","*.pickle"),
                                                        ("All files","*.*")])
        if not os.path.exists(filename):
            print('file does not exist')
            return
        if filename:
            filetype = os.path.splitext(filename)[1]
            model = TableModel()
            model.load(filename, filetype)
            self.updateModel(model)
            self.filename = filename
            self.adjustColumnWidths()
            self.redraw()
        return

    def saveAs(self, filename=None, dbReady = False):
        """Save dataframe to file"""
        if filename: # this is really only checking that we've ever initially loaded ... something. (I believe)
            dfForExport = copy.deepcopy(self.model.df) # deep copy the existing model before we make changes to the data.
            exportColumns = [] # build a list of columns to be saved (outgoing columns)
            for item in dfForExport.columns.values.tolist(): # this should probably be a list comprehension
                if item not in ['site#', 'specimen#' ,'-']: # never export these helper columns (else we'll multiply them each import)
                    exportColumns.append(item)

            # if this function was passed with the 'dbReady' set to True. Meaning, it should be "database ready"
            if dbReady:
                fileNamePreamble = 'DBReady'  # to avoid people overwriting their source data, suggest a preamble string to the file name
                exclusionList = ['path','collectionName'] # stuff we invented, and don't need to be sending to the portals.
                exportColumns = [colLabel for colLabel in exportColumns if colLabel not in exclusionList]

                # limit the dataframe for export to actual record specimens, by excluding "site" level records.
                #Explination for the filter below: dfForExport rows which do not include '#' or '!AddSITE' in the 'specimen#' column.
                dfForExport = dfForExport[~dfForExport['specimen#'].isin(['#','!AddSITE'])]

            # if we're just saving this work because we've made progress on it, keep it excel friendly.
            else:
                fileNamePreamble = 'Processed'  # to avoid people overwriting their source data, suggest a preamble string to the file name

                #Excel is interpreting site numbers < 12 as dates and converting them. Ex: 08-16 to Aug-16.
                #Also, many spreadsheet programs are altering the iso date format.
                #If dbReady = False, then include a " ' " before the problem values so that they're
                numericColumnsToCheck = ['otherCatalogNumbers','eventDate','dateIdentified']
                for numericColumn in numericColumnsToCheck:
                    try:
                        dfForExport[numericColumn] = dfForExport[numericColumn].apply(lambda x: ("'")+str(x))
                    except (KeyError):
                        print('KeyError attempting to save the {} in a spreadsheet friendly format'.format(numericColumn))
                    pass

            # prep the file name using the conditionally generated preamble.
            defFileName = self.filename.split('/')[-1] # prep the default suggested filename.
            if defFileName.split()[0] != fileNamePreamble: # ensure this file does not already have the preamble string
                defFileName = '{} {}'.format(fileNamePreamble,defFileName) # if it passes this ocndition, add preamble.
            filename = filedialog.asksaveasfilename(parent=self.master,
                                                        defaultextension='.csv',
                                                        initialfile = defFileName,
                                                        initialdir = os.getcwd(),
                                                        filetypes=[("csv","*.csv")])


            dfForExport.to_csv(filename, encoding = 'utf-8', index = False, columns = exportColumns)
        else: 
            return
    def saveForDatabase(self):
        """ simply calls "saveAs(filename, dbReady = True)
        Allowing us to make a button to generate a csv file which is ready for portal submission.
        The distinction is necessary because of the leading " ' " in some fields which are necessary
        for friendly input and output from common spreadsheet programs."""

        self.saveAs(self.filename, dbReady = True)
        
        
    def save(self):
        """Save current file"""
    # It's probably annoying we've stripped this and made it into a "save as" function
    # I'd rather be slightly annoying than risk loss overwriting the researchers field data.
        self.saveAs(self.filename)
        
    def importCSV(self, filename=None, dialog=False, **kwargs):
        """Import from csv file"""

        if self.importpath == None:
            self.importpath = os.getcwd()
        if filename == None:
            filename = filedialog.askopenfilename(parent=self.master,
                                                          defaultextension='.csv',
                                                          initialdir=self.importpath,
                                                          filetypes=[("csv","*.csv")])
        if not filename:
            return
        else:
            self.filename = filename
        if dialog == True:  # I believe this will like... never be true? We may have stripped this entirely out.
            impdialog = ImportDialog(self, filename=filename)
            df = impdialog.df
            if df is None:
                return
        else:
            df = pd.read_csv(filename, encoding = 'utf-8',keep_default_na=False, dtype=str,)

        #Excel is interpreting site numbers < 12 as dates and converting them. Ex: 08-16 to Aug-16.
        #To prevent data loss mobile app sends field numbers with a leading " ' " which we don't want.
        # The saveAs() also exports csv files with the leading " ' " added. unless "dbReady = True" when called
            numericColumnsToCheck = ['otherCatalogNumbers','eventDate','dateIdentified']
            for numericColumn in numericColumnsToCheck:
                try:
                    df[numericColumn] = df[numericColumn].apply(lambda x: x.lstrip("'"))
                except KeyError:
                    print('KeyError attempting to load in {} header.'.format(numericColumn))
                    pass
            df['-'] = '-' # add in the little "-" seperator.
            df.fillna('') # make any nans into empty strings.
            self.refreshSpecimenSiteNums(df)
        model = TableModel(dataframe=df)
        self.updateModel(model)
        self.sortTable([self.model.df.columns.get_loc('site#'),self.model.df.columns.get_loc('specimen#')])
        self.adjustColumnWidths()

        #this solves addressing errors related to index at row 1 = 1 on import, and various functions later properly reset the index to 0
        self.model.resetIndex()
        self.redraw()
        self.setSelectedRow(0)
        self.drawSelectedRow()
        self.drawSelectedRect(0,0)
        self.importpath = os.path.dirname(filename)
        return

    def loadExcel(self, filename=None):
        """Load excel file"""

        if filename == None:
            filename = filedialog.askopenfilename(parent=self.master,
                                                          defaultextension='.xls',
                                                          initialdir=os.getcwd(),
                                                          filetypes=[("xls","*.xls"),
                                                                     ("xlsx","*.xlsx"),
                                                            ("All files","*.*")])
        if not filename:
            return

        df = pd.read_excel(filename,sheetname=0)
        model = TableModel(dataframe=df)
        self.updateModel(model)
        return

    def doExport(self, filename=None):
        """Do a simple export of the cell contents to csv"""

        if filename == None:
            filename = filedialog.asksaveasfilename(parent=self.master,
                                                      defaultextension='.csv',
                                                      initialdir = os.getcwd(),
                                                      filetypes=[("csv","*.csv"),
                                                           ("excel","*.xls"),
                                                           ("html","*.html"),
                                                        ("All files","*.*")])
        if filename:
            self.model.save(filename)
            self.filename = filename
            self.currentdir = os.path.basename(filename)
        return
    def refreshSpecimenSiteNums(self, dframe):
    
        def specimenNumExtract(catNum):
            try:
                result = catNum.split('-')[1]
                if result.isdigit():
                    return int(result)
                else:
                    return '!AddSITE'
            except (ValueError, IndexError, AttributeError) as e:
                return '!AddSITE'

        def siteNumExtract(catNum):
            try:
                result = catNum.split('-')[0]
                if result.isdigit():
                    return int(result)
                else:
                    return ''
            #except ValueError:
            except (ValueError, IndexError, AttributeError) as e:
                return ''
        
        df = dframe
        if self.column_order:
            df['site#'] = df['otherCatalogNumbers'].apply(lambda x: siteNumExtract(x))
            df['specimen#'] = df['otherCatalogNumbers'].apply(lambda x: specimenNumExtract(x))
            for item in df.columns.values.tolist():
                if item not in self.column_order:
                    self.column_order.append(item)
            #If it needs to add a new column full of empty values, bring it in as a string dtype.
            self.model.df = df.reindex(columns = self.column_order, fill_value= '')
            
    def getGeometry(self, frame):
        """Get frame geometry"""

        return frame.winfo_rootx(), frame.winfo_rooty(), frame.winfo_width(), frame.winfo_height()

    def clearFormatting(self):
        self.set_defaults()
        self.columncolors = {}
        self.rowcolors = pd.DataFrame()
        return

    def helpDocumentation(self):
        link='https://github.com/j-h-m/Plant-Digitization-Project/wiki'
        webbrowser.open(link,autoraise=1)
        return

    def quit(self):
        self.main.destroy()
        return

    def saveBarPrefs(self):
        """ saves the CollectionDataEntryBar settings """
        # Save CollectionDataEntry Bar settings
        self.prefs.set('collName', CollectionDataEntryBar.collNameVar.get())
        self.prefs.set('detName',CollectionDataEntryBar.detNameVar.get())        
        self.prefs.set('useDetDate',CollectionDataEntryBar.useDetDateVar.get())
        # Save Cat Number Bar settings
        self.prefs.set('catPrefix',CatNumberBar.catPrefixVar.get())
        self.prefs.set('catDigits',CatNumberBar.catDigitsVar.get())
        self.prefs.set('catStart',CatNumberBar.catStartVar.get())
        # Save student collection settings
        self.prefs.set('stuCollVerifyBy',CatNumberBar.stuCollVerifyByVar.get())
        self.prefs.set('stuCollCheckBox',CatNumberBar.stuCollCheckBoxVar.get())

class CollectionDataEntryBar(Frame):
    """Uses the parent instance to store collection specific data and application functions"""

    def __init__(self, parent=None, parentapp=None):


            Frame.__init__(self, parent, width=600, height=40)
            self.parentframe = parent
            self.parentapp = parentapp
            #Collection Name Stuff

           
            self.labelCollText = StringVar()
            self.labelCollText.set("Collection Name:")
            self.labelColl = Label(self, textvariable=self.labelCollText)
            self.labelColl.grid(row=0, column=1, rowspan = 1, sticky='news', pady=1, ipady=1)
            #self.collName = StringVar() #Variable for collection name
            self.collEntryBox = Entry(self,textvariable=self.collNameVar, width=45)
            self.collEntryBox.grid(row=0, column=2, rowspan = 2, sticky='news', pady=1, ipady=1)

            self.addCollNameButton = Button(self, text = 'Add', command = self.addCollectionName, width = 5)
            ToolTip.createToolTip(self.addCollNameButton,'Add collection name to all records')
            self.addCollNameButton.grid(row=0, column=3, rowspan =1, sticky ='news', pady=1, ipady=1)
            self.delCollNameButton = Button(self, text = 'Del', command = self.delCollectionName, width = 5)
            ToolTip.createToolTip(self.delCollNameButton,'Remove collection name from all records')
            self.delCollNameButton.grid(row=0, column=4, rowspan =1, sticky ='news', pady=1, ipady=1)
            #Determined By Stuff
            self.labelDetText = StringVar()
            self.labelDetText.set("Determined By:")
            self.labelDet = Label(self, textvariable=self.labelDetText)
            self.labelDet.grid(row=0, column=5, rowspan = 1, sticky='news', pady=1, ipady=1)
            self.detName = StringVar() #Variable for Determiner name
            self.detEntryBox = Entry(self,textvariable=self.detNameVar, width=20)
            self.detEntryBox.grid(row=0, column=6, rowspan = 2, sticky='news', pady=1, ipady=1)

            #self.useDetDateVar = IntVar() #Variable for Determination date Preference
            self.useDetDateCheckButton = Checkbutton(self, text="Date", variable=self.useDetDateVar)

            ToolTip.createToolTip(self.useDetDateCheckButton,"Add today's date as the determination date")
            self.useDetDateCheckButton.grid(row=0, column=7, rowspan=1, sticky ='news', pady=1, ipady=1)
            self.addDetByNameButton = Button(self, text = 'Add', command = self.addDetByName, width = 5)
            ToolTip.createToolTip(self.addDetByNameButton,'Add determined by name to all records')
            self.addDetByNameButton.grid(row=0, column=8, rowspan =1, sticky ='news', pady=1, ipady=1)
            self.delDetByNameButton = Button(self, text = 'Del', command = self.delDetByName, width = 5)
            ToolTip.createToolTip(self.delDetByNameButton,'Remove determined by from all records')
            self.delDetByNameButton.grid(row=0, column=9, rowspan =1, sticky ='news', pady=1, ipady=1)

#Functions to operate within the CollectionDataEntryBar's tkinter space.

    def addCollectionName(self):
        collName = self.collNameVar.get()
        self.parentapp.model.df['collectionName'] = collName
        self.parentapp.redraw()

    def delCollectionName(self):
        try:
            self.parentapp.model.df.drop('collectionName', axis=1, inplace=True)
        except ValueError:
            pass
        self.parentapp.redraw()

    def addDetByName(self): # Only replacing empty cells.
        detByCol = self.parentapp.model.df['identifiedBy']
        detName = self.detNameVar.get()
        self.parentapp.model.df.loc[detByCol == '', 'identifiedBy'] = detName
        #self.parentapp.model.df['identifiedBy'] = detName
        if self.useDetDateVar.get() == 1:
            from datetime import date
            isoDate = date.today().isoformat()
            self.parentapp.model.df['dateIdentified'] = isoDate
        self.parentapp.redraw()

    def delDetByName(self): # Should this only remove the "added" names?
        try:
            self.parentapp.model.df.drop('identifiedBy', axis=1, inplace=True)
            self.parentapp.model.df.drop('dateIdentified', axis=1, inplace=True)
        except ValueError:
            pass
        self.parentapp.redraw()


class CatNumberBar(Frame):
    """Uses the parent instance to store collection specific data and application functions"""
    def __init__(self, parent=None, parentapp=None):

            Frame.__init__(self, parent, width=600, height=40)
            self.parentframe = parent
            self.parentapp = parentapp

            #Catalog Number Stuff
            catStatus = NORMAL
            self.labelCatNumText = StringVar()
            self.labelCatNumText.set('Catalog Number Prefix:')
            self.labelCatPrefix = Label(self, textvariable=self.labelCatNumText)
            self.labelCatPrefix.grid(row=1, column=1, rowspan = 1, sticky='news', pady=1, ipady=1)

            self.catPrefixEntryBox = Entry(self,textvariable=self.catPrefixVar, width=12, state=catStatus)
            self.catPrefixEntryBox.grid(row=1, column=2, rowspan = 1, sticky='news', pady=1, ipady=1)

            self.labelCatDigitsText = StringVar()
            self.labelCatDigitsText.set('Digits:')
            self.labelCatDigits = Label(self, textvariable=self.labelCatDigitsText)
            self.labelCatDigits.grid(row=1, column=3, rowspan = 1, sticky='news', pady=1, ipady=1)

            self.catDigitsEntryBox = Entry(self,textvariable=self.catDigitsVar, width=3, state=catStatus)
            self.catDigitsEntryBox.grid(row=1, column=4, rowspan = 1, sticky='news', pady=1, ipady=1)

            self.labelCatStartText = StringVar()
            self.labelCatStartText.set('Start:')
            self.labelCatStart = Label(self, textvariable=self.labelCatStartText)
            self.labelCatStart.grid(row=1, column=5, rowspan = 1, sticky='news', pady=1, ipady=1)

            self.catStartEntryBox = Entry(self,textvariable=self.catStartVar, width=10, state=catStatus)
            self.catStartEntryBox.grid(row=1, column=6, rowspan = 1, sticky='news', pady=1, ipady=1)
            
            self.catPreviewText = StringVar()
            self.catPreviewText.set('')
            self.labelCatPreview = Label(self, textvariable=self.catPreviewText, state=catStatus, foreground ="gray25",  width = 18)
            self.labelCatPreview.grid(row=1, column=7, rowspan = 1, sticky='e', pady=1, ipady=1)
            
            self.previewCatButton = Button(self, text = 'Preview', command = self.genCatNumPreview, width = 7, state=catStatus)
            ToolTip.createToolTip(self.previewCatButton,'Preview catalog number format')
            self.previewCatButton.grid(row=1, column=8, rowspan = 1, sticky='news', pady=1, ipady=1)

            
            self.addCatNumButton = Button(self, text = 'Add', command = self.addCatalogNumbers, width = 5, state=catStatus)
            ToolTip.createToolTip(self.addCatNumButton,'Assign catalog numbers to each record')
            self.addCatNumButton.grid(row=1, column=9, rowspan =1, sticky ='news', pady=1, ipady=1)
            self.delCatNumButton = Button(self, text = 'Del', command = self.delCatalogNumbers, width = 5, state=catStatus)
            ToolTip.createToolTip(self.delCatNumButton,'Remove catalog numbers from all records')
            self.delCatNumButton.grid(row=1, column=10, rowspan =1, sticky ='news', pady=1, ipady=1)

            #add student collection widgets
            self.stuCollCheckBox = Checkbutton(self, text="Student Collection", variable = self.stuCollCheckBoxVar, command = self.stuCollCheckBoxChange)
            #variable=self.stuCollCheckBox
            ToolTip.createToolTip(self.stuCollCheckBox,"Add a 'Verified By:' notice on labels for student collections")
            self.stuCollCheckBox.grid(row=2, column=1, rowspan = 1, sticky='news', pady=1, ipady=1)

            self.stuCollVerifyByText = StringVar()
            self.stuCollVerifyByText.set('Verified By:')
            self.stuCollVerifyBylabel = Label(self, textvariable=self.stuCollVerifyByText)
            self.stuCollVerifyBylabel.grid(row=2, column=2, rowspan = 1, sticky='news', pady=1, ipady=1)

            if self.stuCollCheckBoxVar.get() == 1:
                stuCollState = NORMAL
            else:
                stuCollState = DISABLED
            self.stuCollVerifyBy = Entry(self,textvariable=self.stuCollVerifyByVar, width=16, state=stuCollState)
            self.stuCollVerifyBy.grid(row=2, column=3, rowspan = 1,columnspan = 4, sticky='news', pady=1, ipady=1)
#Functions to operate within the CatNumberBar's tkinter space.

    def stuCollCheckBoxChange(self):
        """disables or enables the stuCollVerifyBy entry field depending on the checkbox Status"""
        if self.stuCollCheckBoxVar.get() == 1:
            self.stuCollVerifyBy.configure(state=NORMAL)
        else:
            self.stuCollVerifyBy.configure(state=DISABLED)
        self.parentapp.saveBarPrefs()

    def genCatNumPreview(self):
        """Generate catalog number preview ..."""
        self.parentapp.savePrefs()
        prefix = self.catPrefixVar.get()
        digits = self.catDigitsVar.get()
        start = str(self.catStartEntryBox.get()).zfill(digits)
        if len(start) > digits:
            messagebox.showwarning("Starting Value Error", "Starting Catalog Number Value Exceeds Entered The Max Digits")
        else:
            self.catPreviewText.set(prefix+start)
            self.parentapp.redraw()

    def addCatalogNumbers(self):
        """Add catalog numbers..."""
        # todo alter the catalog number assignment to use a pool of available catalog numbers, & maybe when appropriate return removed values to the pool.
        # see the comments below "def delCatalogNumbers(self):"
        prefix = self.catPrefixVar.get()
        digits = self.catDigitsVar.get()
        start = self.catStartVar.get()
        df = self.parentapp.model.df
        specimenRecordGroup = df.iloc[self.parentapp.getOnlySpecimenRecords()]
        
        if len(str(start)) > digits: #check that the starting value does not require more decimal places than the entered digit length
            messagebox.showwarning("Starting Value Error", "Starting Catalog Number Value Exceeds Entered The Max Digits")
        else:
            try: # try and isolate the records which need a catalog number
                groupNeedingBarcodes = specimenRecordGroup[specimenRecordGroup['catalogNumber'].str.len() != (len(str(prefix)) + digits)]
            except KeyError: #if no 'catalogNumber column exists, generate it
                self.parentapp.model.df['catalogNumber'] = ''
                groupNeedingBarcodes = specimenRecordGroup[specimenRecordGroup['catalogNumber'].str.len() != (len(str(prefix)) + digits)]
            catalogValues = [prefix + str(x + int(start)).zfill(digits) for x in range(len(groupNeedingBarcodes))] #Generate a list of the barcodes to assign
            self.catStartVar.set(len(catalogValues) + int(start)) # update the starting view by the quanity being added
            df.loc[groupNeedingBarcodes.index,'catalogNumber'] = catalogValues #apply the selective changes
            self.parentapp.redraw()
                
    def delCatalogNumbers(self):
        """Blindly removes the catalogNumber column..."""
        try:
            # todo
            # currently, there exists an issue where:
            # if a user has one or more pre-existing, yet properly formatted catalog numbers,
            # then assigns numbers to empty catalogNumber fields
            # then removes the catalog numbers
            # the catalog number starting value will roll back further than appropriate
            # because the pre-existing numbers were properly formatted & we're counting the quantity to roll back based on formatting conditions.
            self.parentapp.model.df.drop('catalogNumber', axis=1, inplace=True)
            if messagebox.askyesno("Roll Back Starting Catalog Number?", "Would you like to reduce the starting catalog value by the quantity removed from the table?\nTAKE CAUTION: If you had pre-existing catalog numbers assigned, this may roll back the starting value too far!"):
                self.catStartVar.set(str(self.catStartVar.get() - len(self.parentapp.getOnlySpecimenRecords())))              
        except ValueError:
            pass
        self.parentapp.redraw()


class ToolBar(Frame):
    """Uses the parent instance to provide the functions"""

    def __init__(self, parent=None, parentapp=None):

        Frame.__init__(self, parent, width=600, height=40)
        self.parentframe = parent
        self.parentapp = parentapp

        img = images.importcsv()
        func = lambda: self.parentapp.importCSV(dialog=False)
        addButton(self, 'Import', func, img, 'import csv', side=LEFT)

        img = images.save_proj()
        addButton(self, 'Save', self.parentapp.save, img, 'save', side=LEFT)

        # add in an option for database ready Export 
        img = images.open_proj()
        addButton(self, 'DB Save', self.parentapp.saveForDatabase, img, 'Save in Database Format', side=LEFT)

        # add an image for the button later, using existing img until this one is resized.
        #img = images.open_processRecords() 
        img = images.merge() 
        addButton(self, 'Process Records', self.parentapp.processRecords, img, 'Process Records', side=LEFT)

        img = images.aggregate() #hijacking random image for now
        addButton(self, 'Export',self.parentapp.genLabelPDF, img, 'Export Labels to PDF', side=LEFT)

        img = images.table_delete()  
        addButton(self, 'Undo',self.parentapp.undo, img, 'Undo the last major change.', side=LEFT)
        
        img = images.prefs()
        addButton(self, 'Preferences', self.parentapp.showPrefs, img, 'Show Preferences', side = LEFT)
        
        img = images.cross()
        addButton(self, 'Help', self.parentapp.helpDocumentation , img , 'Help Documentation', side=LEFT)

        # List of unused button assets (for temp use before we get in our assets)
        # img = images.open_proj()
        #img = images.excel()        
        #img = images.copy()        
        # img = images.paste()        
        # img = images.plot()        
        # img = images.transpose()        
        # img = images.aggregate()        
        # img = images.pivot()        
        # img = images.melt()        
        # img = images.merge()        
        # img = images.table_multiple()        
        # img, 'sub-table from selection')
        # img = images.filtering()        
        # img = images.calculate()        
        # img = images.fit()        
        #img = images.table_delete()        
        #img = images.prefs()
        #img = images.table_delete()
        #img = images.paste()
        #img = images.transpose()
        return

class ChildToolBar(ToolBar):
    """Smaller toolbar for child table"""

    def __init__(self, parent=None, parentapp=None):
        Frame.__init__(self, parent, width=600, height=40)
        self.parentframe = parent
        self.parentapp = parentapp
        img = images.open_proj()
        addButton(self, 'Load table', self.parentapp.load, img, 'load table')
        img = images.importcsv()
        func = lambda: self.parentapp.importCSV(dialog=1)
        addButton(self, 'Import', func, img, 'import csv')
        # img = images.transpose()
        # addButton(self, 'Transpose', self.parentapp.transpose, img, 'transpose')
        img = images.copy()
        addButton(self, 'Copy', self.parentapp.copyTable, img, 'copy to clipboard')
        img = images.paste()
        addButton(self, 'Paste', self.parentapp.pasteTable, img, 'paste table')
        img = images.table_delete()
        addButton(self, 'Clear', self.parentapp.clearTable, img, 'clear table')
        img = images.cross()
        addButton(self, 'Close', self.parentapp.remove, img, 'close')
        return

class statusBar(Frame):
    """Status bar class"""

    def __init__(self, parent=None, parentapp=None):

        Frame.__init__(self, parent)
        self.parentframe = parent
        self.parentapp = parentapp
        sfont = ("Helvetica bold", 10)
        clr = '#A10000'
        self.rowsvar = StringVar()
        l=Label(self,textvariable=self.rowsvar,font=sfont,foreground=clr)
        l.pack(fill=X, side=LEFT)
        Label(self,text='rows x',font=sfont,foreground=clr).pack(side=LEFT)
        self.colsvar = StringVar()
        self.colsvar.set(len(self.parentapp.model.df))
        l=Label(self,textvariable=self.colsvar,font=sfont,foreground=clr)
        l.pack(fill=X, side=LEFT)
        Label(self,text='columns',font=sfont,foreground=clr).pack(side=LEFT)
        self.filenamevar = StringVar()
        l=Label(self,textvariable=self.filenamevar,font=sfont)
        l.pack(fill=X, side=RIGHT)
        return

    def update(self):
        """Update status bar"""

        model = self.parentapp.model
        self.rowsvar.set(len(model.df))
        self.colsvar.set(len(model.df.columns))
        if self.parentapp.filename != None:
            self.filenamevar.set(self.parentapp.filename)
        return
