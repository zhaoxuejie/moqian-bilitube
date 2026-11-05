<#
  周更流水线。默认只更新本地数据；加 -Push 进仓库，加 -Deploy 才发版上线。

  用法：
    powershell -File scripts/update.ps1                        # 只跑流水线
    powershell -File scripts/update.ps1 -Build                 # 跑完再本地构建，检查产物
    powershell -File scripts/update.ps1 -Push                  # 跑完提交数据并推 main（不部署）
    powershell -File scripts/update.ps1 -Deploy                # 提交 + 推 main + 推 release（部署）
    powershell -File scripts/update.ps1 -Deploy -Tag v0.3.0    # 顺带打 tag

  为什么分两层：
    Cloudflare 的生产分支是 release，不是 main。
    推 main 只进仓库、不构建；推 release 才触发构建与部署。

  挂计划任务（每周日 23:00，只收数据不发版）：
    schtasks /create /tn "BiliTube 周更" /sc weekly /d SUN /st 23:00 ^
      /tr "powershell -NoProfile -ExecutionPolicy Bypass -File <你的项目路径>\scripts\update.ps1 -Push"
#>
param(
    [int]$MaxPages = 3,
    [switch]$SkipCards,
    [switch]$Build,
    [switch]$Push,
    [switch]$Deploy,
    [string]$Tag
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $root

$python = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) { $python = 'python' }

$pipelineArgs = @('-m', 'bilitube', 'update', '--max-pages', $MaxPages)
if ($SkipCards) { $pipelineArgs += '--skip-cards' }

Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm')] 开始增量更新（max-pages=$MaxPages）"
& $python @pipelineArgs
if ($LASTEXITCODE -ne 0) {
    Write-Host "更新中断（exit $LASTEXITCODE）；已采部分已落库，重跑即可续上" -ForegroundColor Yellow
    exit $LASTEXITCODE
}

if ($Build) {
    Write-Host '本地构建（只为检查产物，不部署）…'
    & npm --prefix web run build
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    Write-Host '构建完成：web/out'
}

if ($Push -or $Deploy) {
    & git add web/public/data
    & git diff --cached --quiet
    if ($LASTEXITCODE -eq 0) {
        Write-Host '数据没有变化，跳过提交'
    } else {
        $stamp = Get-Date -Format 'yyyy-MM-dd'
        & git commit -m "data: 周更 $stamp"
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
    Write-Host '推送到 main（不触发部署）…'
    & git push origin HEAD:main
    if ($LASTEXITCODE -ne 0) {
        Write-Host '推送 main 失败：检查远端与凭据' -ForegroundColor Yellow
        exit $LASTEXITCODE
    }
}

if ($Deploy) {
    if ($Tag) {
        Write-Host "创建 tag $Tag…"
        & git tag -a $Tag -m $Tag
        if ($LASTEXITCODE -ne 0) { Write-Host "tag $Tag 已存在或创建失败，跳过" -ForegroundColor Yellow }
    }
    Write-Host '推送 release（触发 Cloudflare 构建与部署）…'
    & git push origin HEAD:release
    if ($LASTEXITCODE -ne 0) {
        Write-Host '推送 release 失败：检查远端与凭据' -ForegroundColor Yellow
        exit $LASTEXITCODE
    }
    if ($Tag) { & git push origin $Tag }
    Write-Host '已发版：约 2-3 分钟后 https://www.51bilitube.com 更新'
}

Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm')] 完成"
