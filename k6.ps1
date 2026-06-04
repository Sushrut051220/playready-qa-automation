$token = az account get-access-token --resource https://cognitiveservices.azure.com --query accessToken -o tsv

k6 run `
  -e AUTH_TOKEN=$token `
  playready_load_test.js