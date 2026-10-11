---
name: windows-app-zero-to-one
description: 把一个模糊想法变成可分发的 Windows exe 程序的完整流程。This skill should be used when the user describes a desktop app idea and wants it actually built ("帮我做一个 Windows 小程序" / "我要一个能 XX 的 exe" / "把这个脚本做成 exe 发给别人")，或需要从零创建、打包、签名任意 Windows 可执行程序。覆盖需求澄清、技术选型（Go / .NET / Python）、骨架搭建、编码实现、命令行构建（无需 Visual Studio）、Authenticode 签名到交付的全过程，也支持照着某个现有软件仿作一个（会主动追问功能清单，区分必做 / 可选 / 不做）。
agent_created: true
---

# Windows 应用从 0 到 1

## Overview

把"我想要一个能做 XX 的 Windows 程序"变成手里一个能双击运行、能发给别人的 exe。
不依赖 Visual Studio，用命令行工具链直接构建并签名。

核心价值在于**过程**：先想清楚要什么，再动手，最后验证交付。构建链只是其中一步。

## 工作流

### 阶段 0 · 先问清楚，再写代码

**形态不预设，每次使用时问。** 拿到想法后先把关键问题一次性问清楚（不要挤牙膏式追问），
缺的信息用合理默认值补上并告知用户：

| 要确认的事 | 为什么重要 | 常用默认 |
|---|---|---|
| 要图形窗口吗 | 决定整个技术栈，选错要重写 | 不要（命令行/后台工具） |
| 给谁用 | 决定签名策略，见下面签名一节 | 只自己用 |
| 核心功能一句话 | 圈定范围，防止无限发散 | 用户描述的第一句 |
| 要不要联网 / 写注册表 | 影响杀软误报率和是否需要管理员权限 | 都不要 |
| 数据存哪 | 用户目录 `%APPDATA%\<AppName>` 最安全 | 单文件配置 |
| 需要开机自启 / 常驻吗 | 常驻要处理单实例和托盘 | 一次性跑完就退 |

产出：不超过 10 行的需求摘要，含"做什么 / 不做什么"。

### 仿作模式 · 照着现有软件 / 安装包 / 截图做一个

当用户说"做一个像 XX / 仿 XX"，**或上传了一个 exe / apk / 截图**，**或用文字描述想要的功能**时，进入仿作模式。

核心原则：**先模仿其"形"（界面、图标、入口、布局），功能（必做 / 可选 / 不做）由开发者自己想，或你帮它大致推测里面有什么，再让开发者拍板。** 仿作是"做出同等体验的最小实现"，不是逐像素复刻。

参照物有五种形态，取"形"的方式不同：

| 参照物 | 怎么"模仿其形" | 功能从哪来 |
|---|---|---|
| 一个软件名（"像 XX"） | 让开发者描述，或你按常识给 UI 草图 | 开发者定 / 你推测 |
| 上传的 **apk** | 用工具链 `aapt2 dump badging` 取包名、入口 Activity、权限、特性、图标；看 res 布局与 strings | 从权限 / Activity / 字符串**推测**，开发者确认 |
| 上传的 **exe** | 看图标、`(Get-Item).VersionInfo` 版本信息、manifest；有截图就看界面布局 | 从界面与同类软件推测，开发者确认 |
| 上传的**截图** | 直接照布局 / 配色 / 控件复刻界面 | 开发者定 / 你推测 |
| 用户**文字描述的功能**（"要一个能 XX 的"） | 功能已由用户给出，形由你给 UI 草图或参照同类软件 | 功能已由用户描述，你来落地 |

仍要一次性追问的功能清单（分三档，防发散）：

