from telethon.sync import TelegramClient, events
session_name = "test_chhanel"
api_id = 8956213
api_hash = "XXXXXX"

channelId = ["https://t.me/CMC_fastest_alerts", "https://t.me/CG_fastest_alerts", "https://t.me/mumusgems"]

client = TelegramClient(session_name, api_id, api_hash)

@client.on(events.NewMessage(chats = channelId))
async def new_message_listener(event):
    print("event : ", event)

################# Start the telegram client #################
client.start()
client.run_until_disconnected()