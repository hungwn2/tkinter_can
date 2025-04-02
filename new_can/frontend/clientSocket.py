import socketcan
import socketserver
import asyncio
import json
import threading
import tkinter as tk

HOST = "127.0.0.1"

class WebSocketClient:
    def __init__(self, url, text_widget):
        self.url=url
        self.text_widget=text_widget
 
    async def listen_to_websockets():
        with websockets.connect("ws://localhost:") as ws:
            while True:
                try:
                    message=await ws.recv()
                    data=json.loads(message)
                    print(f"Received : {data}")
                    self.text_widget.insert(tk.END, f"{data}\n")
                    self.text_widget.see(tk.END)
                except:
                    break

    def start_websocket_listener(self):
        loop=asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.listen())


root=tk.Tk()
root.title("can wbesockeyt listener")

text_area=scrolledtext.ScrolledText(root, width=80, height=20)
text_area.pack()

client=WebScoketClient("self.url", text_area)
threading.Thread(target=client.strat, daemon=True).start()

root.mainloop()
