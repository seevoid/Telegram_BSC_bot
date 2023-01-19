import requests
import json

def getFees(tokenAddress):
    buyFees = None
    sellFees = None
    URL = "https://app.staysafu.org/api" + "/simulatebuy?tokenAddress=" + tokenAddress
    result = requests.get(URL)
    try:
            result = json.loads(result.text)["result"]
    except:
            buyFees = -1
            sellFees = -1
    else:
            try:
                    buyFees = float(result["buyFee"])
                    sellFees = float(result["sellFee"])
            except Exception as e:
                    buyFees = -1
                    sellFees = -1
    return buyFees, sellFees


tokenAddress = "0xf2f087955684eabdf252a16c7b6620a1e3774515"

buyFees, sellFees = getFees(tokenAddress)

print("buyFees : ", buyFees)
print("sellFees : ", sellFees)