from web3 import Web3
import time

bscNode = "./node/geth.ipc"
previous_progress = 0

web3 = Web3(Web3.IPCProvider(bscNode))
while True:
    block = web3.eth.syncing
    print(str(block))
    # now_block = int(block['currentBlock'])
    # max_block = int(block['highestBlock'])
    # progress = (100 * now_block) / max_block
    # if progress != previous_progress:
        # print(str(round(progress,4)) + "%")
    # previous_progress = progress
    time.sleep(2)