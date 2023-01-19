import os
import time
import re
import asyncio
import threading
from web3 import Web3
from telethon.sync import TelegramClient, events
from requests import Request, Session
from requests.exceptions import ConnectionError, Timeout, TooManyRedirects
from pythonpancakes import PancakeSwapAPI
from bs4 import BeautifulSoup
import requests

import json

from utils import *

clearConsole = lambda: os.system('cls' if os.name in ('nt', 'dos') else 'clear')
clearConsole()

LOGGER.header(NAME_OF_BOT_FOR_DISPLAY)
print("\n")

LOGGER.general("Telegram Channel: {channel}".format(channel = channelId))
LOGGER.general("Amount to Snipe : " + str(snipeBNBAmount))

################# Init all the stuff #################
if MUSIC_ALERT:
        LOGGER.general("Music Alert: {alert}".format(alert = "ON"))
        from pygame import mixer 
        mixer.init()
        mixer.music.load("./song.mp3")
else:
        LOGGER.general("Music Alert: {alert}".format(alert = "OFF"))

client = TelegramClient(session_name, api_id, api_hash)
globalWeb3 = Web3(Web3.WebsocketProvider(bscNode))

################# Global variables #################
BNBTokenAddress = Web3.toChecksumAddress("0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c")
GLOBAL_PROGRESSION = 0

if MAIL_ALERT:
        LOGGER.general("Mail Alert: {alert}".format(alert = "ON"))
        EMAIL = "martin.baty@gmail.com"
        SUBJECT = "NEW BUY - CMC ALERT"
        CONTENT = "New token bought : ${symbol} : {address}"
else:
        LOGGER.general("Mail Alert: {alert}".format(alert = "OFF"))

################# Print BNB Balance #################
def get_balance_bnb():
        balance = globalWeb3.eth.get_balance(walletAddress)
        humanReadable = globalWeb3.fromWei(balance,'ether')
        return humanReadable
