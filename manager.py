import hashlib
import json
from time import time
from time import sleep
from urllib.parse import urlparse
from uuid import uuid4
import random
import threading
import datetime
import subprocess
import miner

import requests
from flask import Flask, jsonify, request

class Blockchain:
    def __init__(self):
        self.current_transactions = []
        self.chain = []
        self.nodes = set()
        self.slave_nodes = set()
        self.number_of_nodes = 0

        # Create the genesis block
        self.new_genesis_block(previous_hash='1', proof=100, block_transactions=[])

        # Add first neighbor node
        self.register_node("http://0.0.0.0:5000")

    def register_node(self, address):
        """
        Add a new node to the list of nodes

        :param address: Address of node. Eg. 'http://192.168.0.5:5000'
        """

        parsed_url = urlparse(address)
        if parsed_url.netloc:
            self.nodes.add(parsed_url.netloc)
        elif parsed_url.path:
            # Accepts an URL without scheme like '192.168.0.5:5000'.
            self.nodes.add(parsed_url.path)
        else:
            raise ValueError('Invalid URL')

    def resolve_nodes(self, node_address):
        """
        Spread node list to neighbor nodes
        """
        # TODO: Ability to remove adress completely from network
        neighbors = self.nodes
        if len(neighbors) > 1:
            payload = {'nodes': list(neighbors)}
            headers = {'content-type': 'application/json'}
            for node in neighbors:
                # Do not request node list from itself
                if node != node_address:
                    response = requests.post(url=f'http://{node}/nodes/register', json=payload, headers=headers)

    def valid_chain(self, chain):
        """
        Determine if a given blockchain is valid

        :param chain: A blockchain
        :return: True if valid, False if not
        """

        last_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]
            print(f'{last_block}')
            print(f'{block}')
            print("\n-----------\n")
            # Check that the hash of the block is correct
            last_block_hash = self.hash(last_block)
            if block['previous_hash'] != last_block_hash:
                return False

            # Check that the Proof of Work is correct
            if not self.valid_proof(last_block['proof'], block['proof'], last_block_hash):
                return False

            last_block = block
            current_index += 1

        return True

    def resolve_conflicts(self):
        """
        This is our consensus algorithm, it resolves conflicts
        by replacing our chain with the longest one in the network.

        :return: True if our chain was replaced, False if not
        """

        neighbours = self.nodes
        new_chain = None

        # We're only looking for chains longer than ours
        max_length = len(self.chain)

        # Grab and verify the chains from all the nodes in our network
        for node in neighbours:
            response = requests.get(f'http://{node}/chain')

            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']

                # Check if the length is longer and the chain is valid
                if length >= max_length and self.valid_chain(chain):
                    max_length = length
                    new_chain = chain

        # Replace our chain if we discovered a new, valid chain longer than ours
        if new_chain:
            self.chain = new_chain
            return True
        return False

    def compose_block_transactions(self):
        # Max size of block in "kilobytes"
        max_size = 2000

        block_size = 0
        block_transactions = []
        if self.chain:
            while True:
                if self.current_transactions:
                    transaction_size = self.current_transactions[0]['size']
                    if (transaction_size + block_size) <= max_size:
                        block_transactions.append(self.current_transactions[0])
                        del self.current_transactions[0]
                        block_size += transaction_size
                    else:
                        break
                else:
                    # Put transactions back in front of queue
                    for e in reversed(block_transactions):
                        self.current_transactions.insert(0, e)
                    return []
        return block_transactions

    def add_block(self, block):
        """
        Create a new Block in the Blockchain

        :param proof: The proof given by the Proof of Work algorithm
        :param previous_hash: Hash of previous Block
        :return: New Block
        """
        # Ensure we are the longest chain
        if self.resolve_conflicts():
            self.chain.append(block)
            return block
    
    def new_genesis_block(self, proof, previous_hash, block_transactions):
        if not self.chain:
            block_size = 0
            for t in block_transactions:
                block_size += t['size']

            block = {
                'index': len(self.chain) + 1,
                'timestamp': time(),
                'transactions': block_transactions,
                'proof': proof,
                'previous_hash': previous_hash or self.hash(self.chain[-1]),
                'size': block_size,   # 2MB max size
            }

            self.chain.append(block)
            return block

    def new_transaction(self, sender, recipient, amount):
        """
        Creates a new transaction to go into the next mined Block

        :param sender: Address of the Sender
        :param recipient: Address of the Recipient
        :param amount: Amount
        :return: The index of the Block that will hold this transaction
        """
        self.current_transactions.append({
            'sender': sender,
            'recipient': recipient,
            'amount': amount,
            'size': random.randint(10,100),         # Simulated size in kilobytes
            'id': str(uuid4()).replace('-', '')     # Unique ID
        })

        return self.last_block['index'] + 1
    
    # TODO: Fixa transaktionssync
    def resolve_transactions():
        pass


    @property
    def last_block(self):
        if self.chain:
            return self.chain[-1]
        return 0

    @staticmethod
    def hash(block):
        """
        Creates a SHA-256 hash of a Block

        :param block: Block
        """

        # We must make sure that the Dictionary is Ordered, or we'll have inconsistent hashes
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    def proof_of_work(self, last_block):
        """
        Simple Proof of Work Algorithm:

         - Find a number p' such that hash(pp') contains leading 4 zeroes
         - Where p is the previous proof, and p' is the new proof
         
        :param last_block: <dict> last Block
        :return: <int>
        """

        last_proof = last_block['proof']
        last_hash = self.hash(last_block)

        proof = 0
        while self.valid_proof(last_proof, proof, last_hash) is False:
            proof += 1
        # Simulated mining
        sleep(random.randint(1,4))
        return proof

    @staticmethod
    def valid_proof(last_proof, proof, last_hash):
        """
        Validates the Proof

        :param last_proof: <int> Previous Proof
        :param proof: <int> Current Proof
        :param last_hash: <str> The hash of the Previous Block
        :return: <bool> True if correct, False if not.
        """

        guess = f'{last_proof}{proof}{last_hash}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:2] == "00"           # Hash made easy to simulate mining


