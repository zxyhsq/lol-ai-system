# LOL AI System — 与 GitHub 同步
# 仓库: git@github.com:zxyhsq/lol-ai-system.git

param(
    [Parameter(Position = 0)]
    [ValidateSet("pull", "push", "status", "log")]
    [string]$Action = "status",

    [string]$Message = "Update"
)

$Git = "C:\Program Files\Git\cmd\git.exe"
$RepoRoot = $PSScriptRoot

if (-not (Test-Path $Git)) {
    Write-Error "未找到 Git，请安装: https://git-scm.com/download/win"
    exit 1
}

Set-Location $RepoRoot

function Invoke-Git {
    param([string[]]$Args)
    & $Git @Args
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

switch ($Action) {
    "pull" {
        Write-Host ">>> 从 GitHub 拉取最新代码 ..."
        Invoke-Git fetch origin
        Invoke-Git pull origin main
        Write-Host ">>> 拉取完成"
    }
    "push" {
        Write-Host ">>> 提交并推送到 GitHub ..."
        Invoke-Git add -A
        $status = & $Git status --porcelain
        if ($status) {
            Invoke-Git -c user.name="lol-ai-system" -c user.email="lol-ai-system@local" commit -m $Message
        } else {
            Write-Host "没有需要提交的更改"
        }
        Invoke-Git push -u origin main
        Write-Host ">>> 推送完成"
    }
    "status" {
        Invoke-Git status
        Invoke-Git remote -v
    }
    "log" {
        Invoke-Git log --oneline -10
    }
}
