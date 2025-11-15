# star_craft/bridge_listener.py
# Author: Senior Blockchain Architect

import os
import time
import logging
import json
from typing import Dict, Any, Optional

from web3 import Web3
from web3.contract import Contract
from web3.logs import DISCARD
from requests.exceptions import ConnectionError, Timeout
from dotenv import load_dotenv

# --- Configuration & Setup ---

# Load environment variables from .env file
load_dotenv()

# Setup structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(module)s.%(funcName)s] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# --- Constants ---

# These would typically be complex ABIs loaded from JSON files.
# For this simulation, we define a minimal ABI for the event we are interested in.
SOURCE_CHAIN_BRIDGE_ABI = json.loads('''
[
    {
        "anonymous": false,
        "inputs": [
            {
                "indexed": true,
                "internalType": "address",
                "name": "sender",
                "type": "address"
            },
            {
                "indexed": true,
                "internalType": "address",
                "name": "recipient",
                "type": "address"
            },
            {
                "indexed": false,
                "internalType": "uint256",
                "name": "amount",
                "type": "uint256"
            },
            {
                "indexed": false,
                "internalType": "uint256",
                "name": "nonce",
                "type": "uint256"
            }
        ],
        "name": "TokensLocked",
        "type": "event"
    }
]
''')

DESTINATION_CHAIN_BRIDGE_ABI = json.loads('''
[
    {
        "inputs": [
            {
                "internalType": "address",
                "name": "recipient",
                "type": "address"
            },
            {
                "internalType": "uint256",
                "name": "amount",
                "type": "uint256"
            },
            {
                "internalType": "uint256",
                "name": "sourceNonce",
                "type": "uint256"
            }
        ],
        "name": "unlockTokens",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]
''')

# --- Class Definitions ---

class ChainConnector:
    """Manages the connection to a single blockchain node via Web3.py."""

    def __init__(self, rpc_url: str, chain_name: str):
        """
        Initializes the connector for a specific chain.
        Args:
            rpc_url (str): The HTTP RPC endpoint for the blockchain node.
            chain_name (str): A human-readable name for the chain (e.g., 'Sepolia').
        """
        if not rpc_url:
            raise ValueError(f"RPC URL for {chain_name} cannot be empty.")
        self.rpc_url = rpc_url
        self.chain_name = chain_name
        self.web3: Optional[Web3] = None
        self.connect()

    def connect(self) -> None:
        """Establishes a connection to the blockchain node."""
        try:
            self.web3 = Web3(Web3.HTTPProvider(self.rpc_url))
            if self.is_connected():
                logging.info(f"Successfully connected to {self.chain_name} at {self.rpc_url}")
            else:
                raise ConnectionError("Failed to connect after initialization.")
        except (ConnectionError, Timeout) as e:
            logging.error(f"Failed to connect to {self.chain_name}: {e}")
            self.web3 = None

    def is_connected(self) -> bool:
        """Checks if the connection to the node is active."""
        return self.web3 is not None and self.web3.is_connected()

    def get_contract(self, address: str, abi: Dict) -> Optional[Contract]:
        """Returns a Web3 contract instance if connected."""
        if not self.is_connected():
            logging.warning(f"Cannot get contract; not connected to {self.chain_name}.")
            return None
        if not Web3.is_address(address):
            logging.error(f"Invalid contract address provided for {self.chain_name}: {address}")
            return None
        return self.web3.eth.contract(address=Web3.to_checksum_address(address), abi=abi)

    def get_latest_block_number(self) -> Optional[int]:
        """Fetches the most recent block number."""
        if not self.is_connected():
            logging.warning(f"Cannot get block number; not connected to {self.chain_name}.")
            return None
        try:
            return self.web3.eth.block_number
        except Exception as e:
            logging.error(f"Error fetching block number from {self.chain_name}: {e}")
            return None

