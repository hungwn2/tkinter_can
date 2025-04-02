# This script recieves CAN data and stores the data on mongodb

from datetime import datetime
import json
import random
import argparse
import sys
import os
import time
import cantools
import can
import requests
import asyncio
import queue



# Disables printing
def blockPrint():
    sys.stdout = open(os.devnull, 'w')

# Restores printing
def enablePrint():
    sys.stdout = sys.__stdout__

parser = argparse.ArgumentParser()
parser.add_argument('-s', action='store_true', help="silence output")
options = parser.parse_args()

client = InfluxDBClient(url="http://localhost:8086", token=token)
write_api = client.write_api(write_options=SYNCHRONOUS)

message_queue=queue
can_channel="vcan0"
can_bustype="socketcan"
can_bitrate=800000
can_dbc_file="system_can.dbc"

can_bus = can.interface.Bus(can_channel, bustype=can_bustype, bitrate=can_bitrate)
db = cantools.database.load_file(can_dbc_file)

# python concurrency leaves much to be desired, so we have to use some 'tricks'
# https://stackoverflow.com/questions/8600161/executing-periodic-actions/20169930#20169930
async def do_every(period, f, *args):
    def g_tick():
        t = time.time()
        while True:
            t += period
            yield max(t - time.time(),0)
    g = g_tick()
    while True:
        time.sleep(next(g))
        f(*args)

async def update_can_settings():
    while True:
        try:
            response = requests.get("http://localhost:8000/get_can_settings")
            r = response.json()
            can_channel = r['channel']
            can_bustype = r['bustype']
            can_bitrate = r['bitrate']
            can_bus = can.interface.Bus(can_channel, bustype=can_bustype, bitrate=can_bitrate)
            await asyncio.sleep(0.01)
        except Exception as e:
            await asyncio.sleep(0.01)

async def decode_and_send():
    while True:
        message = can_bus.recv()
        if message:
            decoded = db.decode_message(message.arbitration_id, message.data)

            msg_info={
                 "timestamp" :str(datetime.fromtimestamp(message.timestamp)),
                 "name" : db.get_message_by_frame_id(message.arbitration_id).name,
                 "sender" : db.get_message_by_frame_id(message.arbitration_id).senders[0],
                 "arbitration_id": hex(message.arbitration_id),
                 "dlc": message.dlc,
                 "hex": message.data.hex(),
                 "bin_data": ''.join(format(byte, '08b')).
                 "dec" : int.from_bytes(message.data, byteorder='big', signed=False), 
                 "decoded_data": decoded
            }
            message_queue.put(msg_info)
            print(msg_info) 
            await asyncio.sleep(0)

async def clear_queue():
    if message_queue.size()>50:

def start_reading():
    loop = asyncio.get_event_loop()
    asyncio.ensure_future(decode_and_send())
    asyncio.ensure_future(update_can_settings())
    loop.run_forever()