# Instantiate the Node
app = Flask(__name__)

# Generate a globally unique address for this node
node_identifier = str(uuid4()).replace('-', '')
node_address = ""

# Instantiate the Blockchain
blockchain = Blockchain()

# Activates / Deactivates node list syncing process
is_syncing = True

# Pauses mining of all slaves if solution is found
solution_found = False


class Manage(threading.Thread):
    def __init__(self, task_id):
        threading.Thread.__init__(self)
        self.task_id = task_id
    
    def run(self):
        for miner in blockchain.slave_nodes:
            payload = {
                'transactions': blockchain.compose_block_transactions(),
                'last_block': blockchain.last_block()
            }
            requests.post(url=miner+'/start', json=payload)
            

class NewMiner(threading.Thread):
    def __init__(self, task_id):
        threading.Thread.__init__(self)
        self.task_id = task_id
    
    def run(self):
        port = 6000+blockchain.number_of_nodes
        address = '0.0.0.0:{}'.format(port)
        blockchain.slave_nodes.add(address)
        miner.start('http://0.0.0.0', port=port, manager_address=node_address)


class Sync(threading.Thread):
    def __init__(self, task_id):
        threading.Thread.__init__(self)
        self.task_id = task_id

    def run(self):
        while is_syncing:
            blockchain.resolve_nodes(node_address)
            sleep(5)


@app.route('/sync', methods=['GET'])
def sync_nodes():
    global is_syncing
    is_syncing = True
    async_task = Sync(task_id=2)
    try:
        with app.test_request_context():
            async_task.start()
        return 'Started syncing node lists', 200
    except RuntimeError:
        return 'Node is already syncing', 400


@app.route('/sync/stop', methods=['GET'])
def stop_syncing():
    global is_syncing
    is_syncing = False
    return 'Syncing process stopped', 400


