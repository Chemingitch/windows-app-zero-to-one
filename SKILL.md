---
name: windows-app-zero-to-one
description: 把一个模糊想法变成可分发的 Windows exe 程序的完整流程。This skill should be used when the user describes a desktop app idea and wants it actually built ("帮我做一个 Windows 小程序" / "我要一个能 XX 的 exe" / "把这个脚本做成 exe 发给别人")，或需要从零创建、打包、签名任意 Windows 可执行程序。覆盖需求澄清、技术选型（Go / .NET / Python）、骨架搭建、编码实现、命令行构建（无需 Visual Studio）、Authenticode 签名到交付的全过程。
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

### 准备工具链（新机器一次性）

目标机器上什么都没有时，先跑自动部署。**不需要 Visual Studio、不需要管理员权限**：

```bash
python scripts/setup_dev_chain.py --lang go            # ~70MB，13 秒
python scripts/setup_dev_chain.py --lang dotnet        # ~200MB
python scripts/setup_dev_chain.py --lang python        # 装 PyInstaller 到当前解释器
python scripts/setup_dev_chain.py --proxy http://127.0.0.1:7890
```

装到 `~/.windows-zero-to-one`，写 `devchain.json`；之后 `build_exe.py` **自动读取，无需参数**。

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

- `scripts/setup_dev_chain.py` — 自动部署 Go / .NET / PyInstaller（空机器一键可用）
- `scripts/build_exe.py` — 自动识别语言并构建单 exe
- `scripts/sign_exe.py` — 生成个人证书 + Authenticode 签名 + 时间戳
- `references/build-options.md` — 各形态构建命令、体积、取舍
- `references/signing-and-smartscreen.md` — 证书类型、SmartScreen 机制、杀软误报
- `references/pitfalls.md` — 按卡壳时长排序的实战坑
- `assets/starter-go/`、`assets/starter-python/` — 最小可运行骨架
