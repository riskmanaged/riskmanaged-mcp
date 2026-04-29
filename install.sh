#!/bin/bash
set -e

echo "Installing riskmanaged-mcp..."
pip install --user git+https://github.com/riskmanaged/riskmanaged-mcp.git
echo ""
echo "✅ Installed successfully!"
echo ""
echo "Next steps:"
echo "  1. Generate an API token at https://riskmanaged.io/profile"
echo "  2. Configure: riskmanaged auth configure --token YOUR_TOKEN"
echo "  3. Verify:    riskmanaged auth whoami"
echo ""
echo "For MCP (Claude Desktop), add to your config:"
echo '  { "mcpServers": { "riskmanaged": { "command": "riskmanaged-mcp", "env": { "RISKMANAGED_TOKEN": "YOUR_TOKEN" } } } }'
