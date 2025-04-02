import tkinter as tk
from tkinter import ttk, messagebox
import requests
import json

import matplotlib.ply as plt
import pandas as pd

API_BASE_URL = '127.0.0.01'

#idk not done

class CanMonitorApp:
    def __init__(self, root):
        self.root=root
        self.root.title("CAN Explorer (Tkinter)")

    
def fetch_can_data():
    try:
        response = requests.get(f"{API_BASE_URL}/can_data")
        response.raise_for_status()  
        data = response.json()
        update_treeview(data)
    except requests.exceptions.RequestException as e:
        messagebox.showerror("Error", f"Failed to fetch data: {e}")

def update_treeview(data):
    tree.delete(*tree.get_children())
    for item in data:
        tree.insert("", "end", values=(item["id"], item["data"]))

def send_can_message():
    can_id = id_entry.get()
    can_data = data_entry.get()

    try:
        response = requests.post(
            f"{API_BASE_URL}/send_can_message", json={"id": can_id, "data": can_data}
        )
        response.raise_for_status()
        messagebox.showinfo("Success", "CAN message sent successfully.")
    except requests.exceptions.RequestException as e:
        messagebox.showerror("Error", f"Failed to send message: {e}")


tree = ttk.Treeview(root, columns=("ID", "Data"), show="headings")
tree.heading("ID", text="CAN ID")
tree.heading("Data", text="CAN Data")
tree.pack(pady=10)

fetch_button = tk.Button(root, text="Fetch Data", command=fetch_can_data)
fetch_button.pack(pady=5)

id_label = tk.Label(root, text="CAN ID:")
id_label.pack()
id_entry = tk.Entry(root)
id_entry.pack()

data_label = tk.Label(root, text="CAN Data:")
data_label.pack()
data_entry = tk.Entry(root)
data_entry.pack()

send_button = tk.Button(root, text="Send CAN Message", command=send_can_message)
send_button.pack(pady=5)

root.mainloop()