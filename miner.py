import hashlib
import datetime
import json
from uuid import uuid4
from time import sleep
from urllib.parse import urlparse
import random
import threading

import requests
from flask import Flask, jsonify, request

class Miner:
    def __init__(self):
        self.manager_node = ""
        self.node_identifier = node_identifier = str(uuid4()).replace('-', '')
        self.node_address = ""
        self.current_transactions = []
        self.last_block = {}

        # Activates / Deactivates mining process
        self.is_mining = False

    def new_block(self, proof, previous_hash, block_transactions, node_identifier):
        """
        Create a new Block for the manager node

        :param proof: The proof given by the Proof of Work algorithm
        :param previous_hash: Hash of previous Block
        :return: New Block
        """
        # Ensure we are the longest chain
        if self.resolve_conflicts():
            block_size = 0
            for t in block_transactions:
                block_size += t['size']

            block = {
                'index': len(self.chain) + 1,
                'timestamp': datetime.datetime.now(),
                'transactions': block_transactions,
                'proof': proof,
                'previous_hash': previous_hash or self.hash(self.chain[-1]),
                'size': block_size,   # 2MB max size
                'node': node_identifier
            }

            self.chain.append(block)
            return block
        
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
miner = Miner()

class Mine(threading.Thread):
    def __init__(self, task_id):
        threading.Thread.__init__(self)
        self.task_id = task_id

    def run(self):
        while miner.is_mining:
            #TODO: Sync transactions across network

            # Compose list of transactions of block
            block_transactions = miner.current_transactions
            if block_transactions:
                # We run the proof of work algorithm to get the next proof...
                last_block = miner.last_block
                proof = miner.proof_of_work(last_block)

                # Forge the new Block by adding it to the chain
                previous_hash = miner.hash(last_block)
                block = miner.new_block(proof, previous_hash, block_transactions, miner.node_identifier)
                if block != None:
                    who = {'node': miner.address}
                    response = {
                        'message': "New Block Forged",
                        'index': block['index'],
                        'transactions': block['transactions'],
                        'proof': block['proof'],
                        'previous_hash': block['previous_hash'],
                        'size': block['size']
                    }

                    # We must receive a reward for finding the proof.
                    # The sender is "0" to signify that this node has mined a new coin.
                    payload = {
                        'sender': '0',
                        'recipient': miner.node_identifier,
                        'amount': 1
                    }

                    requests.post(url=miner.manager_node+'/slave_done', json=[response, who])
                    requests.post(url=miner.manager_node+'/transactions/new', json=payload)
                    miner.is_mining = False

        miner.current_transactions = []
        miner.last_block = {}


@app.route('/start', methods=['POST'])
def add_block(self):
    miner.is_mining = True
    values = request.get_json()

    # Check that the required fields are in the POST'ed data
    required = ['transactions', 'last_block']
    if not all(k in values for k in required):
        return 'Missing values', 400

    miner.current_transactions = values['transactions']
    miner.last_block = values['last_block']

    async_task = Mine(task_id=1)
    try:
        with app.test_request_context():
            async_task.start()
        return 'Started mining process', 200
    except RuntimeError:
        return 'Node is already mining', 400

    response = {'message': f'Transactions recieved'}
    return jsonify(response), 201


@app.route('/stop', methods=['GET'])
def stop_mining(self):
    miner.is_mining = False

def start(self, address='http://0.0.0.0', port=6000, manager_address='http://0.0.0.0:5000'):
    miner.manager_node = manager_address
    miner.address = '{}:{}'.format(address, port)
    
    # Start flask app
    app.run(host='0.0.0.0', port=port)