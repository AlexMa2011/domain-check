# domain-check
## 如何使用
- 下载最新版本
- 安装依赖
`pip install -r requirements.txt`
- 运行
例如查询包含数字和字母的3位（最多3位，最少3位）.nz域名
```
domain.py \
  -t .nz \
  -c abcdefghijklmnopqrstuvwxyz1234567890 \
  --min-len 2 --max-len 2 \
  -o results.txt
```
