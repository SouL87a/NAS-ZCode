# ZCode · 飞牛 fnOS 原生版

把 [Z.ai 开源的 AI 编程工作台 ZCode](https://github.com/zai-org/ZCode) 打包成飞牛 fnOS 的**原生第三方应用**（非 Docker）：

- 服务端跑在 NAS 上，浏览器 / 飞牛桌面里直接用完整工作台——**Agent 对话、代码工作区、内置终端**
- 登录态与工作区保存在 NAS 上，手机 / 平板 / 电脑共用一份
- **非 Docker**：原生 Node.js 运行，复用应用中心的 **Node.js v22**（`install_dep_apps` 自动装）
- **一个包同时支持 x86_64 与 arm64**（`platform = all`，原生模块用官方预编译件）
- **双入口**：飞牛统一网关（桌面图标）+ 端口直连（访问令牌）
- 基于 ZCode 官方 Web 运行时，与桌面版共用同一套前端组件

> 基于 [zai-org/ZCode](https://github.com/zai-org/ZCode)（Z.ai，Apache-2.0）与 [Kasbuky-sudo/NAS-ZCode](https://github.com/Kasbuky-sudo/NAS-ZCode) 的 fnOS 打包，由 [SouL87](https://github.com/SouL87a) 维护本发行版。详见文末「维护与致谢」。

## 安装

1. 应用中心安装（或随包自动装）**Node.js v22**
2. 从 [Releases](../../releases) 下载 `zcode-<版本>.fpk`（不要用 Actions Artifact 的 zip）
3. 应用中心 → 手动安装 → 选择 fpk
4. 从**桌面图标**打开，或浏览器访问 `http://NAS_IP:8988`

## 双入口

| 入口 | 地址 | 鉴权 |
|---|---|---|
| **统一网关**（推荐） | 飞牛桌面图标 → `/app/zcode` | 飞牛 NAS 登录态；打开即可用 |
| **端口直连** | `http://NAS_IP:8988` | 访问令牌登录框（令牌**不进地址栏**） |

- 网关请求由 `gateway-proxy` 识别 `X-Trim-*` 身份后注入令牌，桌面免手输
- 端口访问先弹登录框，输入令牌后由服务端下发 **HttpOnly** cookie
- 请**勿**将 8988 映射到公网

## 访问令牌（重要）

ZCode Web 等于把能执行命令的 AI agent + 终端开在 NAS 上，访问令牌是端口入口的唯一屏障：

- **安装向导**要求填写「访问令牌」：**至少 16 位**随机字母/数字/下划线/中划线（勿用常见词、生日）
- 修改：应用中心 → ZCode → 应用设置 → 访问令牌 → **重启应用**
- 服务端对 `/ws`、`/ws/*`、`/api/*` 鉴权（静态页放行）；接受 `?token=` 或 cookie `zcode_lite_token`
- **旧版短令牌**（8–15 位）升级后无法在登录框提交，请到应用设置重设为 ≥16 位

## 安全说明

- 端口令牌**不在 URL 路径**中（不进浏览器历史/截图）
- 登录成功使用服务端 **HttpOnly** cookie
- 网关 Unix Socket 仅对带飞牛会话身份（`X-Trim-*`）的请求注入令牌
- 令牌经环境变量传给服务端（不出现在进程命令行）
- 以专用包用户运行（`run-as: package`，非 root）
- 建议：仅在可信局域网使用；强随机令牌；不暴露公网

## 工作区

安装后创建共享目录 `zcode/workspace` 作为默认工作区。要操作其它目录：应用中心 → ZCode → 设置 → 访问权限 → 添加授权目录 → 重启。

## 构建

```bash
# 1) 准备官方 runtime：zcode-<ver>.tar.gz
#    clone zai-org/ZCode，Node 24.14.0 + pnpm 10.33.2
#    pnpm install --frozen-lockfile && pnpm typecheck
#    node scripts/build-zcode.mjs --base-url http://127.0.0.1/zcode/
#    或使用本仓库 GitHub Actions 的 runtime artifact

# 2) 打 fpk
bash packaging/fnOS/scripts/build.sh --runtime /path/to/zcode-<ver>.tar.gz
```

### 发版流程

| 动作 | 结果 |
|---|---|
| `git push origin main` / `test/*` | 只构建 Artifacts，**不发 Release** |
| 验证通过后 `git tag v3.14.x && git push origin v3.14.x` | 自动构建并发布 Release（含 changelog） |
| Actions → Run workflow → 勾选 publish_release | 同上 |

版本变更说明见 [CHANGELOG.md](CHANGELOG.md)。

## 与桌面版的差异

| | 桌面版 | NAS 版 |
|---|---|---|
| 界面 | Electron 窗口 | 浏览器 / 飞牛桌面 iframe |
| 终端 | 本机 node-pty | 服务端 node-pty（浏览器内） |
| 浏览器自动化 | 内置 Electron/Chromium | **依赖系统 Chrome/Chromium**（见下） |
| 配置与凭据 | 本机用户目录 | NAS 应用数据目录（升级保留） |

### 浏览器能力说明（NAS 版）

| 能力 | NAS 版 | 原因 |
|---|---|---|
| **「开启内置浏览器控制」（Browser Use 官方插件）** | ❌ **不可用** | 依赖 **Electron 主进程 + 内置 WebView**（CDP executor / 受控 view）；Web/服务端形态没有这套宿主。UI 也标明「浏览器面板仅桌面端可用」 |
| Playwright 调系统 Chrome/Chromium | ✅ 条件可用 | 包内有 `playwright-core`；需系统里有浏览器（见下） |
| 外挂浏览器（CDP / Chrome DevTools MCP 等） | ✅ **推荐** | 不绑内置 WebView，agent 走 **Chrome 远程调试（CDP）** 操作你装的浏览器 |

**这不是 fpk 打包时「删掉了浏览器」**，而是桌面版用 Electron 嵌入式浏览器当「内置浏览器」；NAS 跑的是 Node 服务端 + 网页 UI，没有 Electron Main，所以该开关打不开。

#### 推荐：fnOS 应用商店 Chrome + CDP

1. 在 **飞牛应用中心** 安装 **Chrome 浏览器** 应用（或自行部署开启远程调试的 Chromium）。
2. 确认 **Chrome 远程调试（CDP）** 已开启，本机调试地址示例：

   ```text
   http://127.0.0.1:16002/json/version
   ```

   浏览器或 `curl` 能打开该 JSON，即表示 CDP 可用。
3. 在 ZCode 中配置 **Chrome DevTools MCP / Playwright MCP（CDP）/ Agent Browser** 等，指向上述调试端点，由 agent 控制该 Chrome。

#### 其它方式

- 系统包管理安装 **Chrome/Chromium**（Playwright 默认查找）：  
  `/usr/bin/google-chrome-stable` · `/usr/bin/google-chrome` · `/usr/bin/chromium` · `/usr/bin/chromium-browser` · `/snap/bin/chromium`  
  或显式：`--browser-executable <绝对路径>`
- 工具描述里的「控制 ZCode 内置浏览器」仍指桌面 WebView；NAS 上请用 **CDP + 外部 Chrome**。

## 目录结构

```
packaging/fnOS/
├── manifest              # 应用元信息
├── cmd/                  # 生命周期脚本
├── config/               # privilege / resource
├── ui/config             # 桌面入口（统一网关）
├── scripts/
│   ├── build.sh          # 打包 fpk
│   ├── gateway-proxy.mjs # Unix Socket 网关适配
│   └── inject-entry-token.py  # 端口登录门禁
└── wizard/               # 安装向导（访问令牌）
```

## 维护与致谢

| 角色 | 归属 |
|---|---|
| ZCode 核心（Agent / 工作台 / 终端） | Z.ai |
| 飞牛 fnOS 原生打包初版 | Kasbuky-sudo |
| 本发行版维护、双入口网关、安全加固、发版流水线 | SouL87 |

按 Apache-2.0 保留原作者版权声明；二次分发请同样保留本致谢。

## 许可

- ZCode：Apache-2.0（© Z.ai）
- 本仓库移植与打包脚本：Apache-2.0
