# 签名、SmartScreen 与杀软误报

这是 Windows 和安卓最大的差别：**安卓自签能装能用，Windows 自签照样被拦**。

## 三种证书的差别

| 类型 | 成本 | 自己机器上 | 别人机器上 | 获取方式 |
|---|---|---|---|---|
| 自签（本脚本生成） | 0 | `Valid` | **蓝框警告**，需手动放行 | 脚本一键生成 |
| OV（组织验证） | 约 ¥1000-3000/年 | Valid | 仍可能提示，下载量上来后消失 | 向 CA 代理商购买 |
| EV（扩展验证） | 更贵，需硬件令牌 | Valid | **立即获得 SmartScreen 信誉** | 同上 |

## SmartScreen 到底在判断什么

它不是"有没有签名"，而是**信誉度**：

1. 完全没签名 → 蓝框，最吓人的那种
2. 有自签/未知证书 → 仍是蓝框「Windows 已保护你的电脑」，要点「更多信息 → 仍要运行」
3. 有 OV 证书 → 随下载量增长逐渐不再提示（微软按证书累计信誉）
4. 有 EV 证书 → 立刻不提示

所以自签证书的**真实价值**是：
- 证明这个文件确实是你发的、中途没被改过（`Status: Valid`）
- 让**你自己**机器上验证通过
- 给企业环境 / 内部部署用（域内可信任该证书）

它**不能**让陌生用户无感安装。

## 时间戳为什么重要（脚本已默认开启）

签名时打上时间戳后，即使证书 5 年后过期，Windows 仍认为签名有效——
因为签名发生在证书有效期内。没有时间戳，证书过期那天所有已发出的 exe 全部变成"签名无效"。

本脚本用 `http://timestamp.digicert.com`；网络不通时会自动降级为不加时间戳并提示。

## 杀软误报

高发场景，按概率排序：

1. **PyInstaller 单文件** — 解压行为像加壳，最容易误报
2. 全新编译、从没被见过的小程序 — 无信誉，部分引擎直接标可疑
3. Go 程序体积大但结构干净，误报率明显低于 PyInstaller

应对：
- 签名是唯一有效手段（尤其 OV/EV）
- 向各厂商提交白名单申诉（Windows Defender 有在线提交入口）
- 别用加壳/压缩壳，那只会加重误报

## 验证命令

```powershell
(Get-AuthenticodeSignature MyApp.exe).Status                    # Valid / NotSigned / UnknownError
(Get-AuthenticodeSignature MyApp.exe).SignerCertificate.Subject # CN=...
(Get-AuthenticodeSignature MyApp.exe).TimeStamperCertificate    # 有值 = 已加时间戳
```

`UnknownError` 通常是**证书链不受信**（自签证书没导入本机受信任根），不是签名失败。
本脚本生成证书时会自动把它加入 `CurrentUser\Root`，所以本机应显示 `Valid`。

## 商业证书怎么用

拿到 `.pfx` 后：

```bash
python scripts/sign_exe.py MyApp.exe --pfx mycert.pfx --password <密码>
```

脚本会自动加时间戳并验证。