| 要追问的功能点 | 目的 |
|---|---|
| 参照物是软件名 / exe / apk / 截图 / 文字描述？ | 决定上面怎么取"形" |
| 你最在意它的哪一点？ | 抓住"灵魂"，别被表面 UI 带偏 |
| **必做**的核心功能（逐条列出） | 圈定 MVP，第一版只做这些 |
| 可以**砍掉 / 简化**的功能 | 先做最小可用，后续再迭代 |
| 目标形态（窗口 / 命令行） | 复用上面"形态询问" |
| 有没有界面参考（截图 / 描述 / 配色） | 减少来回确认 |
| 数据从哪来？要不要兼容原软件的文件格式？ | 决定本地存储 vs 联网、是否要解析旧格式 |
| 给谁用、要不要联网 | 影响签名策略与杀软误报 |

产出：界面草图 / 清单（形）+「功能清单（必做 / 可选 / 不做）」+ 一句话定位，再进入阶段 1 选型。

> 从安装包推测功能的线索：apk 权限 `CAMERA`→拍照类、`INTERNET`→联网、`READ_CONTACTS`→通讯录；exe 版本信息里的产品名 / 描述也常暴露用途。推测只是辅助，最终由开发者确认。
> 详见 `references/replicate-app.md`（含"从安装包 / 截图仿作"的具体步骤与示例）。

### 阶段 1 · 选型

**要不要窗口是分水岭：**

| 形态 | 首选 | 理由 | 产物体积 |
|---|---|---|---|
| 命令行 / 后台工具 | **Go** | 一条 `go build` 出真单文件，零运行时依赖 | 5-15 MB |
| 同上，但求最快 | Python + PyInstaller | 有现成脚本就能转 | 8-30 MB |
| 带窗口的桌面软件 | **C# + dotnet CLI** | WinForms/WPF 是原生 GUI，不用装 VS | 10-70 MB |
| 现代化漂亮界面 | Tauri | Web 技术栈，体积小 | 3-10 MB |

判据补充：
- 要**发给不懂技术的人**且是单个文件 → Go 最省心
- 要**真正的窗口程序**（按钮、表格、设置页）→ C#，别用 Go 硬凑 GUI
- 已有 Python 脚本要变成 exe → PyInstaller，但注意杀软误报率高

### 准备工具链（新机器一次性）· Windows 构建工具（windowsbuildtools）

目标机器上什么都没有时，先跑自动部署。**不需要 Visual Studio、不需要管理员权限**：

```bash
python scripts/setup_dev_chain.py --lang go            # ~70MB，13 秒
python scripts/setup_dev_chain.py --lang dotnet        # ~200MB
python scripts/setup_dev_chain.py --lang python        # 下载独立 CPython 到 <root>/python 并装 PyInstaller
python scripts/setup_dev_chain.py --proxy http://127.0.0.1:7890
```

> `--lang python` 会**下载一份独立的 CPython** 到 `<root>/python`（默认 `~/.windowsbuildtools/python`），
> 再往里 `pip install pyinstaller`。它**不污染你机器上已有的任何 Python**：本机没装 Python 也能用。
> 若同版本 Python 已注册（WiX 拒绝装第二份），脚本自动从注册表/`AppData` 复用已装的，并装好 PyInstaller。

**开发者已自带 Python + PyInstaller？先提醒再决定，不要静默下载。**
进入 Python 路线前，先确认目标机器上是否已经有一套能用的环境：

- 自动检测：`python -m PyInstaller --version` 能正常输出版本号，即视为已具备。
- 若已具备，**主动提醒开发者**：技能默认会再下载一份「独立 CPython + PyInstaller」装到 `<root>/python`，
  目的是**隔离现有环境、保证构建可复现、换机/团队一致**；但如果只是自用、环境已稳定，
  **完全可以跳过下载**，直接用现有解释器跑 `build_exe.py`（脚本会自动用 `sys.executable` 作为构建 Python）。
- 让开发者二选一，**不要替他默认下载**：
  1. **用现有环境（不下载）** —— 直接 `python scripts/build_exe.py --src <project>`，省时省盘。
  2. **仍装独立工具箱（隔离 / 可复现）** —— 跑 `setup_dev_chain.py --lang python`。

