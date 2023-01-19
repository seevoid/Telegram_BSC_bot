import os
import time
from datetime import datetime
import re
import asyncio
from web3.middleware import geth_poa_middleware
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

os.system("clear")

from utils import *

from pythonpancakes import PancakeSwapAPI

ps = PancakeSwapAPI()

# clearConsole = lambda: os.system('cls' if os.name in ('nt', 'dos') else 'clear')
# clearConsole()

LOGGER.header(NAME_OF_BOT_FOR_DISPLAY)
LOGGER.info("\n")

LOGGER.general("Telegram Channel: {channel}".format(channel = channelId))
LOGGER.general("Amount to Snipe BNB: " + str(snipeBNBAmount))
LOGGER.general("Amount to Snipe BUSD: " + str(snipeBUSDAmount))
LOGGER.general("Amount to Snipe USDT: " + str(snipeUSDTAmount))
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

globalWeb3 = Web3(Web3.WebsocketProvider(bscNode))
globalWeb3.middleware_onion.inject(geth_poa_middleware, layer=0)

################# Global variables #################
BNBTokenAddress = Web3.toChecksumAddress("0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c")
USDTTokenAddress = Web3.toChecksumAddress("0x55d398326f99059ff775485246999027b3197955")
BUSDTokenAddress = Web3.toChecksumAddress("0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56")
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
BUSDContract = globalWeb3.eth.contract(BUSDTokenAddress, abi=sellAbi)
INITIAL_BUSD_BALANCE = globalWeb3.fromWei(BUSDContract.functions.balanceOf(walletAddress).call(),'ether')
USDTContract = globalWeb3.eth.contract(USDTTokenAddress, abi=sellAbi)
INITIAL_USDT_BALANCE = globalWeb3.fromWei(USDTContract.functions.balanceOf(walletAddress).call(),'ether')

LOGGER.info("\n")
LOGGER.good("##")
LOGGER.good("###### BNB Balance: {balance} BNB".format(balance = str(INITIAL_BNB_BALANCE)))
LOGGER.good("###### BUSD Balance: {balance} BUSD".format(balance = str(INITIAL_BUSD_BALANCE)))
LOGGER.good("###### USDT Balance: {balance} USDT".format(balance = str(INITIAL_USDT_BALANCE)))
LOGGER.good("##")
LOGGER.info("\n")

liquidityTypeAmount = {"BNB": {"address": BNBTokenAddress, "snipeAmount": snipeBNBAmount},
                       "BUSD": {"address": BUSDTokenAddress, "snipeAmount": snipeBUSDAmount},
                       "USDT": {"address": USDTTokenAddress, "snipeAmount": snipeUSDTAmount}
                       }


BUY_PRICE = 0
TOKEN_BALANCE = 0
IN_PROGRESS = False