@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    values = request.get_json()

    # Check that the required fields are in the POST'ed data
    required = ['sender', 'recipient', 'amount']
    if not all(k in values for k in required):
        return 'Missing values', 400

    # Create a new Transaction
    index = blockchain.new_transaction(values['sender'], values['recipient'], values['amount'])

    response = {'message': f'Transaction will be added to Block {index}'}
    return jsonify(response), 201


@app.route('/transactions', methods=['GET'])
def get_transactions():
    response = {
        'transactions': blockchain.current_transactions,
        'size': len(blockchain.current_transactions)
    }
    return jsonify(response), 200


@app.route('/transactions/sync', methods=['POST'])
def sync_transactions(self):
    values = request.get_json()

    transactions = values['transactions']
    if transactions is None:
        return "Error: Please supply a valid list of transactions", 400

    for trans in transactions:
        if trans not in self.current_transactions:      #TODO: Bättre datastruktur, hashmap?
            blockchain.new_transaction()

    response = {
        'message': 'New nodes have been added',
        'total_nodes': list(blockchain.nodes),
    }
    return jsonify(response), 201


@app.route('/slave/done', methods=['POST'])
def slave_done():
    values = request.get_json()
    finder = values[1]['node']
    for miner in blockchain.slave_nodes:
        if miner != values[1]['node']:
            requests.get(miner+'/stop')

    blockchain.add_block(values)


@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
    }
    return jsonify(response), 200


@app.route('/nodes', methods=['GET'])
def get_nodes():
    response = {
        'nodes': list(blockchain.nodes)
    }
    return jsonify(response), 200


@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    values = request.get_json()

    nodes = values['nodes']
    if nodes is None:
        return "Error: Please supply a valid list of nodes", 400

    for node in nodes:
        blockchain.register_node(node)

    response = {
        'message': 'New nodes have been added',
        'total_nodes': list(blockchain.nodes),
    }
    return jsonify(response), 201


@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    replaced = blockchain.resolve_conflicts()

    if replaced:
        response = {
            'message': 'Our chain was replaced',
            'new_chain': blockchain.chain
        }
    else:
        response = {
            'message': 'Our chain is authoritative',
            'chain': blockchain.chain
        }
    return jsonify(response), 200


@app.route('/cluster', methods=['GET'])
def get_cluster():
    return jsonify(list(blockchain.slave_nodes)), 200


# Adds a miner node to cluster
@app.route('/cluster/add_miner', methods=['GET'])
def add_miner():
    async_task = NewMiner(task_id=3)
    try:
        with app.test_request_context():
            async_task.start()
    except RuntimeError:
        return 'Could not create a new miner', 400

    blockchain.number_of_nodes = len(blockchain.slave_nodes)
    return 'Miner node created and added to cluster!', 200


# Tells cluster to start mining
@app.route('/cluster/start', methods=['GET'])
def start_cluster():
    async_task = Manage(task_id=4)
    try:
        with app.test_request_context():
            async_task.start()
    except RuntimeError:
        return 'Could not start cluster mining', 400
    return 'Cluster mining initiated!', 200


# Generate transactions for testing
@app.route('/transactions/generate', methods=['POST'])
def generate_transactions():
    values = request.get_json()
    amount = values.get('amount')

    for i in range(0, amount):
        amount = recipient = random.randint(1,1000)
        sender = random.randint(1,100)
        recipient = random.randint(1,100)
        while recipient == sender:
            recipient = random.randint(1,100)
        
        blockchain.new_transaction(sender, recipient, amount)
    return '{} transactions generated!'.format(amount)


# Initialization --------------------
# Activate syncing of node lists
sync_nodes()


if __name__ == '__main__':
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default=5000, type=int, help='port to listen on')
    args = parser.parse_args()
    port = args.port

    # Add own address to node list
    address = 'http://0.0.0.0:{}'.format(port)
    blockchain.register_node(address)
    node_address = address

    # Start flask app
    app.run(host='0.0.0.0', port=port)