print("\n")
LOGGER.good("##")
LOGGER.good("###### BNB Balance: {balance} BNB".format(balance = str(round(get_balance_bnb(), 4))))
LOGGER.good("##")
print("\n")


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
                self.listStep = []
                self.buyingSucceed = False
                self.step = 0.2
                for i in range(1,15):
                        self.listStep.append(1 + i*self.step)
                balance = self.getBNBBalanceThread()
                if balance > 0.0005:
                        self.buy()
                

        def run(self):
                if SELL:
                        if TEST_SELL:
                                self.sell()
                        elif self.buyPrice is None:
                                pass
                        elif self.buyingSucceed:
                                while(not self.stop):
                                        try:
                                                self.price = self.getTokenPrice(self.tokenAddress)
                                        except Exception as e:
                                                if str(e) != "code = 4040 (private use), reason = Draining connection":
                                                        LOGGER.fail("[MONITOR] Error when get price in loop thread !")
                                                        print("e: {e}".format(e = str(e)))
                                
                                        if self.previous_step_sell != float('-inf'):
                                                if self.price < (self.previous_step_sell * self.buyPrice):
                                                        print("{color}[MONITOR] Sell for step {step} for {symbol} : {address}".format(color = bcolors.OKGREEN, step = str(self.previous_step_sell), \
                                                                symbol = self.tokenSymbol, address = self.tokenAddress))
                                                        self.sell()

                                        if (self.price > (self.buyPrice * self.step_sell)):
                                                self.getStep()
                                                if self.previous_step_sell != float('-inf'):
                                                        print("{color}[MONITOR] Multiplier {step} successfully passed for {symbol} : {address} ! Next step : {sellingPrice1}".\
                                                                format(color = bcolors.OKCYAN, step = str(self.previous_step_sell), symbol = self.tokenSymbol, address = self.tokenAddress, \
                                                                        sellingPrice1 = self.buyPrice * self.step_sell))
                                                if self.step_sell >= self.listStep[-1]:
                                                        self.sell()
                                        
                                        if (self.price <= self.buyPrice * lowThresholdSell):
                                                print("self.price : ", self.price)
                                                print("self.buyPrice * lowThresholdSell : ", self.buyPrice * lowThresholdSell)
                                                print("{color}[MONITOR] Sell at price:{price} , because lowThresholdSell reached for {symbol} : {address}".format(color = bcolors.FAIL, \
                                                        symbol = self.tokenSymbol, price = self.price, address = self.tokenAddress))
                                                self.sell()

                                        time.sleep(2)

        def getBNBBalanceThread(self):
                balance = self.web3Thread.eth.get_balance(walletAddress)
                humanReadable = self.web3Thread.fromWei(balance,'ether')
                return humanReadable    

        def getStep(self):
                for s in self.listStep:
                        # print("s : ", s)
                        # print("self.buyPrice * s : ", self.buyPrice * s)
                        # print("self.buyPrice * (s+self.step) : ", self.buyPrice * (s+self.step))
                        if self.price > (self.buyPrice * s) and self.price < (self.buyPrice * (s+self.step)):
                                print("On rentre")
                                self.step_sell = s+self.step
                                self.previous_step_sell = s

        def getTokenPrice(self, tokenAddress):
                URL = "https://deep-index.moralis.io/api/v2/erc20/{tokenAddress}/price?chain=bsc".format(tokenAddress = self.tokenAddress)
                headers = {'X-API-Key': 'IVOc3LB6vmTKTnSfI7TPHaRKfKTbgpi8U6avyDocdf2P0nPCKeYNkNBszBbUdUE4', 'accept': 'application/json'}
                req = requests.get(URL, headers=headers)
                tokenPrice = json.loads(req.text)["usdPrice"]
                tokenPrice = float(tokenPrice)

                return tokenPrice

        def getGasAmount(self, contract, tokenToBuy):
                nonce = self.web3Thread.eth.get_transaction_count(walletAddress)
                # if WBNBAdress in [self.token0, self.token1]:
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
                gas_estimate = self.web3Thread.eth.estimateGas(pancakeswap2_txn)
                return int(gas_estimate*1.2)

        def buy(self):
                global END_TIME
                global BEGIN_TIME
                try:
                        if(self.tokenAddress != None):
                                LOGGER.info("[BUY] Buying {symbol} ({address}) for {amount} BNB".format(symbol = self.tokenSymbol, address = self.tokenAddress, amount = snipeBNBAmount))
                                tokenToBuy = self.web3Thread.toChecksumAddress(self.tokenAddress)
                                contract = self.web3Thread.eth.contract(address=pancakeSwapRouterAddress, abi=pancakeABI)
                                counterBuy = 0
                                gasAmount = self.getGasAmount(contract, tokenToBuy)
                                while not self.buyingSucceed and counterBuy < 2:
                                        if counterBuy == 1:
                                                persoGasPrice = str(int(gasPrice) + 1)
                                                persoGasAmount = gasAmount*2
                                        else:
                                                persoGasPrice = gasPrice
                                                persoGasAmount = gasAmount
                                                
                                        nonce = self.web3Thread.eth.get_transaction_count(walletAddress)
                                        # if WBNBAdress in [self.token0, self.token1]:
                                        pancakeswap2_txn = contract.functions.swapExactETHForTokensSupportingFeeOnTransferTokens(
                                                0, # Set to 0 or specify min number of tokens - setting to 0 just buys X amount of tokens for whatever BNB specified
                                                [BNBTokenAddress,tokenToBuy],
                                                walletAddress,
                                                (int(time.time()) + transactionRevertTimeSeconds)
                                                ).buildTransaction({
                                                'from': walletAddress,
                                                'value': self.web3Thread.toWei(float(snipeBNBAmount), 'ether'),
                                                'gas': persoGasAmount,
                                                'gasPrice': self.web3Thread.toWei(persoGasPrice,'gwei'),
                                                'nonce': nonce,
                                        })
                                        sellTokenContract = self.web3Thread.eth.contract(tokenToBuy, abi=sellAbi)
                                        try:
                                                signed_txn = self.web3Thread.eth.account.sign_transaction(pancakeswap2_txn, walletPrivateKey)
                                                tx_token = self.web3Thread.eth.send_raw_transaction(signed_txn.rawTransaction) #BUY THE TOKEN
                                                response = self.web3Thread.eth.wait_for_transaction_receipt(transaction_hash=tx_token, timeout=15, poll_latency=0.1)
                                                print("result : ", response["status"])
                                                if response["status"] == 1:
                                                        END_TIME = time.time()
                                                        self.buyingSucceed = True
                                                else:
                                                        self.buyingSucceed = False
                                                self.buyPrice = self.getTokenPrice(self.tokenAddress)
                                        except Exception as ex:
                                                self.buyPrice = None
                                                LOGGER.fail("[BUY] FAILED when buying {symbol} | Error: {error}s".format(symbol = self.tokenSymbol, error = str(ex)))
                                                return
                                        counterBuy += 1

                                if self.buyingSucceed:
                                        try:
                                                LOGGER.info("[BUY] Time between alert and buy : {time}s".format(time = str(round((END_TIME - BEGIN_TIME),2))))
                                                LOGGER.info("[BUY] Buy Price: {price}".format(price = str(self.buyPrice)))
                                                LOGGER.info("[BUY] Low threshold: {low}".format(low=str(self.buyPrice*lowThresholdSell)))
                                        except Exception as e:
                                                LOGGER.fail("e: " + str(e))
                                
                                if self.buyingSucceed:
                                        #Get BNB price
                                        req = requests.get("https://coin360.com/coin/binance-coin-bnb")
                                        soup = BeautifulSoup(req.text, "html.parser")
                                        BNBPrice = soup.find_all("div", {"class": "CoinPageHead__PriceUsd"})[0].text[1:-1]
                                        BNBPrice = float(BNBPrice)
                                        #Get Token Balance
                                        balance = sellTokenContract.functions.balanceOf(walletAddress).call()
                                        LOGGER.good("[BUY] Successfully bought $" + self.tokenSymbol + " for " + str(snipeBNBAmount) + " BNB ({dollarz}$) || \
Adress : ".format(dollarz = str(round(snipeBNBAmount*BNBPrice, 2))) + self.tokenAddress)
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
                                                LOGGER.fail("[BUY] Error when trying to know if it's approved or not | Error: {error}.".format(error = str(e)))

                                        if int(resultApproved) == 0:
                                                # Approve token for future selling
                                                try:
                                                        approve = sellTokenContract.functions.approve(pancakeSwapRouterAddress, balance*10).buildTransaction({
                                                                'from': walletAddress,
                                                                'gasPrice': self.web3Thread.toWei(gasPrice,'gwei'),
                                                                'nonce': self.web3Thread.eth.get_transaction_count(walletAddress),
                                                                })

                                                        signed_txn = self.web3Thread.eth.account.sign_transaction(approve, private_key=walletPrivateKey)
                                                        tx_token = self.web3Thread.eth.send_raw_transaction(signed_txn.rawTransaction)
                                                        LOGGER.good("[BUY] Approved Token {symbol} for future selling".format(symbol = self.tokenSymbol))
                                                        LOGGER.info("[MONITOR] Start monitoring the price")
                                                        print("\n")
                                                        LOGGER.header("---------------------------------------------------------------------------------------")
                                                        print("\n")
                                                        
                                                except Exception as e:
                                                        LOGGER.fail("[BUY] FAILED when approving {symbol} | Error: {error}".format(symbol = self.tokenSymbol, error = str(e)))
                                                        print("\n")
                                                        LOGGER.header("---------------------------------------------------------------------------------------")
                                                        print("\n")
                                        else:
                                                LOGGER.good("[BUY] Token {symbol} already approved for future selling".format(symbol = self.tokenSymbol))
                                                LOGGER.info("[MONITOR] Start monitoring the price")
                                                print("\n")
                                                LOGGER.header("---------------------------------------------------------------------------------------")
                                                print("\n")
                                else:
                                        LOGGER.fail("[BUY] FAILED when bought $" + self.tokenSymbol + " for " + str(snipeBNBAmount) + " BNB || Adress : " + self.tokenAddress)
                                        print("\n")
                                        LOGGER.header("---------------------------------------------------------------------------------------")
                                        print("\n")

                except Exception as ex:
                        LOGGER.fail("[BUY] Transaction failed: likely not enough gas.")
                        LOGGER.fail("[BUY] FAILED when bought: {error}".format(error = str(ex)))
                        print("\n")
                        LOGGER.header("---------------------------------------------------------------------------------------")
                        print("\n")

        def sell(self):
                global GLOBAL_PROGRESSION

                contract_id = self.web3Thread.toChecksumAddress(self.tokenAddress)
                contract = self.web3Thread.eth.contract(address=pancakeSwapRouterAddress, abi=pancakeABI)
                sellTokenContract = self.web3Thread.eth.contract(contract_id, abi=sellAbi)

                #Get Token Balance
                balance = sellTokenContract.functions.balanceOf(walletAddress).call()
                readable = self.web3Thread.fromWei(balance,'ether')
                LOGGER.info("[SELL] Balance of {symbol}: {balance}".format(symbol = self.tokenSymbol, balance = str(readable)))

                tokenAmount = float(readable)
                tokenValue = self.web3Thread.toWei(tokenAmount, 'ether')

                #Approve Token before Selling
                tokenValue2 = self.web3Thread.fromWei(tokenValue, 'ether')

                LOGGER.info(f"[SELL] Swapping {tokenValue2} {self.tokenSymbol} for BNB")

                sellSucceed = False
                #Create token Instance for Token
                sellTokenContract = self.web3Thread.eth.contract(contract_id, abi=sellAbi)
                counterSellRetry = 0
                try:
                        while not sellSucceed:
                                #Swaping exact Token for ETH 
                                pancakeswap2_txn = contract.functions.swapExactTokensForETHSupportingFeeOnTransferTokens(
                                        balance ,SLIPPAGE_SELL, 
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
                                time.sleep(3)
                                response = self.web3Thread.eth.wait_for_transaction_receipt(transaction_hash=tx_token, timeout=30, poll_latency=0.1)
                                print('response["status"] : ', response["status"])
                                if response["status"] == 1:
                                        sellSucceed = True
                                else:
                                        sellSucceed = False
                                LOGGER.fail("[SELL] FAILED when selling {symbol} : {address} ! Retrying Again...".format(symbol = self.tokenSymbol, address = self.tokenAddress))
                                counterSellRetry += 1
                                if counterSellRetry == 6:
                                        LOGGER.fail("[SELL] FAILED when selling {symbol} : {address} ! Too much tries...".format(symbol = self.tokenSymbol, address = self.tokenAddress))
                                        if MAIL_ALERT:
                                                mail = Mail()
                                                content = "$" + self.tokenSymbol + " : " + self.tokenAddress
                                                mail.send(EMAIL, content, content)
                                        self.stop = True
                                        return
                                time.sleep(2)
                except Exception as e:
                        if MAIL_ALERT:
                                mail = Mail()
                                content = "$" + self.tokenSymbol + " : " + self.tokenAddress
                                mail.send(EMAIL, content, content)
                        LOGGER.fail("[SELL] FAILED when selling {symbol} : {address} !".format(symbol = self.tokenSymbol, address = self.tokenAddress))
                        LOGGER.fail("[SELL] ERROR: {error}".format(error = str(e)))
                        self.stop = True
                        return

                self.progression = (self.price * tokenAmount) - (self.buyPrice * tokenAmount)

                if sellSucceed:
                        LOGGER.good("[SELL] Successfully Sold {symbol} : {address} at step {step}".format(symbol = self.tokenSymbol,\
                         address = self.tokenAddress, step = str(self.previous_step_sell)))
                else:
                        if MAIL_ALERT:
                                mail = Mail()
                                content = "$" + self.tokenSymbol + " : " + self.tokenAddress
                                mail.send(EMAIL, content, content)
                        LOGGER.fail("[SELL] FAILED when selling {symbol} : {address} !".format(symbol = self.tokenSymbol, address = self.tokenAddress))
                GLOBAL_PROGRESSION = GLOBAL_PROGRESSION + self.progression
                LOGGER.info("### Token Progression : {progression}".format(progression = round(self.progression, 4)))
                LOGGER.important("### GLOBAL PROGRESSION : {progression}".format(progression = round(GLOBAL_PROGRESSION, 4)))
                LOGGER.info("###")
                try:
                        print("{color}###### BNB Balance: {balance} BNB".format(color = bcolors.OKCYAN, balance = str(round(get_balance_bnb(), 4))))
                except:
                        pass
                LOGGER.info("###")
                print("\n")
                LOGGER.header("---------------------------------------------------------------------------------------")
                print("\n")
                self.stop = True

@client.on(events.NewMessage(chats = channelId))
async def new_message_listener(event):
        global BEGIN_TIME
        global BUYING_FINISHED
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
                        tokenMonitor = TokenMonitor(tokenAddress = tokenAddress, tokenSymbol = tokenSymbol)
                        tokenMonitor.start()
                
                token_already_got.append(tokenAddress)
        
        return

async def main():
    while True:
            await asyncio.sleep(60)

################# Start the telegram client #################
client.start()
client.loop.run_until_complete(main())