装到 **`~/.windowsbuildtools`**（即"Windows 构建工具"目录，简称 windowsbuildtools），写 `devchain.json`；
之后 `build_exe.py` / `sign_exe.py` **自动读取，无需参数**。
> 兼容：旧版装在 `~/.windows-zero-to-one` 的工具与证书也会被自动识别，无需迁移。

### 阶段 2 · 起骨架

复制 `assets/` 下对应骨架（Go 骨架已实测可编译出 1.6MB 单文件 exe）：

```
assets/starter-go/       go.mod + main.go
assets/starter-python/   main.py
```

C# 项目直接 `dotnet new winforms -n MyApp`（骨架不预置，模板自带）。

### 阶段 3 · 实现

顺序：先确定入口和依赖 → 再核心逻辑 → 最后界面。
命令行程序把参数解析做扎实（`--help`、`--version`、非零退出码），这是分发给别人后的主要交互面。

### 阶段 4 · 构建

```bash
python scripts/build_exe.py --src <project> --out dist/MyApp.exe
python scripts/build_exe.py --src <project> --noconsole   # GUI 程序（python）
```

脚本按 `go.mod` / `*.csproj` / `*.py` **自动识别语言**，也可 `--lang` 强制。
已做的优化：`-trimpath -ldflags "-s -w"` 去符号表、`CGO_ENABLED=0` 保证纯静态、
.NET 走 `PublishSingleFile` + 压缩。

### 个人签名证书（要发给别人时必做）

Windows 的规则和安卓不同，**自签证书只在自己机器上有效**：

```bash
python scripts/sign_exe.py dist/MyApp.exe --name "Your Name"
```

用 PowerShell 自带命令实现，零安装，产出 `certs/code-signing.pfx` + `signing.properties`。
签名会**自动加时间戳**（DigiCert 服务器），所以证书 5 年过期后签名依然有效。

必须让用户知道的三件事：

1. 自签证书 + 导入本机受信任根 → 本机 `Status: Valid`
2. **别人机器上 SmartScreen 仍弹蓝框**「Windows 已保护你的电脑」，需点「更多信息 → 仍要运行」
3. 彻底消除警告只能买 **OV 证书**（约 ¥1000-3000/年）或靠下载量自然积累信誉

详见 `references/signing-and-smartscreen.md`。

### 阶段 5 · 验证

```powershell
(Get-AuthenticodeSignature MyApp.exe).Status        # 应为 Valid
```

不能只信"构建成功"。至少确认：能双击运行、签名 Valid、换一台没装任何环境的机器仍能跑
（Go/自包含 .NET 应该可以；PyInstaller 单文件也要验一次）。

### 阶段 6 · 交付

- 文件名带用途和版本，如 `MyApp-1.0.0.exe`
- 附上"首次运行会弹蓝框，点更多信息 → 仍要运行"的说明——**提前说比让用户以为中毒强**
- 提醒备份 `certs/code-signing.pfx` + `signing.properties`，丢了旧签名就失效
- 若走商业证书，用 `--pfx <证书> --password <密码>` 签名

## 资源

- `scripts/setup_dev_chain.py` — 自动部署 Go / .NET / 独立 CPython+PyInstaller（空机器一键可用）
- `scripts/build_exe.py` — 自动识别语言并构建单 exe
- `scripts/sign_exe.py` — 生成个人证书 + Authenticode 签名 + 时间戳
- `references/build-options.md` — 各形态构建命令、体积、取舍
- `references/signing-and-smartscreen.md` — 证书类型、SmartScreen 机制、杀软误报
- `references/pitfalls.md` — 按卡壳时长排序的实战坑
- `references/replicate-app.md` — 仿作模式：功能追问模板 + 示例
- `assets/starter-go/`、`assets/starter-python/` — 最小可运行骨架
