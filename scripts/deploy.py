#!/usr/bin/env python3

import os
import json
import time
import requests
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
        self.bscscan_api_key = os.getenv('BSCSCAN_API_KEY', '')  # Optional for auto-verification
        
        if not self.private_key:
            raise ValueError("❌ PRIVATE_KEY environment variable is required")
        
        # Setup Web3
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        self.account = Account.from_key(self.private_key)
        self.address = self.account.address
        
        print(f"🔗 Connected to BSC Testnet")
        print(f"📍 Deployer Address: {self.address}")
        
        # Check connection
        if not self.w3.is_connected():
            raise Exception("❌ Failed to connect to BSC testnet")
        
        # Check balance
        balance = self.w3.eth.get_balance(self.address)
        balance_bnb = self.w3.from_wei(balance, 'ether')
        print(f"💰 Balance: {balance_bnb} BNB")
        
        if balance == 0:
            print("⚠️  Warning: No BNB balance detected!")
            print("🔗 Get testnet BNB from: https://testnet.binance.org/faucet-smart")
    
    def compile_contract(self, contract_path):
        """Compile Solidity contract with BSCScan-compatible settings"""
        try:
            # Use exact version for BSCScan compatibility
            solc_version = '0.8.19'
            print(f"📦 Installing Solidity compiler {solc_version}...")
            install_solc(solc_version)
            set_solc_version(solc_version)
            
            # Read contract source
            with open(contract_path, 'r') as f:
                contract_source = f.read()
            
            print("🔨 Compiling contract with BSCScan-compatible settings...")
            
            # Compile with exact settings for BSCScan verification
            compiled_sol = compile_source(
                contract_source,
                output_values=['abi', 'bin', 'bin-runtime'],
                solc_version=solc_version,
                optimize=True,  # Enable optimization
                optimize_runs=200,  # Standard optimization runs
                evm_version=None  # Use default EVM version
            )
            
            # Get contract interface
            contract_name = None
            for key in compiled_sol.keys():
                if 'MetacoreToken' in key:
                    contract_name = key
                    break
            
            if not contract_name:
                contract_name = list(compiled_sol.keys())[0]
            
            contract_interface = compiled_sol[contract_name]
            
            # Store compilation info for verification
            self.compilation_info = {
                'source_code': contract_source,
                'solc_version': solc_version,
                'optimization_enabled': True,
                'optimization_runs': 200,
                'contract_name': 'MetacoreToken',
                'license_type': 'MIT'
            }
            
            print("✅ Contract compiled successfully with BSCScan-compatible settings!")
            print(f"📋 Compiler: v{solc_version} (Optimization: Enabled, Runs: 200)")
            
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
            
            # Get gas price with retry logic
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    gas_price = self.w3.eth.gas_price
                    break
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise e
                    print(f"⚠️  Retry {attempt + 1}: Getting gas price...")
                    time.sleep(2)
            
            print(f"⛽ Gas Price: {self.w3.from_wei(gas_price, 'gwei')} Gwei")
            
            # Get nonce
            nonce = self.w3.eth.get_transaction_count(self.address)
            print(f"🔢 Nonce: {nonce}")
            
            # Build constructor transaction
            constructor_txn = contract.constructor().build_transaction({
                'from': self.address,
                'nonce': nonce,
                'gas': 2000000,
                'gasPrice': gas_price,
            })
            
            print(f"💰 Estimated gas cost: {self.w3.from_wei(constructor_txn['gas'] * gas_price, 'ether')} BNB")
            
            # Sign transaction
            signed_txn = self.account.sign_transaction(constructor_txn)
            
            # Send transaction
            print("🚀 Deploying contract...")
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            print(f"📝 Transaction Hash: {tx_hash.hex()}")
            
            # Wait for confirmation with timeout
            print("⏳ Waiting for confirmation...")
            start_time = time.time()
            timeout = 300  # 5 minutes
            
            while time.time() - start_time < timeout:
                try:
                    tx_receipt = self.w3.eth.get_transaction_receipt(tx_hash)
                    if tx_receipt:
                        break
                except:
                    pass
                time.sleep(5)
                print("⏳ Still waiting...")
            else:
                raise Exception("❌ Transaction timeout - check BSCScan for status")
            
            if tx_receipt.status == 1:
                contract_address = tx_receipt.contractAddress
                print("🎉 Contract deployed successfully!")
                print(f"📍 Contract Address: {contract_address}")
                print(f"⛽ Gas Used: {tx_receipt.gasUsed:,}")
                print(f"🧱 Block Number: {tx_receipt.blockNumber}")
                print(f"🔗 BSCScan: https://testnet.bscscan.com/address/{contract_address}")
                
                return contract_address, contract_interface['abi'], tx_receipt
            else:
                raise Exception("❌ Contract deployment failed - transaction reverted")
                
        except Exception as e:
            print(f"❌ Deployment error: {e}")
            raise
    
    def verify_on_bscscan(self, contract_address):
        """Attempt automatic verification on BSCScan"""
        if not self.bscscan_api_key:
            print("⚠️  No BSCScan API key provided - skipping automatic verification")
            self.print_manual_verification_guide(contract_address)
            return False
        
        try:
            print("🔍 Attempting automatic verification on BSCScan...")
            
            # BSCScan testnet API endpoint
            api_url = "https://api-testnet.bscscan.com/api"
            
            verification_data = {
                'apikey': self.bscscan_api_key,
                'module': 'contract',
                'action': 'verifysourcecode',
                'contractaddress': contract_address,
                'sourceCode': self.compilation_info['source_code'],
                'codeformat': 'solidity-single-file',
                'contractname': self.compilation_info['contract_name'],
                'compilerversion': f"v{self.compilation_info['solc_version']}+commit.7dd6d404",
                'optimizationUsed': '1' if self.compilation_info['optimization_enabled'] else '0',
                'runs': str(self.compilation_info['optimization_runs']),
                'licenseType': '3'  # MIT License
            }
            
            response = requests.post(api_url, data=verification_data, timeout=30)
            result = response.json()
            
            if result['status'] == '1':
                guid = result['result']
                print(f"✅ Verification submitted! GUID: {guid}")
                
                # Check verification status
                for i in range(12):  # Check for 12 attempts (1 minute)
                    time.sleep(5)
                    status_data = {
                        'apikey': self.bscscan_api_key,
                        'module': 'contract',
                        'action': 'checkverifystatus',
                        'guid': guid
                    }
                    
                    try:
                        status_response = requests.get(api_url, params=status_data, timeout=10)
                        status_result = status_response.json()
                        
                        if status_result['status'] == '1':
                            print("🎉 Contract verified successfully on BSCScan!")
                            return True
                        elif status_result['result'] == 'Pending in queue':
                            print(f"⏳ Verification pending... (attempt {i+1}/12)")
                        else:
                            print(f"❌ Verification failed: {status_result['result']}")
                            break
                    except Exception as e:
                        print(f"⚠️  Status check error: {e}")
                        continue
                
                print("⚠️  Verification is taking longer than expected.")
                
            else:
                print(f"❌ Verification submission failed: {result.get('message', 'Unknown error')}")
                
        except Exception as e:
            print(f"❌ Verification error: {e}")
        
        # Fallback to manual verification guide
        self.print_manual_verification_guide(contract_address)
        return False
    
    def print_manual_verification_guide(self, contract_address):
        """Print detailed manual verification instructions"""
        print("\n" + "="*80)
        print("📋 MANUAL VERIFICATION GUIDE FOR BSCSCAN")
        print("="*80)
        print(f"🔗 Verification URL: https://testnet.bscscan.com/verifyContract?a={contract_address}")
        print("\n📝 Step-by-step instructions:")
        print("1. Click the verification URL above")
        print("2. Select 'Via Solidity (Single file)'")
        print("3. Use these EXACT settings:")
        print("   ┌─────────────────────────────────────────────────────────┐")
        print("   │ Compiler Type: Solidity (Single file)                  │")
        print(f"   │ Compiler Version: v{self.compilation_info['solc_version']}+commit.7dd6d404              │")
        print("   │ Open Source License Type: 3) MIT License (MIT)         │")
        print("   │ Optimization: Yes                                       │")
        print(f"   │ Runs: {self.compilation_info['optimization_runs']}                                           │")
        print("   └─────────────────────────────────────────────────────────┘")
        print("4. Copy the source code from 'verification_source.sol' file")
        print("5. Leave Constructor Arguments EMPTY")
        print("6. Click 'Verify and Publish'")
        print("="*80)
    
    def verify_deployment(self, contract_address, abi):
        """Verify the deployed contract functions"""
        try:
            contract = self.w3.eth.contract(address=contract_address, abi=abi)
            
            # Call contract functions with retry logic
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    name = contract.functions.name().call()
                    symbol = contract.functions.symbol().call()
                    decimals = contract.functions.decimals().call()
                    total_supply = contract.functions.totalSupply().call()
                    owner = contract.functions.owner().call()
                    break
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise e
                    print(f"⚠️  Retry {attempt + 1}: Verifying contract functions...")
                    time.sleep(3)
            
            print("\n📋 Contract Function Verification:")
            print(f"✅ Name: {name}")
            print(f"✅ Symbol: {symbol}")
            print(f"✅ Decimals: {decimals}")
            print(f"✅ Total Supply: {total_supply / (10**decimals):,.0f} {symbol}")
            print(f"✅ Owner: {owner}")
            
            return {
                'name': name,
                'symbol': symbol,
                'decimals': decimals,
                'totalSupply': str(total_supply),
                'owner': owner
            }
            
        except Exception as e:
            print(f"❌ Contract function verification error: {e}")
            return {
                'name': 'Unknown',
                'symbol': 'Unknown',
                'decimals': 18,
                'totalSupply': '0',
                'owner': 'Unknown'
            }
    
    def save_deployment_info(self, contract_address, abi, tx_receipt, contract_info, verification_attempted=False):
        """Save comprehensive deployment information"""
        deployment_data = {
            'deployment_info': {
                'contract_address': contract_address,
                'transaction_hash': tx_receipt.transactionHash.hex(),
                'block_number': tx_receipt.blockNumber,
                'gas_used': tx_receipt.gasUsed,
                'deployer_address': self.address,
                'network': 'BSC Testnet',
                'network_id': 97,
                'deployment_time': datetime.utcnow().isoformat(),
                'bscscan_url': f"https://testnet.bscscan.com/address/{contract_address}",
                'transaction_url': f"https://testnet.bscscan.com/tx/{tx_receipt.transactionHash.hex()}",
                'verification_url': f"https://testnet.bscscan.com/verifyContract?a={contract_address}"
            },
            'contract_info': contract_info,
            'compilation_info': self.compilation_info,
            'verification_info': {
                'auto_verification_attempted': verification_attempted,
                'manual_verification_url': f"https://testnet.bscscan.com/verifyContract?a={contract_address}",
                'compiler_version': f"v{self.compilation_info['solc_version']}+commit.7dd6d404",
                'optimization_enabled': self.compilation_info['optimization_enabled'],
                'optimization_runs': self.compilation_info['optimization_runs'],
                'license_type': 'MIT'
            },
            'abi': abi
        }
        
        # Save deployment result
        with open('deployment_result.json', 'w') as f:
            json.dump(deployment_data, f, indent=2, default=str)
        
        # Save source code for manual verification
        with open('verification_source.sol', 'w') as f:
            f.write(self.compilation_info['source_code'])
        
        print("💾 Files saved:")
        print("   📄 deployment_result.json - Complete deployment info")
        print("   📄 verification_source.sol - Source code for BSCScan verification")
        
        return deployment_data

