# Docker Desktop 诊断和修复脚本

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Docker Desktop 诊断和修复工具" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 1. 检查 Docker Desktop 是否安装
Write-Host "[1/6] 检查 Docker Desktop 安装..." -ForegroundColor Yellow
$dockerPath = Get-Command docker -ErrorAction SilentlyContinue
if ($dockerPath) {
    Write-Host "✓ Docker 已安装: $($dockerPath.Source)" -ForegroundColor Green
    docker --version
} else {
    Write-Host "✗ Docker 未安装，请先安装 Docker Desktop" -ForegroundColor Red
    Write-Host "下载地址: https://www.docker.com/products/docker-desktop/" -ForegroundColor Yellow
    exit 1
}

Write-Host ""

# 2. 检查 Docker Desktop 进程是否运行
Write-Host "[2/6] 检查 Docker Desktop 进程..." -ForegroundColor Yellow
$dockerProcess = Get-Process "Docker Desktop" -ErrorAction SilentlyContinue
if ($dockerProcess) {
    Write-Host "✓ Docker Desktop 进程正在运行 (PID: $($dockerProcess.Id))" -ForegroundColor Green
} else {
    Write-Host "✗ Docker Desktop 进程未运行" -ForegroundColor Red
    Write-Host "正在尝试启动 Docker Desktop..." -ForegroundColor Yellow
    
    # 尝试启动 Docker Desktop
    $dockerDesktopPath = "${env:ProgramFiles}\Docker\Docker\Docker Desktop.exe"
    if (Test-Path $dockerDesktopPath) {
        Start-Process $dockerDesktopPath
        Write-Host "✓ 已启动 Docker Desktop，请等待 30-60 秒后重试" -ForegroundColor Green
        Write-Host "提示: Docker Desktop 启动需要一些时间，请查看系统托盘图标" -ForegroundColor Yellow
    } else {
        Write-Host "✗ 找不到 Docker Desktop 可执行文件" -ForegroundColor Red
        Write-Host "请手动启动 Docker Desktop" -ForegroundColor Yellow
    }
    exit 1
}

Write-Host ""

# 3. 检查 Docker 守护进程连接
Write-Host "[3/6] 检查 Docker 守护进程连接..." -ForegroundColor Yellow
try {
    docker ps 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Docker 守护进程连接正常" -ForegroundColor Green
    } else {
        Write-Host "✗ Docker 守护进程连接失败" -ForegroundColor Red
        Write-Host "尝试重启 Docker Desktop..." -ForegroundColor Yellow
        exit 1
    }
} catch {
    Write-Host "✗ Docker 守护进程连接失败: $_" -ForegroundColor Red
    Write-Host "请确保 Docker Desktop 已完全启动" -ForegroundColor Yellow
    exit 1
}

Write-Host ""

# 4. 检查 Docker Compose
Write-Host "[4/6] 检查 Docker Compose..." -ForegroundColor Yellow
$composeVersion = docker-compose --version 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Docker Compose 可用: $composeVersion" -ForegroundColor Green
} else {
    Write-Host "✗ Docker Compose 不可用" -ForegroundColor Red
    exit 1
}

Write-Host ""

# 5. 检查项目文件
Write-Host "[5/6] 检查项目文件..." -ForegroundColor Yellow
if (Test-Path "docker-compose.yml") {
    Write-Host "✓ docker-compose.yml 存在" -ForegroundColor Green
} else {
    Write-Host "✗ docker-compose.yml 不存在" -ForegroundColor Red
    exit 1
}

if (Test-Path "backend/Dockerfile") {
    Write-Host "✓ backend/Dockerfile 存在" -ForegroundColor Green
} else {
    Write-Host "✗ backend/Dockerfile 不存在" -ForegroundColor Red
    exit 1
}

Write-Host ""

# 6. 测试构建
Write-Host "[6/6] 测试 Docker 构建..." -ForegroundColor Yellow
Write-Host "执行: docker-compose build backend" -ForegroundColor Gray
Write-Host ""

docker-compose build backend

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "✓ 所有检查通过！Docker 已准备就绪" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "下一步: 运行 'docker-compose up -d' 启动服务" -ForegroundColor Cyan
} else {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "✗ 构建失败，请检查错误信息" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    exit 1
}

