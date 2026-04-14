---
description: Python 环境约束 — 使用 python3.8 和 venv
---

# Python 环境约束

## 规则

1. **永远使用 `python3.8`**，不要用 `python3`、`python` 或其他版本
2. 后端项目在 `agentic_on_arch/` 目录下，使用 venv 虚拟环境
3. 运行 Python 命令时，先 `source venv/bin/activate`，再用 `python`（venv 内的 python 就是 3.8）
4. 如果不在 venv 内运行，必须显式使用 `python3.8 -m ...`

## 示例

```bash
# ✅ 正确 — 在 venv 内
cd "/Users/mason/Desktop/code /angenimi-agentic/lawfirmAGplat/agentic_on_arch" && source venv/bin/activate && python -c "print('hello')"

# ✅ 正确 — 显式版本
python3.8 -c "print('hello')"

# ❌ 错误 — 不要用这些
python3 -c "print('hello')"
python -c "print('hello')"
```

## 端口约束

- 后端端口: **8001**（8000 被其他程序占用）
- 前端端口: **5173**（Vite 默认）
