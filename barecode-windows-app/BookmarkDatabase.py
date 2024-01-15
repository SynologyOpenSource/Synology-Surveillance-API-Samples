# -*- coding: UTF-8 -*-

class BookmarkDB:
    '''
    BookmarkDB is a virtual database class including getter and setter to get and set the bookmark info. 
    '''
    def __init__(self):
        self.DB = dict()

    def BookmarkDBSet(self, Barcode:str, NasIP:str, CamID:str, StartTime:str, EndTime:str, BookmarkId:str, Comment:str=' ', DsID:str=None):
        self.DB[Barcode] = {"nasIP":NasIP, "camID":CamID, "dsID":DsID, "startTime":StartTime, "endTime":EndTime, "bookmarkID":BookmarkId, "comment":Comment}
 
    def BookmarkDBGet(self, Barcode:str)->dict:
        if not self.DB.get(Barcode):
            return None
        BookmarkData = self.DB[Barcode]
        return {"NasIP":BookmarkData["nasIP"], "CamID":BookmarkData["camID"], "BookmarkID":BookmarkData["bookmarkID"], "StartTime":BookmarkData["startTime"], "EndTime":BookmarkData["endTime"]}
