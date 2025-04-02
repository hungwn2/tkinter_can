import asyncio
import aiohttp
import requests
BASE_URL="http://localhost:8000"
#can change url for this app

def flattenCanMessageObject(messages):
    return [{"frameID":frame_id, **attributes} for frame_id, attributes in messages.items()]

async def uploadFile(file):
    try:
        with open (file_path, "rb") as file:
            response=requests.post(f"{BASE_URL}/upload/db", files={"data": file})
        return response.text
    except excpetion as e:
        print("Failed to upload, "e)
        return None
async def getPreview():
    try:
        response=requests.get(f"{BASE_URL}/view/dbc")
        json_data=response.json()
        return json_data.get("response", [])
    except Exception as e:
        print("fetching files failed", e)  
        return None
def view_files(filename):
    try:
        response = requests.get(f"{BASE_URL}/view/can/{filename}")
        canMessages=requests.json()
        return can_messages.get("response", [])
    except Exception as e:
        print("Fetching file failed",e)
        return None
    
def view_can_messages(filename):
    try:
        response=requests.get(f"{BASE_URL}/view/can/{filename}")
        json_data=response.json()
        return flatten_can_message(json_data.get("response", []))
    except Exception as e:
        print("Fetching CAN messages failed", e)
        return None
    
def transmit_can_messages(frame_id, name, file, signals):
    try:
        response=requests.post(f"{BASE_URL}/transmit", json={
            "frame_id": frame_id,
            "name": name,
            "file": file,
            "signals": signals
        })
        return response.text
    
    except Exception as e:
        print("transmitting CAN message failed retarf", e)
        return None

def change_settings(settings):
    try:
        response=requests.put("http://localhost:8000/change_can_settings");
        json_data=response.json()
        print(json_data)
        return json_data
    except Exception as e:
        print("failed to change settings, ", e)
        return None
def get_settings():
    try:
        response=requests.get(f"{BASE_URL}/get_can_settings")
        return response.json()  
    except Exception as e:
        print("failed to fetch settings ", e)
        return None