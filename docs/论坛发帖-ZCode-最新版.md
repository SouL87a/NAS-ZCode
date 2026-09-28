# 【原生应用】ZCode · 飞牛 fnOS 版 —— 把 AI 编程工作台放上 NAS，关掉浏览器它接着干

> 维护发行：**SouL87** · 起于 [Kasbuky-sudo/NAS-ZCode](https://github.com/Kasbuky-sudo/NAS-ZCode) 打包 · 上游 [zai-org/ZCode](https://github.com/zai-org/ZCode)  
> **非官方**：不是 Z.ai / 飞牛官方应用。Apache-2.0。

## 这是什么

把 Z.ai 开源的 **ZCode**（AI 编程工作台）打成飞牛 **fnOS 原生应用**（非 Docker）：

- Agent 对话、代码工作区、**内置终端**
- 服务端权威：**关掉浏览器，长任务继续跑**
- 登录态与工作区在 NAS 上，手机 / 平板 / 电脑共用
- **双入口**：飞牛桌面（统一网关）+ 端口直连（令牌登录框）
- x86_64 + arm64 一个包（`platform = all`）

## 快速安装

1. 应用中心安装 **Node.js v22**（或随包自动装）
2. 下载 Releases 中的 **`zcode-*.fpk`**（不要用 Actions Artifact 的 zip）
3. 应用中心 → 手动安装
4. 向导填写 **≥16 位随机访问令牌**
5. 桌面图标打开，或浏览器访问 `http://NAS_IP:8988`

## 双入口与鉴权

| 入口 | 鉴权 |
|---|---|
| 桌面图标 → `/app/zcode`（统一网关） | 飞牛 NAS 登录态，打开即用 |
| `http://NAS_IP:8988` | 访问令牌**登录框**；令牌**不进地址栏** |

- 端口登录成功后使用服务端 **HttpOnly** cookie
- 修改令牌：应用中心 → ZCode → 应用设置 → 重启

## 安全（务必阅读）

ZCode Web ≈ 在 NAS 上开了「能执行命令的 agent + 终端」：

- **请勿映射 8988 到公网**
- 令牌 ≥16 位随机；勿用弱口令
- 工作区只授权必要目录
- 仅在可信局域网使用
- 演示/发帖时勿录制真实令牌与内网 IP

## 与桌面版差异

| | 桌面版 | NAS 版 |
|---|---|---|
| 界面 | Electron | 浏览器 / 飞牛桌面 iframe |
| **内置浏览器（Browser Use）** | ✅ | ❌（需 Electron WebView） |
| 外挂 Chrome + CDP/MCP | — | ✅ 推荐 |

fnOS 应用中心安装 Chrome 后，可用 CDP（如 `http://127.0.0.1:16002/json/version`）+ Chrome DevTools MCP 等方式做网页自动化。

## 反馈

- 仓库 Issues：源码仓库
- 请附：fnOS 版本、应用日志（`info.log`）、复现步骤

---

*历史版本（v3.14.2 及更早）的发帖/说明见同目录其它文档，鉴权描述以本篇为准。*