def main():
    print("🌟 GitHub Actions BSC Contract Deployer with Verification")
    print("=" * 65)
    
    try:
        # Initialize deployer
        deployer = GitHubBSCDeployer()
        
        # Compile contract
        contract_interface = deployer.compile_contract('contracts/MetacoreToken.sol')
        
        # Deploy contract
        contract_address, abi, tx_receipt = deployer.deploy_contract(contract_interface)
        
        # Verify contract functions
        contract_info = deployer.verify_deployment(contract_address, abi)
        
        # Attempt BSCScan verification
        verification_attempted = deployer.verify_on_bscscan(contract_address)
        
        # Save deployment info
        deployment_data = deployer.save_deployment_info(
            contract_address, abi, tx_receipt, contract_info, verification_attempted
        )
        
        # Set GitHub Actions outputs
        if os.getenv('GITHUB_ACTIONS'):
            github_output = os.getenv('GITHUB_OUTPUT')
            if github_output:
                with open(github_output, 'a') as f:
                    f.write(f"contract_address={contract_address}\n")
                    f.write(f"transaction_hash={tx_receipt.transactionHash.hex()}\n")
                    f.write(f"bscscan_url=https://testnet.bscscan.com/address/{contract_address}\n")
                    f.write(f"verification_url=https://testnet.bscscan.com/verifyContract?a={contract_address}\n")
                    f.write(f"verification_attempted={verification_attempted}\n")
        
        print(f"\n🎉 Deployment completed successfully!")
        print(f"📍 Contract Address: {contract_address}")
        
        if verification_attempted:
            print("✅ Contract verification attempted automatically")
        else:
            print("📋 Use the manual verification guide above to verify on BSCScan")
        
    except Exception as e:
        print(f"❌ Deployment failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

if __name__ == "__main__":
    main()
