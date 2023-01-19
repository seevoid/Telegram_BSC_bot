from web3 import Web3



globalWeb3 = Web3(Web3.WebsocketProvider(bscNode))



def sell(tokenAddress, tokenSymbol, previous_step_sell):
    global GLOBAL_PROGRESSION
    global IN_PROGRESS

    contract_id = globalWeb3.toChecksumAddress(tokenAddress)
    contract = globalWeb3.eth.contract(address=pancakeSwapRouterAddress, abi=pancakeABI)
    sellTokenContract = globalWeb3.eth.contract(contract_id, abi=sellAbi)
    LOGGER.info("[SELL] Balance of {symbol}: {balance}".format(symbol = tokenSymbol, balance = str(TOKEN_BALANCE)))

    tokenAmount = float(TOKEN_BALANCE)
    tokenValue = globalWeb3.toWei(tokenAmount, 'ether')

    #Approve Token before Selling
    tokenValue2 = globalWeb3.fromWei(tokenValue, 'ether')

    LOGGER.info(f"[SELL] Swapping {tokenValue2} {tokenSymbol} for BNB")

    sellSucceed = False

    counterSellRetry = 0
    try:
        while not sellSucceed:
            #Swaping exact Token for ETH 
            pancakeswap2_txn = contract.functions.swapExactTokensForETHSupportingFeeOnTransferTokens(
                    TOKEN_BALANCE ,SLIPPAGE_SELL, 
                    [contract_id, BNBTokenAddress],
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
    price = getTokenPrice(tokenAddress)
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