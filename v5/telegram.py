import os
import time
from datetime import datetime
import re
import asyncio
import threading
from web3 import Web3
from telethon.sync import TelegramClient, events
from bs4 import BeautifulSoup
import requests
import json
import ssl
# import certifi
# ssl._create_default_https_context = ssl._create_unverified_context

ssl._create_unverified_context

from utils import *

from pythonpancakes import PancakeSwapAPI

ps = PancakeSwapAPI()

# clearConsole = lambda: os.system('cls' if os.name in ('nt', 'dos') else 'clear')
# clearConsole()

LOGGER.header(NAME_OF_BOT_FOR_DISPLAY)
LOGGER.info("\n")

LOGGER.general("Telegram Channel: {channel}".format(channel = channelId))
LOGGER.general("Amount to Snipe : " + str(snipeBNBAmount))
if TEST_MODE:
        LOGGER.general("Test Mode : ON")
else:
        LOGGER.general("Test Mode : OFF")

################# Init all the stuff #################
if MUSIC_ALERT:
        LOGGER.general("Music Alert: {alert}".format(alert = "ON"))
        from pygame import mixer 
        mixer.init()
        mixer.music.load("./song.mp3")
else:
        LOGGER.general("Music Alert: {alert}".format(alert = "OFF"))

client = TelegramClient(session_name, api_id, api_hash)

WEB3_OPTIONS = {'extra_headers': {'x-api-key': '563ea456-6189-425c-9388-d899a8bf5e93'}}

globalWeb3 = Web3(Web3.IPCProvider(bscNode))

################# Global variables #################
BNBTokenAddress = Web3.toChecksumAddress("0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c")
GLOBAL_PROGRESSION = 0
WEB3_IN_USE = False

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

INITIAL_BNB_BALANCE = get_balance_bnb()

LOGGER.info("\n")
LOGGER.good("##")
LOGGER.good("###### BNB Balance: {balance} BNB".format(balance = str(INITIAL_BNB_BALANCE)))
LOGGER.good("##")
LOGGER.info("\n")