class EventProcessor:
    """Processes and validates events fetched from the source chain."""

    def __init__(self):
        # In a real system, this would be a persistent database (e.g., Redis, PostgreSQL)
        self.processed_nonces = set()
        logging.info("EventProcessor initialized with in-memory state for nonces.")

    def process_log(self, log: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parses a raw log entry, validates it, and checks for replays.
        Args:
            log (Dict[str, Any]): A raw log entry from a web3 filter.
        Returns:
            Optional[Dict[str, Any]]: A dictionary with structured event data if valid, else None.
        """
        try:
            args = log.get('args', {})
            nonce = args.get('nonce')

            # Edge Case: Check if the event has a nonce
            if nonce is None:
                logging.warning(f"Skipping event with no nonce. TxHash: {log.get('transactionHash').hex()}")
                return None

            # Edge Case: Replay attack prevention
            if nonce in self.processed_nonces:
                logging.warning(f"Replay detected. Nonce {nonce} has already been processed. Skipping.")
                return None

            # Basic validation of expected fields
            required_fields = ['recipient', 'amount', 'nonce']
            if not all(field in args for field in required_fields):
                logging.error(f"Event log is missing required fields. Log: {log}")
                return None

            processed_event = {
                'recipient': args['recipient'],
                'amount': args['amount'],
                'source_nonce': nonce,
                'tx_hash': log.get('transactionHash').hex(),
                'block_number': log.get('blockNumber')
            }

            # Mark this nonce as processed to prevent replays
            self.processed_nonces.add(nonce)
            logging.info(f"Successfully validated and processed event for nonce {nonce}.")
            return processed_event

        except Exception as e:
            logging.error(f"An unexpected error occurred during log processing: {e}")
            return None

class TransactionSubmitter:
    """Simulates the submission of transactions to the destination chain."""

    def __init__(self, chain_connector: ChainConnector, bridge_contract: Contract):
        """
        Args:
            chain_connector (ChainConnector): Connector for the destination chain.
            bridge_contract (Contract): The bridge contract instance on the destination chain.
        """
        self.connector = chain_connector
        self.contract = bridge_contract
        # In a real application, this would be loaded securely (e.g., from AWS KMS, HashiCorp Vault)
        # Here, we simulate it.
        self.validator_address = "0xAb5801a7D398351b8bE11C439e05C5B3259aeC9B" # Simulated validator address
        logging.info(f"TransactionSubmitter initialized for contract {self.contract.address} on {self.connector.chain_name}.")

    def submit_unlock_transaction(self, event_data: Dict[str, Any]) -> bool:
        """
        Builds and 'sends' a transaction to unlock tokens on the destination chain.
        This is a simulation and will not actually send a real transaction.

        Args:
            event_data (Dict[str, Any]): The processed data from the source chain event.
        Returns:
            bool: True if the simulated submission was successful, False otherwise.
        """
        if not self.connector.is_connected():
            logging.error("Cannot submit transaction: destination chain is not connected.")
            return False

        try:
            recipient = event_data['recipient']
            amount = event_data['amount']
            nonce = event_data['source_nonce']

            logging.info(f"Preparing 'unlockTokens' transaction for recipient {recipient} with amount {amount} and nonce {nonce}.")

            # --- SIMULATION SECTION ---
            # In a real-world scenario, you would do the following:
            # 1. Get the validator's nonce: `nonce = web3.eth.get_transaction_count(self.validator_address)`
            # 2. Estimate gas: `gas_estimate = self.contract.functions.unlockTokens(...).estimate_gas(...)`
            # 3. Build the transaction dictionary.
            # 4. Sign the transaction: `signed_txn = web3.eth.account.sign_transaction(txn, private_key)`
            # 5. Send raw transaction: `tx_hash = web3.eth.send_raw_transaction(signed_txn.rawTransaction)`
            # 6. Wait for receipt: `receipt = web3.eth.wait_for_transaction_receipt(tx_hash)`

            # For this simulation, we will just log the intended action.
            print("--- SIMULATED TRANSACTION SUBMISSION ---")
            print(f"  Chain:         {self.connector.chain_name}")
            print(f"  Contract:      {self.contract.address}")
            print(f"  Function:      unlockTokens")
            print(f"  Recipient:     {recipient}")
            print(f"  Amount:        {amount}")
            print(f"  Source Nonce:  {nonce}")
            print("------------------------------------------")

            # Simulate a short delay as if a real transaction is being processed
            time.sleep(2)

            logging.info(f"Simulated transaction for source nonce {nonce} successfully submitted.")
            return True

        except KeyError as e:
            logging.error(f"Missing key in event_data for transaction submission: {e}")
            return False
        except Exception as e:
            logging.error(f"Failed to submit unlock transaction for nonce {event_data.get('source_nonce')}: {e}")
            return False

class CrossChainBridgeListener:
    """The main orchestrator for listening to bridge events and relaying them."""

    def __init__(self, config: Dict[str, str]):
        """
        Initializes the entire listener service.
        Args:
            config (Dict[str, str]): A dictionary containing configuration details.
        """
        self.config = config
        self.source_connector = ChainConnector(config['source_rpc'], 'SourceChain')
        self.dest_connector = ChainConnector(config['dest_rpc'], 'DestinationChain')
        
        self.source_bridge_contract = self.source_connector.get_contract(
            config['source_contract_address'], SOURCE_CHAIN_BRIDGE_ABI
        )
        self.dest_bridge_contract = self.dest_connector.get_contract(
            config['dest_contract_address'], DESTINATION_CHAIN_BRIDGE_ABI
        )

        self.event_processor = EventProcessor()
        self.tx_submitter = TransactionSubmitter(self.dest_connector, self.dest_bridge_contract)

        self.is_running = False
        self.last_checked_block = int(config.get('start_block', self.source_connector.get_latest_block_number() - 10))
        logging.info(f"CrossChainBridgeListener initialized. Will start scanning from block {self.last_checked_block}.")

    def check_initialization(self) -> bool:
        """Checks if all components were initialized correctly."""
        if not self.source_connector.is_connected() or not self.dest_connector.is_connected():
            logging.critical("One or both chains are not connected. Aborting.")
            return False
        if not self.source_bridge_contract or not self.dest_bridge_contract:
            logging.critical("Could not instantiate one or both bridge contracts. Check addresses and ABIs. Aborting.")
            return False
        return True

    def poll_for_events(self) -> None:
        """The main event loop that polls for new 'TokensLocked' events."""
        if not self.check_initialization():
            return

        self.is_running = True
        logging.info("Starting event polling loop...")

        while self.is_running:
            try:
                latest_block = self.source_connector.get_latest_block_number()
                if latest_block is None:
                    logging.warning("Could not fetch latest block from source chain. Retrying after delay.")
                    time.sleep(30) # Longer delay on RPC failure
                    continue

                # Edge Case: Avoid re-scanning the same block repeatedly
                if self.last_checked_block >= latest_block:
                    time.sleep(10) # Wait for a new block
                    continue

                # Scan a safe range of blocks (from last checked + 1 to latest)
                from_block = self.last_checked_block + 1
                to_block = latest_block
                
                logging.info(f"Scanning for 'TokensLocked' events from block {from_block} to {to_block}...")

                event_filter = self.source_bridge_contract.events.TokensLocked.create_filter(
                    fromBlock=from_block,
                    toBlock=to_block
                )
                
                logs = event_filter.get_all_entries()

                if not logs:
                    logging.info("No new 'TokensLocked' events found in this range.")
                else:
                    logging.info(f"Found {len(logs)} new event(s) to process.")
                    for log in logs:
                        processed_event = self.event_processor.process_log(log)
                        if processed_event:
                            self.tx_submitter.submit_unlock_transaction(processed_event)
                
                # Update the last checked block to avoid re-scanning
                self.last_checked_block = to_block

                # Polling interval
                time.sleep(15)

            except KeyboardInterrupt:
                self.stop()
            except Exception as e:
                logging.error(f"An error occurred in the main polling loop: {e}", exc_info=True)
                time.sleep(60) # Wait longer after a critical error

    def stop(self) -> None:
        """Stops the event listener gracefully."""
        logging.info("Shutdown signal received. Stopping listener...")
        self.is_running = False

# --- Main Execution ---

def main():
    """Main function to set up and run the listener."""
    # Configuration is loaded from environment variables for security and flexibility.
    # See README.md for how to set up the .env file.
    config = {
        'source_rpc': os.getenv('SOURCE_CHAIN_RPC_URL'),
        'dest_rpc': os.getenv('DESTINATION_CHAIN_RPC_URL'),
        'source_contract_address': os.getenv('SOURCE_CONTRACT_ADDRESS'),
        'dest_contract_address': os.getenv('DESTINATION_CONTRACT_ADDRESS'),
        'start_block': os.getenv('START_BLOCK', '0')
    }

    # Validate essential configuration
    for key, value in config.items():
        if key != 'start_block' and not value:
            logging.critical(f"Missing configuration for '{key}' in environment variables. Please check your .env file.")
            return

    listener = CrossChainBridgeListener(config)
    listener.poll_for_events()

if __name__ == "__main__":
    main()

# @-internal-utility-start
def format_timestamp_4251(ts: float):
    """Formats a unix timestamp into ISO format. Updated on 2025-11-15 19:00:37"""
    import datetime
    dt_object = datetime.datetime.fromtimestamp(ts)
    return dt_object.isoformat()
# @-internal-utility-end

