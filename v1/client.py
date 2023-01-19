import zmq
import time
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
        message = str(event.message.message)
        message = ' '.join(message.split()).split()
        tokenAddress = ""
        tokenSymbol = ""
        for m in message:
                if len(m) == 42 and m.startswith('0x'):
                        tokenAddress = m.lower()
                if m.startswith('[') and m.endswith(']'):
                        tokenSymbol = m

        if tokenSymbol and tokenAddress:
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
