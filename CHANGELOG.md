# Changelog

## ZCode 3.14.3 · 飞牛 fnOS（本仓库相对最初 Fork 打包）

> 上游：[zai-org/ZCode](https://github.com/zai-org/ZCode) @ `29628c9a`  
> 本包只做 NAS 移植/打包，不修改 ZCode 本体逻辑。

### 新增

- **统一网关入口**（`/app/zcode`）：复用飞牛 NAS 登录态，桌面图标打开免令牌
  - `gateway-proxy.mjs`：Unix Socket → 本机 TCP，剥离网关前缀
  - 自动改写前端 `/assets`、`/ws`、`/api` 根路径到网关前缀
  - WebSocket 经网关可用
- **端口登录门禁**：`http://NAS:8988` 弹出令牌登录框（**令牌不进 URL 地址栏**）
  - 登录成功由服务端下发 **HttpOnly** cookie
  - 移动端适配（safe-area / 触控 / 小屏）
  - 失败次数增加自动冷却（软限速）
- **自动 Release**：打 `v*` tag 或 Actions 手动勾选后发布，自动附 fpk 与 changelog

### 双入口（并存）

| 入口 | 鉴权 |
|---|---|
| 桌面图标 → 统一网关 | 飞牛登录态（`X-Trim-*`） |
| `http://NAS:8988` | 访问令牌登录框 |

### 安全加固

- 网关 Socket 仅对**带飞牛会话身份**的请求注入令牌（本机任意进程直连 socket 不会自动获得权限）
- Socket 权限 `0666`（对齐官方示例），鉴权不依赖 socket 文件权限
- 令牌经**环境变量**传给服务端，不再出现在进程命令行（`/proc/*/cmdline`）
- 访问令牌要求 **≥16 位**（向导、脚本、登录框一致）；脚本内二次校验格式
- 登录改用 `?token=` 换 HttpOnly cookie，JS 不写明文 cookie
- GitHub Actions 输入改走 `env`，避免脚本注入
- 修复网关代理对压缩 HTML 误删 `content-encoding` 的问题

### 体验修复

- 桌面/应用图标路径修正为 `images/icon_{0}.png`
- 登录门禁「探测优先」：HttpOnly cookie / 网关会话下不会反复弹框
- 登录过程不再闪现「WebSocket connection failed / Web 启动失败」
- 无会话时立即显示登录框，减少空等
- 打包脚本补全 `wizard/`（安装向导），并清除 UTF-8 BOM（避免 fnOS 解析失败）
- 去掉不兼容的 `os_min_version`（会导致「应用包不符合系统要求」）

### 构建与发版

- push `main` / `test/*` / `feature/*`：**只出 Actions Artifacts**，不自动发 Release
- 发正式版：`git tag v3.14.x && git push origin v3.14.x`（或 Actions 勾选 `publish_release`）
- Release notes 自动包含「上次 tag 以来」的 commit 列表

### 真机验证摘要

- 登录框探测优先、HttpOnly cookie 可续用
- 无令牌 / 错误令牌 → 401；正确令牌 → 200 + Set-Cookie
- WebSocket：有 cookie **101**，无 cookie **401**
- 页面 TTFB 约 80ms 量级（NAS 局域网）

### 升级注意

- 若原访问令牌 **不足 16 位**：升级后到「应用中心 → ZCode → 应用设置」重设为 ≥16 位，再重启
- 建议卸载旧版后安装新包（同版本号可能被应用中心拒绝）
- 请勿将 8988 端口映射公网

### 安装

1. 应用中心安装 Node.js v22（或随包自动安装）
2. 下载 `zcode-3.14.3.fpk`（Release 附件，不是 Artifact zip）
3. 手动安装 → 向导填写 ≥16 位随机访问令牌
4. 桌面图标（网关）或 `http://NAS:8988`（登录框）进入
