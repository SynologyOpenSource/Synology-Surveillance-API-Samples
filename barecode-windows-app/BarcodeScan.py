# -*- coding: UTF-8 -*-
import os
from typing import Callable
from datetime import datetime, date, time
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from BookmarkLibrary import BookmarkVideoDownload, BookmarkCreate, BookmarkDelete
from BookmarkDatabase import BookmarkDB


def TimeFormatConvert(Time:list[int])->str:
    '''
    Convert the time into legal string for surveillance API.

    @param Time: list in [year, month, data, hour, minute, second] formate

    @return : Time string in YY-MM-DDThh:mm:ss format
    '''
    return f"{date(Time[0], Time[1], Time[2])}T{time(Time[3], Time[4], Time[5])}"

def FilenameCheck(Folderpath:str, Filename:str)->str|None:
    '''
    Check the download file name legality and modify.

    @param Folderpath: folder path
    @param Filename: file name

    @return None: folder path not exist or illegal
    @return str: modified file name
    '''
    if not os.path.exists(Folderpath):
        return
    if Folderpath == "./":
        FilePath = Folderpath + Filename
    else:
        FilePath = f"{Folderpath}/{Filename}"
    if not os.path.exists(FilePath + ".zip"):
        return FilePath + ".zip"
    FileNum = 1
    while os.path.exists(f"{FilePath}{str(FileNum)}.zip"):
        FileNum += 1
    return f"{FilePath}{str(FileNum)}.zip"

def DownloadModeScan(NasIP:str, SId:str, BookmarkDB:BookmarkDB, Folderpath:str, Filename:str)->None:
    '''
    Preprogress for bookmark video download before scanning barcode.

    @param NasIP: NAS IP
    @param SId: SID
    @param BookmarkDB: database of bookmarks
    @param Folderpath: folder path
    @param Filename: file name
    '''
    if not Filename:
        messagebox.showerror("ERROR", "Please fill Filename.")
        return
    Filepath = FilenameCheck(Folderpath, Filename)
    ScanWindow(DownloadVideo, NasIP, SId, BookmarkDB, Filepath)

def DownloadVideo(Barcode:str, NasIP:str, SId:str, BookmarkDB:BookmarkDB, Filepath:str)->None:
    '''
    Download bookmark video.

    @param Barcode: barcode corresponding to certain bookmark
    @param NasIP: NAS IP
    @param SId: SID
    @param BookmarkDB: database of bookmarks
    @param Filepath: filepath of download video
    '''
    BookmarkInfo = BookmarkDB.BookmarkDBGet(Barcode)
    if not BookmarkInfo:
        messagebox.showerror("Error", "Barcode not exist")
        return
    if not Filepath:
        messagebox.showerror("Error", "Path not exist")
        return
    if BookmarkInfo["NasIP"]!=NasIP:
        messagebox.showerror("Error", "Wrong NAS IP")
        return
    StartTime = BookmarkInfo["StartTime"]
    EndTime = BookmarkInfo["EndTime"]
    Info = [f"Bookamrk Name: {Barcode}", f"Start Time: {StartTime[0:4]}/{StartTime[5:7]}/{StartTime[8:10]} {StartTime[11:13]}:{StartTime[14:16]}:{StartTime[17:]}", \
            f"End Time: {EndTime[0:4]}/{EndTime[5:7]}/{EndTime[8:10]} {EndTime[11:13]}:{EndTime[14:16]}:{EndTime[17:]}"]
    Result = messagebox.askyesno("Download", "\n".join(Info))
    if not Result: return
    try:
        BookmarkVideoDownload(NasIP, SId, BookmarkInfo["BookmarkID"], Filepath)
        messagebox.showinfo("Download success", f"Download to {Filepath}")
    except:
        messagebox.showerror("Error", "Bookmark download failed(probably due to start time not legal).")

