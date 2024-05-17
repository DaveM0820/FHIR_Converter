# Check if Python is installed
if (-Not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error "Python is not installed. Please install Python before running this script."
    exit 1
}

# Check if pip is installed
if (-Not (Get-Command pip -ErrorAction SilentlyContinue)) {
    Write-Error "pip is not installed. Please install pip before running this script."
    exit 1
}

# Path to the requirements file
$requirementsFile = "requirements.txt"

# Check if requirements file exists
if (-Not (Test-Path $requirementsFile)) {
    Write-Error "requirements.txt file not found in the current directory."
    exit 1
}

# Install the dependencies listed in requirements.txt
try {
    Write-Output "Installing Python dependencies from $requirementsFile..."
    pip install -r $requirementsFile
    Write-Output "Dependencies installed successfully."
} catch {
    Write-Error "An error occurred while installing the dependencies: $_"
    exit 1
}

