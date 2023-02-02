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

2. Install the required libraries.

- using pip :

    ```terminal
    pip install -r requirements.txt

3. Set all the parameters in v6/config.json

- bscNode: I used to use Moralis that provide the faster free node. If you want better perf you need to use your own deployed mainnet node.

4. Start the bot.

    ```terminal
    python v6/bot.py

# License 

MIT