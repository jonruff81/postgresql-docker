// Debug script to add to the console to monitor cost codes UI refreshes
// Use this script in the browser console to monitor why the UI is refreshing

(function() {
    console.log('📊 Cost Codes UI Monitoring Script Activated');
    
    // Store the original fetch to monitor API calls
    const originalFetch = window.fetch;
    window.fetch = function() {
        const url = arguments[0];
        if (typeof url === 'string' && url.includes('/api/cost-codes-with-groups')) {
            console.log('🔍 API Call to cost-codes-with-groups at', new Date().toISOString());
            console.trace('Call stack for fetch request:');
        }
        return originalFetch.apply(this, arguments);
    };
    
    // Monitor grid refreshes by overriding setRowData
    if (gridApi && gridApi.setGridOption) {
        const originalSetOption = gridApi.setGridOption;
        gridApi.setGridOption = function(key, value) {
            if (key === 'rowData') {
                console.log('⚠️ Grid data refresh at', new Date().toISOString(), 'with', value.length, 'rows');
                console.trace('Call stack for grid refresh:');
            }
            return originalSetOption.apply(this, arguments);
        };
        console.log('🔄 Grid refresh monitoring enabled');
    } else {
        console.warn('⚠️ Grid API not available yet - run this script after grid initialization');
    }
    
    // Monitor DOM mutations to catch potential UI reflows
    const observer = new MutationObserver((mutations) => {
        mutations.forEach(mutation => {
            // Only log significant DOM changes to the grid
            if (mutation.type === 'childList' && 
                (mutation.target.id === 'grid' || 
                 mutation.target.closest('#grid'))) {
                if (mutation.addedNodes.length > 5 || mutation.removedNodes.length > 5) {
                    console.log('🔄 Significant grid DOM mutation detected at', new Date().toISOString());
                    console.log('   Added nodes:', mutation.addedNodes.length, 
                                'Removed nodes:', mutation.removedNodes.length);
                }
            }
        });
    });
    
    observer.observe(document.body, {
        childList: true,
        subtree: true,
        attributes: false,
        characterData: false
    });
    
    console.log('👁️ DOM mutation observer started');
    
    // Add a simple timer to detect regular intervals
    let refreshCounter = 0;
    let lastRefreshTime = 0;
    const refreshIntervals = [];
    
    window.setInterval(() => {
        if (lastRefreshTime > 0) {
            const currentTime = Date.now();
            const interval = currentTime - lastRefreshTime;
            refreshIntervals.push(interval);
            
            // Keep only the last 10 intervals
            if (refreshIntervals.length > 10) {
                refreshIntervals.shift();
            }
            
            // Check if we have consistent intervals (indicating a timer)
            if (refreshIntervals.length >= 3) {
                const averageInterval = refreshIntervals.reduce((a, b) => a + b, 0) / refreshIntervals.length;
                const variance = refreshIntervals.map(i => Math.abs(i - averageInterval)).reduce((a, b) => a + b, 0) / refreshIntervals.length;
                
                if (variance < 100 && averageInterval < 2000) { // Low variance means consistent timing
                    console.warn('⏰ POSSIBLE TIMER DETECTED: UI refreshes occurring approximately every', 
                                Math.round(averageInterval), 'ms');
                }
            }
            
            lastRefreshTime = currentTime;
        }
    }, 1000);
    
    // Export useful functions to window for manual debugging
    window.clearCostCodesCache = function() {
        try {
            localStorage.removeItem('cost_codes_data_cache');
            console.log('🧹 Cost codes cache cleared');
            return true;
        } catch (e) {
            console.error('Error clearing cache:', e);
            return false;
        }
    };
    
    window.debugFetchData = async function(bypassCache = true) {
        console.log('🔍 Manual data fetch requested (bypass cache:', bypassCache, ')');
        const url = bypassCache ? 
            '/api/cost-codes-with-groups?no-cache=true&t=' + Date.now() : 
            '/api/cost-codes-with-groups';
        
        try {
            console.time('API Request');
            const response = await fetch(url);
            const data = await response.json();
            console.timeEnd('API Request');
            console.log('📊 Received', data.length, 'records');
            return data;
        } catch (e) {
            console.error('Error in manual fetch:', e);
            return null;
        }
    };
})();

// USAGE INSTRUCTIONS:
// 1. Copy this entire script
// 2. Open the browser console on the cost codes page
// 3. Paste and run the script
// 4. Watch the console for any detected patterns of refreshes
// 5. Use window.clearCostCodesCache() to manually clear the cache
// 6. Use window.debugFetchData() to manually test the API
