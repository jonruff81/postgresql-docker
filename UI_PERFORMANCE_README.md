# UI Performance Improvements

## 📑 Table of Contents
- [Issue: Cost Codes UI Page Flashing](#issue-cost-codes-ui-page-flashing)
- [Root Causes](#root-causes)
- [Implemented Solutions](#implemented-solutions)
  - [Client-Side Improvements](#client-side-improvements-cost_codes_gridhtml)
  - [Server-Side Improvements](#server-side-improvements-apppy)
- [Tools for Debugging](#tools-for-debugging)
- [How to Test](#how-to-test)
- [Additional Notes](#additional-notes)
- [Core Tech Stack](#core-tech-stack)

## Issue: Cost Codes UI Page Flashing

The Cost Codes grid page was flashing and refreshing frequently, causing visual disruption and potentially affecting performance.

## Root Causes

The investigation revealed several causes of the frequent refreshing:

1. **Frequent API Calls**: The UI was making frequent API calls to refresh data without proper throttling.
2. **Ineffective Caching**: Both client-side and server-side caching were not optimally configured.
3. **Unnecessary Redraws**: The grid was being redrawn even when data hadn't changed.
4. **Short Cache Timeouts**: Cache expiration times were too short (1 minute).

## Implemented Solutions

### Client-Side Improvements (cost_codes_grid.html)

1. **Reduced Data Refresh Frequency**:
   - Increased cache duration from 5 minutes to 30 minutes
   - Increased minimum time between refreshes from 10 to 30 seconds
   - Initial load now prioritizes cached data instead of forcing a refresh

2. **Prevented Unnecessary Grid Updates**:
   - Added data comparison to avoid updating the grid when data hasn't changed
   - Silent background refreshes don't trigger visual updates unless data changes
   - Improved status message handling to reduce UI flickering

3. **Enhanced Cache Management**:
   - Clear cache explicitly on manual refresh operations
   - Better error handling for cache operations

### Server-Side Improvements (app.py)

1. **Advanced HTTP Caching**:
   - Implemented ETag-based caching for efficient 304 Not Modified responses
   - Added proper Cache-Control headers
   - Extended server-side cache duration from 60 seconds to 5 minutes

2. **Optimized Data Comparison**:
   - Server now calculates content hash to efficiently determine if data has changed
   - Conditional requests are properly handled

3. **Improved Error Handling**:
   - Better error detection and reporting for API failures

## Tools for Debugging

We've also created several debugging tools to help diagnose and fix any future performance issues:

1. **Debug Page**: A special debug page at `/debug/cost-codes` that includes tools to:
   - Force refresh data
   - Clear browser cache
   - Monitor API response times
   - View raw API responses

2. **Monitoring Script**: The `monitor_api_calls.py` script can now track API performance over time.

3. **Console Debug Script**: A JavaScript snippet you can paste in your browser console to diagnose issues.

## How to Test

1. Navigate to the Cost Codes page and observe if the flashing/refreshing has stopped
2. Use the Debug tool at `/debug/cost-codes` if you need to clear cache or force a refresh
3. Check browser network traffic to verify reduced API calls

## Additional Notes

- The application now makes better use of client-side caching, reducing server load
- Data integrity is maintained as any manual refresh will still get the latest data
- Status messages now appear only for user-initiated actions, reducing visual noise

## Core Tech Stack

- **Frontend**: JavaScript with AG-Grid Enterprise
- **Backend**: Python Flask application
- **Caching**: Browser localStorage and ETag-based HTTP caching
- **Debugging Tools**: Custom monitoring scripts and debug pages
- **Performance Monitoring**: Network request tracking and timing
- **Data Comparison**: Hash-based content comparison for change detection
