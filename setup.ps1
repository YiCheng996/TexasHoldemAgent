# 创建目录结构
$directories = @(
    "src\engine",
    "src\agents",
    "src\api",
    "src\web",
    "src\db",
    "src\utils",
    "config",
    "data",
    "tests",
    "docs"
)

foreach ($dir in $directories) {
    New-Item -ItemType Directory -Force -Path $dir
}

# 创建核心文件
$files = @(
    "src\engine\game.py",
    "src\engine\rules.py",
    "src\engine\state.py",
    "src\engine\dealer.py",
    "src\agents\base.py",
    "src\agents\llm.py",
    "src\agents\memory.py",
    "src\utils\logger.py",
    "config\game.yml",
    "config\agent.yml",
    "requirements.txt",
    "README.md",
    "docs\scratchpad.md",
    "docs\PRD.md",
    "docs\rules.md"
)

foreach ($file in $files) {
    New-Item -ItemType File -Force -Path $file
}

Write-Host "Project structure created successfully!" 