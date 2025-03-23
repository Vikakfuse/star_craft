# StarCraft: Cross-Chain Bridge Event Listener

A simulation of a robust, production-grade event listener for a cross-chain bridge. This component is designed to monitor events on a source blockchain (e.g., `TokensLocked`) and trigger corresponding actions on a destination blockchain (e.g., `unlockTokens`).

This script is built with a focus on modularity, error handling, and clear separation of concerns, reflecting the architectural principles of a real decentralized application backend.

## Concept

A cross-chain bridge allows users to transfer assets or data from one blockchain to another. A common mechanism is the "lock-and-mint" (or "lock-and-unlock") model:

1.  **Lock**: A user sends tokens to a bridge contract on the **Source Chain**. The contract locks these tokens and emits an event (`TokensLocked`) containing details of the transaction (recipient address on the destination chain, amount, etc.).
2.  **Relay**: A network of off-chain nodes, called **listeners** or **validators**, constantly monitors the Source Chain for these `TokensLocked` events.
3.  **Verify & Submit**: Upon detecting a valid event, a listener verifies it and submits a transaction to the bridge contract on the **Destination Chain**.
4.  **Unlock/Mint**: The Destination Chain's contract, upon receiving this validated request, mints or unlocks the equivalent amount of tokens and sends them to the specified recipient address.

This Python script simulates the critical **listener/validator** component (Step 2 and 3).

## Code Architecture

The system is designed with a multi-class architecture to ensure each component has a single, well-defined responsibility. This makes the system easier to test, maintain, and extend.

```
+------------------------------+
|   CrossChainBridgeListener   | (Orchestrator)
|------------------------------|
| - config: Dict               |
| - source_connector           | ------------------> +--------------------+
| - dest_connector             |           |         |   ChainConnector   |
| - event_processor            |           |         |--------------------|
| - tx_submitter               |           |         | - rpc_url: str     |
| - last_checked_block: int    |           |         | - web3: Web3       |
|------------------------------|           |         |--------------------|
| + poll_for_events()          |           |         | + connect()        |
| + stop()                     |           |         | + is_connected()   |
+------------------------------+           |         | + get_contract()   |
              |                          |         +--------------------+
              |                          |
              | (Validated Event)        v
              v
+------------------------------+
|      TransactionSubmitter    |
|------------------------------|
| - connector: ChainConnector  |         +--------------------+
| - contract: Contract         |         |   EventProcessor   |
|------------------------------|         |--------------------|
| + submit_unlock_transaction()| <------ | - processed_nonces | (Raw Log)
+------------------------------+  (Event)  |--------------------|
                                         | + process_log()    |
                                         +--------------------+
```

*   **`CrossChainBridgeListener`**: The main class that orchestrates the entire process. It initializes all other components, manages the main polling loop, and handles state like the last block scanned.
*   **`ChainConnector`**: A utility class responsible for managing the connection to a single blockchain node via its RPC endpoint. It encapsulates all `web3.py` connection logic.
*   **`EventProcessor`**: Responsible for taking raw event logs from the blockchain, parsing them, validating their structure, and preventing replay attacks by tracking processed nonces (transaction identifiers).
*   **`TransactionSubmitter`**: Simulates the final step. It takes processed event data and constructs/submits a corresponding transaction to the destination chain. In this simulation, it prints the transaction details instead of sending a real one.

## How it Works

1.  **Initialization**: The `main` function loads configuration from a `.env` file. This includes RPC URLs for both chains and the addresses of the bridge contracts.
2.  **Connection**: The `CrossChainBridgeListener` creates two instances of `ChainConnector`, one for the source chain and one for the destination chain, establishing connections.
3.  **Contract Instantiation**: It uses the connectors to create `web3.py` contract objects, which allow interaction with the smart contracts on both chains.
4.  **Polling Loop**: The `poll_for_events()` method starts an infinite loop. In each iteration, it:
    a.  Fetches the latest block number from the source chain.
    b.  Defines a block range to scan (from `last_checked_block + 1` to `latest_block`).
    c.  Uses a `web3.py` event filter to query the source chain's bridge contract for `TokensLocked` events within that block range.
5.  **Event Processing**: For each event log found:
    a.  It is passed to the `EventProcessor`.
    b.  The processor checks if the event's unique nonce has been seen before (to prevent processing the same event twice).
    c.  It validates that the event contains all necessary data (`recipient`, `amount`, etc.).
