#!/bin/bash

echo "==================================================="
echo "Cost Codes UI Debugger and Performance Optimization"
echo "==================================================="
echo ""
echo "This script will help diagnose and fix UI performance issues."
echo ""

echo "1. Testing API endpoint response times..."
python3 test-diagnose/test_api_endpoint.py

echo ""
echo "2. Creating debug output file..."
echo "// Copy this script to your browser console to debug UI updates" > debug_output.js
cat test-diagnose/debug_cost_codes_ui.js >> debug_output.js
echo ""
echo "Debug script has been saved to debug_output.js"
echo ""

echo "3. Starting the web server with caching enabled..."
python3 web_ui/app.py &
SERVER_PID=$!

echo ""
echo "4. Opening instructions..."
echo ""
echo "TROUBLESHOOTING STEPS:"
echo "1. Open http://localhost:5000/cost-codes-grid in your browser"
echo "2. Open browser developer tools (F12 or Cmd+Option+I)"
echo "3. Copy contents of debug_output.js and paste into Console"
echo "4. Watch for any patterns of refreshes or UI flickering"
echo "5. Use window.clearCostCodesCache() to manually clear cache"
echo "6. Use window.debugFetchData() to test API response"
echo ""
echo "Press Ctrl+C to stop the server and exit..."

# Wait for user to terminate
wait $SERVER_PID
