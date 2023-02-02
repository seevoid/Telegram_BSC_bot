# Telegram BSC Bot



# What is this?

This is trading bot developed in python using web3 and telegram.
The bot monitor the telegram channel of your choice. The best thing is to monitor a telegram channel that gives you the next future listing of tokens in CoinGecko / Coin Market Cap.

When the bot get a token, it buys it and then sell it when threshold.

You can configure a lot of parameters : see config.json in v6 folder (last version).

# How to use?

1. Clone this repo.

    ```terminal
    git clone https://github.com/seevoid/Telegram_BSC_bot.git

1. Activate virtual env.
    - on Windows :
        ```terminal
        ./telegram_bsc_bot_env/Scripts/activate

3. Install the required libraries.

    - using pip :

        ```terminal
        pip install -r requirements.txt

4. Set all the parameters in v6/config.json

    - bscNode: I used to use Moralis that provide the faster free node. If you want better perf you need to use your own deployed mainnet node.
    - bot_token: You need to generate a telegram bot token
    - max_concurrent_tokens: The number of tokens to monitor in the same time (I use multi threading)
    - gasPrice / gasAmount: You'll probably have to play with those values to be the fast as possible to sell/buy tokens
    - lowThresholdSell: The bot sell if the token value is lowThresholdSell*buyingValue
    - highThresholdSell: The bot sell if the token value is buyingValue*0.1*highThresholdSell. But theres are steps of 0.1, so you can't go below after each step passed.

5. Start the bot.

    ```terminal
    python v6/bot.py

# License 

MIT