6.  **Transaction Submission**: If an event is valid and new, the processed data is handed to the `TransactionSubmitter`.
    a.  The submitter builds an `unlockTokens` transaction for the destination chain.
    b.  It then **simulates** sending this transaction by printing its details to the console.
7.  **State Update**: After scanning a block range, the `last_checked_block` is updated to the `latest_block` so the next iteration starts where the last one left off.
8.  **Error Handling**: The loop includes robust error handling for RPC connection issues, allowing the script to wait and retry instead of crashing.

## Usage Example

**1. Clone the repository and create a virtual environment:**

```bash
git clone https://github.com/your-username/star_craft.git
cd star_craft
python3 -m venv venv
source venv/bin/activate
```

**2. Install dependencies:**

```bash
pip install -r requirements.txt
```

**3. Create a `.env` file:**

Create a file named `.env` in the root directory of the project and add your configuration. You can get a free RPC URL from services like Infura, Alchemy, or Chainstack.

```ini
# .env file

# RPC URL for the source chain (e.g., Sepolia testnet)
SOURCE_CHAIN_RPC_URL="https://sepolia.infura.io/v3/YOUR_INFURA_PROJECT_ID"

# RPC URL for the destination chain (can be the same for simulation)
DESTINATION_CHAIN_RPC_URL="https://sepolia.infura.io/v3/YOUR_INFURA_PROJECT_ID"

# Address of the bridge contract on the source chain
# We will use the address of the Uniswap V3 Factory on Sepolia as an example source of events
SOURCE_CONTRACT_ADDRESS="0x0227628f3F023bb0B980b67D528571c95c6DaC1c"

# Address of the bridge contract on the destination chain (can be a mock address)
DESTINATION_CONTRACT_ADDRESS="0x1111111111111111111111111111111111111111"

# (Optional) The block number to start scanning from. Defaults to the latest block.
# START_BLOCK="5750000"
```

**4. Run the script:**

Open your terminal and run the Python script.

```bash
python bridge_listener.py
```

**5. Observe the output:**

The script will start logging its activities. It will connect to the chains and begin scanning for events. Since we are listening for a `TokensLocked` event which might not exist on the example contract, you will likely see polling messages. If an event that matches the ABI signature were to be emitted by the contract, you would see output like this:

```
2023-10-27 14:30:00 - INFO - [bridge_listener.main] - CrossChainBridgeListener initialized. Will start scanning from block 5750000.
2023-10-27 14:30:01 - INFO - [ChainConnector.connect] - Successfully connected to SourceChain at https://sepolia.infura.io/v3/...
2023-10-27 14:30:02 - INFO - [ChainConnector.connect] - Successfully connected to DestinationChain at https://sepolia.infura.io/v3/...
2023-10-27 14:30:02 - INFO - [bridge_listener.<module>] - Starting event polling loop...
2023-10-27 14:30:03 - INFO - [bridge_listener.poll_for_events] - Scanning for 'TokensLocked' events from block 5750001 to 5750123...
2023-10-27 14:30:05 - INFO - [bridge_listener.poll_for_events] - Found 1 new event(s) to process.
2023-10-27 14:30:05 - INFO - [EventProcessor.process_log] - Successfully validated and processed event for nonce 101.
2023-10-27 14:30:05 - INFO - [TransactionSubmitter.submit_unlock_transaction] - Preparing 'unlockTokens' transaction for recipient 0x... with amount 500000000 and nonce 101.
--- SIMULATED TRANSACTION SUBMISSION ---
  Chain:         DestinationChain
  Contract:      0x1111111111111111111111111111111111111111
  Function:      unlockTokens
  Recipient:     0xRecipientAddress...
  Amount:        500000000
  Source Nonce:  101
------------------------------------------
2023-10-27 14:30:07 - INFO - [TransactionSubmitter.submit_unlock_transaction] - Simulated transaction for source nonce 101 successfully submitted.
2023-10-27 14:30:22 - INFO - [bridge_listener.poll_for_events] - Scanning for 'TokensLocked' events from block 5750124 to 5750125...
2023-10-27 14:30:24 - INFO - [bridge_listener.poll_for_events] - No new 'TokensLocked' events found in this range.
```
