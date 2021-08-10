from web3 import Web3
import json
import requests

ABI_ENDPOINT = 'https://api.etherscan.io/api?module=contract&action=getabi&apikey=MSXNM2STXHIDHBS9ZAHA4CS5E5FW5U3VU2&address='
url = "https://eth-mainnet.alchemyapi.io/v2/jUHFvIpnWEkKMCAkVD8A9EgU7M-hooe-"
web3 = Web3(Web3.HTTPProvider(url))

def initWeb3():
    print('Initializing web3...')
    global web3
    web3 = Web3(Web3.HTTPProvider(url))
    print('web3 intialized')

def getContractABI(contract_address):
    json_res = {}
    response = requests.get('%s%s'%(ABI_ENDPOINT, contract_address))
    response_json = response.json()
    if response_json.get('result') == 'Contract source code not verified':
        json_res = [{"constant":True,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"payable":False,"stateMutability":"view","type":"function"}]
    else:
        json_res = json.loads(response_json['result'])
    return json_res

def getTotalSupplyAtWrappedContract(contract_address, wrapped_contract_address):
    total_supply = 0
    abi_json = getContractABI(contract_address)
    if abi_json:
        ContractFactory = web3.eth.contract(abi=abi_json)
        contract = ContractFactory(web3.toChecksumAddress(contract_address))
        total_supply = contract.functions.balanceOf(web3.toChecksumAddress(wrapped_contract_address)).call()
    return total_supply