def monitor(tokenAddress, tokenSymbol, liquidityType):
    previous_step_sell = float('-inf')
    listStep = []
    step_sell = 1.1
    step = 0.1
    for i in range(1,8):
        listStep.append(1 + i*step)
    while(True):
        try:
            price = getTokenPrice(tokenAddress, liquidityType)
        except Exception as e:
            LOGGER.fail("[MONITOR] Error when get price in loop thread !")
            LOGGER.fail("e: {e}".format(e = str(e)))

        if previous_step_sell != float('-inf'):
            if price*TOKEN_BALANCE < previous_step_sell * (BUY_PRICE*TOKEN_BALANCE):
                LOGGER.info("{color}[MONITOR] Sell for step {step} for {symbol} : {address}".format(color = bcolors.OKGREEN, step = str(previous_step_sell), \
                        symbol = tokenSymbol, address = tokenAddress))
                LOGGER.info("price before sell : {price}".format(price = price))
                if not TEST_MODE:
                    sell(tokenAddress, tokenSymbol, previous_step_sell, liquidityType)
                    break

        if price*TOKEN_BALANCE > (BUY_PRICE*TOKEN_BALANCE) * step_sell:
            step_sell, previous_step_sell = getStep(price, listStep, step)
            if previous_step_sell != float('-inf'):
                LOGGER.info("{color}[MONITOR] Multiplier {step} successfully passed ({priceStep}) for {symbol} : {address} ! Next step : {sellingPrice1}".\
                format(color = bcolors.OKCYAN, step = str(previous_step_sell), priceStep = str(BUY_PRICE * previous_step_sell), \
                        symbol = tokenSymbol, address = tokenAddress, sellingPrice1 = BUY_PRICE * step_sell))
            if step_sell >= listStep[-1]:
                LOGGER.info("price before sell : {price}".format(price = price))
                if not TEST_MODE:
                    sell(tokenAddress, tokenSymbol, previous_step_sell, liquidityType)
                    break

        
        if (price*TOKEN_BALANCE <= (BUY_PRICE*TOKEN_BALANCE) * lowThresholdSell):
            if price*TOKEN_BALANCE <= (BUY_PRICE*TOKEN_BALANCE) * lowThresholdSell:
                LOGGER.info("price : {price}".format(price = str(price)))
                LOGGER.info("BUY_PRICE * lowThresholdSell : {low}".format(low = str((BUY_PRICE*TOKEN_BALANCE) * lowThresholdSell)))
                LOGGER.fail("[MONITOR] Sell at price:{price} ,because lowThresholdSell reached for {symbol} : {address}".format(symbol = tokenSymbol,\
                        price = price, address = tokenAddress))
                if not TEST_MODE:
                    sell(tokenAddress, tokenSymbol, previous_step_sell, liquidityType)
                    break

        time.sleep(0.5)

def getBNBPrice():
    req = requests.get("https://coin360.com/coin/binance-coin-bnb")
    soup = BeautifulSoup(req.text, "html.parser")
    BNBPrice = soup.find_all("div", {"class": "CoinPageHead__PriceUsd"})[0].text[1:-1]
    BNBPrice = float(BNBPrice)
    return BNBPrice
        

def getStep(price, listStep, step):
    for s in listStep:
        if (price*TOKEN_BALANCE) > ((BUY_PRICE*TOKEN_BALANCE) * s) and (price*TOKEN_BALANCE) < ((BUY_PRICE*TOKEN_BALANCE) * (s+step)):
            step_sell = s+step
            previous_step_sell = s
            return (step_sell, previous_step_sell)

def getTokenPricePancake(tokenAddress):
    tokens = ps.tokens(tokenAddress)
    price = tokens["data"]["price"]
    return float(price)

def getPair(tokenAddress):
    tokenAddress = globalWeb3.toChecksumAddress(tokenAddress)
    contract = globalWeb3.eth.contract(address=pancakeSwapFactoryAddress, abi=listeningABI)
    pairAddress = contract.functions.getPair(WBNBAdress, tokenAddress).call()
    return pairAddress

def getReserves(pairAddressforReserves):  # fundamental code for liquidity detection
    pairAddressforReserves = globalWeb3.toChecksumAddress(pairAddressforReserves)
    router = globalWeb3.eth.contract(address=pairAddressforReserves, abi=pairABI)
    pairReserves = router.functions.getReserves().call()
    token0 = router.functions.token0().call()
    token1 = router.functions.token1().call()
    return pairReserves, token0, token1

def isBNBLiquidity(tokenAddress):
    pairAddress = getPair(tokenAddress)
    pairReserves, token0, token1 = getReserves(pairAddress)
    BNBReserve = 0
    TokenReserve = 0

    if token0 == WBNBAdress or token1 == WBNBAdress:
        return True
    else:
        return False

