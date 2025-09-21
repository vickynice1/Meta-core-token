#!/usr/bin/env python3

import os
import json
import time
from datetime import datetime
from web3 import Web3
from eth_account import Account
from solcx import compile_source, install_solc, set_solc_version

class BSCDeployer:
    def __init__(self):
        self.private_key = os.getenv('PRIVATE_KEY')
        self.rpc_url = os.getenv('BSC_RPC_URL', 'https://data-seed-prebsc-1-s1.binance.org:8545/')
        
        if not self.private_key:
            raise ValueError("❌ PRIVATE_KEY environment variable is required")
        
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        self.account = Account.from_key(self.private_key)
        self.address = self.account.address
        
        print(f"🔗 Connected to BSC Testnet")
        print(f"📍 Deployer Address: {self.address}")
        
        balance = self.w3.eth.get_balance(self.address)
        balance_bnb = self.w3.from_wei(balance, 'ether')
        print(f"💰 Balance: {balance_bnb} BNB")
    
    def compile_contract(self, contract_path):
        """Compile contract with EXACT BSCScan settings"""
        try:
            # Use the EXACT version that BSCScan expects
            solc_version = '0.8.19'
            print(f"📦 Installing Solidity compiler {solc_version}...")
            install_solc(solc_version)
            set_solc_version(solc_version)
            
            with open(contract_path, 'r') as f:
                contract_source = f.read()
            
            print("🔨 Compiling contract with BSCScan-compatible settings...")
            
            # Compile with EXACT settings for BSCScan verification
            compiled_sol = compile_source(
                contract_source,
                output_values=['abi', 'bin', 'bin-runtime'],
                solc_version=solc_version,
                optimize=True,  # Optimization ENABLED
                optimize_runs=200,  # Exactly 200 runs
                evm_version=None  # Use default EVM version
            )
            
            contract_name = None
            for key in compiled_sol.keys():
                if 'MetacoreToken' in key:
                    contract_name = key
                    break
            
            if not contract_name:
                contract_name = list(compiled_sol.keys())[0]
            
            contract_interface = compiled_sol[contract_name]
            
            # Store the exact source code used for compilation
            self.source_code = contract_source
            self.compiler_version = solc_version
            
            print("✅ Contract compiled with BSCScan-compatible settings!")
            print(f"📋 Compiler: v{solc_version}")
            print(f"📋 Optimization: Enabled (200 runs)")
            
            return contract_interface
            
        except Exception as e:
            print(f"❌ Compilation error: {e}")
            raise
    
    def deploy_contract(self, contract_interface):
        """Deploy contract to BSC testnet"""
        try:
            contract = self.w3.eth.contract(
                abi=contract_interface['abi'],
                bytecode=contract_interface['bin']
            )
            
            gas_price = self.w3.eth.gas_price
            print(f"⛽ Gas Price: {self.w3.from_wei(gas_price, 'gwei')} Gwei")
            
            # Print bytecode info for verification
            print(f"📝 Bytecode length: {len(contract_interface['bin'])} characters")
            print(f"📝 Bytecode hash: {Web3.keccak(hexstr=contract_interface['bin']).hex()}")
            
            constructor_txn = contract.constructor().build_transaction({
                'from': self.address,
                'nonce': self.w3.eth.get_transaction_count(self.address),
                'gas': 2000000,
                'gasPrice': gas_price,
            })
            
            signed_txn = self.account.sign_transaction(constructor_txn)
            
            print("🚀 Deploying contract...")
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            print(f"📝 Transaction Hash: {tx_hash.hex()}")
            
            print("⏳ Waiting for confirmation...")
            tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
            
            if tx_receipt.status == 1:
                contract_address = tx_receipt.contractAddress
                print("🎉 Contract deployed successfully!")
                print(f"📍 Contract Address: {contract_address}")
                print(f"⛽ Gas Used: {tx_receipt.gasUsed:,}")
                print(f"🔗 BSCScan: https://testnet.bscscan.com/address/{contract_address}")
                
                return contract_address, contract_interface['abi'], tx_receipt
            else:
                raise Exception("❌ Contract deployment failed!")
                
        except Exception as e:
            print(f"❌ Deployment error: {e}")
            raise
    
    def print_verification_guide(self, contract_address):
        """Print detailed verification instructions"""
        print("\n" + "="*80)
        print("🔍 EXACT VERIFICATION INSTRUCTIONS FOR BSCSCAN")
        print("="*80)
        print(f"1. Go to: https://testnet.bscscan.com/address/{contract_address}")
        print("2. Click 'Contract' tab")
        print("3. Click 'Verify and Publish'")
        print("4. Select 'Via Solidity (Single file)'")
        print("5. Use EXACTLY these settings:")
        print("   ┌─────────────────────────────────────────────────────────┐")
        print("   │ Compiler Type: Solidity (Single file)                  │")
        print("   │ Compiler Version: v0.8.19+commit.7dd6d404              │")
        print("   │ Open Source License Type: 3) MIT License (MIT)         │")
        print("   └─────────────────────────────────────────────────────────┘")
        print("6. In 'Solidity Contract Code' section:")
        print("   - Paste the EXACT source code (saved in verification_source.sol)")
        print("7. In 'Compiler Configuration' section:")
        print("   ┌─────────────────────────────────────────────────────────┐")
        print("   │ Optimization: Yes                                       │")
        print("   │ Runs (Optimizer): 200                                   │")
        print("   │ Enter the Solidity Contract Code below: [paste code]   │")
        print("   └─────────────────────────────────────────────────────────┘")
        print("8. Leave 'Constructor Arguments ABI-encoded' EMPTY")
        print("9. Click 'Verify and Publish'")
        print("="*80)
        print("💡 TIP: The source code has been saved to 'verification_source.sol'")
        print("💡 Copy and paste it exactly as-is for verification!")
        print("="*80)
    
    def save_verification_files(self, contract_address, abi, tx_receipt, contract_info):
        """Save files needed for verification"""
        
        # Save the exact source code used for compilation
        with open('verification_source.sol', 'w') as f:
            f.write(self.source_code)
        
        # Save deployment info
        deployment_data = {
            'deployment_info': {
                'contract_address': contract_address,
                'transaction_hash': tx_receipt.transactionHash.hex(),
                'block_number': tx_receipt.blockNumber,
                'gas_used': tx_receipt.gasUsed,
                'deployer_address': self.address,
                'network': 'BSC Testnet',
                'deployment_time': datetime.utcnow().isoformat(),
                'bscscan_url': f"https://testnet.bscscan.com/address/{contract_address}",
                'verification_url': f"https://testnet.bscscan.com/verifyContract?a={contract_address}"
            },
            'verification_settings': {
                'compiler_type': 'Solidity (Single file)',
                'compiler_version': f'v{self.compiler_version}+commit.7dd6d404',
                'license_type': '3) MIT License (MIT)',
                'optimization_enabled': True,
                'optimization_runs': 200,
                'constructor_arguments': 'NONE - Leave empty'
            },
            'contract_info': contract_info,
            'abi': abi
        }
        
        with open('deployment_result.json', 'w') as f:
            json.dump(deployment_data, f, indent=2, default=str)
        
        print("💾 Verification files saved:")
        print("   📄 verification_source.sol - Exact source code for BSCScan")
        print("   📄 deployment_result.json - Complete deployment info")
        
        return deployment_data
    
    def verify_deployment(self, contract_address, abi):
        """Verify the deployed contract works"""
        try:
            contract = self.w3.eth.contract(address=contract_address, abi=abi)
            
            name = contract.functions.name().call()
            symbol = contract.functions.symbol().call()
            decimals = contract.functions.decimals().call()
            total_supply = contract.functions.totalSupply().call()
            owner = contract.functions.owner().call()
            
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
            print(f"❌ Contract verification error: {e}")
            return {}

