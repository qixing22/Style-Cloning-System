# 风格分析与克隆系统 v1.0

这是一套以大模型执行图像分析和主题适配、以结构化数据维持风格复用的系统。主文档可以单文件启动。仓库附带验证、槽位绑定、四版编译和验收汇总工具。

## 风格库与跨仓库入口

- [风格库](library/README.md)收录可直接调用的档案，首个档案为「暖红等轴测方块信息图」。
- [信息图形知识库对接](integrations/README.md)用固定版本的案例资料和数据生成结构化任务与四版提示词。

## 三种启动方式

### 网页大模型

上传 `STYLE-SYSTEM.md`，按任务同时上传可查看的风格参考图或既有风格档案。输入：

> 启动风格分析和克隆系统。分析这些参考，提取可复用规则。新主题是〔主题〕，输出通用母版、四版提示词和验收清单。

已有档案时：

> 启动风格分析和克隆系统。使用本次上传的档案，主题改为〔主题〕。保留核心风格关系，输出具体提示词的四个版本。

### 仓库

复制本目录进入自己的仓库。向可读仓库的助手输入：

> 读取 STYLE-SYSTEM.md、schema/style-system.schema.json 和 examples 中的示例，启动风格分析和克隆系统。使用我指定的档案版本。先完成〔分析、迁移、扩展、换主题、修订或验收〕。

如果放在子目录，相应提供文件路径。网页和仓库都使用相同的字段含义。图像分析与双语编写由可读图的模型和人工复核完成；本仓库的 Python 工具编译已经确认的双语规则，自动校验结构、引用、槽位、规则覆盖和验收状态。

### 跨会话记忆

将 `MEMORY.md` 中的调用卡交给支持记忆的平台，请求保存后在新会话测试口令。完整流程使用 `STYLE-SYSTEM.md` 的对应版本；调用某个具体风格还需要可访问的档案。记忆适合保存工作方式与入口，项目文件保存档案、证据和版本。

## 工具调用

Python 3.10+。在本目录中运行：

```sh
python -m pip install -r requirements.txt
python style_system.py validate examples/profile.json
python style_system.py validate examples/02-repair-bay.json
python style_system.py compile examples/02-repair-bay.json --out build/repair-bay
python style_system.py audit examples/02-repair-bay.json
```

`compile` 的目标应是新的目录。输出：

| 文件 | 内容 |
|---|---|
| `prompt.zh.json` | 中文六字段 JSON |
| `prompt.en.json` | 英文六字段 JSON |
| `prompt.zh.short.txt` | 中文简易提示词，包含全部必须项和规格 |
| `prompt.en.txt` | 英文自然语言提示词 |
| `coverage.json` | 当前档案与任务版本、各版本包含的规则 ID、交付规格 |

Python 项目可以导入 `compile_bundle(bundle)`，取得文件内容及启用规则，在人工或视觉模型填入验收项后可调用 `audit_bundle(bundle, rules)`。JSON Schema 中还提供 `generation_prompt` 定义，供集成方校验编译结果。

## 使用示例

- `examples/profile.json` 是同一个虚构风格档案的通用母版，保留双语槽位。
- `01-night-alley.json` 是已有主题的风格迁移。
- `02-repair-bay.json` 扩展到新的环境与动作。
- `03-lunar-archive.json` 将主体换为物件，变更画幅并加入准确中文文案。同一个档案版本继续使用，关闭不适用的条件规则。
- `examples/compiled/` 是第二个例子的四版实际编译输出。

示例证据是为了演示数据关系编写的假设。所有示例均未生成成图，验收状态为 `not_generated`。通过编译代表结构和规则传递检查通过。翻译的语义质量及成图效果还要分别复核。

## 数据与来源

系统沿用《视觉语言基础》的光线、色彩、构图、风格与材质分析思路，使用《VSCF》与《结构化提示词风格克隆系统》的五总控、十三模块、参考角色、规则属性、六字段生成结构与验收分层。多图校验沿用《AI 辅助脚本与分镜设计》的脚本、帧间功能与连续性方法。本版本将原六字段实现为可追踪的规则数组，以便在四种导出中核对覆盖。

约定：
- `style_profile` 是来源与规则。项目锁定进入 `image_task.requirements`。
- `image_task` 引用明确的档案版本，记录主题、字段、槽位、条件决定和规格。系列可加 `storyboard`。
- `image_review` 指向具体任务和产物版本。工具汇总提交的检查证据。
- 英文、中文描述由双语对象提供。编译器检查两种语言的槽位与规则覆盖，翻译语义由审阅者确认。
