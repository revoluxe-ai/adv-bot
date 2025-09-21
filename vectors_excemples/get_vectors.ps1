# Скрипт для получения векторов из Redis в Kubernetes

# Получаем 100 ключей item_vector
$itemKeys = kubectl exec -it redis-1739448617-master-0 -- redis-cli --raw KEYS "item_vector:*" | Select-Object -First 100

# Получаем значения векторов item_vector
$itemVectorsFile = "vectors_excemples/item_vectors_100.txt"
New-Item -ItemType File -Path $itemVectorsFile -Force | Out-Null
foreach ($key in $itemKeys) {
    if ($key -match "item_vector:(.+)") {
        $itemId = $matches[1]
        Write-Host "Getting vector for item $itemId..."
        $vector = kubectl exec -it redis-1739448617-master-0 -- redis-cli --raw GET "$key"
        if ($vector) {
            Add-Content -Path $itemVectorsFile -Value "$key`n$vector`n" -Encoding utf8
        }
    }
}

# Получаем 100 ключей keyword_vector
$keywordKeys = kubectl exec -it redis-1739448617-master-0 -- redis-cli --raw KEYS "keyword_vector:*" | Select-Object -First 100

# Получаем значения векторов keyword_vector
$keywordVectorsFile = "vectors_excemples/keyword_vectors_100.txt"
New-Item -ItemType File -Path $keywordVectorsFile -Force | Out-Null
foreach ($key in $keywordKeys) {
    Write-Host "Getting vector for keyword..."
    $vector = kubectl exec -it redis-1739448617-master-0 -- redis-cli --raw GET "$key"
    if ($vector) {
        Add-Content -Path $keywordVectorsFile -Value "$key`n$vector`n" -Encoding utf8
    }
}

Write-Host "Done! Vectors saved to $itemVectorsFile and $keywordVectorsFile"
