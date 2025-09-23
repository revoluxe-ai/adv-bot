param(
    [string]$SpecUrl = "https://dev.wildberries.ru/yaml/ru/08-promotion.yaml",
    [string]$Generator = "python-pydantic-v2",
    [string]$ConfigPath = "/local/app/core/mp/wb/api/swagger_clients/promotion/v1_generated/config.yaml",
    [string]$OutputDir = "/local/app/core/mp/wb/api/swagger_clients/promotion/v1_generated"
)

# Проверка наличия Docker
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Docker не найден. Установите Docker и попробуйте снова."
    exit 1
}

Write-Host "🚀 Генерация клиента из $SpecUrl ..."

# Очистка папки перед генерацией
if (Test-Path $OutputDir) {
    Write-Host "🧹 Очистка старой версии клиента..."
    Remove-Item $OutputDir -Recurse -Force
}

# Генерация клиента через Docker
docker run --rm -v "${PWD}:/local" openapitools/openapi-generator-cli generate `
    -i $SpecUrl `
    -g $Generator `
    -o $OutputDir `
    -c $ConfigPath

Write-Host "✅ Готово! Клиент сгенерирован в $OutputDir"