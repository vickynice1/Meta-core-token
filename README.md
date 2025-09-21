# BSC Smart Contract Auto-Deployer

This repository automatically deploys smart contracts to Binance Smart Chain testnet using GitHub Actions.

## 🚀 Features

- Automated deployment via GitHub Actions
- Scheduled deployments (cron jobs)
- Manual deployment triggers
- Lightweight Python-based deployment (no Hardhat)
- Automatic contract verification
- Deployment result artifacts
- BSCScan integration

## 📋 Setup Instructions

1. **Fork this repository**

2. **Add your private key as a secret:**
   - Go to Settings → Secrets and variables → Actions
   - Add `PRIVATE_KEY` with your wallet private key

3. **Get testnet BNB:**
   - Visit: https://testnet.binance.org/faucet-smart
   - Add your wallet address

4. **Deploy contract:**
   - Go to Actions tab
   - Select "Deploy Smart Contract to BSC Testnet"
   - Click "Run workflow"

## 🕐 Scheduled Deployments

The workflow runs automatically:
- Daily at 12:00 UTC
- On push to main branch (when contracts change)
- Manual trigger available

## 📊 Deployment Results

After each deployment, check:
- Actions summary for contract address
- Artifacts for detailed deployment info
- BSCScan link for contract verification

## 🔧 Customization

Edit `contracts/MetacoreToken.sol` to modify your contract.
Edit `.github/workflows/deploy-contract.yml` to change deployment schedule.

## 📝 Contract Details

- **Name:** Metacore Token
- **Symbol:** META
- **Decimals:** 18
- **Total Supply:** 1,000,000 META
- **Network:** BSC Testnet
