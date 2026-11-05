<#
  每周增量更新：采集 → 补齐 → 过滤 → 评分 → 弹幕 → 卡片 → 导出
  （可选再构建站点、提交数据快照并推送，推上去后 Cloudflare Pages 自动部署）。

  用法：
    powershell -File scripts/update.ps1
    powershell -File scripts/update.ps1 -MaxPages 5 -Build
    powershell -File scripts/update.ps1 -SkipCards          # 不花钱，只更新数据
    powershell -File scripts/update.ps1 -Build -Push        # 更新 + 构建 + 推送（自动部署）

  挂计划任务示例（每周日 23:00）：
    schtasks /create /tn "BiliTube 周更" /sc weekly /d SUN /st 23:00 ^
      /tr "powershell -NoProfile -ExecutionPolicy Bypass -File <你的项目路径>\scripts\update.ps1 -Build -Push"
#>
param(
    [int]$MaxPages = 3,
    [switch]$SkipCards,
    [switch]$Build,
    [switch]$Push
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
    Write-Host '构建静态站点…'
    & npm --prefix web run build
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    Write-Host '构建完成：web/out'
}

if ($Push) {
    # 只提交数据快照；没有变化就不产生空提交
    & git add web/public/data
    & git diff --cached --quiet
    if ($LASTEXITCODE -eq 0) {
        Write-Host '数据没有变化，跳过提交'
    } else {
        $stamp = Get-Date -Format 'yyyy-MM-dd'
        & git commit -m "data: 周更 $stamp"
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        Write-Host '推送到远端，触发 Cloudflare Pages 构建…'
        & git push
        if ($LASTEXITCODE -ne 0) {
            Write-Host '推送失败：请检查远端配置与凭据（git remote -v / git push 单独试）' -ForegroundColor Yellow
            exit $LASTEXITCODE
        }
    }
}

Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm')] 完成"
