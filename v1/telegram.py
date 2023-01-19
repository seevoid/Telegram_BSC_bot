import os
import sys
import time
import threading
import asyncio
from web3 import Web3
from pythonpancakes import PancakeSwapAPI
import zmq

from utils import *

context = zmq.Context()
socket = context.socket(zmq.REP)
socket.bind("tcp://*:5555")

clearConsole = lambda: os.system('cls' if os.name in ('nt', 'dos') else 'clear')
clearConsole()

print(NAME_OF_BOT_FOR_DISPLAY)
print("\n")

print("{color}Telegram Channel: {channel}".format(color = bcolors.OKBLUE, channel = channelId))

################# Init all the stuff #################
if MUSIC_ALERT:
        print("{color}Music Alert: {alert}".format(color = bcolors.OKBLUE, alert = "ON"))
        from pygame import mixer 
        mixer.init()
        mixer.music.load("./song.mp3")
else:
        print("{color}Music Alert: {alert}".format(color = bcolors.OKBLUE, alert = "OFF"))


globalWeb3 = Web3(Web3.WebsocketProvider(bscNode))

################# Global variables #################
BNBTokenAddress = Web3.toChecksumAddress("0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c")
GLOBAL_PROGRESSION = 0
if MAIL_ALERT:
        print("{color}Mail Alert: {alert}".format(color = bcolors.OKBLUE, alert = "ON"))
        EMAIL = "martin.baty@gmail.com"
        SUBJECT = "NEW BUY - CMC ALERT"
        CONTENT = "New token bought : ${symbol} : {address}"
else:
        print("{color}Mail Alert: {alert}".format(color = bcolors.OKBLUE, alert = "OFF"))


################# Remove the file oof the previous telegram session if exist #################
# os.chdir(sys.path[0])
# if "{session_name}.session".format(session_name = session_name) in os.listdir():
#         os.remove("{session_name}.session".format(session_name = session_name))

################# Print BNB Balance #################
def get_balance_bnb():
        balance = globalWeb3.eth.get_balance(walletAddress)
        humanReadable = globalWeb3.fromWei(balance,'ether')
        return humanReadable
print("\n")
print("{color}##".format(color = bcolors.OKGREEN))
print("{color}###### BNB Balance: {balance} BNB".format(color = bcolors.OKGREEN, balance = str(round(get_balance_bnb(), 4))))
print("{color}##".format(color = bcolors.OKGREEN))
print("\n")


################# Function to buy the token #################


