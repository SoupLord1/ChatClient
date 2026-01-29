import threading
import time
from tkinter import *
import tkinter.font as TkFont
import json
import websocket
from functools import partial
import math

root = Tk()
root.title("Soup Chat")
root.configure(background="orange")
root.minsize(1200,600)

#https://websocket-client.readthedocs.io/en/latest/examples.html#dispatching-multiple-websocketapps

WEBSOCKET_URL: str = "ws://5.78.46.132/soupchat"
wsapp: websocket.WebSocketApp = None


def processMessage(username: str, message: str):
        MAXCHARS = 50

        totalSubs: int = math.floor(len(message) / MAXCHARS)

        if (len(message) % MAXCHARS != 0):
            totalSubs+=1


        substrings = []

        for i in range(totalSubs):
            substrings.append(message[i*MAXCHARS:(i+1)*MAXCHARS])

        tFrame = Frame(screenManager.screens.get("chat").scrollFrame.scrollable_frame)
        tFrame.pack(anchor="w")
        Label(tFrame, text=f"{username}", font=("Arial", 20, "bold")).pack(side=LEFT)


        for string in substrings:
            tFrame = Frame(screenManager.screens.get("chat").scrollFrame.scrollable_frame)
            tFrame.pack(anchor="w")
            Label(tFrame, text=f"{string}", font=("Arial", 20)).pack(side=LEFT)

        screenManager.screens.get("chat").scrollFrame.canvas.update_idletasks()
        screenManager.screens.get("chat").scrollFrame.canvas.yview_moveto('1.0')

class wsRequest():
    wsapp: websocket.WebSocket = None
    def __init__(self, wsapp):
        self.wsapp = wsapp

    def get_chats(self):
        if (wsapp == None):
            return

        payload = {
            'request': 'get_chats'
        }
        jsonPayload = json.dumps(payload)
        wsapp.send(jsonPayload)
        print(payload)

    def host(self, name: str, username: str, slots: int):
        if (wsapp == None):
            return
        
        payload = {
            "request": "host_room",
            "name": name, 
            "username": username, 
            "slots": slots
        }

        jsonPayload = json.dumps(payload)
        wsapp.send(jsonPayload)

    def join(self, name:str, username: str):
        if (wsapp == None):
            return
        
        self.set_username(username)
        
        payload = {
            "request": "join_room", 
            "name": name, 
            "username": username
        }

        jsonPayload = json.dumps(payload)
        wsapp.send(jsonPayload)

    def leave(self):
        if (wsapp == None):
            return
        payload = {
            "request": "leave_room", 
        }

        jsonPayload = json.dumps(payload)
        wsapp.send(jsonPayload)

    def send_chat(self, message):
        if (wsapp == None):
            return
        
        payload = {
            "request": "send_message", 
            "message": message
        }

        jsonPayload = json.dumps(payload)
        wsapp.send(jsonPayload)

    def set_username(self, username: str):
        if (wsapp == None):
            return
        payload = {
            "request": "set_username", 
            "username": username, 
        }

        jsonPayload = json.dumps(payload)
        wsapp.send(jsonPayload)
    
requester: wsRequest = None

class websocket_controller():
        
    def start(self):
        global wsapp
        wsapp = websocket.WebSocketApp(WEBSOCKET_URL, on_message=on_message, on_open=on_open, on_close=on_close, on_error=on_error)
        wsapp.run_forever()
    
websocket_controller1 = websocket_controller()

websocket_thread = threading.Thread(target=websocket_controller1.start, daemon=True)

