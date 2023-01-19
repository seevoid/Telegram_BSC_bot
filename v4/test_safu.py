import requests
import json

tokenAdress = "0x0bcd8bcc1411bc19747d0ab2f7a8b3a740b549d6"
URL = "https://app.staysafu.org/api" + "/simulatebuy?tokenAddress=" + tokenAdress

result = requests.get(URL)
result = json.loads(result.text)["result"]

# buyFees = result["buyFee"]
# sellFees = result["sellFee"]

print(result)

