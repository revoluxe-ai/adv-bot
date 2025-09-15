# =============================
# Генерация единого файла моделей из Swagger с правильной обработкой кодировки
# =============================

# --- Настройки ---
$swaggerFile = ".wb-api-swaggers/08-promotion.yaml"
$outputDir = "app/core/mp/wb/generated/promotion/v1"
$modelFile = Join-Path $outputDir "models.py"

# --- Шаг 0: Создаём папку для моделей ---
if (-not (Test-Path $outputDir))
{
    New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
    Write-Host "Создана папка: $outputDir"
}

# --- Функция для правильной обработки кодировки файлов ---
function Fix-FileEncoding
{
    param($FilePath)

    try
    {
        # Сначала пробуем прочитать как UTF-8
        $content = Get-Content -Raw -Path $FilePath -Encoding UTF8

        # Проверяем, есть ли замещающие символы или некорректные данные
        if ($content -match "[\uFFFD]" -or ($content.Length -gt 0 -and $content[0] -eq [char]0xFEFF))
        {
            throw "Возможно некорректная кодировка"
        }

        Write-Host "Файл уже в корректной UTF-8 кодировке: $FilePath"
        return $content
    }
    catch
    {
        Write-Host "Исправляем кодировку файла: $FilePath"

        # Пробуем различные кодировки для чтения
        $encodings = @(
            [System.Text.Encoding]::GetEncoding("windows-1251"),
            [System.Text.Encoding]::GetEncoding("utf-8"),
            [System.Text.Encoding]::Default,
            [System.Text.Encoding]::GetEncoding("iso-8859-1")
        )

        foreach ($encoding in $encodings)
        {
            try
            {
                $bytes = [System.IO.File]::ReadAllBytes($FilePath)
                $content = $encoding.GetString($bytes)

                # Проверяем качество декодирования
                if (-not ($content -match "[\uFFFD]") -and $content.Length -gt 0)
                {
                    # Сохраняем в UTF-8 без BOM
                    $utf8NoBom = New-Object System.Text.UTF8Encoding $false
                    [System.IO.File]::WriteAllText($FilePath, $content, $utf8NoBom)
                    Write-Host "Файл перекодирован из $( $encoding.EncodingName ) в UTF-8: $FilePath"
                    return $content
                }
            }
            catch
            {
                continue
            }
        }
        throw "Не удалось определить корректную кодировку файла"
    }
}

# --- Функция для исправления кодировки сгенерированного файла ---
function Fix-GeneratedFileEncoding
{
    param($FilePath)

    if (-not (Test-Path $FilePath))
    {
        throw "Файл не найден: $FilePath"
    }

    try
    {
        # Читаем файл как байты
        $bytes = [System.IO.File]::ReadAllBytes($FilePath)

        # Пробуем различные кодировки для декодирования
        $encodings = @(
            [System.Text.Encoding]::UTF8,
            [System.Text.Encoding]::GetEncoding("windows-1251"),
            [System.Text.Encoding]::Default
        )

        $bestContent = $null
        $bestEncoding = $null

        foreach ($encoding in $encodings)
        {
            try
            {
                $content = $encoding.GetString($bytes)

                # Проверяем качество декодирования
                if (-not ($content -match "[\uFFFD]") -and
                        $content -match "class\s+\w+" -and
                        $content.Length -gt 50)
                {

                    # Если есть русские символы, проверяем их корректность
                    if ($content -match "[а-яё]")
                    {
                        # Проверяем, что нет крякозябр типа "Р'Р»РѕРє"
                        if (-not ($content -match "[Р][°-№]"))
                        {
                            $bestContent = $content
                            $bestEncoding = $encoding
                            Write-Host "Найдена корректная кодировка с русскими символами: $( $encoding.EncodingName )"
                            break
                        }
                    }
                    else
                    {
                        # Если русских символов нет, используем первый рабочий вариант
                        if ($null -eq $bestContent)
                        {
                            $bestContent = $content
                            $bestEncoding = $encoding
                        }
                    }
                }
            }
            catch
            {
                continue
            }
        }

        if ($null -eq $bestContent)
        {
            Write-Warning "Не удалось найти корректную кодировку, используем UTF-8 по умолчанию"
            $bestContent = [System.Text.Encoding]::UTF8.GetString($bytes)
            $bestEncoding = [System.Text.Encoding]::UTF8
        }

        # Сохраняем в UTF-8 без BOM
        $utf8NoBom = New-Object System.Text.UTF8Encoding $false
        [System.IO.File]::WriteAllText($FilePath, $bestContent, $utf8NoBom)

        Write-Host "Кодировка файла исправлена: $( $bestEncoding.EncodingName ) -> UTF-8"
        return $bestContent
    }
    catch
    {
        Write-Error "Ошибка при исправлении кодировки файла $FilePath : $_"
        return $null
    }
}

# --- Шаг 1: Проверяем и исправляем кодировку исходного YAML файла ---
try
{
    $yamlContent = Fix-FileEncoding -FilePath $swaggerFile
    Write-Host "✅ YAML файл обработан корректно"
}
catch
{
    Write-Error "Ошибка при обработке YAML файла: $_"
    exit 1
}

# --- Шаг 2: Настраиваем окружение для корректной работы с UTF-8 ---
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"
$env:LC_ALL = "en_US.UTF-8"

Write-Host "Переменные окружения для UTF-8 установлены"

# --- Шаг 3: Генерация файла моделей ---
Write-Host "Генерация моделей из YAML..."

try
{
    datamodel-codegen `
        --input $swaggerFile `
        --input-file-type openapi `
        --output-model-type pydantic_v2.BaseModel `
        --output $modelFile `
        --encoding utf-8

    if (-not (Test-Path $modelFile))
    {
        throw "Файл models.py не был создан"
    }

    Write-Host "✅ Файл моделей сгенерирован: $modelFile"
}
catch
{
    Write-Error "Ошибка при генерации моделей: $_"
    exit 1
}

# --- Шаг 4: Исправляем кодировку сгенерированного файла ---
Write-Host "Исправление кодировки сгенерированного файла..."

try
{
    $finalContent = Fix-GeneratedFileEncoding -FilePath $modelFile

    if ($null -eq $finalContent)
    {
        throw "Не удалось исправить кодировку файла models.py"
    }

    Write-Host "✅ Кодировка исправлена успешно"
}
catch
{
    Write-Error "Ошибка при исправлении кодировки: $_"
    exit 1
}

# --- Шаг 5: Создаём __init__.py для удобного импорта ---
$initFile = Join-Path $outputDir "__init__.py"
$initContent = @"
# Auto-generated models from Swagger
from .models import *
"@

try
{
    $utf8NoBom = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText($initFile, $initContent, $utf8NoBom)
    Write-Host "✅ Создан файл __init__.py"
}
catch
{
    Write-Warning "Не удалось создать __init__.py: $_"
}

# --- Шаг 6: Финальная проверка ---
if (Test-Path $modelFile)
{
    $fileSize = (Get-Item $modelFile).Length
    Write-Host ""
    Write-Host "🎉 Генерация завершена успешно!"
    Write-Host "📁 Файл: $modelFile"
    Write-Host "📏 Размер: $fileSize bytes"
    Write-Host ""
    Write-Host "Использование:"
    Write-Host "  from dto.models import ClassName"
    Write-Host "  # или"
    Write-Host "  from dto import ClassName  # если есть __init__.py"
}
else
{
    Write-Error "❌ Финальная проверка не пройдена - файл models.py не найден"
    exit 1
}