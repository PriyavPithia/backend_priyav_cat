# SSH Tunnel Manager for RDS Connection
# PowerShell version of manage_tunnel.sh

param(
    [string]$Action = "status"
)

# Configuration
$RDS_ENDPOINT = "stg-sattva-database.cx4eqksy0skp.eu-west-2.rds.amazonaws.com"
$BASTION_HOST = "18.170.28.143"
$LOCAL_PORT = "5433"
$RDS_PORT = "5432"
$SSH_KEY = "C:\Users\Priyav Pithia\Downloads\accesskey.pem"
$BASTION_USER = "ubuntu"

# Colors for output
$RED = "Red"
$GREEN = "Green"
$YELLOW = "Yellow"

# Function to check if tunnel is running
function Test-Tunnel {
    # Check if port is in use (better method for Windows)
    $portTest = Get-NetTCPConnection -LocalPort $LOCAL_PORT -ErrorAction SilentlyContinue
    if ($portTest) {
        return $true
    }
    
    # Fallback: Check SSH processes
    $processes = Get-Process -Name "ssh" -ErrorAction SilentlyContinue
    foreach ($proc in $processes) {
        try {
            $cmdLine = (Get-WmiObject Win32_Process -Filter "ProcessId = $($proc.Id)").CommandLine
            if ($cmdLine -and $cmdLine -like "*$LOCAL_PORT*") {
                return $true
            }
        } catch {
            # Ignore errors getting command line
        }
    }
    return $false
}

# Function to start tunnel
function Start-Tunnel {
    Write-Host "Starting SSH tunnel to RDS..." -ForegroundColor $YELLOW
    
    # Kill existing tunnel if any
    Stop-Tunnel
    
    try {
        # Start tunnel without -f flag (fork) which causes issues on Windows
        # Use Start-Process to run in background instead
        $sshArgs = @(
            "-L", "${LOCAL_PORT}:${RDS_ENDPOINT}:${RDS_PORT}",
            "-i", "${SSH_KEY}",
            "${BASTION_USER}@${BASTION_HOST}",
            "-N",
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=NUL",
            "-o", "LogLevel=ERROR",
            "-o", "ServerAliveInterval=60",
            "-o", "ServerAliveCountMax=3"
        )
        
        $sshProcess = Start-Process -FilePath "ssh" -ArgumentList $sshArgs -WindowStyle Hidden -PassThru
        
        # Wait for tunnel to establish
        Start-Sleep -Seconds 5
        
        # Check if tunnel is working
        $maxRetries = 10
        $retries = 0
        while ($retries -lt $maxRetries) {
            if (Test-Tunnel) {
                Write-Host "✅ SSH tunnel started successfully" -ForegroundColor $GREEN
                Write-Host "   Local port: $LOCAL_PORT" -ForegroundColor $GREEN
                Write-Host "   Remote: ${RDS_ENDPOINT}:${RDS_PORT}" -ForegroundColor $GREEN
                Write-Host "   Process ID: $($sshProcess.Id)" -ForegroundColor $GREEN
                return $true
            }
            Start-Sleep -Seconds 1
            $retries++
        }
        
        Write-Host "❌ Failed to start SSH tunnel - port not accessible" -ForegroundColor $RED
        if ($sshProcess -and !$sshProcess.HasExited) {
            $sshProcess.Kill()
        }
        return $false
        
    } catch {
        Write-Host "❌ Failed to start SSH tunnel: $($_.Exception.Message)" -ForegroundColor $RED
        return $false
    }
}

# Function to stop tunnel
function Stop-Tunnel {
    Write-Host "Stopping SSH tunnel..." -ForegroundColor $YELLOW
    
    # Find and stop SSH processes related to our tunnel
    $processes = Get-Process -Name "ssh" -ErrorAction SilentlyContinue
    $stopped = $false
    
    foreach ($proc in $processes) {
        try {
            $cmdLine = (Get-WmiObject Win32_Process -Filter "ProcessId = $($proc.Id)").CommandLine
            if ($cmdLine -and $cmdLine -like "*$LOCAL_PORT*") {
                $proc | Stop-Process -Force
                $stopped = $true
                Write-Host "✅ Stopped SSH process (PID: $($proc.Id))" -ForegroundColor $GREEN
            }
        } catch {
            # If we can't get command line, stop all ssh processes to be safe
            $proc | Stop-Process -Force -ErrorAction SilentlyContinue
            $stopped = $true
        }
    }
    
    if (-not $stopped) {
        Write-Host "No tunnel was running" -ForegroundColor $YELLOW
    }
    
    # Wait a moment for cleanup
    Start-Sleep -Seconds 1
}

