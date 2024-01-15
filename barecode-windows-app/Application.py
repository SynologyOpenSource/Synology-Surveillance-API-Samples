# -*- coding: UTF-8 -*-
import tkinter as tk
import tkinter.ttk as ttk
from tkinter import filedialog, messagebox
from BookmarkLibrary import SIDGet, CameraListGet
import BookmarkDatabase
from BarcodeScan import CreateModeScan, DownloadModeScan

def ClearFrame():
    '''
    This function is used to clear all widgets in window.
    '''
    for widget in Window.winfo_children():
        widget.destroy()

def SwitchMode():
    '''
    This function is used to switch the mode of creating bookmark and download video.
    '''
    global CREATEMODE
    if CREATEMODE:
        CREATEMODE = False
        ClearFrame()
        BookmarkDownloadMode()
    else:
        CREATEMODE = True
        ClearFrame()
        BookmarkCreateMode()
    tk.Label(Window, text="Download/Create mode")
    SwitchButton = tk.Button(Window, command=SwitchMode, text="Switch mode")
    SwitchButton.grid(row=1, column=1, sticky='w')

def PathChoose(PathLabel:tk.Label):
    '''
    This function offer direction choose window for user.

    @param PathLabel: Label object that make the text of the label changeable.  
    '''
    global FOLDERPATH
    FOLDERPATH = filedialog.askdirectory()
    if (len(FOLDERPATH)<=2) :FOLDERPATH="./"
    PathLabel["text"] = FOLDERPATH
    
def CamListSimplify()->list[str]:
    '''
    Return camera info string for camera choosing mean used.

    @return list of camera info strings
    '''
    CamInfo = CameraListGet(NASIP, SID)
    SimpCamInfo = list()
    for Cam in CamInfo:
        SimpCamInfo.append(str(Cam["camId"])+'/'+Cam["name"]+'/'+Cam["ip"])
    return SimpCamInfo

def BookmarkDownloadMode():
    '''
    Create bookmark video download mode window
    '''
    Frame = ttk.Frame(Window)
    Frame.place(relx=0.5, rely=0.5, anchor="center")
    FilenameVar = tk.StringVar()
    FilenameVar.set("NewFile")
    PathLabel = tk.Label(Frame, text=FOLDERPATH, wraplength=150)
    PathLabel.grid(row=3, column=2)
    FilanameEntry = ttk.Entry(Frame, textvariable=FilenameVar)
    FilanameEntry.grid(row=4, column=2)
    PathChooseButton = tk.Button(Frame, width=12, text="Choose folder", command=lambda:PathChoose(PathLabel))
    PathChooseButton.grid(row=3, column=3)
    ScanStartButton = tk.Button(Frame, width=12, text="Start scan", command=lambda:DownloadModeScan(NASIP, SID, BookmarkDB, FOLDERPATH, FilenameVar.get()))
    ScanStartButton.grid(row=4, column=3)
    
def BookmarkCreateMode():
    '''
    Create bookmark creating mode window 
    '''
    MainFrame = ttk.Frame(Window)
    MainFrame.place(relx=0.5, rely=0.5, anchor="center")
    DateFrame = ttk.Frame(MainFrame)
    DateFrame.grid(row=2, column=1, sticky='w')
    ComAndButtonFrame = ttk.Frame(MainFrame)
    ComAndButtonFrame.grid(row=3, column=1, sticky='w')
    ttk.Label(DateFrame, text="Start Time:").grid(row=2, column=1, sticky='w')
    ttk.Label(DateFrame, text="End Time:").grid(row=3, column=1, sticky='w')
    ttk.Label(ComAndButtonFrame, text="Comment:").grid(row=5, column=1, sticky='w')
    ttk.Label(ComAndButtonFrame, text="Camera(Id/Name/IP):").grid(row=5, column=5, sticky='w', columnspan=3)
    Unit = ["Y", "M", "D", "h", "m", "s"]
    for i in range(6):
        ttk.Label(DateFrame, text=Unit[i]).grid(row=1, column=2+i)
    StartTimeEntry = [ttk.Entry(DateFrame, width=4) for _ in range(6)]
    EndTimeEntry = [ttk.Entry(DateFrame, width=4) for _ in range(6)]
    for i in range(6):
        StartTimeEntry[i].grid(row=2, column=2+i, sticky='w')
    for i in range(6):
        EndTimeEntry[i].grid(row=3, column=2+i, sticky='w')
    ComEntry = tk.Text(ComAndButtonFrame, width=14, height=2.5)
    ComEntry.grid(row=5, column=2, columnspan=3, rowspan=2)
    CamInfo = CamListSimplify()
    Cam = tk.StringVar()
    Cam.set(CamInfo[0])
    CamMeau = ttk.OptionMenu(ComAndButtonFrame, Cam, CamInfo[0], *CamInfo)
    CamMeau.grid(row=6, column=5, columnspan=3)
    BookmarkCreatButton = tk.Button(ComAndButtonFrame, text="Start Scan", \
                              command=lambda:CreateModeScan(NASIP, SID, BookmarkDB, Cam.get(), [StartTimeEntry[i].get() for i in range(6)], \
                                                      [EndTimeEntry[i].get() for i in range(6)], ComEntry.get('1.0', 'end')))
    BookmarkCreatButton.grid(row=7, column=6)

def SignIn(NasIP:str, Account:str, Password:str):
    '''
    Sign in and set the SId.

    @param NasIP: NAS IP string
    @param Account: NAS account
    @param Password: NAS password
    '''
    global NASIP, SID
    try:
        SID = SIDGet(NasIP, Account, Password)
        NASIP = NasIP
    except:
        messagebox.showerror("Error", "Wrong NAS IP, Account or Password")
        return
    ClearFrame()
    BookmarkCreateMode()
    tk.Label(Window, text="Download/Create mode")
    SwitchButton = tk.Button(Window, command=SwitchMode, text="Switch mode")
    SwitchButton.grid(row=1, column=1, sticky='w')

def SignInPage():
    '''
    Create sign in window.
    '''
    Frame = ttk.Frame(Window)
    Frame.place(relx=0.5, rely=0.5, anchor="center")
    ttk.Label(Frame, text="Account: ").grid(row=2, column=2, sticky='w')
    ttk.Label(Frame, text="Password: ").grid(row=3, column=2, sticky='w')
    ttk.Label(Frame, text="NAS IP: ").grid(row=1, column=2, sticky='w')
    NasIPEntry = ttk.Entry(Frame)
    NasIPEntry.grid(row=1, column=3)
    AccountEntry = ttk.Entry(Frame)
    AccountEntry.grid(row=2, column=3)
    PasswordEntry = ttk.Entry(Frame, show="*")
    PasswordEntry.grid(row=3, column=3)
    ttk.Button(Frame, text="Sign in", command=lambda:SignIn(NasIPEntry.get(), AccountEntry.get(), PasswordEntry.get())).grid(row=4, column=3)
    Window.bind("<Return>", lambda e:SignIn(NasIPEntry.get(), AccountEntry.get(), PasswordEntry.get()))

if  __name__ == '__main__':
    Window = tk.Tk()
    Window.title("Surveillance barcode scanner")
    Window.geometry("400x200")
    CREATEMODE = True
    FOLDERPATH = "./"
    NASIP = ""
    SID = ""
    BookmarkDB = BookmarkDatabase.BookmarkDB()
    SignInPage()
    Window.mainloop()