def StartEndTimeCheck(StartTime:list[str], EndTime:list[str])->bool:
    '''
    Check start time not bigger than end time.

    @param StartTime: bookamrk start time
    @param EndTime: bookmark end time
    '''
    try:
        for i in range(6):
            StartTime[i] = int(StartTime[i])
            EndTime[i] = int(EndTime[i])
        print(StartTime, EndTime)
        StartTime = datetime(StartTime[0], StartTime[1], StartTime[2], StartTime[3], StartTime[4], StartTime[5])
        EndTime = datetime(EndTime[0], EndTime[1], EndTime[2], EndTime[3], EndTime[4], EndTime[5])
        print(StartTime, EndTime, StartTime >= EndTime)

    except:
        return False
    if StartTime >= EndTime: return False
    return True

def CreateModeScan(NasIP:str, SId:str, BookmarkDB:BookmarkDB, Cam:str, StartTime:list, EndTime:list, Comment:str=' ')->None:
    '''
    Preprogress for bookmark creating before scanning barcode.
    @param NasIP: NAS IP
    @param SId: SID
    @param BookmarkDB: database of bookmarks
    @param Cam: camera info with "camera id/ name/ IP" format
    @param StartTime: bookamrk start time
    @param EndTime: bookmark end time
    @param Comment(Optional): bookamrk comment
    '''
    if not Cam or not StartTime or not EndTime:
        messagebox.showerror("ERROR", "Please fill necessary info.")
        return
    CamId = Cam.split('/')[0]
    if not StartEndTimeCheck(StartTime, EndTime):
        messagebox.showerror("Error", "Start time and End time illegal.")
        return 
    StartTime = TimeFormatConvert(StartTime)
    EndTime = TimeFormatConvert(EndTime)
    ScanWindow(CreateBookmark, NasIP, SId, BookmarkDB, CamId, StartTime, EndTime, Comment)

def CreateBookmark(Barcode:str, NasIP:str, SId:str, BookmarkDB:BookmarkDB, CamId:str, StartTime:str, EndTime:str, Comment:str=' ')->None:
    '''
    Create bookmark.

    @param Barcode: barcode corresponding to certain bookmark
    @param NasIP: NAS IP
    @param SId: SID
    @param BookmarkDB: database of bookmarks
    @param CamId: camera id
    @param StartTime: bookamrk start time
    @param EndTime: bookmark end time
    @param Comment(Optional): bookamrk comment
    '''
    OldBookmarkInfo = BookmarkDB.BookmarkDBGet(Barcode)
    if OldBookmarkInfo != None:
        BookmarkDelete(NasIP, SId, OldBookmarkInfo["BookmarkID"])
    try:
        BookmarkInfo = BookmarkCreate(NasIP, SId, CamId, Barcode, StartTime, EndTime, Comment)
    except:
        return
    BookmarkDB.BookmarkDBSet(Barcode, NasIP, CamId, StartTime, EndTime, BookmarkInfo["bookmarkId"], Comment, BookmarkInfo["dsId"])
    messagebox.showinfo("Create success", f"Create bookmark : {Barcode}")

def BarcodeGet(event:tk.Event, BarcodeList:list, ScanWindow:tk.Toplevel, TextLabel:tk.Label, func: Callable, *args)->None:
    '''
    Scanning barcode and send to certain function.

    @param event: scanning event
    @param BarcodeList: barcode list that store the characters in bracode
    @param ScanWindow: the scanning window frame object
    @param TextLabel: label object of the scanning window
    @param func: callable function
    @param args: arguments that send to func
    '''
    if event.keysym != 'Return':
        BarcodeList.append(event.char)
    elif event.keysym == 'Return':
        ScanWindow.unbind("<Key>")
        Barcode = ''.join(BarcodeList)
        TextLabel["text"] = "Please wait"
        func(Barcode, *args)
        ScanWindow.destroy()

def ScanWindow(func:Callable, *args)->None:
    '''
    Create scanning window.

    @param func: callable function that trigger after scanning
    @param args: arguments that send to func
    '''
    BarcodeList = list()
    ScanWindow = tk.Toplevel()
    ScanWindow.geometry('130x50')
    ScanWindow.title("Scan barcode")
    TextLabel = ttk.Label(ScanWindow, text="Please scan barcode")
    TextLabel.place(relx=0.5, rely=0.5, anchor="center")
    ScanWindow.bind("<Key>", lambda event:BarcodeGet(event, BarcodeList, ScanWindow, TextLabel, func, *args))
    ScanWindow.grab_set()
    ScanWindow.focus()
