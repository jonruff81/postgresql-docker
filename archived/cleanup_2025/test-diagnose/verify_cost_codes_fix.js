/**
 * Cost Codes Grid Performance Verification Script
 * 
 * This script helps verify that the cost codes grid is no longer 
 * refreshing constantly. Run this in your browser console while
 * on the cost-codes-grid page to track API calls and grid refreshes.
 * 
 * Usage:
 * 1. Open the cost-codes-grid page in your browser
 * 2. Open browser developer tools (F12 or Ctrl+Shift+I)
 * 3. Paste this entire script in the console and press Enter
 * 4. Watch the output to confirm refreshes are properly throttled
 */

(function() {
    console.clear();
    console.log('🔍 Cost Codes Performance Verification Tool');
    console.log('------------------------------------------');
    
    // Track API calls
    const apiCalls = [];
    
    // Track grid refreshes
    const gridRefreshes = [];
    
    // Create a timestamp formatter
    function formatTime(date) {
        return date.toLocaleTimeString();
    }
    
    // Intercept fetch calls to track API requests
    const originalFetch = window.fetch;
    window.fetch = function(url, options) {
        if (url.toString().includes('/api/cost-codes-with-groups')) {
            const timestamp = new Date();
            const hasNoCache = url.toString().includes('no-cache=true');
            
            apiCalls.push({
                timestamp,
                url: url.toString(),
                forced: hasNoCache
            });
            
            console.log(
                `🌐 ${formatTime(timestamp)} - API Call: ${url.toString().split('?')[0]} ${hasNoCache ? '(forced refresh)' : '(conditional)'}`
            );
        }
        return originalFetch.apply(this, arguments);
    };
    
    // Track grid API usage to detect refreshes
    if (window.gridApi) {
        const originalSetRowData = window.gridApi.setGridOption;
        window.gridApi.setGridOption = function(optionName, value) {
            if (optionName === 'rowData') {
                const timestamp = new Date();
                gridRefreshes.push({
                    timestamp,
                    rowCount: value ? value.length : 0
                });
                
                console.log(
                    `🔄 ${formatTime(timestamp)} - Grid Refresh: ${value ? value.length : 0} rows`
                );
            }
            return originalSetRowData.apply(this, arguments);
        };
        
        console.log('✅ Successfully attached to grid API');
    } else {
        console.warn('⚠️ Grid API not found - wait for grid to initialize');
        
        // Try again in a second
        setTimeout(() => {
            if (window.gridApi) {
                const originalSetRowData = window.gridApi.setGridOption;
                window.gridApi.setGridOption = function(optionName, value) {
                    if (optionName === 'rowData') {
                        const timestamp = new Date();
                        gridRefreshes.push({
                            timestamp,
                            rowCount: value ? value.length : 0
                        });
                        
                        console.log(
                            `🔄 ${formatTime(timestamp)} - Grid Refresh: ${value ? value.length : 0} rows`
                        );
                    }
                    return originalSetRowData.apply(this, arguments);
                };
                
                console.log('✅ Successfully attached to grid API (delayed)');
            } else {
                console.error('❌ Could not find grid API after waiting');
            }
        }, 1000);
    }
    
    // Report statistics every 30 seconds
    function reportStats() {
        const now = new Date();
        const thirtySecondsAgo = new Date(now.getTime() - 30000);
        
        const recentApiCalls = apiCalls.filter(call => call.timestamp > thirtySecondsAgo);
        const recentGridRefreshes = gridRefreshes.filter(refresh => refresh.timestamp > thirtySecondsAgo);
        
        console.log('📊 STATISTICS (last 30 seconds)');
        console.log(`   API Calls: ${recentApiCalls.length}`);
        console.log(`   Grid Refreshes: ${recentGridRefreshes.length}`);
        
        if (recentApiCalls.length > 2) {
            console.warn('⚠️ Multiple API calls detected - fix may not be working');
        } else if (recentGridRefreshes.length > 2) {
            console.warn('⚠️ Multiple grid refreshes detected - fix may not be working');
        } else {
            console.log('✅ Performance looks good - no excessive refreshing');
        }
    }
    
    // Report stats immediately to create baseline
    setTimeout(reportStats, 5000);
    
    // Continue monitoring
    setInterval(reportStats, 30000);
    
    console.log('🕒 Monitoring started - leave this page open for at least 1 minute to verify fix');
    console.log('👉 Success criteria: Should see no more than 1 API call per 30 seconds unless manually refreshed');
})();
