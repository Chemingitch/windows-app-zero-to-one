# windows-app-zero-to-one

把"我想要一个能做 XX 的 Windows 程序"变成手里一个能双击运行、能发给别人的 exe —— 不需要 Visual Studio。

适用于命令行工具、后台服务、带窗口的桌面软件等各类 Windows 程序。

## 这个技能做什么

构建链只是其中一步。真正重要的是过程：**先想清楚要什么（尤其要不要窗口、给谁用），再动手，最后验证交付。**
脚本负责自动部署工具链、识别语言并构建单文件 exe、并用 PowerShell 自带命令完成 Authenticode 签名。

## 快速开始

```bash
# 1. 复制最小骨架
cp -r assets/starter-go myapp

# 2. 准备工具链（空机器第一次；go 约 13 秒 / .NET 约 48 秒 / python 约 1 分钟）
python scripts/setup_dev_chain.py --lang go            # 命令行程序首选
python scripts/setup_dev_chain.py --lang dotnet        # 真正的窗口程序
python scripts/setup_dev_chain.py --lang python        # 下载独立 CPython+PyInstaller（不污染本机 Python）
# 若本机已有可用的 Python + PyInstaller，可跳过上面这行，直接跑 build_exe.py（用现有解释器）

# 3. 构建（自动识别 go.mod / *.csproj / *.py）
python scripts/build_exe.py --src myapp --out myapp.exe

# 4. 签名（要发给别人时必做）
python scripts/sign_exe.py myapp.exe --name "Your Name"
```

## 选型：要不要窗口是分水岭

| 形态 | 首选 | 产物体积 |
|---|---|---|
| 命令行 / 后台工具 | **Go** | 1-2 MB |
| 同上，求最快 | Python + PyInstaller | 8 MB |
| 带窗口的桌面软件 | **C# + dotnet CLI** | 35 MB |
| 现代化漂亮界面 | Tauri | 3-10 MB |

`.NET` 路线不需要 Visual Studio —— `dotnet` SDK 就是免费的命令行工具。

## 签名：Windows 和安卓不同

自签证书**只在自己机器上有效**。别人打开你发的 exe 仍然会看到 SmartScreen 蓝框
「Windows 已保护你的电脑」，需点「更多信息 → 仍要运行」。

- 脚本用 PowerShell 自带命令（`New-SelfSignedCertificate` / `Set-AuthenticodeSignature`）实现，**零安装**
- 默认打时间戳（DigiCert 服务器），证书过期后签名依然有效
- 彻底消除蓝框只能买 **OV 证书**（约 ¥1000-3000/年）或靠下载量积累信誉
- 交付时务必提前告知用户"首次运行要手动放行"

详见 `references/signing-and-smartscreen.md`。

## 仿作模式（照着现有软件做一个）

如果用户说"做一个像 XX 的软件 / 仿 XX"，先别照抄界面——按这份清单一次性问清功能边界：

1. 参考的是哪个软件？最在意它的哪一点？
2. **必做**的核心功能（逐条列出，圈定 MVP）
3. 可以**砍掉 / 简化**的功能
4. 目标形态（窗口 / 命令行）
5. 有没有界面参考（截图 / 描述 / 配色）
6. 数据从哪来？要不要兼容原软件的文件格式？
7. 给谁用、要不要联网

产出：功能清单（必做 / 可选 / 不做）+ 一句话定位，再进入选型。
工具链装在 **`~/.windowsbuildtools`**（Windows 构建工具目录），构建/签名脚本自动读取；旧版 `~/.windows-zero-to-one` 也能被识别。

## 安装到 WorkBuddy

把整个目录解压到 `~/.workbuddy/skills/windows-app-zero-to-one/`，刷新技能列表即可在对话中触发。

## 目录结构

```
SKILL.md                      六阶段工作流 + 签名专节
scripts/setup_dev_chain.py    自动部署 Go / .NET / 独立 CPython+PyInstaller
scripts/build_exe.py           自动识别语言并构建单 exe
scripts/sign_exe.py            生成个人证书 + Authenticode 签名 + 时间戳
references/                    构建选项 / 签名与 SmartScreen / 踩坑
assets/starter-go/             最小可编译骨架
assets/starter-python/         main.py 骨架
```

## 许可

MIT —— 见 [LICENSE](LICENSE)。
