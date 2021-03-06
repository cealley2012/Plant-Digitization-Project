#!/usr/bin/env python

from types import *
from copy import deepcopy
import operator
import os, string, types, copy
import pickle
import numpy as np
import pandas as pd
import util
import core

class TableModel(object):
    """A data model for the Table class that uses pandas

    Args:
        dataframe: pandas dataframe
        rows: number of rows if empty table
        columns: number of columns if empty table
    """

    keywords = {'colors':'colors'}

    def __init__(self, dataframe=None, rows=20, columns=5):
        """Constructor for table model. """
        self.initialiseFields()
        self.setup(dataframe, rows, columns)
        return

    def setup(self, dataframe, rows=20, columns=5):
        """Create table model"""

        if not dataframe is None:
            self.df = dataframe
        else:
            colnames = list(string.ascii_lowercase[:columns])
            self.df = pd.DataFrame(index=range(rows),columns=colnames)
        self.reclist = self.df.index # not needed now?
        return

    def initialiseFields(self):
        """Create meta data fields"""
        self.meta = {}
        self.columnwidths = {} #used to store col widths
        return

    def save(self, filename):
        """Save dataframe"""

        ftype = os.path.splitext(filename)[1]
        if ftype == '.mpk':
            self.df.to_msgpack(filename)
        elif ftype == '.pickle':
            self.df.to_pickle(filename)
        elif ftype == '.xls':
            self.df.to_excel(filename)
        elif ftype == '.csv':
            self.df.to_csv(filename)
        #elif ftype == '.html':
        #    self.df.to_html(filename)
        return

    def load(self, filename, filetype=None):
        """Load file, if no filetype given assume it's msgpack format"""

        if filetype == '.pickle':
            self.df = pd.read_pickle(filename)
        else:
            self.df = pd.read_msgpack(filename)
        return

    def getlongestEntry(self, colindex):
        """Get the longest string in the column for determining width"""

        df = self.df
        col = df.columns[colindex]
        try:
            if df.dtypes[col] == 'float64':
                c = df[col].round(3)
            else:
                c = df[col]
        except:
            return 1
        longest = c.astype('object').astype('str').str.len().max()
        if np.isnan(longest):
            return 1
        return longest

    def getRecordAtRow(self, rowIndex):
        """Get the entire record at the specifed row"""
        
        # name = self.getRecName(rowIndex)
        # changed this code from 'name' to rowIndex
        record = self.df.ix[rowIndex]
        return record

    def moveColumn(self, oldindex, newindex):
        """Changes the order of columns"""

        df = self.df
        cols = list(df.columns)
        name = cols[oldindex]
        del cols[oldindex]
        cols.insert(newindex, name)
        self.df = df[cols]
        return

    def autoAddRows(self, num):
        """Add n rows to end of dataframe. Will create rows with index starting
           from highest previous row count"""

        df = self.df
        if len(df) == 0:
            self.df = pd.DataFrame(pd.Series(range(num)))
            print (df)
            return
        try:
            ind = self.df.index.max()+1
        except:
            ind = len(df)+1
        new = pd.DataFrame(np.nan, index=range(ind,ind+num), columns=df.columns)
        self.df = pd.concat([df, new])
        
        return
    
    def addRow(self, rowindex):
        """Inserts a row at the required index by append/concat"""

        df = self.df
        a, b = df[:rowindex], df[rowindex:]
        a = a.append(pd.Series(), ignore_index=1)
        self.df = pd.concat([a,b])
        return

    def deleteRow(self, row, unique=True):
        """Delete a row"""

        self.deleteRows([row], unique)
        return

    def deleteRows(self, rowlist=None, unique=True):
        """Delete multiple or all rows"""

        df = self.df
        if unique == True:
            rows = list(set(range(len(df))) - set(rowlist))
            self.df = df.iloc[rows]
        else:
            df.drop(df.index[rowlist],inplace=True)
        return

    def addColumn(self, colname=None, dtype=None, data=None):
        """Add a column"""

        if data is None:
            data = pd.Series(dtype=dtype)
        self.df[colname] = data
        return

    def deleteColumn(self, colindex):
        """delete a column"""

        df = self.df
        colname = df.columns[colindex]
        df.drop([colname], axis=1, inplace=True)
        return

    def deleteColumns(self, cols=None):
        """Remove all cols or list provided"""

        df = self.df
        colnames = df.columns[cols]
        df.drop(colnames, axis=1, inplace=True)
        return

    def deleteCells(self, rows, cols):
        self.df.iloc[rows,cols] = np.nan
        return

    def resetIndex(self):
        """Reset index behaviour"""

        df = self.df
        if df.index.name != None or df.index.names[0] != None:
            drop = False
        else:
            drop = True
        df.reset_index(drop=drop,inplace=True)
        return

    def setindex(self, colindex):
        """Index setting behaviour"""

        df = self.df
        colnames = list(df.columns[colindex])
        indnames = df.index.names
        if indnames[0] != None:
            df.reset_index(inplace=True)
        df.set_index(colnames, inplace=True)
        return

    def copyIndex(self):
        """Copy index to a column"""

        df = self.df
        name = df.index.name
        if name == None: name='index'
        df[name] = df.index#.astype('object')
        return

    def groupby(self, cols):
        """Group by cols"""

        df = self.df
        colnames = df.columns[cols]
        grps = df.groupby(colnames)
        return grps

    def getColumnType(self, columnIndex):
        """Get the column type"""
        coltype = self.df.dtypes[columnIndex]
        return coltype

    def getColumnCount(self):
         """Returns the number of columns in the data model"""
         return len(self.df.columns)

    def getColumnName(self, columnIndex):
         """Returns the name of the given column by columnIndex"""
         return str(self.df.columns[columnIndex])

    def getColumnData(self, columnIndex=None, columnName=None,
                        filters=None):
        """Return the data in a list for this col,
            filters is a tuple of the form (key,value,operator,bool)"""
        if columnIndex != None and columnIndex < len(self.columnNames):
            columnName = self.getColumnName(columnIndex)
        names = Filtering.doFiltering(searchfunc=self.filterBy,
                                         filters=filters)
        coldata = [self.data[n][columnName] for n in names]
        return coldata

    def getColumns(self, colnames, filters=None, allowempty=True):
        """Get column data for multiple cols, with given filter options,
            filterby: list of tuples of the form (key,value,operator,bool)
            allowempty: boolean if false means rows with empty vals for any
            required fields are not returned
            returns: lists of column data"""

        def evaluate(l):
            for i in l:
                if i == '' or i == None:
                    return False
            return True
        coldata=[]
        for c in colnames:
            vals = self.getColumnData(columnName=c, filters=filters)
            coldata.append(vals)
        if allowempty == False:
            result = [i for i in zip(*coldata) if evaluate(i) == True]
            coldata = list(zip(*result))
        return coldata

    def getRowCount(self):
         """Returns the number of rows in the table model."""
         
         #return len(self.reclist) # orig code was calling a variable set on initial load in index length.
         # todo
        #it would be wise to find each instance of getRowCount{} to check if we've already hotfixed (in some hacky way) the symptoms of this problem
         return len(self.df.index)

    def getValueAt(self, rowindex, colindex):
         """Returns the cell value at location specified
             by columnIndex and rowIndex."""

         df = self.df
         value = self.df.iloc[rowindex,colindex]
         if type(value) is float and np.isnan(value):
             return ''
         return value

    def setValueAt(self, value, rowindex, colindex):
        """Changed the dictionary when cell is updated by user"""
        # This first "if" check was introducing 'nan's seemingly randomly .
        # as we don't expect any significant numeric data, I believe it is safe
        # to leave empty strings as empty strings.
        #if value == '':
            #value = np.nan
        
        dtype = self.df.dtypes[colindex]
        #try to cast to column type
        try:
            if dtype == 'float64':
                value = float(value)
            elif dtype == 'int':
                value = int(value)
            elif dtype == 'datetime64[ns]':
                value = pd.to_datetime(value)
        except Exception as e:
            print (e)
        self.df.iloc[rowindex,colindex] = value
        return

    def __repr__(self):
        return 'Table Model with %s rows' %len(self.df)
