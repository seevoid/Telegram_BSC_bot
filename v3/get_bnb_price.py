
from bs4 import BeautifulSoup
import requests

req = requests.get("https://coin360.com/coin/binance-coin-bnb")

soup = BeautifulSoup(req.text, "html.parser")

text = soup.find_all("div", {"class": "CoinPageHead__PriceUsd"})[0].text[1:-1]

print(float(text))