def getTokenPrice(tokenAddress, liquidity):
    pairAddress = getPair(tokenAddress)
    pairReserves, token0, token1 = getReserves(pairAddress)
    LiqReserve = 0
    TokenReserve = 0

    if token0 == WBNBAdress:
        LiqReserve = pairReserves[0]
        TokenReserve = pairReserves[1]
    else:
        LiqReserve = pairReserves[1]
        TokenReserve = pairReserves[0]

    liqPrice = getTokenPricePancake(liquidityTypeAmount[liquidity]["address"])
    tokenPrice = (liqPrice * LiqReserve) / TokenReserve

    return tokenPrice

def buy(tokenAddress, tokenSymbol, liquidityType):
    global END_TIME
    global BEGIN_TIME
    global BUY_PRICE, TOKEN_BALANCE
    global IN_PROGRESS
    IN_PROGRESS = True
    try:
        if(tokenAddress != None):
            LOGGER.info("[BUY] Buying {symbol} ({address}) for {amount} BNB".format(symbol = tokenSymbol, address = tokenAddress, amount = snipeBNBAmount))
            tokenToBuy = globalWeb3.toChecksumAddress(tokenAddress)
            pcsContract = globalWeb3.eth.contract(address=pancakeSwapRouterAddress, abi=pancakeABI)
            nonce = globalWeb3.eth.get_transaction_count(walletAddress)

            pairAddress = liquidityTypeAmount[liquidityType]["address"]
            snipeAmount = liquidityTypeAmount[liquidityType]["snipeAmount"]
            if liquidityType != "BNB":
                BNBPrice = getBNBPrice()
                if liquidityType != "BUSD":
                    snipeAmount = round(snipeBUSDAmount/BNBPrice, 4)
                if liquidityType != "USDT":
                    snipeAmount = round(snipeUSDTAmount/BNBPrice, 4)
            
            print("snipeAmount : ",snipeAmount)
            pancakeswap2_txn = pcsContract.functions.swapExactETHForTokensSupportingFeeOnTransferTokens(
                    0, # Set to 0 or specify min number of tokens - setting to 0 just buys X amount of tokens for whatever BNB specified
                    [pairAddress,tokenToBuy],
                    walletAddress,
                    (int(time.time()) + transactionRevertTimeSeconds)
                    ).buildTransaction({
                    'from': walletAddress,
                    'value': globalWeb3.toWei(float(snipeAmount), 'ether'),
                    'gas': gasAmount,
                    'gasPrice': globalWeb3.toWei(gasPrice,'gwei'),
                    'nonce': nonce,
            })
            tokenToBuyContract = globalWeb3.eth.contract(tokenToBuy, abi=pancakeABI)
            try:
                signed_txn = globalWeb3.eth.account.sign_transaction(pancakeswap2_txn, walletPrivateKey)
                tx_token = globalWeb3.eth.send_raw_transaction(signed_txn.rawTransaction) #BUY THE TOKEN
                response = globalWeb3.eth.wait_for_transaction_receipt(transaction_hash=tx_token, timeout=30, poll_latency=0.01)
                if response["status"] == 1:
                    END_TIME = time.time()
                    buyingSucceed = True
                else:
                    buyingSucceed = False
            except Exception as ex:
                #Get Token Balance
                TOKEN_BALANCE = tokenToBuyContract.functions.balanceOf(walletAddress).call()
                if TOKEN_BALANCE > 0:
                    buyingSucceed = True
                else:
                    BUY_PRICE = None
                    LOGGER.fail("[BUY] FAILED when buying {symbol} | Error: {error}s".format(symbol = tokenSymbol, error = str(ex)))
                    IN_PROGRESS = False
                    return False

            if buyingSucceed:
                getPriceFinished = False
                while not getPriceFinished:
                    try:
                        BUY_PRICE = getTokenPrice(tokenAddress, liquidityType)
                    except Exception as e:
                        LOGGER.fail("e : {error}".format(error=e))
                        getPriceFinished = False
                    else:
                        getPriceFinished = True
                try:
                    LOGGER.info("[BUY] Time between alert and buy : {time}s".format(time = str(round((END_TIME - BEGIN_TIME),2))))
                    LOGGER.info("[BUY] Buy Price: {price}".format(price = str(BUY_PRICE)))
                    LOGGER.info("[BUY] Low threshold: {low}".format(low=str(BUY_PRICE*lowThresholdSell)))
                except Exception as e:
                    LOGGER.fail("e: " + str(e))

                #Get BNB price
                BNBPrice = getBNBPrice()
                #Get Token Balance
                TOKEN_BALANCE = tokenToBuyContract.functions.balanceOf(walletAddress).call()
                LOGGER.good("[BUY] Successfully bought $" + tokenSymbol + " for " + str(snipeBNBAmount) + " BNB ({dollarz}$) || \
Adress : ".format(dollarz = str(round(snipeBNBAmount*BNBPrice, 2))) + tokenAddress)
                if MUSIC_ALERT:
                    mixer.music.play()
                    time.sleep(10)
                    mixer.music.stop()
                try:
                    # Check if it's already approved
                    owner = globalWeb3.toChecksumAddress(walletAddress)
                    spender = globalWeb3.toChecksumAddress(pancakeSwapRouterAddress)
                    resultApproved = tokenToBuyContract.functions.allowance(owner, spender).call()
                except Exception as e:
                    LOGGER.fail("[BUY] Error when trying to know if it's approved or not | Error: {error}.".format(error = str(e)))
                    IN_PROGRESS = False
                    return False
                if int(resultApproved) == 0:
                    # Approve token for future selling
                    try:
                        approve = tokenToBuyContract.functions.approve(pancakeSwapRouterAddress, TOKEN_BALANCE*10).buildTransaction({
                                'from': walletAddress,
                                'gasPrice': globalWeb3.toWei(gasPrice,'gwei'),
                                'nonce': globalWeb3.eth.get_transaction_count(walletAddress),
                                })
                        signed_txn = globalWeb3.eth.account.sign_transaction(approve, private_key=walletPrivateKey)
                        tx_token = globalWeb3.eth.send_raw_transaction(signed_txn.rawTransaction)
                        LOGGER.good("[BUY] Approved Token {symbol} for future selling".format(symbol = tokenSymbol))
                        LOGGER.info("[MONITOR] Start monitoring the price")
                        LOGGER.info("\n")
                        LOGGER.header("---------------------------------------------------------------------------------------")
                        LOGGER.info("\n")
                            
                    except Exception as e:
                        LOGGER.fail("[BUY] FAILED when approving {symbol} | Error: {error}".format(symbol = tokenSymbol, error = str(e)))
                        LOGGER.info("\n")
                        LOGGER.header("---------------------------------------------------------------------------------------")
                        LOGGER.info("\n")
                        IN_PROGRESS = False
                        return False
                else:
                    LOGGER.good("[BUY] Token {symbol} already approved for future selling".format(symbol = tokenSymbol))
                    LOGGER.info("[MONITOR] Start monitoring the price")
                    LOGGER.info("\n")
                    LOGGER.header("---------------------------------------------------------------------------------------")
                    LOGGER.info("\n")
                
                return True
            else:
                LOGGER.fail("[BUY] FAILED when bought $" + tokenSymbol + " for " + str(snipeBNBAmount) + " BNB || Adress : " + tokenAddress)
                LOGGER.info("\n")
                LOGGER.header("---------------------------------------------------------------------------------------")
                LOGGER.info("\n")
                IN_PROGRESS = False
                return False
    except Exception as ex:
        LOGGER.fail("[BUY] Transaction failed: likely not enough gas.")
        LOGGER.fail("[BUY] FAILED when bought: {error}".format(error = str(ex)))
        LOGGER.info("\n")
        LOGGER.header("---------------------------------------------------------------------------------------")
        LOGGER.info("\n")
        IN_PROGRESS = False
        return False

