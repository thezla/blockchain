import hashlib
from datetime import date, datetime
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

    def new_block(self, proof, previous_hash, block_transactions, node_identifier, last_block):
        """
        Create a new Block for the manager node

        :param proof: The proof given by the Proof of Work algorithm
        :param previous_hash: Hash of previous Block
        :return: New Block
        """
        block_size = 0
        for t in block_transactions:
            block_size += t['size']

        block = {
            'index': last_block['index'] + 1,
            'timestamp': datetime.now().isoformat(),
            'transactions': block_transactions,
            'proof': proof,
            'previous_hash': previous_hash,
            'size': block_size,   # 2MB max size
            'node': node_identifier
        }
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
    
    def mine(self):
        # Compose list of transactions of block
        block_transactions = self.current_transactions
        if block_transactions and self.is_mining:
            # We run the proof of work algorithm to get the next proof...
            last_block = self.last_block
            proof = self.proof_of_work(last_block)

            # Forge the new Block by adding it to the chain
            previous_hash = self.hash(last_block)
            block = self.new_block(proof, previous_hash, block_transactions, self.node_identifier, last_block)
            if block != None:
                who = {'node': self.address}
                # We must receive a reward for finding the proof.
                # The sender is "0" to signify that this node has mined a new coin.
                payload = {
                    'sender': '0',
                    'recipient': self.node_identifier,
                    'amount': 1
                }
                requests.post(url=self.manager_node+'/slave/done', json=[block, who])
                requests.post(url=self.manager_node+'/transactions/new', json=payload)
                miner.is_mining = False

        miner.current_transactions = []
        miner.last_block = dict()


# Instantiate the Node
app = Flask(__name__)
miner = Miner()
'''
class Mine(threading.Thread):
    def __init__(self, task_id):
        threading.Thread.__init__(self)
        self.task_id = task_id

    def run(self):
        #while miner.is_mining:
            #TODO: Sync transactions across network

        # Compose list of transactions of block
        block_transactions = miner.current_transactions
        if block_transactions and self.is_mining:
            # We run the proof of work algorithm to get the next proof...
            last_block = miner.last_block
            proof = miner.proof_of_work(last_block)

            # Forge the new Block by adding it to the chain
            previous_hash = miner.hash(last_block)
            block = miner.new_block(proof, previous_hash, block_transactions, miner.node_identifier, last_block)
            if block != None:
                who = {'node': miner.address}

                # We must receive a reward for finding the proof.
                # The sender is "0" to signify that this node has mined a new coin.
                payload = {
                    'sender': '0',
                    'recipient': miner.node_identifier,
                    'amount': 1
                }
                requests.post(url=miner.manager_node+'/slave/done', json=[block, who])
                requests.post(url=miner.manager_node+'/transactions/new', json=payload)
                miner.is_mining = False
        else:
            miner.is_mining = False

        miner.current_transactions = []
        miner.last_block = dict()
'''

@app.route('/start', methods=['POST'])
def add_block():
    miner.is_mining = True
    values = request.get_json()

    # Check that the required fields are in the POST'ed data
    required = ['transactions', 'last_block']
    if not all(k in values for k in required):
        return 'Missing values', 400

    miner.current_transactions = values['transactions']
    miner.last_block = values['last_block']

    miner.mine()

    '''
    async_task = Mine(task_id=1)
    try:
        with app.test_request_context():
            async_task.start()
        return 'Started mining process', 200
    except RuntimeError:
        return 'Node is already mining', 400
    '''
    response = {'message': f'Transactions recieved, started mining'}
    return jsonify(response), 200


@app.route('/stop', methods=['GET'])
def stop_mining():
    miner.is_mining = False
    return 'Mining process stoppped in node: {}'.format(miner.node_address), 200

# Starts a miner node
def start(self, address='http://0.0.0.0', port=6000, manager_address='http://0.0.0.0:5000'):
    miner.manager_node = manager_address
    miner.address = '{}:{}'.format(address, port)
    
    # Start flask app
    app.run(host='0.0.0.0', port=port)