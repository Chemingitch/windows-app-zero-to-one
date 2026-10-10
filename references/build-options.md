# 构建方案速查

设备形态无关，但**要不要窗口**决定一切。

## 实测数据（本机 Windows 11 x64）

| 方案 | 工具链部署 | 构建耗时 | 产物体积 | 启动 |
|---|---|---|---|---|
| Go 1.27.2 | 77 MB / 13 s | 秒级 | hello **1.65 MB**，骨架 1.87 MB | 瞬间 |
| .NET 8 console（self-contained 单文件） | 48 s | 22 s（含首次还原） | **35 MB** | 快 |
| Python 3.13 + PyInstaller | pip 21 s | 21 s | **8.5 MB** | 1-3 s |

三者都实测跑通并签名验证过。体积排序：Go ≪ Python ≪ .NET。

## Go

```bash
CGO_ENABLED=0 go build -trimpath -ldflags "-s -w" -o MyApp.exe .
```

- `CGO_ENABLED=0` — 保证纯静态，不依赖任何 DLL
- `-trimpath` — 去掉本机绝对路径，构建可复现
- `-ldflags "-s -w"` — 去符号表和 DWARF，体积约减 30%
- 交叉编译：`GOOS=windows GOARCH=amd64 go build`（在 Mac/Linux 上出 exe 也行）
- GUI 弱项：要用窗口得引第三方（fyne、walk、webview），能不用就别用

**最省心的一条路**：一个真单文件，拷到任何 Windows 都能跑，不需要运行库。

## .NET（C#）

```bash
dotnet new winforms -n MyApp
dotnet publish -c Release -r win-x64 --self-contained true \
  -p:PublishSingleFile=true \
  -p:IncludeNativeLibrariesForSelfExtract=true \
  -p:EnableCompressionInSingleFile=true \
  -o dist
```

- **不需要 Visual Studio**，`dotnet` SDK 就是命令行工具，免费
- self-contained 体积大但对方零依赖；`PublishTrimmed=true` 可瘦身（可能有反射问题）
- 首次 publish 会拉 NuGet 包，慢是正常的
- 想更小可试 Native AOT（`-p:PublishAot=true`），但限制多（无反射序列化）

**做真正的窗口程序首选**，WinForms/WPF 都是原生控件。

## Python + PyInstaller

```bash
pyinstaller --onefile --noconsole --name MyApp main.py
```

- `--onefile` 每次启动要解压到临时目录，慢 1-3 秒；`--onedir` 更快但是一整个文件夹
- 中文路径、中文用户名容易触发打包失败，路径尽量全英文
- 杀软误报率明显高，见 `signing-and-smartscreen.md`
- 打包环境要和 Python 位数一致（32 位 Python 只能出 32 位 exe）

## Tauri

体积小、界面漂亮，但要 Rust 工具链，首次编译数分钟。
只在"必须用 Web 技术栈做界面"时才值得。

## 怎么选

```
要窗口吗？
├─ 不要 → Go（要分发的首选） / Python（已有脚本，最快）
└─ 要   → C# + dotnet CLI（原生控件，性价比最高）
           └─ 必须 Web 观感 → Tauri
```
