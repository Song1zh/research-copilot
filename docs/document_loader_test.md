# Document loader 测试记录

 ## 1.目标

验证文档加载模块是否能正确读取以下文件类型，并比较切分前后效果
- txt
- md
- pdf

## 2. 文件位置

```text
core/document_loader.py
tests/test_document_loader.py
```

## 3. 测试命令

### txt
```bash
python -m tests.test_document_loader --path data/sample.txt
```

### md
```bash
python -m tests.test_document_loader --path README.md
```

### pdf
```bash
python -m tests.test_document_loader --path data/sample.pdf
```

## 4.测试点
- 是否成功读取
- 是否正确识别
- pdf是否能提取出文本
- 切分前文本长度与切分后chunk数量
- chunk是否合理

## 5.当前边界

当前版本的 document loader 存在以下边界：

1. markdown 按纯文本处理，未做结构解析
2. pdf 仅适用于文本型 PDF
3. 对扫描版 PDF 不支持 OCR
4. 切分策略为简单字符切分，尚未按语义边界优化