Write-Host "----- Cleaning environment for RAGAS -----"

# Remove API key (critical for RAGAS)
if (Test-Path Env:AZURE_OPENAI_API_KEY) {
    Remove-Item Env:AZURE_OPENAI_API_KEY -ErrorAction SilentlyContinue
    Write-Host "✔ Removed AZURE_OPENAI_API_KEY"
} else {
    Write-Host "✔ AZURE_OPENAI_API_KEY already not set"
}

# Optional: remove embedding key if exists
if (Test-Path Env:AZURE_OPENAI_EMBEDDING_API_KEY) {
    Remove-Item Env:AZURE_OPENAI_EMBEDDING_API_KEY -ErrorAction SilentlyContinue
    Write-Host "✔ Removed AZURE_OPENAI_EMBEDDING_API_KEY"
}

# Validate
$apiKey = $env:AZURE_OPENAI_API_KEY
if ($null -eq $apiKey -or $apiKey -eq "") {
    Write-Host "✅ Environment clean - using DefaultAzureCredential"
} else {
    Write-Host "❌ API key still present!"
}

Write-Host "----- Done -----"
``