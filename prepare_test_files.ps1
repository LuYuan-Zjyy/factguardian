# 测试文件准备脚本
# 帮助用户准备和验证测试文件

Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host "测试文件准备助手" -ForegroundColor Cyan
Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host ""

$projectRoot = $PSScriptRoot
if (-not $projectRoot) {
    $projectRoot = Get-Location
}

Write-Host "项目根目录: $projectRoot" -ForegroundColor Yellow
Write-Host ""

# 检查文件
Write-Host "检查测试文件..." -ForegroundColor Yellow
Write-Host ""

$files = @{
    "参考对比测试文件" = @(
        "main.docx",
        "reference1.docx",
        "reference2.docx"
    )
    "图片对比测试文件" = @(
        "architecture.png",
        "diagram.png",
        "flowchart.png",
        "system.png",
        "document.docx"
    )
}

$allFound = $true

foreach ($category in $files.Keys) {
    Write-Host "$category :" -ForegroundColor Cyan
    $categoryFiles = $files[$category]
    
    foreach ($file in $categoryFiles) {
        $filePath = Join-Path $projectRoot $file
        $exists = Test-Path $filePath
        
        if ($exists) {
            $size = (Get-Item $filePath).Length
            $sizeKB = [math]::Round($size / 1KB, 2)
            Write-Host "  ✓ $file ($sizeKB KB)" -ForegroundColor Green
        } else {
            Write-Host "  ✗ $file (未找到)" -ForegroundColor Red
            $allFound = $false
        }
    }
    Write-Host ""
}

# 总结
Write-Host "=" * 70 -ForegroundColor Cyan
if ($allFound) {
    Write-Host "✓ 所有测试文件已准备完成！" -ForegroundColor Green
    Write-Host ""
    Write-Host "可以运行测试:" -ForegroundColor Yellow
    Write-Host "  python test_reference_comparison.py" -ForegroundColor White
    Write-Host "  python test_image_comparison.py" -ForegroundColor White
} else {
    Write-Host "⚠ 部分文件缺失" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "请将以下文件放在项目根目录:" -ForegroundColor Yellow
    Write-Host "  参考对比:" -ForegroundColor Cyan
    Write-Host "    - main.docx (必需)" -ForegroundColor White
    Write-Host "    - reference1.docx (至少需要一个)" -ForegroundColor White
    Write-Host "  图片对比:" -ForegroundColor Cyan
    Write-Host "    - architecture.png (或 diagram.png/flowchart.png/system.png)" -ForegroundColor White
    Write-Host "    - document.docx" -ForegroundColor White
    Write-Host ""
    Write-Host "项目根目录: $projectRoot" -ForegroundColor Yellow
}
Write-Host "=" * 70 -ForegroundColor Cyan