def main():
    print("🌟 BSC Contract Deployer (BSCScan Verification Compatible)")
    print("=" * 60)
    
    try:
        deployer = BSCDeployer()
        
        # Compile with exact BSCScan settings
        contract_interface = deployer.compile_contract('contracts/MetacoreToken.sol')
        
        # Deploy contract
        contract_address, abi, tx_receipt = deployer.deploy_contract(contract_interface)
        
        # Verify contract functions work
        contract_info = deployer.verify_deployment(contract_address, abi)
        
        # Save verification files
        deployment_data = deployer.save_verification_files(contract_address, abi, tx_receipt, contract_info)
        
        # Print verification guide
        deployer.print_verification_guide(contract_address)
        
        # Set GitHub Actions outputs
        if os.getenv('GITHUB_ACTIONS'):
            github_output = os.getenv('GITHUB_OUTPUT')
            if github_output:
                with open(github_output, 'a') as f:
                    f.write(f"contract_address={contract_address}\n")
                    f.write(f"transaction_hash={tx_receipt.transactionHash.hex()}\n")
                    f.write(f"bscscan_url=https://testnet.bscscan.com/address/{contract_address}\n")
                    f.write(f"verification_url=https://testnet.bscscan.com/verifyContract?a={contract_address}\n")
        
        print(f"\n🎉 Deployment completed successfully!")
        print(f"📍 Contract Address: {contract_address}")
        print(f"📋 Use the verification guide above to verify on BSCScan!")
        
    except Exception as e:
        print(f"❌ Deployment failed: {e}")
        exit(1)

if __name__ == "__main__":
    main()