################# Class (Thread) to monitor the token price and sell when condition is reached #################
class TokenMonitor (threading.Thread):
        def __init__(self, tokenAddress, tokenSymbol):
                threading.Thread.__init__(self)
                self.tokenAddress = tokenAddress
                self.tokenSymbol = tokenSymbol
                self.buyPrice = None
                self.web3Thread = Web3(Web3.WebsocketProvider(bscNode))
                self.price = 0
                self.progression = 0
                self.stop = False
                self.step_sell = 1.1
                self.previous_step_sell = float('-inf')
                self.listStep = [1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 2]
                self.buy()
                

        def run(self):
                if TEST_SELL:
                        self.sell()
                elif self.buyPrice is None:
                        pass
                elif self.buyingSucceed:
                        while(not self.stop):
                                try:
                                        self.price = self.getTokenPrice(self.tokenAddress)
                                except Exception as e:
                                        print("{color}[MONITOR] Error when get price in loop thread !".format(color = bcolors.FAIL))
                                        print("e: {e}".format(e = str(e)))
                        
                                if self.previous_step_sell != float('-inf'):
                                        if self.price < (self.previous_step_sell * self.buyPrice):
                                                print("{color}[MONITOR] Sell for step {step} for {symbol} : {address}".format(color = bcolors.OKGREEN, step = str(self.previous_step_sell), \
                                                        symbol = self.tokenSymbol, address = self.tokenAddress))
                                                self.sell()

                                if (self.price > (self.buyPrice * self.step_sell)):
                                        self.getStep()
                                        
                                        print("{color}[MONITOR] Multiplier {step} successfully passed for {symbol} : {address} ! Will sell if price > {sellingPrice1} or price < {sellingPrice2}".\
                                                format(color = bcolors.OKCYAN, step = str(self.previous_step_sell), symbol = self.tokenSymbol, address = self.tokenAddress, \
                                                        sellingPrice1 = str(round(self.buyPrice * self.step_sell, 4)),\
                                                        sellingPrice2 = str(round(self.buyPrice * self.previous_step_sell, 4))))
                                        if self.step_sell == 2:
                                                self.sell()
                                
                                if (self.price <= self.buyPrice * lowThresholdSell):
                                        print("{color}[MONITOR] Sell because lowThresholdSell reached for {symbol} : {address}".format(color = bcolors.FAIL, \
                                                symbol = self.tokenSymbol, address = self.tokenAddress))
                                        self.sell()

                                time.sleep(2)
                                        

        def getStep(self):
                for s in self.listStep:
                        if self.price > (self.buyPrice * s) and self.price < (self.buyPrice * (s+1)):
                                self.step_sell = s+1
                                self.previous_step_sell = s

        def getPair(self, tokenAddress):
                tokenAddress = self.web3Thread.toChecksumAddress(tokenAddress)
                contract = self.web3Thread.eth.contract(address=pancakeSwapFactoryAddress, abi=listeningABI)
                pairAddress = contract.functions.getPair(WBNBAdress, tokenAddress).call()
                return pairAddress

        def getReserves(self, pairAddressforReserves):  # fundamental code for liquidity detection
                pairAddressforReserves = self.web3Thread.toChecksumAddress(pairAddressforReserves)
                router = self.web3Thread.eth.contract(address=pairAddressforReserves, abi=pairABI)
                pairReserves = router.functions.getReserves().call()
                token0 = router.functions.token0().call()
                token1 = router.functions.token1().call()
                return pairReserves, token0, token1

        def getTokenPrice(self, tokenAddress):
                pancake = PancakeSwapAPI()
                pairAddress = self.getPair(tokenAddress)
                pairReserves, token0, token1 = self.getReserves(pairAddress)
                BNBReserve = 0
                TokenReserve = 0

                if token0 == WBNBAdress:
                        BNBReserve = pairReserves[0]
                        TokenReserve = pairReserves[1]
                else:
                        BNBReserve = pairReserves[1]
                        TokenReserve = pairReserves[0]

                BNBPrice = pancake.tokens(WBNBAdress)
                BNBPrice = BNBPrice["data"]["price"]
                BNBPrice = float(BNBPrice)
                tokenPrice = (BNBPrice * BNBReserve) / TokenReserve

                return tokenPrice

        def buy(self):
                global END_TIME
                global BEGIN_TIME
                try:
                        if(self.tokenAddress != None):
                                print("{color}[BUY] Buying {symbol} ({address}) for {amount} BNB".format(color = bcolors.OKCYAN, symbol = self.tokenSymbol, address = self.tokenAddress, amount = snipeBNBAmount))
                                tokenToBuy = self.web3Thread.toChecksumAddress(self.tokenAddress)
                                contract = self.web3Thread.eth.contract(address=pancakeSwapRouterAddress, abi=pancakeABI)
                                nonce = self.web3Thread.eth.get_transaction_count(walletAddress)
                                pancakeswap2_txn = contract.functions.swapExactETHForTokensSupportingFeeOnTransferTokens(
                                        0, # Set to 0 or specify min number of tokens - setting to 0 just buys X amount of tokens for whatever BNB specified
                                        [BNBTokenAddress,tokenToBuy],
                                        walletAddress,
                                        (int(time.time()) + transactionRevertTimeSeconds)
                                        ).buildTransaction({
                                        'from': walletAddress,
                                        'value': self.web3Thread.toWei(float(snipeBNBAmount), 'ether'),
                                        'gas': gasAmount,
                                        'gasPrice': self.web3Thread.toWei(gasPrice,'gwei'),
                                        'nonce': nonce,
                                })

                                #Create token Instance for Token
                                sellTokenContract = self.web3Thread.eth.contract(tokenToBuy, abi=sellAbi)
                                try:
                                        signed_txn = self.web3Thread.eth.account.sign_transaction(pancakeswap2_txn, walletPrivateKey)
                                        tx_token = self.web3Thread.eth.send_raw_transaction(signed_txn.rawTransaction) #BUY THE TOKEN
                                        response = self.web3Thread.eth.wait_for_transaction_receipt(transaction_hash=tx_token, timeout=15, poll_latency=0.1)
                                        if response["status"] == 1:
                                                END_TIME = time.time()
                                                self.buyingSucceed = True
                                        else:
                                                self.buyingSucceed = False

                                        self.buyPrice = self.getTokenPrice(self.tokenAddress)
                                except Exception as ex:
                                        self.buyPrice = None
                                        print("{color}[BUY] FAILED when buying {symbol} | Error: {error}s".format(color = bcolors.FAIL, symbol = self.tokenSymbol, error = str(ex)))

                                if self.buyingSucceed:
                                        try:
                                                print("{color}[BUY] Time between alert and buy : {time}s".format(color = bcolors.OKCYAN, time = str(round((END_TIME - BEGIN_TIME),2))))
                                                print("{color}[BUY] Buy Price: {price}".format(color = bcolors.OKCYAN, price = str(self.buyPrice)))
                                                print("{color}[BUY] Low threshold: {low}".format(color = bcolors.OKCYAN, low=str(self.buyPrice*lowThresholdSell)))
                                        except Exception as e:
                                                print("e: ", str(e))
                                
                                #Get Token Balance
                                balance = sellTokenContract.functions.balanceOf(walletAddress).call()
                                readable = self.web3Thread.fromWei(balance,'ether')
                                if self.buyingSucceed:
                                        print("{color}[BUY] Successfully bought $".format(color = bcolors.OKGREEN) + self.tokenSymbol + " for " + str(snipeBNBAmount) + " BNB || Adress : " + tokenAddress)
                                        if MUSIC_ALERT:
                                                mixer.music.play()
                                                time.sleep(10)
                                                mixer.music.stop()

                                        # Check if it's already approved
                                        _owner = self.web3Thread.toChecksumAddress(walletAddress)
                                        _spender = self.web3Thread.toChecksumAddress(pancakeSwapRouterAddress)
                                        try:
                                                abi = [{"constant":True,"inputs":[{"name":"_owner","type":"address"},{"name":"_spender","type":"address"}],"name":"allowance","outputs":[{"name":"","type":"uint256"}],"payable":False,"stateMutability":"view","type":"function"},]
                                                contract = self.web3Thread.eth.contract(address=tokenToBuy, abi=abi)
                                                resultApproved = contract.functions.allowance(_owner, _spender).call()
                                        except Exception as e:
                                                print("{color}[BUY] Error when trying to know if it's approved or not | Error: {error}.".format(color = bcolors.FAIL, error = str(e)))
                                        print("resultApproved : ", resultApproved)
                                        if int(resultApproved) == 0:
                                                # Approve token for future selling
                                                try:
                                                        approve = sellTokenContract.functions.approve(pancakeSwapRouterAddress, balance).buildTransaction({
                                                                'from': walletAddress,
                                                                'gasPrice': self.web3Thread.toWei(gasPrice,'gwei'),
                                                                'nonce': self.web3Thread.eth.get_transaction_count(walletAddress),
                                                                })

                                                        signed_txn = self.web3Thread.eth.account.sign_transaction(approve, private_key=walletPrivateKey)
                                                        tx_token = self.web3Thread.eth.send_raw_transaction(signed_txn.rawTransaction)
                                                        print("{color}[BUY] Approved Token {symbol} for future selling".format(color = bcolors.OKGREEN, symbol = self.tokenSymbol))
                                                        print("{color}[MONITOR] Start monitoring the price".format(color = bcolors.OKCYAN))
                                                        print("\n")
                                                        print("{color}---------------------------------------------------------------------------------------".format(color = bcolors.HEADER))
                                                        print("\n")
                                                        
                                                except Exception as e:
                                                        print("{color}[BUY] FAILED when approving {symbol} | Error: {error}".format(color = bcolors.FAIL, symbol = self.tokenSymbol, error = str(e)))
                                                        print("\n")
                                                        print("{color}---------------------------------------------------------------------------------------".format(color = bcolors.HEADER))
                                                        print("\n")
                                        else:
                                                print("{color}[BUY] Token {symbol} already approved for future selling".format(color = bcolors.OKGREEN, symbol = self.tokenSymbol))
                                                print("{color}[MONITOR] Start monitoring the price".format(color = bcolors.OKCYAN))
                                                print("\n")
                                                print("{color}---------------------------------------------------------------------------------------".format(color = bcolors.HEADER))
                                                print("\n")
                                else:
                                        print("{color}[BUY] FAILED when bought $".format(color = bcolors.FAIL) + self.tokenSymbol + " for " + str(snipeBNBAmount) + " BNB || Adress : " + tokenAddress)
                                        print("\n")
                                        print("{color}---------------------------------------------------------------------------------------".format(color = bcolors.HEADER))
                                        print("\n")

                except Exception as ex:
                        print("{color}[BUY] Transaction failed: likely not enough gas.".format(color = bcolors.FAIL))
                        print("{color}[BUY] FAILED when bought: {error}".format(color = bcolors.FAIL, error = str(ex)))
                        print("\n")
                        print("{color}---------------------------------------------------------------------------------------".format(color = bcolors.HEADER))
                        print("\n")

        def sell(self):
                global GLOBAL_PROGRESSION

                contract_id = self.web3Thread.toChecksumAddress(self.tokenAddress)
                contract = self.web3Thread.eth.contract(address=pancakeSwapRouterAddress, abi=pancakeABI)
                sellTokenContract = self.web3Thread.eth.contract(contract_id, abi=sellAbi)

                #Get Token Balance
                balance = sellTokenContract.functions.balanceOf(walletAddress).call()
                readable = self.web3Thread.fromWei(balance,'ether')
                print("{color}[SELL] Balance of {symbol}: {balance}".format(color = bcolors.OKCYAN, symbol = self.tokenSymbol, balance = str(readable)))

                tokenAmount = float(readable)
                tokenValue = self.web3Thread.toWei(tokenAmount, 'ether')

                #Approve Token before Selling
                tokenValue2 = self.web3Thread.fromWei(tokenValue, 'ether')

                print(f"{bcolors.OKCYAN}[SELL] Swapping {tokenValue2} {self.tokenSymbol} for BNB")

                sellSucceed = False
                #Create token Instance for Token
                sellTokenContract = self.web3Thread.eth.contract(contract_id, abi=sellAbi)
                balanceBeforeSell = get_balance_bnb()

                try:
                        #Swaping exact Token for ETH 
                        pancakeswap2_txn = contract.functions.swapExactTokensForETHSupportingFeeOnTransferTokens(
                                tokenValue ,SLIPPAGE_SELL, 
                                [contract_id, BNBTokenAddress],
                                walletAddress,
                                (int(time.time()) + 1000000)
                                ).buildTransaction({
                                'from': walletAddress,
                                'gasPrice': self.web3Thread.toWei(gasPrice,'gwei'),
                                'nonce': self.web3Thread.eth.get_transaction_count(walletAddress),
                                })
                        
                        signed_txn = self.web3Thread.eth.account.sign_transaction(pancakeswap2_txn, private_key=walletPrivateKey)
                        tx_token = self.web3Thread.eth.send_raw_transaction(signed_txn.rawTransaction)
                        response = self.web3Thread.eth.wait_for_transaction_receipt(transaction_hash=tx_token, timeout=30, poll_latency=0.1)
                        if response["status"] == 1:
                                sellSucceed = True
                        else:
                                sellSucceed = False
                except Exception as e:
                        if MAIL_ALERT:
                                mail = Mail()
                                content = "$" + self.tokenSymbol + " : " + self.tokenAddress
                                mail.send(EMAIL, content, content)
                        print("{color}[SELL] FAILED when selling {symbol} : {address} !".format(color = bcolors.FAIL, symbol = self.tokenSymbol, address = self.tokenAddress))
                        print("{color}[SELL] ERROR: {error}".format(color = bcolors.FAIL, error = str(e)))
                        self.stop = True
                        return

                balanceAfterSell = get_balance_bnb()
                self.progression = balanceAfterSell - balanceBeforeSell

                if sellSucceed:
                        print("{color}[SELL] Successfully Sold {symbol} : {address} at step {step}".format(color = bcolors.OKGREEN, symbol = self.tokenSymbol,\
                         address = self.tokenAddress, step = str(self.previous_step_sell)))
                else:
                        if MAIL_ALERT:
                                mail = Mail()
                                content = "$" + self.tokenSymbol + " : " + self.tokenAddress
                                mail.send(EMAIL, content, content)
                        print("{color}[SELL] FAILED when selling {symbol} : {address} !".format(color = bcolors.FAIL, symbol = self.tokenSymbol, address = self.tokenAddress))
                GLOBAL_PROGRESSION = GLOBAL_PROGRESSION + self.progression
                print("{color}### Token Progression : {progression}".format(color = bcolors.OKCYAN, progression = round(self.progression, 4)))
                print("{color}### GLOBAL PROGRESSION : {progression}".format(color = bcolors.BOLD, progression = round(GLOBAL_PROGRESSION, 4)))
                print("{color}###".format(color = bcolors.OKCYAN))
                print("{color}###### BNB Balance: {balance} BNB".format(color = bcolors.OKCYAN, balance = str(round(get_balance_bnb(), 4))))
                print("{color}###".format(color = bcolors.OKCYAN))
                print("\n")
                print("{color}---------------------------------------------------------------------------------------".format(color = bcolors.HEADER))
                print("\n")
                self.stop = True

    
while True:
        #  Wait for next request from client
        message = socket.recv_string()
        if message == "Connected":
                print("Client well connected")
        else:
                message = message.split(",")
                if message[0] == "Alert":
                        tokenAddress = message[1]
                        tokenSymbol = message[2]
                        print("Lance du Thread pour {symbol}".format(symbol = tokenSymbol))
                        tokenMonitor = TokenMonitor(tokenAddress = tokenAddress, tokenSymbol = tokenSymbol)
                        token_thread_list.append(tokenMonitor)
                        token_thread_list[-1].start()

        #  Send reply back to client
        socket.send_string("OK")