################# Class (Thread) to monitor the token price and sell when condition is reached #################
class TokenMonitor (threading.Thread):
        def __init__(self, tokenAddress, tokenSymbol):
                threading.Thread.__init__(self)
                self.tokenAddress = tokenAddress
                self.tokenSymbol = tokenSymbol
                self.buyPrice = None
                self.web3Thread = Web3(Web3.IPCProvider(bscNode))
                self.balance = 0
                self.price = 0
                self.stop = False
                self.step_sell = 1.1
                self.previous_step_sell = float('-inf')
                self.listStep = []
                self.buyingSucceed = False
                self.step = 0.1
                for i in range(1,50):
                        self.listStep.append(1 + i*self.step)
                # balanceBNB = self.getBNBBalanceThread()
                if TEST_MODE:
                        self.buyPrice = self.getTokenPrice(self.tokenAddress)
                else:
                        # if balanceBNB > (snipeBNBAmount + 0.003):
                        self.buy()

        def run(self):
                if SELL or TEST_MODE:
                        if TEST_SELL:
                                self.sell()
                        elif self.buyPrice is None and not TEST_MODE:
                                pass
                        elif self.buyingSucceed or TEST_MODE:
                                while(not self.stop):
                                        try:
                                                self.price = self.getTokenPrice(self.tokenAddress)
                                        except Exception as e:
                                                LOGGER.fail("[MONITOR] Error when get price in loop thread !")
                                                LOGGER.fail("e: {e}".format(e = str(e)))
                                                # print("e: {e}".format(e = str(e)))
                                
                                        if self.previous_step_sell != float('-inf'):
                                                if self.price*self.balance < self.previous_step_sell * (self.buyPrice*self.balance):
                                                        time.sleep(1)
                                                        self.price = self.getTokenPrice(self.tokenAddress)
                                                        if self.price*self.balance < self.previous_step_sell * (self.buyPrice*self.balance):
                                                                LOGGER.info("{color}[MONITOR] Sell for step {step} for {symbol} : {address}".format(color = bcolors.OKGREEN, step = str(self.previous_step_sell), \
                                                                        symbol = self.tokenSymbol, address = self.tokenAddress))
                                                                LOGGER.info("self.price before sell : {price}".format(price = self.price))
                                                                if not TEST_MODE:
                                                                        self.sell()

                                        if self.price*self.balance > (self.buyPrice*self.balance) * self.step_sell:
                                                self.getStep()
                                                if self.previous_step_sell != float('-inf'):
                                                        LOGGER.info("{color}[MONITOR] Multiplier {step} successfully passed ({priceStep}) for {symbol} : {address} ! Next step : {sellingPrice1}".\
                                                        format(color = bcolors.OKCYAN, step = str(self.previous_step_sell), priceStep = str(self.buyPrice * self.previous_step_sell), \
                                                                symbol = self.tokenSymbol, address = self.tokenAddress, sellingPrice1 = self.buyPrice * self.step_sell))
                                                if self.step_sell >= self.listStep[-1]:
                                                        LOGGER.info("self.price before sell : ", self.price)
                                                        if not TEST_MODE:
                                                                self.sell()

                                        
                                        if self.price*self.balance <= (self.buyPrice*self.balance) * lowThresholdSell:
                                                # time.sleep(1)
                                                self.price = self.getTokenPrice(self.tokenAddress)
                                                if (self.price <= self.buyPrice * lowThresholdSell):
                                                        time.sleep(1)
                                                        self.price = self.getTokenPrice(self.tokenAddress)
                                                        if self.price*self.balance <= (self.buyPrice*self.balance) * lowThresholdSell:
                                                                LOGGER.info("self.price : ", self.price)
                                                                LOGGER.info("self.buyPrice * lowThresholdSell : ", (self.buyPrice*self.balance) * lowThresholdSell)
                                                                LOGGER.fail("[MONITOR] Sell at price:{price} ,because lowThresholdSell reached for {symbol} : {address}".format(symbol = self.tokenSymbol,\
                                                                 price = self.price, address = self.tokenAddress))
                                                                if not TEST_MODE:
                                                                        self.sell()

                                        time.sleep(1)

        def getFees(self):
                buyFees = None
                sellFees = None
                URL = "https://app.staysafu.org/api" + "/simulatebuy?tokenAddress=" + self.tokenAddress
                result = requests.get(URL)
                try:
                        result = json.loads(result.text)["result"]
                except:
                        LOGGER.info("StaySafu down... Continue...") 
                        buyFees = -1
                        sellFees = -1
                else:
                        try:
                                buyFees = float(result["buyFee"])
                                sellFees = float(result["sellFee"])
                        except Exception as e:
                                LOGGER.info("StaySafu down 2... Continue...") 
                                buyFees = -1
                                sellFees = -1
                return buyFees, sellFees

        def getBNBBalanceThread(self):
                balance = self.web3Thread.eth.get_balance(walletAddress)
                humanReadable = self.web3Thread.fromWei(balance,'ether')
                return humanReadable

        def getBNBPrice(self):
                req = requests.get("https://coin360.com/coin/binance-coin-bnb")
                soup = BeautifulSoup(req.text, "html.parser")
                BNBPrice = soup.find_all("div", {"class": "CoinPageHead__PriceUsd"})[0].text[1:-1]
                BNBPrice = float(BNBPrice)
                return BNBPrice
                

        def getStep(self):
                for s in self.listStep:
                        if (self.price*self.balance) > ((self.buyPrice*self.balance) * s) and (self.price*self.balance) < ((self.buyPrice*self.balance) * (s+self.step)):
                                self.step_sell = s+self.step
                                self.previous_step_sell = s

        def getTokenPricePancake(self, tokenAddress):
                tokens = ps.tokens(tokenAddress)
                # print("tokens : ", tokens)
                price = tokens["data"]["price"]
                return float(price)

        def getTokenPriceMoralis(self, tokenAddress):
                URL = "https://deep-index.moralis.io/api/v2/erc20/{tokenAddress}/price?chain=bsc".format(tokenAddress = tokenAddress)
                headers = {'X-API-Key': 'IVOc3LB6vmTKTnSfI7TPHaRKfKTbgpi8U6avyDocdf2P0nPCKeYNkNBszBbUdUE4', 'accept': 'application/json'}
                req = requests.get(URL, headers=headers)
                try:
                        tokenPrice = json.loads(req.text)["usdPrice"]
                except Exception as e:
                        LOGGER.fail("[GET TOKEN PRICE] Error when get price Moralis!")
                        LOGGER.fail("e: {e}".format(e = str(e)))
                        tokenPrice = self.price
                else:
                        tokenPrice = float(tokenPrice)

                return tokenPrice

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

                BNBPrice = self.getTokenPricePancake(WBNBAdress)
                tokenPrice = (BNBPrice * BNBReserve) / TokenReserve

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
                return int(gas_estimate*1.6)

        def buy(self):
                global END_TIME
                global BEGIN_TIME
                try:
                        if(self.tokenAddress != None):
                                LOGGER.info("[BUY] Buying {symbol} ({address}) for {amount} BNB".format(symbol = self.tokenSymbol, address = self.tokenAddress, amount = snipeBNBAmount))
                                tokenToBuy = self.web3Thread.toChecksumAddress(self.tokenAddress)
                                pcsContract = self.web3Thread.eth.contract(address=pancakeSwapRouterAddress, abi=pancakeABI)
                                counterBuy = 0
                                # gasAmount = self.getGasAmount(contract, tokenToBuy)
                                while not self.buyingSucceed and counterBuy < 2:
                                        if counterBuy == 1:
                                                persoGasPrice = str(int(gasPrice) + 1)
                                                persoGasAmount = gasAmount*2
                                        else:
                                                persoGasPrice = gasPrice
                                                persoGasAmount = gasAmount
                                                
                                        nonce = self.web3Thread.eth.get_transaction_count(walletAddress)
                                        # if WBNBAdress in [self.token0, self.token1]:
                                        pancakeswap2_txn = pcsContract.functions.swapExactETHForTokensSupportingFeeOnTransferTokens(
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
                                        tokenToBuyContract = self.web3Thread.eth.contract(tokenToBuy, abi=sellAbi)
                                        getPriceFinished = False
                                        try:
                                                signed_txn = self.web3Thread.eth.account.sign_transaction(pancakeswap2_txn, walletPrivateKey)
                                                tx_token = self.web3Thread.eth.send_raw_transaction(signed_txn.rawTransaction) #BUY THE TOKEN
                                                response = self.web3Thread.eth.wait_for_transaction_receipt(transaction_hash=tx_token, timeout=30, poll_latency=0.1)
                                                if response["status"] == 1:
                                                        END_TIME = time.time()
                                                        self.buyingSucceed = True
                                                else:
                                                        self.buyingSucceed = False
                                                getPriceFinished = False
                                        except Exception as ex:
                                                #Get Token Balance
                                                self.balance = tokenToBuyContract.functions.balanceOf(walletAddress).call()
                                                if self.balance > 0:
                                                        self.buyingSucceed = True
                                                else:
                                                        self.buyPrice = None
                                                        LOGGER.fail("[BUY] FAILED when buying {symbol} | Error: {error}s".format(symbol = self.tokenSymbol, error = str(ex)))
                                                        return
                                        counterBuy += 1

                                if self.buyingSucceed:
                                        while not getPriceFinished:
                                                try:
                                                        self.buyPrice = self.getTokenPrice(self.tokenAddress)
                                                except Exception as e:
                                                        LOGGER.fail("e : {error}".format(error=e))
                                                        getPriceFinished = False
                                                else:
                                                        getPriceFinished = True
                                        try:
                                                LOGGER.info("[BUY] Time between alert and buy : {time}s".format(time = str(round((END_TIME - BEGIN_TIME),2))))
                                                LOGGER.info("[BUY] Buy Price: {price}".format(price = str(self.buyPrice)))
                                                LOGGER.info("[BUY] Low threshold: {low}".format(low=str(self.buyPrice*lowThresholdSell)))
                                        except Exception as e:
                                                LOGGER.fail("e: " + str(e))
                                
                                if self.buyingSucceed:
                                        #Get BNB price
                                        BNBPrice = self.getBNBPrice()
                                        #Get Token Balance
                                        self.balance = tokenToBuyContract.functions.balanceOf(walletAddress).call()
                                        LOGGER.good("[BUY] Successfully bought $" + self.tokenSymbol + " for " + str(snipeBNBAmount) + " BNB ({dollarz}$) || \
Adress : ".format(dollarz = str(round(snipeBNBAmount*BNBPrice, 2))) + self.tokenAddress)
                                        if MUSIC_ALERT:
                                                mixer.music.play()
                                                time.sleep(10)
                                                mixer.music.stop()

                                        try:
                                                # Check if it's already approved
                                                owner = self.web3Thread.toChecksumAddress(walletAddress)
                                                spender = self.web3Thread.toChecksumAddress(pancakeSwapRouterAddress)
                                                resultApproved = tokenToBuyContract.functions.allowance(owner, spender).call()
                                        except Exception as e:
                                                LOGGER.fail("[BUY] Error when trying to know if it's approved or not | Error: {error}.".format(error = str(e)))

                                        if int(resultApproved) == 0:
                                                # Approve token for future selling
                                                try:
                                                        approve = tokenToBuyContract.functions.approve(pancakeSwapRouterAddress, self.balance*10).buildTransaction({
                                                                'from': walletAddress,
                                                                'gasPrice': self.web3Thread.toWei(gasPrice,'gwei'),
                                                                'nonce': self.web3Thread.eth.get_transaction_count(walletAddress),
                                                                })

                                                        signed_txn = self.web3Thread.eth.account.sign_transaction(approve, private_key=walletPrivateKey)
                                                        tx_token = self.web3Thread.eth.send_raw_transaction(signed_txn.rawTransaction)
                                                        LOGGER.good("[BUY] Approved Token {symbol} for future selling".format(symbol = self.tokenSymbol))
                                                        LOGGER.info("[MONITOR] Start monitoring the price")
                                                        LOGGER.info("\n")
                                                        LOGGER.header("---------------------------------------------------------------------------------------")
                                                        LOGGER.info("\n")
                                                        
                                                except Exception as e:
                                                        LOGGER.fail("[BUY] FAILED when approving {symbol} | Error: {error}".format(symbol = self.tokenSymbol, error = str(e)))
                                                        LOGGER.info("\n")
                                                        LOGGER.header("---------------------------------------------------------------------------------------")
                                                        LOGGER.info("\n")
                                        else:
                                                LOGGER.good("[BUY] Token {symbol} already approved for future selling".format(symbol = self.tokenSymbol))
                                                LOGGER.info("[MONITOR] Start monitoring the price")
                                                LOGGER.info("\n")
                                                LOGGER.header("---------------------------------------------------------------------------------------")
                                                LOGGER.info("\n")
                                else:
                                        LOGGER.fail("[BUY] FAILED when bought $" + self.tokenSymbol + " for " + str(snipeBNBAmount) + " BNB || Adress : " + self.tokenAddress)
                                        LOGGER.info("\n")
                                        LOGGER.header("---------------------------------------------------------------------------------------")
                                        LOGGER.info("\n")

                except Exception as ex:
                        LOGGER.fail("[BUY] Transaction failed: likely not enough gas.")
                        LOGGER.fail("[BUY] FAILED when bought: {error}".format(error = str(ex)))
                        LOGGER.info("\n")
                        LOGGER.header("---------------------------------------------------------------------------------------")
                        LOGGER.info("\n")

        def sell(self):
                global WEB3_IN_USE
                global GLOBAL_PROGRESSION

                contract_id = self.web3Thread.toChecksumAddress(self.tokenAddress)
                contract = self.web3Thread.eth.contract(address=pancakeSwapRouterAddress, abi=pancakeABI)
                sellTokenContract = self.web3Thread.eth.contract(contract_id, abi=sellAbi)

                # readable = self.web3Thread.fromWei(self.balance,'ether')
                LOGGER.info("[SELL] Balance of {symbol}: {balance}".format(symbol = self.tokenSymbol, balance = str(self.balance)))

                tokenAmount = float(self.balance)
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
                                        self.balance ,SLIPPAGE_SELL, 
                                        [contract_id, BNBTokenAddress],
                                        walletAddress,
                                        (int(time.time()) + 1000000)
                                        ).buildTransaction({
                                        'from': walletAddress,
                                        'gasPrice': self.web3Thread.toWei("7",'gwei'),
                                        'nonce': self.web3Thread.eth.get_transaction_count(walletAddress),
                                        })
                                
                                signed_txn = self.web3Thread.eth.account.sign_transaction(pancakeswap2_txn, private_key=walletPrivateKey)
                                tx_token = self.web3Thread.eth.send_raw_transaction(signed_txn.rawTransaction)
                                time.sleep(3)
                                response = self.web3Thread.eth.wait_for_transaction_receipt(transaction_hash=tx_token, timeout=30, poll_latency=0.1)
                                if response["status"] == 1:
                                        sellSucceed = True
                                else:
                                        sellSucceed = False
                                        LOGGER.fail("[SELL] FAILED when selling {symbol} : {address} ! Retrying Again...".format(symbol = self.tokenSymbol, address = self.tokenAddress))
                                counterSellRetry += 1
                                if counterSellRetry == 8:
                                        LOGGER.fail("[SELL] FAILED when selling {symbol} : {address} ! Too much tries...".format(symbol = self.tokenSymbol, address = self.tokenAddress))
                                        if MAIL_ALERT:
                                                mail = Mail()
                                                content = "$" + self.tokenSymbol + " : " + self.tokenAddress
                                                mail.send(EMAIL, content, content)
                                        self.stop = True
                                        WEB3_IN_USE = False
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
                        WEB3_IN_USE = False
                        return

                balance_now = self.getBNBBalanceThread()
                progression = balance_now - INITIAL_BNB_BALANCE
                self.price = self.getTokenPrice(self.tokenAddress)
                LOGGER.info("self.price : {price}".format(self.price))
                LOGGER.info("tokenAmount : {amount}".format(tokenAmount))

                if sellSucceed:
                        LOGGER.good("[SELL] Successfully Sold {symbol} : {address} for ({dollarz}$) at step {step}".format(symbol = self.tokenSymbol,\
                         address = self.tokenAddress, dollarz = str(round(self.price*tokenAmount, 2)), step = str(self.previous_step_sell)))
                else:
                        if MAIL_ALERT:
                                mail = Mail()
                                content = "$" + self.tokenSymbol + " : " + self.tokenAddress
                                mail.send(EMAIL, content, content)
                        LOGGER.fail("[SELL] FAILED when selling {symbol} : {address} !".format(symbol = self.tokenSymbol, address = self.tokenAddress))
                LOGGER.info("###")
                LOGGER.important("### GLOBAL PROGRESSION SINCE BEGINNING : {progression} ({dollarz}$)".format(progression = round(progression, 4), dollarz = round(float(progression)*float(self.getBNBPrice()), 2)))
                LOGGER.info("###")
                try:
                        LOGGER.info("{color}###### BNB Balance: {balance} BNB".format(balance = str(round(get_balance_bnb(), 4))))
                except:
                        pass
                LOGGER.info("###")
                LOGGER.info("\n")
                LOGGER.header("---------------------------------------------------------------------------------------")
                LOGGER.info("\n")
                self.stop = True
                WEB3_IN_USE = False


