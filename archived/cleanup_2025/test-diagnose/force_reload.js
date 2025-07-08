// Force reload script - run this in browser console
(function() {
    console.log('🧹 Force reload script activated');
    
    // Clear localStorage cache
    try {
        localStorage.removeItem('cost_codes_data_cache');
        console.log('✅ Local storage cache cleared');
    } catch (e) {
        console.error('❌ Error clearing local storage:', e);
    }
    
    // Function to force reload with cache busting
    function forceReload() {
        console.log('🔄 Forcing page reload with cache busting...');
        // Add cache busting parameter to URL
        const currentUrl = new URL(window.location.href);
        currentUrl.searchParams.set('_t', Date.now());
        window.location.href = currentUrl.toString();
    }
    
    // Check if grid is initialized
    if (typeof gridApi !== 'undefined' && gridApi) {
        console.log('📊 Grid API found, attempting to force data refresh first...');
        
        try {
            // Show visual indicator
            const statusDiv = document.getElementById('statusMessage');
            if (statusDiv) {
                statusDiv.innerHTML = `
                    <div class="alert alert-info alert-dismissible fade show" role="alert">
                        <strong>Forcing data reload...</strong>
                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                    </div>
                `;
            }
            
            // Try to force refresh through the existing API
            const fetchAndLoad = async () => {
                try {
                    const url = '/api/cost-codes-with-groups?no-cache=true&t=' + Date.now();
                    console.log('📡 Fetching fresh data from:', url);
                    
                    const response = await fetch(url);
                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }
                    
                    const data = await response.json();
                    if (!Array.isArray(data)) {
                        throw new Error('Received non-array data');
                    }
                    
                    console.log(`✅ Received ${data.length} records`);
                    
                    // Update grid with new data
                    if (gridApi.setGridOption) {
                        gridApi.setGridOption('rowData', data);
                        console.log('✅ Grid data updated');
                        
                        if (statusDiv) {
                            statusDiv.innerHTML = `
                                <div class="alert alert-success alert-dismissible fade show" role="alert">
                                    <strong>Successfully loaded ${data.length} records!</strong>
                                    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                                </div>
                            `;
                        }
                        
                        return true;
                    }
                } catch (e) {
                    console.error('❌ Error refreshing data:', e);
                    return false;
                }
            };
            
            fetchAndLoad().then(success => {
                if (!success) {
                    console.log('⚠️ Direct data refresh failed, falling back to page reload');
                    setTimeout(forceReload, 1000);
                }
            });
        } catch (e) {
            console.error('❌ Error during refresh attempt:', e);
            setTimeout(forceReload, 1000);
        }
    } else {
        console.log('⚠️ Grid API not found, performing full page reload');
        forceReload();
    }
})();
