#!/bin/bash

# 设置镜像名称
IMAGE_NAME="brooksli1/rednote-research-agent"
TAG="latest"

# 检查是否有版本参数
if [ -n "$1" ]; then
    TAG="$1"
fi

FULL_IMAGE_NAME="$IMAGE_NAME:$TAG"

echo "🚀 开始构建镜像: $FULL_IMAGE_NAME"

# 构建镜像
docker build -t $FULL_IMAGE_NAME -f docker/Dockerfile .

if [ $? -eq 0 ]; then
    echo "✅ 镜像构建成功"
    
    echo "📤 准备推送到 Docker Hub..."
    docker push $FULL_IMAGE_NAME
    
    if [ $? -eq 0 ]; then
        echo "✅ 镜像推送成功: $FULL_IMAGE_NAME"
    else
        echo "❌ 镜像推送失败"
        exit 1
    fi
else
    echo "❌ 镜像构建失败"
    exit 1
fi
