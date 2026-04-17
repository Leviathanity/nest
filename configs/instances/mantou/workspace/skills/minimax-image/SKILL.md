---
name: minimax-image
description: |
  使用 MiniMax Image Generation API 进行图像生成
  支持文生图、图生图（人物主体参考）
---

# MiniMax 图像生成技能

## 概述

使用 MiniMax Image Generation API 生成图像。

## API 信息

- **端点**: `POST https://api.minimaxi.com/v1/image_generation`
- **模型**: `image-01` (基础) 或 `image-01-live` (支持多种画风)
- **API Key**: 使用当前配置的 `${MINIMAX_API_KEY}`

## 使用方式

### 基本调用

```bash
cd ~/.openclaw/workspace/skills/minimax-image/scripts
./image.sh "一只小狗在踢足球" [输出文件路径]
```

### 参数说明

| 参数 | 必填 | 说明 |
|-----|-----|-----|
| prompt | ✅ | 图像描述文本 |
| output | ❌ | 输出文件路径，默认 `/tmp/image_output.png` |

### 可选参数

修改 `image.sh` 脚本中的参数：

| 参数 | 默认值 | 说明 |
|-----|-------|-----|
| MODEL | `image-01` | 图像生成模型 |
| ASPECT_RATIO | `1:1` | 宽高比 (1:1, 16:9, 9:16, 4:3, 3:4) |
| RESOLUTION | `1024x1024` | 输出分辨率 |

### 画风选项 (image-01-live)

可选风格：`风格漫画、3D动漫、写实风格、插画风格、国风、赛博朋克`

## 输出

生成的图像文件保存为 PNG 格式。

## 示例

```bash
# 基本用法
./image.sh "一只可爱的小狗在草地上奔跑"

# 指定输出路径
./image.sh "未来城市夜景" "/tmp/future_city.png"

# 使用16:9宽屏
ASPECT_RATIO="16:9" ./image.sh "风景照片"
```

## 注意事项

1. API 调用可能需要几秒钟
2. 图像描述越详细效果越好
3. 中文描述可以直接使用