def sell(tokenAddress, tokenSymbol, previous_step_sell, liquidityType):
    global GLOBAL_PROGRESSION
    global IN_PROGRESS

    contract_id = globalWeb3.toChecksumAddress(tokenAddress)
    contract = globalWeb3.eth.contract(address=pancakeSwapRouterAddress, abi=pancakeABI)
    LOGGER.info("[SELL] Balance of {symbol}: {balance}".format(symbol = tokenSymbol, balance = str(TOKEN_BALANCE)))

    tokenAmount = float(TOKEN_BALANCE)
    tokenValue = globalWeb3.toWei(tokenAmount, 'ether')

    #Approve Token before Selling
    tokenValue2 = globalWeb3.fromWei(tokenValue, 'ether')

    LOGGER.info(f"[SELL] Swapping {tokenValue2} {tokenSymbol} for BNB")

    sellSucceed = False

    counterSellRetry = 0
    try:
        pairAddress = liquidityTypeAmount[liquidityType]["address"]
        while not sellSucceed:
            #Swaping exact Token for ETH 
            pancakeswap2_txn = contract.functions.swapExactTokensForETHSupportingFeeOnTransferTokens(
                    TOKEN_BALANCE ,SLIPPAGE_SELL, 
                    [contract_id, pairAddress],
                    walletAddress,
                    (int(time.time()) + 1000000)
                    ).buildTransaction({
                    'from': walletAddress,
                    'gasPrice': globalWeb3.toWei("7",'gwei'),
                    'nonce': globalWeb3.eth.get_transaction_count(walletAddress),
                    })
            
            signed_txn = globalWeb3.eth.account.sign_transaction(pancakeswap2_txn, private_key=walletPrivateKey)
            tx_token = globalWeb3.eth.send_raw_transaction(signed_txn.rawTransaction)
            time.sleep(3)
            response = globalWeb3.eth.wait_for_transaction_receipt(transaction_hash=tx_token, timeout=30, poll_latency=0.1)
            if response["status"] == 1:
                sellSucceed = True
            else:
                sellSucceed = False
                LOGGER.fail("[SELL] FAILED when selling {symbol} : {address} ! Retrying Again...".format(symbol = tokenSymbol, address = tokenAddress))
            counterSellRetry += 1
            if counterSellRetry == 8:
                LOGGER.fail("[SELL] FAILED when selling {symbol} : {address} ! Too much tries...".format(symbol = tokenSymbol, address = tokenAddress))
                if MAIL_ALERT:
                    mail = Mail()
                    content = "$" + tokenSymbol + " : " + tokenAddress
                    mail.send(EMAIL, content, content)
                return
    except Exception as e:
        if MAIL_ALERT:
            mail = Mail()
            content = "$" + tokenSymbol + " : " + tokenAddress
            mail.send(EMAIL, content, content)
        LOGGER.fail("[SELL] FAILED when selling {symbol} : {address} !".format(symbol = tokenSymbol, address = tokenAddress))
        LOGGER.fail("[SELL] ERROR: {error}".format(error = str(e)))
        IN_PROGRESS = False
        return

    balance_now = get_balance_bnb()
    progression = balance_now - INITIAL_BNB_BALANCE
    price = getTokenPrice(tokenAddress, liquidityType)
    LOGGER.info("price : {price}".format(price = price))
    LOGGER.info("tokenAmount : {amount}".format(amount = tokenAmount))

    if sellSucceed:
        LOGGER.good("[SELL] Successfully Sold {symbol} : {address} for ({dollarz}$) at step {step}".format(symbol = tokenSymbol,\
            address = tokenAddress, dollarz = str(round(price*tokenAmount, 2)), step = str(previous_step_sell)))
    else:
        if MAIL_ALERT:
            mail = Mail()
            content = "$" + tokenSymbol + " : " + tokenAddress
            mail.send(EMAIL, content, content)
        LOGGER.fail("[SELL] FAILED when selling {symbol} : {address} !".format(symbol = tokenSymbol, address = tokenAddress))
        IN_PROGRESS = False
        return
    LOGGER.info("###")
    LOGGER.important("### GLOBAL PROGRESSION SINCE BEGINNING : {progression} ({dollarz}$)".format(progression = round(progression, 4), dollarz = round(float(progression)*float(getBNBPrice()), 2)))
    LOGGER.info("###")
    try:
        LOGGER.info("{color}###### BNB Balance: {balance} BNB".format(balance = str(round(get_balance_bnb(), 4))))
    except:
        IN_PROGRESS = False
        return
    LOGGER.info("###")
    LOGGER.info("\n")
    LOGGER.header("---------------------------------------------------------------------------------------")
    LOGGER.info("\n")
    IN_PROGRESS = False