token_already_got = []
threadList = []

@client.on(events.NewMessage(chats = channelId))
async def new_message_listener(event):
        global BEGIN_TIME
        global threadList
        global BUYING_FINISHED
        global WEB3_IN_USE
        BEGIN_TIME = time.time()
        text = event.raw_text
        regexOnlyNumbers = r"[0-9]+"
        regexAddress = r"0x\S{40}"
        regexFirstAlert = r"🔴"
        regexSymbol = r'[[\bA-Za-z\b]*]'
        regexLiquidity = r"[0-9]+.[0-9]{2} BNB"
        regexBuyFees = r"[0-9]+% \(buy\)"
        regexSellFees = r"[0-9]+% \(sell\)"
        matchesAddress = re.findall(regexAddress, text, re.MULTILINE)
        matchesFirstAlert = re.findall(regexFirstAlert, text, re.MULTILINE)
        matchesSymbol = re.findall(regexSymbol, text)
        matchesLiquidity = re.findall(regexLiquidity, text)
        matchesBuyFees = re.findall(regexBuyFees, text)
        matchesSellFees = re.findall(regexSellFees, text)
        tokenAddress = None
        tokenSymbol = None
        liquidity = None

        if matchesFirstAlert:

                if len(matchesAddress) > 0:
                        tokenAddress = matchesAddress[0]
                else:
                        return

                if len(matchesSymbol) > 0:
                        tokenSymbol = matchesSymbol[0]
                else:
                        return

                if len(matchesBuyFees) > 0:
                        buyFees = matchesBuyFees[0]
                        buyFees = re.findall(regexOnlyNumbers, buyFees)
                        buyFees = float(buyFees[0])
                else:
                        return

                if len(matchesSellFees) > 0:
                        sellFees = matchesSellFees[0]
                        sellFees = re.findall(regexOnlyNumbers, sellFees)
                        sellFees = float(sellFees[0])
                else:
                        return

                if buyFees > MAX_BUY_FEES or sellFees > MAX_SELL_FEES:
                        LOGGER.info("\n")
                        LOGGER.info("[INFO] Transactions fees too high for {symbol} {address} : BuyFees: {buyFees}% | SellFees: {sellFees}% !".format(symbol = tokenSymbol,\
                                address = tokenAddress, buyFees = str(buyFees), sellFees = str(sellFees)))
                        LOGGER.info("\n")
                        return

                if len(matchesLiquidity) > 0:
                        liquidity = matchesLiquidity[0]
                        liquidity = float(liquidity[0:6])
                else:
                        LOGGER.info("\n")
                        LOGGER.info("[INFO] Liquidity not in BNB for {symbol} {address} !".format(symbol = tokenSymbol,\
                                address = tokenAddress))
                        LOGGER.info("\n")  
                if liquidity:
                        if liquidity < MIN_LIQUIDITY:
                                LOGGER.info("\n")
                                LOGGER.info("[INFO] Too few liquidity for {symbol} {address} : Liquidity: {liquidity} BNB !".format(symbol = tokenSymbol,\
                                        address = tokenAddress, liquidity = str(liquidity)))
                                LOGGER.info("\n")
                                return
                        elif liquidity > MAX_LIQUIDITY:
                                LOGGER.info("\n")
                                LOGGER.info("[INFO] Too much liquidity for {symbol} {address} : Liquidity: {liquidity} BNB !".format(symbol = tokenSymbol,\
                                        address = tokenAddress, liquidity = str(liquidity)))
                                LOGGER.info("\n")
                                return
                        else:
                                if tokenSymbol and tokenAddress:
                                        if tokenAddress not in token_already_got:
                                                WEB3_IN_USE = True
                                                if max_concurrent_tokens == 0:
                                                        tokenMonitor = TokenMonitor(tokenAddress = tokenAddress, tokenSymbol = tokenSymbol)
                                                        threadList.append(tokenMonitor)
                                                        tokenMonitor.start()
                                                else:
                                                        if len(threadList) < max_concurrent_tokens:
                                                                tokenMonitor = TokenMonitor(tokenAddress = tokenAddress, tokenSymbol = tokenSymbol)
                                                                threadList.append(tokenMonitor)
                                                                tokenMonitor.start()
                                                        else:
                                                                for i in range(0, len(threadList)):
                                                                        if threadList[i].stop == True:
                                                                                threadList[i].join()
                                                                                del threadList[i]
                                                                if len(threadList) < max_concurrent_tokens:
                                                                        # print("C'est OK pour les threads")
                                                                        tokenMonitor = TokenMonitor(tokenAddress = tokenAddress, tokenSymbol = tokenSymbol)
                                                                        threadList.append(tokenMonitor)
                                                                        tokenMonitor.start()

        if tokenAddress:            
                token_already_got.append(tokenAddress)
        
        return

async def main():
    while True:
            await asyncio.sleep(60)

################# Start the telegram client #################
client.start()
client.loop.run_until_complete(main())