def on_message(wsapp: websocket.WebSocketApp, message):
    
    payload: dict = json.loads(message)
    request: str = payload.get("request")

    if request == "host_failed":
        errorLabel: Label = screenManager.screens.get("host").errorLabel
        errorLabel.config(text=f"Error: {payload.get('reason')}")
        pass

    if request == "send_chats":
        try:
            chatsOnlineLabel:Label = screenManager.screens.get("menu").chatsOnlineLabel

            chatRooms: list = payload.get("payload")
            chatsOnlineLabel.config(text=f"Chats Online: {len(chatRooms)}")

            for child in screenManager.screens.get("join").scrollFrame.scrollable_frame.winfo_children():
                child.destroy()

            for chat in chatRooms:
                chatName = chat.get('name')
                partialJoin = partial(screenManager.screens.get("join").joinButtonClicked, chatName)
                tFrame = Frame(screenManager.screens.get("join").scrollFrame.scrollable_frame)
                Label(tFrame, text=f"{chatName}: {chat.get('totalConnections')}/{chat.get('maxConnections')}", font=("Arial", 20)).pack(side=LEFT)
                button = Button(tFrame, text=f"Join", font=("Arial", 20), command=partialJoin)
                button.pack(side=LEFT, padx= 10)
                tFrame.pack(side=TOP)
                

        except Exception as e:
            print(e)

    if request == "send_message":
        processMessage(payload.get("username"), payload.get("message"))


def on_open(wsapp: websocket.WebSocketApp):

    global requester
    connectedLabel:Label = screenManager.screens.get("menu").connectedLabel
    connectedLabel.config(text="Connected!")
    requester = wsRequest(wsapp)
    requester.get_chats()

def on_close(wsapp: websocket.WebSocketApp, close_status_code, close_msg):
    with open("error_log.txt", "+a") as file:
        file.write(f"Status code: {close_status_code} Msg: {close_msg}\n")
    time.sleep(5)
    wsapp.run_forever()

def on_error(wsapp: websocket.WebSocketApp, error):
    with open("error_log.txt", "+a") as file:
        file.write(f"Error: {error}\n")

buttonFont = TkFont.Font(family="Arial", size=20, weight="bold")

