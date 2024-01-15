# -*- coding: UTF-8 -*-
import requests
from tkinter import messagebox

def SIDGet(NasIP:str, Account:str, Password:str)->str:
    '''
    Get SID with NAS IP, account and password.

    @param NasIP: NAS IP
    @param Account: NAS account
    @param Password: NAS password

    @return SID: SId
    '''
    URL = f"https://{NasIP}:5001/webapi/SurveillanceStation/ThirdParty/Auth/Login/v1?account={Account}&passwd={Password}"
    Headers = {"accept" : "application/json"}
    try:
        r = requests.get(URL, headers=Headers, verify=False).json()
    except:
        raise
    SID = r["data"]["sid"]
    return SID

def CameraListGet(NasIP:str, SId:str)->list[dict]:
    '''
    Provide cameras' info.

    @param NasIP: NAS IP
    @param Sid: SID

    @return CamList: Cameras' info including "statusId", "status", "dsName", "model", "vendor", "dsId", "name", "mac", "ip" and "camId"
    '''
    URL = f"https://{NasIP}:5001/webapi/SurveillanceStation/ThirdParty/Camera/List/v1?_sid={SId}"
    Headers = {"accept": "application/json"}
    CamList = requests.get(URL, headers=Headers, verify=False).json()["data"]["cameras"]
    return CamList

def BookmarkListGet(NasIP:str, SId:str, CamID:str)->list[dict]:
    '''
    Provide all bookamrks' info of certain camera.

    @param NasIP: NAS IP
    @param Sid: SID
    @param CamID: camera ID

    @return None: request failed
    @return BookmarkList: bookmarks info including "camName", "camId", "dsId", "endTime", "startTime", "bookmarkId", "comment" and "name"
    '''
    URL = f"https://{NasIP}:5001/webapi/SurveillanceStation/ThirdParty/Bookmark/List/v1?camIds=%22{CamID}%22&_sid={SId}"
    Headers = {"accept": "application/json"}
    try:
        BookmarkList = requests.get(URL, headers=Headers, verify=False).json()["data"]["bookmarks"]
    except:
        return
    return BookmarkList
    
def BookmarkVideoDownload(NasIP:str, SId:str, BookmarkId:str, Filepath:str)->None:
    '''
    Download bookmark video
    
    @param NasIP: NAS IP
    @param Sid: SID
    @param BookmarkId: bookamrk ID
    @param Filepath: file path 
    '''
    URL = f"https://{NasIP}:5001/webapi/SurveillanceStation/ThirdParty/Bookmark/DownloadRecording/v1?bookmarkId={BookmarkId}&_sid={SId}"
    Headers = {"accept": "application/zip"}
    Response = requests.get(URL, headers=Headers, verify=False)
    if Response.headers["Content-Type"] != "application/zip":
        raise
    with open(Filepath, 'wb') as f:
        f.write(Response.content)

def BookmarkCreate(NasIP:str, SId:str, CamID:str, Barcode:str, StartTime:str, EndTime:str, Command:str=None)->dict:
    '''
    Create bookmark on NAS and return bookmark info.

    @param NasIP: NAS IP
    @param SId: SID
    @param CamID: camera ID
    @param Barcode: barcode, also the bookmark name
    @param StartTime: bookamrk start time
    @param EndTime: bookmark end time
    @param Comment(Optional): bookamrk comment

    @return BookmarkInfo: bookmark info including "camName", "camId", "dsId", "endTime", "startTime", "bookmarkId", "comment" and "name"
    '''
    Barcode = BookmarkNameFormatCheck(Barcode)
    if not Barcode:
        messagebox.showerror("bookmark format error, +~!=@#$%^&*()/\|{}[]:'\" are illegal")
        raise
    URL = f"https://{NasIP}:5001/webapi/SurveillanceStation/ThirdParty/Bookmark/Create/v1?camId=%22{CamID}%22&name=%22 \
        {Barcode}%22&startTime=%22{StartTime}%22&endTime=%22{EndTime}%22&comment=%22{Command}%22&_sid={SId}"
    Headers = {"accept": "application/json"}
    try:
        BookmarkInfo = requests.get(URL, headers=Headers, verify=False).json()["data"]["bookmark"]
        return BookmarkInfo[0]
    except:
        messagebox.showerror("Error", "Bookmark create failed.")
        raise

def BookmarkDelete(NasIP:str, SId:str, BookmarkId:str):
    '''
    Delete bookamrk.

    @param NasIP: NAS IP
    @param SId: SID
    @param Bookmarkid: bookmark ID
    '''
    URL = f"https://{NasIP}:5001/webapi/SurveillanceStation/ThirdParty/Bookmark/Delete/v1?bookmarkIds=%22{BookmarkId}%22&_sid={SId}"
    Headers = {"accept": "application/json"}
    requests.get(URL, headers=Headers, verify=False)

def BookmarkNameFormatCheck(BookmarkName:str)->str:
    '''
    Cheak if the bookmark name is legal and convert ' ' to '+' to fit the URL rule.

    @param BookmarkName: original bookmark name

    @return None: the bookmark name is illegal
    @return str: the modified bookmark name
    '''
    IllegalChars = "+~!=@#$%^&*()/\|{}[]:'\""
    for i in range(len(BookmarkName)):
        if BookmarkName[i] in IllegalChars:
            return None
        elif BookmarkName[i] == ' ':
            BookmarkName[i] = '+'
    return BookmarkName