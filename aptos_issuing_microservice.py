import requests

# Replace with your Node URL and address details
NODE_URL = "https://fullnode.devnet.aptoslabs.com/v1"
PRIVATE_KEY = "0x678f98e8501f42c26598fad8172702c29660a8afaa949b1ffcdd0367656cb663"
MODULE_ADDRESS = "0xbea350440901118a6a5c369ace28249e19cb4d24affa1379b58a2ae1954fb9d2"
FUNCTION_NAME = "certsecure"

def get_account_sequence_number(address):
    """Fetches the sequence number (nonce) of the Aptos account."""
    response = requests.get(f"{NODE_URL}/accounts/{address}")
    if response.status_code == 200:
        account_info = response.json()
        return account_info['sequence_number']
    else:
        raise Exception("Failed to fetch account sequence number")

def submit_transaction(payload):
    """Submits the transaction to the Aptos blockchain."""
    headers = {"Content-Type": "application/json"}
    response = requests.post(f"{NODE_URL}/transactions", json=payload, headers=headers)
    if response.status_code == 202:
        print(f"Transaction submitted: {response.json()['hash']}")
    else:
        print(f"Failed to submit transaction: {response.text}")

def main():
    address = "0xYourAddress"  # Update this with your address
    sequence_number = get_account_sequence_number(address)
    
    # Define transaction payload
    payload = {
        "sender": address,
        "sequence_number": sequence_number,
        "max_gas_amount": 2000,
        "gas_unit_price": 1,
        "payload": {
            "type": "script_function_payload",
            "function": f"{MODULE_ADDRESS}::{FUNCTION_NAME}",
            "type_arguments": [],
            "arguments": []
        }
    }
    
    # Submit the transaction
    submit_transaction(payload)

if __name__ == "__main__":
    main()
