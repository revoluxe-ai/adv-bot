# =============================
# Генерация моделей из одного Swagger с правильной обработкой кодировки
# =============================

# --- Настройки ---
$swaggerFile = ".wb-api-swaggers/08-promotion.yaml"
$outputDir = "app/core/mp/wb/client/promotion/dto"
$singleModelFile = Join-Path $outputDir "models.py"

# --- Шаг 0: Создаём папку для моделей ---
if (-not (Test-Path $outputDir))
{
    New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
}

# --- Шаг 1: Проверяем и исправляем кодировку YAML файла ---
function Fix-FileEncoding
{
    param($FilePath)

    try
    {
        # Пробуем прочитать как UTF-8
        $content = Get-Content -Raw -Path $FilePath -Encoding UTF8
        # Проверяем, есть ли BOM или некорректные символы
        if ($content -match "[\uFFFD]" -or $content[0] -eq [char]0xFEFF)
        {
            throw "Возможно некорректная кодировка"
        }
        Write-Host "Файл уже в UTF-8: $FilePath"
        return $content
    }
    catch
    {
        Write-Host "Попытка исправить кодировку файла: $FilePath"

        # Пробуем различные кодировки
        $encodings = @(
            [System.Text.Encoding]::GetEncoding("windows-1251"),
            [System.Text.Encoding]::GetEncoding("utf-8"),
            [System.Text.Encoding]::Default
        )

        foreach ($encoding in $encodings)
        {
            try
            {
                $bytes = [System.IO.File]::ReadAllBytes($FilePath)
                $content = $encoding.GetString($bytes)

                # Проверяем, читается ли контент нормально
                if (-not ($content -match "[\uFFFD]") -and $content.Length -gt 0)
                {
                    # Сохраняем в UTF-8 без BOM
                    $utf8NoBom = New-Object System.Text.UTF8Encoding $false
                    [System.IO.File]::WriteAllText($FilePath, $content, $utf8NoBom)
                    Write-Host "Файл перекодирован в UTF-8: $FilePath"
                    return $content
                }
            }
            catch
            {
                continue
            }
        }
        throw "Не удалось определить кодировку файла"
    }
}

$yamlContent = Fix-FileEncoding -FilePath $swaggerFile

# --- Шаг 2: Генерация единого файла моделей ---
Write-Host "Генерация моделей из YAML..."

# Устанавливаем переменные среды для корректной работы с UTF-8
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"

datamodel-codegen `
    --input $swaggerFile `
    --input-file-type openapi `
    --output-model-type pydantic_v2.BaseModel `
    --output $singleModelFile `
    --encoding utf-8

if (-not (Test-Path $singleModelFile))
{
    Write-Error "Ошибка: models.py не был создан!"
    exit 1
}

Write-Host "Сгенерирован единый файл: $singleModelFile"

# --- Шаг 3: Корректная обработка кодировки сгенерированного файла ---
function Fix-GeneratedFileEncoding
{
    param($FilePath)

    try
    {
        # Читаем файл как байты
        $bytes = [System.IO.File]::ReadAllBytes($FilePath)

        # Пробуем декодировать разными способами
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
                # Хороший текст не должен содержать замещающие символы и должен содержать ожидаемые ключевые слова
                if (-not ($content -match "[\uFFFD]") -and
                        $content -match "class\s+\w+" -and
                        $content.Length -gt 100)
                {

                    # Дополнительная проверка: если есть русские символы, они должны выглядеть правильно
                    if ($content -match "[а-яё]" -and -not ($content -match "[Р][°-№]"))
                    {
                        $bestContent = $content
                        $bestEncoding = $encoding
                        break
                    }
                    elseif (-not ($content -match "[а-яё]"))
                    {
                        # Если русских символов нет, берем первый валидный вариант
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
            Write-Warning "Не удалось корректно декодировать файл, используем UTF-8"
            $bestContent = [System.Text.Encoding]::UTF8.GetString($bytes)
        }

        # Сохраняем в UTF-8 без BOM
        $utf8NoBom = New-Object System.Text.UTF8Encoding $false
        [System.IO.File]::WriteAllText($FilePath, $bestContent, $utf8NoBom)

        Write-Host "Кодировка файла исправлена: $( $bestEncoding.EncodingName )"
        return $bestContent
    }
    catch
    {
        Write-Error "Ошибка при исправлении кодировки: $_"
        return $null
    }
}

$code = Fix-GeneratedFileEncoding -FilePath $singleModelFile

if ($null -eq $code)
{
    Write-Error "Не удалось исправить кодировку файла models.py"
    exit 1
}

# --- Шаг 4: Извлекаем импорты из начала файла ---
$lines = $code -split "`r?`n"
$importLines = @()
$classStartIndex = -1

for ($i = 0; $i -lt $lines.Length; $i++) {
    $line = $lines[$i].Trim()
    if ($line -match "^(from|import)\s+" -and -not ($line -match "^from\s+\.\w+\s+import"))
    {
        $importLines += $line
    }
    elseif ($line -match "^class\s+\w+\(" -and $classStartIndex -eq -1)
    {
        $classStartIndex = $i
        break
    }
}

# --- Шаг 5: Разделяем классы на отдельные файлы ---
if ($classStartIndex -eq -1)
{
    Write-Error "Не найдены определения классов в файле!"
    exit 1
}

$classCode = ($lines[$classStartIndex..($lines.Length - 1)]) -join "`n"
$classMatches = [regex]::Matches($classCode, "^(class\s+\w+\((?:BaseModel|RootModel)\):)", "Multiline")

$classImports = @()

for ($i = 0; $i -lt $classMatches.Count; $i++) {
    $start = $classMatches[$i].Index
    $end = if ($i -lt $classMatches.Count - 1)
    {
        $classMatches[$i + 1].Index
    }
    else
    {
        $classCode.Length
    }

    $singleClassCode = $classCode.Substring($start, $end - $start).Trim()

    # Имя класса
    $classNameMatch = [regex]::Match($singleClassCode, "^class\s+(\w+)\(")
    if (-not $classNameMatch.Success)
    {
        Write-Warning "Не удалось извлечь имя класса из: $($singleClassCode.Substring(0,[Math]::Min(50, $singleClassCode.Length)) )"
        continue
    }

    $className = $classNameMatch.Groups[1].Value

    # Создаем полный код файла с импортами
    $fullClassCode = ($importLines -join "`n") + "`n`n" + $singleClassCode

    $classFile = Join-Path $outputDir "$className.py"

    # Сохраняем в UTF-8 без BOM
    $utf8NoBom = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText($classFile, $fullClassCode, $utf8NoBom)

    # Импорт в __init__.py
    $classImports += "from .$className import $className"
    Write-Host "Создан файл класса: $className.py"
}

# --- Шаг 6: Создаём __init__.py с импортами всех классов ---
$initFile = Join-Path $outputDir "__init__.py"
$initContent = ($classImports -join "`n") + "`n"

$utf8NoBom = New-Object System.Text.UTF8Encoding $false
[System.IO.File]::WriteAllText($initFile, $initContent, $utf8NoBom)

Write-Host "✅ Генерация моделей завершена"
Write-Host "Создано файлов: $( $classImports.Count )"
Write-Host "Все модели доступны через: from dto import ClassName"

# --- Шаг 7: Удаляем временный файл models.py ---
if (Test-Path $singleModelFile)
{
    Remove-Item $singleModelFile -Force
    Write-Host "Временный файл models.py удален"
}