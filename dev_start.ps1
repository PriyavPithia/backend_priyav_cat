# Development Server Startup Script
# PowerShell version of dev_start.sh
# Automatically manages SSH tunnel and starts the backend server

param(
    [switch]$SkipTunnel
)

# Colors
$GREEN = "Green"
$YELLOW = "Yellow"
$RED = "Red"

Write-Host "🚀 Starting CA Tadley Development Environment" -ForegroundColor $YELLOW
Write-Host ("=" * 50) -ForegroundColor $YELLOW

if (-not $SkipTunnel) {
    # Step 1: Ensure SSH tunnel is running
    Write-Host "1. Checking SSH tunnel..." -ForegroundColor $YELLOW
    & ".\manage_tunnel.ps1" -Action "ensure"
    
    # Step 2: Wait a moment for tunnel to stabilize
    Start-Sleep -Seconds 2
    
    # Step 3: Test database connection
    Write-Host "2. Testing database connection..." -ForegroundColor $YELLOW
    if (& ".\manage_tunnel.ps1" -Action "test") {
        Write-Host "✅ Database ready" -ForegroundColor $GREEN
    } else {
        Write-Host "❌ Database connection failed" -ForegroundColor $RED
        exit 1
    }
} else {
    Write-Host "Skipping tunnel setup (using -SkipTunnel flag)" -ForegroundColor $YELLOW
}

# Step 4: Start backend server
Write-Host "3. Starting backend server..." -ForegroundColor $YELLOW
Write-Host "Backend will be available at: http://localhost:8000" -ForegroundColor $GREEN
Write-Host "Press Ctrl+C to stop the server and tunnel" -ForegroundColor $YELLOW
Write-Host ""

# Function to cleanup on exit
function Cleanup {
    Write-Host ""
    Write-Host "Shutting down..." -ForegroundColor $YELLOW
    if (-not $SkipTunnel) {
        Write-Host "Stopping SSH tunnel..." -ForegroundColor $YELLOW
        & ".\manage_tunnel.ps1" -Action "stop"
    }
    exit 0
}

# Register cleanup function for Ctrl+C
[Console]::TreatControlCAsInput = $false
$null = Register-EngineEvent -SourceIdentifier PowerShell.Exiting -Action { Cleanup }

try {
    # Start the server
    & ".\venv\Scripts\uvicorn.exe" "src.main:app" --host "127.0.0.1" --port "8000" --reload
} catch {
    Write-Host "Error starting server: $($_.Exception.Message)" -ForegroundColor $RED
    Cleanup
}
