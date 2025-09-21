#!/usr/bin/env python3

import os
import json
import time
from datetime import datetime
from web3 import Web3
from eth_account import Account
from solcx import compile_source, install_solc, set_solc_version

class GitHubBSCDeployer:
    def __init__(self):
        # Get environment variables
        self.private_key = os.getenv('PRIVATE_KEY')
        self.rpc_url = os.getenv('BSC_RPC_URL', 'https://data-seed-prebsc-1-s1.binance.org:8545/')
        self.github_token = os.getenv('GITHUB_TOKEN')
        
        if not self.private_key:
            raise ValueError("PRIVATE_KEY environment variable is required")
        
        # Setup Web3
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        self.account = Account.from_key(self.private_key)
        self.address = self.account.address
        
        print(f"🔗 Connected to BSC Testnet")
        print(f"📍 Deployer Address: {self.address}")
        
        # Check connection
        if not self.w3.is_connected():
            raise Exception("Failed to connect to BSC testnet")
        
        # Check balance
        balance = self.w3.eth.get_balance(self.address)
        balance_bnb = self.w3.from_wei(balance, 'ether')
        print(f"💰 Balance: {balance_bnb} BNB")
        
        if balance == 0:
            print("⚠️  Warning: No BNB balance detected!")
    
    def compile_contract(self, contract_path):
        """Compile Solidity contract"""
        try:
            # Install Solidity compiler
            print("📦 Installing Solidity compiler...")
            install_solc('0.8.19')
            set_solc_version('0.8.19')
            
            # Read contract source
            with open(contract_path, 'r') as f:
                contract_source = f.read()
            
            print("🔨 Compiling contract...")
            compiled_sol = compile_source(contract_source)
            
            # Get contract interface
            contract_name = None
            for key in compiled_sol.keys():
                if 'MetacoreToken' in key:
                    contract_name = key
                    break
            
            if not contract_name:
                contract_name = list(compiled_sol.keys())[0]
            
            contract_interface = compiled_sol[contract_name]
            print("✅ Contract compiled successfully!")
            
            return contract_interface
            
        except Exception as e:
            print(f"❌ Compilation error: {e}")
            raise
    
    def deploy_contract(self, contract_interface):
        """Deploy contract to BSC testnet"""
        try:
            # Create contract instance
            contract = self.w3.eth.contract(
                abi=contract_interface['abi'],
                bytecode=contract_interface['bin']
            )
            
            # Get gas price
            gas_price = self.w3.eth.gas_price
            print(f"⛽ Gas Price: {self.w3.from_wei(gas_price, 'gwei')} Gwei")
            
            # Build constructor transaction
            constructor_txn = contract.constructor().build_transaction({
                'from': self.address,
                'nonce': self.w3.eth.get_transaction_count(self.address),
                'gas': 2000000,
                'gasPrice': gas_price,
            })
            
            # Sign transaction
            signed_txn = self.account.sign_transaction(constructor_txn)
            
            # Send transaction
            print("🚀 Deploying contract...")
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            print(f"📝 Transaction Hash: {tx_hash.hex()}")
            
            # Wait for confirmation
            print("⏳ Waiting for confirmation...")
            tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
            
            if tx_receipt.status == 1:
                contract_address = tx_receipt.contractAddress
                print("🎉 Contract deployed successfully!")
                print(f"📍 Contract Address: {contract_address}")
                print(f"⛽ Gas Used: {tx_receipt.gasUsed:,}")
                print(f"🧱 Block Number: {tx_receipt.blockNumber}")
                print(f"🔗 BSCScan: https://testnet.bscscan.com/address/{contract_address}")
                
                return contract_address, contract_interface['abi'], tx_receipt
            else:
                raise Exception("Contract deployment failed!")
                
        except Exception as e:
            print(f"❌ Deployment error: {e}")
            raise
    
    def verify_deployment(self, contract_address, abi):
        """Verify the deployed contract"""
        try:
            contract = self.w3.eth.contract(address=contract_address, abi=abi)
            
            # Call contract functions
            name = contract.functions.name().call()
            symbol = contract.functions.symbol().call()
            decimals = contract.functions.decimals().call()
            total_supply = contract.functions.totalSupply().call()
            owner = contract.functions.owner().call()
            
            print("\n📋 Contract Verification:")
            print(f"Name: {name}")
            print(f"Symbol: {symbol}")
            print(f"Decimals: {decimals}")
            print(f"Total Supply: {total_supply / (10**decimals):,.0f} {symbol}")
            print(f"Owner: {owner}")
            
            return {
                'name': name,
                'symbol': symbol,
                'decimals': decimals,
                'totalSupply': str(total_supply),
                'owner': owner
            }
            
        except Exception as e:
            print(f"❌ Verification error: {e}")
            raise
    
    def save_deployment_info(self, contract_address, abi, tx_receipt, contract_info):
        """Save deployment information"""
        deployment_data = {
            'deployment_info': {
                'contract_address': contract_address,
                'transaction_hash': tx_receipt.transactionHash.hex(),
                'block_number': tx_receipt.blockNumber,
                'gas_used': tx_receipt.gasUsed,
                'deployer_address': self.address,
                'network': 'BSC Testnet',
                'deployment_time': datetime.utcnow().isoformat(),
                'bscscan_url': f"https://testnet.bscscan.com/address/{contract_address}"
            },
            'contract_info': contract_info,
            'abi': abi
        }
        
        # Save to file
        with open('deployment_result.json', 'w') as f:
            json.dump(deployment_data, f, indent=2, default=str)
        
        print("💾 Deployment info saved to deployment_result.json")
        return deployment_data

def main():
    print("🌟 GitHub Actions BSC Contract Deployer")
    print("=" * 50)
    
    try:
        # Initialize deployer
        deployer = GitHubBSCDeployer()
        
        # Compile contract
        contract_interface = deployer.compile_contract('contracts/MetacoreToken.sol')
        
        # Deploy contract
        contract_address, abi, tx_receipt = deployer.deploy_contract(contract_interface)
        
        # Verify deployment
        contract_info = deployer.verify_deployment(contract_address, abi)
        
        # Save deployment info
        deployment_data = deployer.save_deployment_info(contract_address, abi, tx_receipt, contract_info)
        
        # Set GitHub Actions output
        if os.getenv('GITHUB_ACTIONS'):
            with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
                f.write(f"contract_address={contract_address}\n")
                f.write(f"transaction_hash={tx_receipt.transactionHash.hex()}\n")
                f.write(f"bscscan_url=https://testnet.bscscan.com/address/{contract_address}\n")
        
        print("\n🎉 Deployment completed successfully!")
        
    except Exception as e:
        print(f"❌ Deployment failed: {e}")
        exit(1)

if __name__ == "__main__":
    main()
