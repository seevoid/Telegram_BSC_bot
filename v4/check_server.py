from web3 import Web3, HTTPProvider

bscNode = "http://135.181.223.100:1805"

web3 = Web3(HTTPProvider(bscNode))
# web3 = Web3(Web3.WebsocketProvider(bscNode))

connected = str(web3.isConnected())

print("is connected ? : ", connected)

# "tcp://127.0.0.1:28658"