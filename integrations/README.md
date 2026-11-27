# 对接 Infographic Design

[信息图形知识库](https://github.com/qixing22/Infographic-Design-)提供案例、数据逻辑、分析和数据表。当前仓库提供风格规则、主题映射、提示词编译及验收。两边通过登记的案例 ID 和固定提交关联，便于复查同一版本。

当前入口支持 **CASE-17 现代肉鸡产业链三维信息图**。数据来自知识库登记的案例 CSV，按源表顺序导入六项可辨识阶段，排除了一条标记待核验的文字记录。导入结果保留来源提交、分析与数据链接、使用的记录和跳过原因。源表只有文字与流程结构，因此关闭定量体积规则，图中各阶段用等体量模块表达顺序。

## 执行

在 Style-Cloning-System 仓库根目录运行。示例假定两库位于同一父目录。

```sh
git clone https://github.com/qixing22/Infographic-Design-.git ../Infographic-Design-
python -m pip install -r requirements.txt
python integrations/import_infographic_case.py \
  --repo ../Infographic-Design- --case CASE-17 --out build/case-17
python style_system.py validate build/case-17/task.json
python style_system.py compile build/case-17/task.json --out build/case-17/prompts
```

导入命令只读本地 Git 的登记快照。比较另一版数据前，在 [关联清单](infographic-design.json)中更新来源提交和记录选择，再重跑验证。新增案例时确认数据逻辑匹配；当前导入器适合无数值的顺序型案例。

回复网页大模型时，可上传 [主文档](../STYLE-SYSTEM.md)、导入得到的 `task.json` 与 `sources.json`，然后要求「启动风格分析和克隆系统，按已有档案编译四版提示词」。