#not mine lol https://blog.teclado.com/tkinter-scrollable-frames/
class ScrollableFrame(Frame):
    def __init__(self, container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        self.canvas = Canvas(self)
        scrollbar = Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")

        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

class Screen():
    screen: Frame
    def __init__(self, root):
        self.screen = Frame(root)

class ScreenManager():
    currentScreen: str 
    screens: dict
    root: Tk
    def __init__(self, root: Tk):
        self.screens = {}
        self.screens.update({"menu": MenuScreen(root)})
        self.screens.update({"join": JoinScreen(root)})
        self.screens.update({"host": HostScreen(root)})
        self.screens.update({"chat": ChatScreen(root)})
        self.root = root
        self.currentScreen = "menu"
        self.screens.get(self.currentScreen).screen.pack(fill=BOTH, expand=True, padx= 10, pady= 10)


    def changeScreen(self, screen: str):
        self.screens.get(self.currentScreen).screen.pack_forget()
        self.currentScreen = screen
        self.screens.get(self.currentScreen).screen.pack(fill=BOTH, expand=True, padx= 10, pady= 10)

class MenuScreen(Screen): 
    def __init__(self, root: Tk):
        super().__init__(root)
        self.screen = Frame(root)
        title: Label = Label(self.screen, text="Menu", font=("Arial", 25))
        title.pack()
        self.connectedLabel = Label(self.screen, text="Connecting...", font=("Arial", 20))
        self.connectedLabel.pack()
        self.chatsOnlineLabel = Label(self.screen, text=f"Chats Online: 0", font=("Arial", 20))
        self.chatsOnlineLabel.pack()
        hostButton = Button(self.screen, text="Host", command=self.hostButtonClicked, width=5, height=1, font=buttonFont)
        hostButton.pack()
        joinButton = Button(self.screen, text="Join", command=self.joinButtonClicked, width=5, height=1, font=buttonFont)
        joinButton.pack()

    def hostButtonClicked(self):
        screenManager.changeScreen("host")


    def joinButtonClicked(self):
        screenManager.changeScreen("join")

class JoinScreen(Screen):
    def __init__(self, root: Tk):
        super().__init__(root)
        title: Label = Label(self.screen, text="Join", font=("Arial", 25))
        title.pack(side=TOP)

        self.scrollFrame = ScrollableFrame(self.screen)


        self.scrollFrame.pack(expand=True, fill=BOTH, padx=10, pady=10)

        menuButton = Button(self.screen, text="Menu", command=self.menuButtonClicked, width=5, height=1, font=buttonFont)
        menuButton.pack(side=BOTTOM)

        usernameFrame = Frame(self.screen)
        Label(usernameFrame, text="Username: ", font=("Arial", 15)).pack(side=LEFT)
        self.usernameEntry = Entry(usernameFrame, width=40, font=("Arial", 15))
        self.usernameEntry.pack(side=LEFT)
        usernameFrame.pack()

    def menuButtonClicked(self):
        screenManager.changeScreen("menu")
        requester.get_chats()

    def joinButtonClicked(self, room:str):
        if (self.usernameEntry.get() == ""):
            return
        requester.join(room, self.usernameEntry.get())
        screenManager.changeScreen("chat")
        screenManager.screens.get("chat").username = self.usernameEntry.get()

        screenManager.screens.get("chat").title.config(text=f"Chat - {room}")

class HostScreen(Screen):
    def __init__(self, root):
        super().__init__(root)
        title: Label = Label(self.screen, text="Host", font=("Arial", 25))
        title.pack(side=TOP)

        Label(self.screen, text="Name",font=("Arial", 20)).pack()
        self.nameEntry = Entry(self.screen, width=40, font=("Arial", 15))
        self.nameEntry.pack()
        Label(self.screen, text="Username",font=("Arial", 20)).pack()
        self.usernameEntry = Entry(self.screen, width=40, font=("Arial", 15))
        self.usernameEntry.pack()
        Label(self.screen, text="Slots",font=("Arial", 20)).pack()
        self.slotsSpinBox = Spinbox(self.screen, from_=4, to=50, width= 30, font=("Arial", 15))
        self.slotsSpinBox.pack()

        self.errorLabel = Label(self.screen, text="", font=("Arial", 15))
        self.errorLabel.pack()

        hostButton = Button(self.screen, text="Host", command=self.hostButtonClicked, width=5, height=1, font=buttonFont)
        hostButton.pack()

        menuButton = Button(self.screen, text="Menu", command=self.menuButtonClicked, width=5, height=1, font=buttonFont)
        menuButton.pack(side=BOTTOM)
        
    def menuButtonClicked(self):
        screenManager.changeScreen("menu")
        requester.get_chats()
    
    def hostButtonClicked(self):
        if (self.nameEntry.get() == "" or self.usernameEntry.get() == ""):
            return
        requester.host(self.nameEntry.get(), self.usernameEntry.get(), self.slotsSpinBox.get())
        screenManager.changeScreen("chat")
        screenManager.screens.get("chat").username = self.usernameEntry.get()
        screenManager.screens.get("chat").title.config(text=f"Chat - {self.nameEntry.get()}")

class ChatScreen(Screen):
    def __init__(self, root):
        super().__init__(root)
        self.title: Label = Label(self.screen, text="Chat", font=("Arial", 25))
        self.title.pack(side=TOP)
        self.scrollFrame = ScrollableFrame(self.screen)
        self.scrollFrame.pack(fill=BOTH, expand=True, padx=20, pady=20)

        self.username = "User"
        
        messageFrame = Frame(self.screen)
        messageFrame.pack()
        Label(messageFrame, text="MESSAGE: ", font=buttonFont).pack(side=LEFT)
        self.messageEntry = Entry(messageFrame, width=40, font=buttonFont)
        self.messageEntry.pack(side=LEFT)
        Button(messageFrame, text="Send", font=buttonFont, command=self.messageButtonClicked).pack(padx=5, side=LEFT)
        Button(messageFrame, text="LEAVE", font=buttonFont, command=self.leaveButtonClicked).pack(padx=5, side=LEFT)
        
        self.scrollFrame.canvas.update_idletasks()
        self.scrollFrame.canvas.yview_moveto('1.0')

    def messageButtonClicked(self):
        if (self.messageEntry.get().strip(" ") == ""):
            return
        requester.send_chat(self.messageEntry.get())
        processMessage(self.username, self.messageEntry.get())
        self.messageEntry.delete(0, END)

    def leaveButtonClicked(self):
        requester.leave()
        screenManager.changeScreen("menu")
        requester.get_chats()
        for child in self.scrollFrame.scrollable_frame.winfo_children():
            child.destroy()

screenManager: ScreenManager = ScreenManager(root)

websocket_thread.start()
root.mainloop()