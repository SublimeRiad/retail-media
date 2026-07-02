#!/bin/bash
# Crypto Price Monitor — checks BTC, ETH, SOL prices and sends Gotify alert
NOTIFY="$HOME/.local/bin/notify"

fetch_price() {
  local coin="$1"
  curl -s "https://api.coingecko.com/api/v3/simple/price?ids=${coin}&vs_currencies=usd&include_24hr_change=true" 2>/dev/null
}

# Fetch prices
BTC=$(fetch_price "bitcoin")
ETH=$(fetch_price "ethereum")
SOL=$(fetch_price "solana")

btc_price=$(echo "$BTC" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"\${d['bitcoin']['usd']:,.0f}\")" 2>/dev/null || echo "N/A")
btc_change=$(echo "$BTC" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"{d['bitcoin']['usd_24h_change']:.1f}%\" if 'usd_24h_change' in d['bitcoin'] else 'N/A\")" 2>/dev/null || echo "N/A")

eth_price=$(echo "$ETH" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"\${d['ethereum']['usd']:,.0f}\")" 2>/dev/null || echo "N/A")
eth_change=$(echo "$ETH" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"{d['ethereum']['usd_24h_change']:.1f}%\" if 'usd_24h_change' in d['ethereum'] else 'N/A\")" 2>/dev/null || echo "N/A")

sol_price=$(echo "$SOL" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"\${d['solana']['usd']:,.0f}\")" 2>/dev/null || echo "N/A")
sol_change=$(echo "$SOL" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"{d['solana']['usd_24h_change']:.1f}%\" if 'usd_24h_change' in d['solana'] else 'N/A\")" 2>/dev/null || echo "N/A")

MSG="BTC: $btc_price ($btc_change)\nETH: $eth_price ($eth_change)\nSOL: $sol_price ($sol_change)"

"$NOTIFY" "📊 Crypto Prices" "$MSG" 3
echo "$(date): $MSG" >> /tmp/crypto-prices.log
