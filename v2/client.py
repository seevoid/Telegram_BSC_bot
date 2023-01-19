import zmq
import time
import re
from telethon.sync import TelegramClient, events
from utils import *

context = zmq.Context()

socket = context.socket(zmq.REQ)
socket.connect("tcp://localhost:5555")

client = TelegramClient(session_name, api_id, api_hash)

################# Listen new message in the telegram channel #################
@client.on(events.NewMessage(chats = channelId))
async def new_message_listener(event):
        global BEGIN_TIME
        global BUYING_FINISHED
        global loop
        BEGIN_TIME = time.time()
        text = event.raw_text
        regex = r"0x\S{40}"
        regex1 = r"🔴"
        regex2 = r'[[\bA-Z\b]*]'
        matches = re.findall(regex, text, re.MULTILINE)
        matches1 = re.findall(regex1, text, re.MULTILINE)
        matches2 = re.findall(regex2, text)
        tokenAddress = None
        tokenSymbol = None
        if len(matches) > 0:
                tokenAddress = matches[0]
        if len(matches2) > 0:
                tokenSymbol = matches2[0]

        if tokenSymbol and tokenAddress and matches1:
                if tokenAddress not in token_already_got:
                    messageToSend = "Alert,{tokenAddress},{tokenSymbol}".format(tokenAddress = tokenAddress, tokenSymbol = tokenSymbol)
                    socket.send_string(messageToSend)
                
                token_already_got.append(tokenAddress)
        
        messageToReceive = socket.recv_string()
        if messageToReceive == "OK":
            print("All Good")
        else:
            print("Pas Good")
        
        return
        
################# Start the telegram client #################
client.start()
client.run_until_disconnected()
