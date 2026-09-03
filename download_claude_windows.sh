#!/bin/bash
# 使用 wget 的浏览器模拟下载 Claude Windows 安装包

DOWNLOAD_URL="https://storage.googleapis.com/osprey-downloads-c02f6a0d-347c-492b-a752-3e0651722e97/nest-win-x64/Claude-Setup-x64.exe"

echo "正在下载 Claude Windows 安装包..."
wget \
  --user-agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" \
  --header="Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8" \
  --header="Accept-Language: en-US,en;q=0.5" \
  --no-check-certificate \
  -O "Claude-Setup-x64.exe" \
  "$DOWNLOAD_URL"

if [ $? -eq 0 ] && [ -f "Claude-Setup-x64.exe" ]; then
    SIZE=$(ls -lh Claude-Setup-x64.exe | awk '{print $5}')
    echo "✅ 下载成功！文件大小: $SIZE"
    file Claude-Setup-x64.exe
else
    echo "❌ 下载失败，尝试备用链接..."
    # 备用：直接从 GitHub releases 或其他镜像下载
fi