WALLETS_TO_MONITOR = ["0x28d2c723018c7c1c064bd122e18290763b448287", "0x211925517b5d17be2540fac2df778e300274fbb4",\
 "0xefc09276e9b5a1f460a42200c4c45c19b7460916", "0x05337ba1598124c1539d2a1052efdc262440f352", "0x91343c0fe2ac825e8c3a0a392adad5d058b4ec60"]

WALLETS_TO_MONITOR = [w.lower() for w in WALLETS_TO_MONITOR]


# def log_loop(event_filter, poll_interval):
#     while True:
#         try:
#             block_hashes = globalWeb3.eth.get_filter_changes(event_filter.filter_id)
#         except:
#             pass
#         for block_hash in block_hashes:
#             block = globalWeb3.eth.get_block(block_hash.hex())
#             transactions = block['transactions']
#             try:
#                 for tx in transactions:
#                     tx_buff = globalWeb3.eth.get_transaction(tx)
#                     walletAddress = tx_buff['from']
#                     if walletAddress.lower() in WALLETS_TO_MONITOR:
#                         contract = globalWeb3.eth.contract(address=pancakeSwapRouterAddress, abi=pancakeABI)
#                         try:
#                             func_obj, func_params = contract.decode_function_input(tx_buff['input'])
#                         except:
#                             pass
#                         else:
#                             tokenAddress = globalWeb3.toChecksumAddress(func_params['path'][-1])
#                             if isBNBLiquidity(tokenAddress):
#                                 gasPrice = str(int(tx_buff['gasPrice'])/math.pow(10, 9))
#                                 now = datetime.now()
#                                 current_time = now.strftime("%H:%M:%S")
#                                 print("---------- FOUND ----------")
#                                 print('tokenAddress : ', tokenAddress)
#                                 print('walletAddress : ', walletAddress)
#                                 print('gasPrice : ', gasPrice)
#                                 print("Time : ", current_time)
#                                 print("---------------------------")
#                                 print("\n \n")
#             except Exception as e:
#                 pass
                
