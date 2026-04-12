# LoCoMo JSON 翻译脚本 - 部署指南

## 1. 克隆仓库

```bash
git clone https://github.com/Chen-yuee/MolyCasesCreate.git
cd MolyCasesCreate
```

## 2. 创建 Conda 环境

```bash
# 创建新环境（Python 3.10）
conda create -n molycase python=3.10 -y

# 激活环境
conda activate molycase
```

## 3. 安装依赖

```bash
pip install -r requirements.txt
```

或手动安装：

```bash
pip install tiktoken requests tqdm
```

## 4. 配置 API

编辑 `config.json`，填入你的 API 信息：

```bash
vim config.json
```

需要修改的字段：
- `api.endpoint`: API 端点
- `api.api_key`: API 密钥
- `api.model`: 模型名称

## 5. 运行翻译

```bash
# 基础用法
python translate_json.py \
  --input locomo10.json \
  --output locomo10_zh.json \
  --config config.json

# 自定义并发和批量大小
python translate_json.py \
  --input locomo10.json \
  --output locomo10_zh.json \
  --config config.json \
  --max-workers 8 \
  --batch-size 20
```

## 6. 参数说明

- `--input`: 输入 JSON 文件路径
- `--output`: 输出 JSON 文件路径
- `--config`: 配置文件路径（默认 `config.json`）
- `--max-workers`: 并发线程数（默认 4）
- `--batch-size`: 批量翻译大小（默认 10）

## 7. 验证结果

```bash
# 检查记录数
python -c "import json; data=json.load(open('locomo10_zh.json')); print(f'Records: {len(data)}')"

# 查看翻译示例
python -c "
import json
data = json.load(open('locomo10_zh.json'))
print('Question:', data[0]['qa'][0]['question'])
print('Answer:', data[0]['qa'][0]['answer'])
print('Conversation:', data[0]['conversation']['session_1'][0]['text'])
"
```

## 8. 常见问题

### 依赖安装失败

```bash
# 使用清华源
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### API 调用失败

检查：
1. `config.json` 中的 `api_key` 是否正确
2. `endpoint` 是否可访问
3. 网络连接是否正常

### 内存不足

减少并发数：

```bash
python translate_json.py \
  --input locomo10.json \
  --output locomo10_zh.json \
  --max-workers 2
```
