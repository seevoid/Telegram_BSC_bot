from web3 import Web3
import asyncio

bscNode = "wss://little-proud-feather.bsc.quiknode.pro/XXXXXX/"

try:
    globalWeb3 = Web3(Web3.WebsocketProvider(bscNode))
except Exception as e:
    print("e : ", e)

# connected = globalWeb3.isConnected()
# print("Connected : ", connected)
test = asyncio.Lock(globalWeb3.eth.getBlock('latest'))