# Function to check tunnel status
function Get-TunnelStatus {
    if (Test-Tunnel) {
        Write-Host "✅ SSH tunnel is running" -ForegroundColor $GREEN
        Write-Host "   Local port: $LOCAL_PORT is active" -ForegroundColor $GREEN
        
        # Show SSH processes if any
        $processes = Get-Process -Name "ssh" -ErrorAction SilentlyContinue
        if ($processes) {
            Write-Host "   SSH processes:" -ForegroundColor $GREEN
            $processes | Format-Table ProcessName, Id, StartTime -AutoSize
        }
    } else {
        Write-Host "❌ SSH tunnel is not running" -ForegroundColor $RED
        Write-Host "   Port $LOCAL_PORT is not in use" -ForegroundColor $RED
    }
}

# Function to test database connection
function Test-DatabaseConnection {
    Write-Host "Testing database connection..." -ForegroundColor $YELLOW
    
    if (-not (Test-Tunnel)) {
        Write-Host "❌ SSH tunnel not running. Starting tunnel first..." -ForegroundColor $RED
        if (-not (Start-Tunnel)) {
            return $false
        }
    }
    
    # Test connection using Python
    $pythonScript = @"
import psycopg2
import sys
try:
    conn = psycopg2.connect(
        host='localhost',
        port=$LOCAL_PORT,
        database='postgres',
        user='rdssattvapg',
        password='(,7(UP4~U#6UadLQ'
    )
    print('✅ Database connection successful!')
    cursor = conn.cursor()
    cursor.execute('SELECT version();')
    version = cursor.fetchone()[0]
    print(f'   Database version: {version[:50]}...')
    conn.close()
except Exception as e:
    print(f'❌ Database connection failed: {e}')
    sys.exit(1)
"@
    
    try {
        & ".\venv\Scripts\python.exe" -c $pythonScript
        return $true
    } catch {
        Write-Host "❌ Database connection test failed: $($_.Exception.Message)" -ForegroundColor $RED
        return $false
    }
}

# Function to ensure tunnel is running
function Ensure-Tunnel {
    if (-not (Test-Tunnel)) {
        Start-Tunnel
    } else {
        Write-Host "✅ SSH tunnel already running" -ForegroundColor $GREEN
    }
}

# Main function
switch ($Action.ToLower()) {
    "start" {
        Start-Tunnel
    }
    "stop" {
        Stop-Tunnel
    }
    "restart" {
        Stop-Tunnel
        Start-Sleep -Seconds 1
        Start-Tunnel
    }
    "status" {
        Get-TunnelStatus
    }
    "test" {
        Test-DatabaseConnection
    }
    "ensure" {
        Ensure-Tunnel
    }
    default {
        Write-Host "Usage: .\manage_tunnel.ps1 {start|stop|restart|status|test|ensure}" -ForegroundColor $YELLOW
        Write-Host ""
        Write-Host "Commands:" -ForegroundColor $YELLOW
        Write-Host "  start   - Start SSH tunnel to RDS" -ForegroundColor $YELLOW
        Write-Host "  stop    - Stop SSH tunnel" -ForegroundColor $YELLOW
        Write-Host "  restart - Restart SSH tunnel" -ForegroundColor $YELLOW
        Write-Host "  status  - Check tunnel status" -ForegroundColor $YELLOW
        Write-Host "  test    - Test database connection" -ForegroundColor $YELLOW
        Write-Host "  ensure  - Ensure tunnel is running (start if needed)" -ForegroundColor $YELLOW
        exit 1
    }
}
