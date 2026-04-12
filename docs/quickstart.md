# swingtradev3 Quickstart Guide (v2.0)

Get your institutional-grade AI swing trader running in 5 minutes.

## 📋 Prerequisites
1. **Zerodha Account** with Kite Connect API subscription (₹500/mo).
2. **NVIDIA NIM API Key** (Free tier).
3. **Tavily API Key** (Free tier).
4. **Docker** installed on your machine.

## 🚀 Step 1: Configuration
1. Open `swingtradev3/.env` and fill in your keys:
   - `KITE_API_KEY`, `KITE_API_SECRET`, `KITE_TOTP_SECRET`
   - `NIM_API_KEY`
   - `TAVILY_API_KEY`
   - `FASTAPI_API_KEY` (Generate any random string)

2. Review `config.yaml` to adjust your trading capital and risk limits.

## 🏗️ Step 2: Build & Start
Run the following command from the `swingtradev3` directory:
```bash
make dev-detach
```
*Note: The first build will take 15-30 minutes because it downloads massive ML libraries (PyTorch/TimesFM). Future starts will be instant.*

## 🔑 Step 3: Kite Authentication
Once the build is done, you must authorize the bot to access your Zerodha account:
```bash
make login
```
1. Open the printed URL in your browser.
2. Login and authorize.
3. Paste the final redirected URL back into your terminal.

## 📈 Step 4: Access the Dashboard
Open your browser to:
**http://localhost:8502**

- Go to the **Research** page.
- Click **"Trigger New Scan"**.
- Watch the **Agent Trace** page to see the AI analyze the Nifty 200 in real-time.

## 🧪 Step 5: Verification
Run the automated test suite to ensure everything is perfect:
```bash
make test
```

## 🛡️ Safety Note
The bot starts in `trading.mode: paper`. It will use real market data but only simulate trades. Only switch to `live` once you have verified the system for at least 2-4 weeks.