#         time.sleep(poll_interval)

# def main():
#     block_filter = globalWeb3.eth.filter('latest')
#     log_loop(block_filter, 0.1)

# if __name__ == '__main__':
#     main()


@client.on(events.NewMessage(chats = channelId))
async def new_message_listener(event):
    global BEGIN_TIME
    global threadList
    global IN_PROGRESS
    if not IN_PROGRESS:
        BEGIN_TIME = time.time()
        text = event.raw_text
        channel = event.chat.title

        if channel in ["Coinmarketcap Fastest Alerts", "Coingecko Fastest Alerts"]:
            channelType = 0
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
        elif channel == "BSCMultiSniper Alerts":
            channelType = 2
            regexOnlyNumbers = r"[0-9]+.[0-9]+"
            regexAddress = r"0x\S{40}"
            regexFirstAlert = r"🔴"
            regexSymbol = r'\x28[A-Za-z]*\x29'
            regexBuyFees = r"Buy fee: [0-9]+.[0-9]+%"
            regexSellFees = r"Sell fee: [0-9]+.[0-9]+%"
            matchesAddress = re.findall(regexAddress, text, re.MULTILINE)
            matchesFirstAlert = re.findall(regexFirstAlert, text, re.MULTILINE)
            matchesSymbol = re.findall(regexSymbol, text)
            matchesLiquidity = ["500.00"]
            matchesBuyFees = re.findall(regexBuyFees, text)
            matchesSellFees = re.findall(regexSellFees, text)
        elif channel =="CMC/CG Premium Alerts" or channel == "Mumus Gem Club":
            channelType = 1
            regexOnlyNumbers = r"[0-9]+.[0-9]+"
            regexAddress = r"0x\S{40}"
            regexFirstAlert1 = r"Solid profit expected, buy ASAP"
            regexFirstAlert2 = r"Might get botted, wait for dump!"
            regexSymbol = r'\x28\$*[A-Za-z]*\x29'
            regexBuyFees = r"Buy fee: [0-9]+.[0-9]+%"
            regexSellFees = r"Sell fee: [0-9]+.[0-9]+%"
            regexLiquidityBNB = r"WBNB"
            regexLiquidityBUSD = r"BUSD"
            regexLiquidityUSDT = r"USDT"
            matchesAddress = re.findall(regexAddress, text, re.MULTILINE)
            matchesFirstAlert = re.findall(regexFirstAlert1, text, re.MULTILINE)
            if not matchesFirstAlert:
                matchesFirstAlert = re.findall(regexFirstAlert2, text, re.MULTILINE)
            matchesSymbol = re.findall(regexSymbol, text)
            matchesLiquidityBNB = re.findall(regexLiquidityBNB, text)
            matchesLiquidityUSDT = re.findall(regexLiquidityUSDT, text)
            matchesLiquidityBUSD = re.findall(regexLiquidityBUSD, text)
            matchesBuyFees = re.findall(regexBuyFees, text)
            matchesSellFees = re.findall(regexSellFees, text)


        tokenAddress = None
        tokenSymbol = None
        liquidity = None

        # print("matchesFirstAlert :", matchesFirstAlert)
        # print("matchesAddress :", matchesAddress)
        # print("matchesSymbol :", matchesSymbol)

        if matchesFirstAlert:
            if len(matchesAddress) > 0:
                tokenAddress = matchesAddress[0]
            else:
                return

            if len(matchesSymbol) > 0:
                tokenSymbol = matchesSymbol[0]

            if channelType == 0:
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
            
            if channelType == 0:
                if len(matchesLiquidity) > 0:
                    liquidity = matchesLiquidity[0]
                    liquidity = float(liquidity[0:6])
                else:
                    LOGGER.info("\n")
                    LOGGER.info("[INFO] Liquidity not in BNB for {symbol} {address} !".format(symbol = tokenSymbol,\
                            address = tokenAddress))
                    LOGGER.info("\n")  
            elif channelType == 1:
                if len(matchesLiquidityBNB) > 0:
                    liquidityType = "BNB"
                if len(matchesLiquidityUSDT) > 0:
                    liquidityType = "USDT"
                    return
                if len(matchesLiquidityBUSD) > 0:
                    liquidityType = "BUSD"


            if channelType == 0:
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
                            resultBuy = buy(tokenAddress, tokenSymbol)
                            if resultBuy:
                                monitor(tokenAddress, tokenSymbol)
            else:
                if tokenAddress:
                    resultBuy = buy(tokenAddress, tokenSymbol, liquidityType)
                    if resultBuy:
                        monitor(tokenAddress, tokenSymbol, liquidityType)

                                                

        if tokenAddress:            
                token_already_got.append(tokenAddress)
        
        return

# async def main():
#     while True:
#         await asyncio.sleep(60)

################# Start the telegram client #################
client.start()
client.run_until_disconnected()