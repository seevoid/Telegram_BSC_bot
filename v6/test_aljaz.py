from web3 import Web3
import time
import statistics


bscNode = "wss://speedy-nodes-nyc.moralis.io/93e949fcee05bbb21894f1f0/bsc/mainnet/ws"
web3 = Web3(Web3.WebsocketProvider(bscNode))

measures = []

block_number = web3.eth.block_number
while True:
    if len(measures) > 99:
        break
    start = time.time()
    if block_number != web3.eth.block_number:
        end = time.time()
        measure = end-start
        measures.append(measure)
        print(f"New block in {measure}")
        monitor_transactions = False
    
average = statistics.mean(measures)
print(f"Average time between 2 blocks : {average}")

