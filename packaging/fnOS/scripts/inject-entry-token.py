#!/usr/bin/env python3
"""给 web/index.html 注入移动端友好的「访问令牌」登录门禁。

安全要点：
- 始终先探测 /api/server-info（HttpOnly cookie 对 JS 不可见，不能靠 document.cookie 分支）
- 校验用 GET /api/server-info?token=...，由服务端 Set-Cookie（HttpOnly）
- 失败冷却限速（客户端软限速）
- 适配手机：safe-area、触控、小屏

统一网关：gateway-proxy 仅对带 X-Trim-* 的网关请求注入令牌，
浏览器侧探测 200 会直接进入，不弹框。

令牌长度与服务端对齐（8–64）：兼容旧包升级留下的短令牌；
新装向导仍建议 ≥16。
"""

from __future__ import annotations

import sys
from pathlib import Path

MARKER = "zcode-fnos-login-gate"

SNIPPET = (
    "<script>/* " + MARKER + " */"
    "(function(){"
    "if(window.__ZCODE_FNOS_LOGIN__)return;"
    "window.__ZCODE_FNOS_LOGIN__=1;"
    "function el(tag,css){var e=document.createElement(tag);if(css)e.style.cssText=css;return e;}"
    "var root=document.getElementById('zcode-fnos-login');"
    "if(!root){"
    "root=el('div','position:fixed;left:0;top:0;right:0;bottom:0;z-index:2147483646;display:flex;align-items:center;justify-content:center;background:#0f172a;padding:16px;box-sizing:border-box;font-family:Inter,-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif;color:#e2e8f0');"
    "root.id='zcode-fnos-login';"
    "(document.documentElement||document.body).appendChild(root);"
    "}"
    "function showStatus(text){"
    "root.innerHTML='';"
    "var card=el('div','width:100%;max-width:360px;padding:28px 24px;border-radius:16px;background:#1e293b;border:1px solid #334155;text-align:center;font-size:13px;color:#94a3b8');"
    "card.textContent=text||'正在验证访问权限…';"
    "root.appendChild(card);"
    "}"
    "function showLogin(err){"
    "root.innerHTML='';"
    "var card=el('div','width:100%;max-width:360px;padding:28px 22px 22px;border-radius:16px;background:#1e293b;border:1px solid #334155;box-shadow:0 18px 50px rgba(0,0,0,.45)');"
    "var h=el('div','font-size:20px;font-weight:600;margin:0 0 8px');h.textContent='ZCode';"
    "var s=el('div','font-size:13px;line-height:1.55;color:#94a3b8;margin-bottom:18px');s.textContent='请输入访问令牌以继续';"
    "var inp=el('input','width:100%;box-sizing:border-box;padding:12px 14px;border-radius:12px;border:1px solid #475569;background:#0f172a;color:#f8fafc;font-size:16px;outline:none');"
    "inp.type='password';inp.placeholder='访问令牌';inp.autocomplete='current-password';inp.setAttribute('enterkeyhint','go');"
    "var msg=el('div','min-height:20px;margin:10px 0 2px;font-size:12px;line-height:1.4;color:#f87171');"
    "if(err)msg.textContent=err;"
    "var btn=el('button','width:100%;margin-top:10px;padding:13px 14px;border:0;border-radius:12px;background:#2563eb;color:#fff;font-size:15px;font-weight:600;cursor:pointer');"
    "btn.type='button';btn.textContent='进入';"
    "card.appendChild(h);card.appendChild(s);card.appendChild(inp);card.appendChild(msg);card.appendChild(btn);"
    "root.appendChild(card);"
    "setTimeout(function(){try{inp.focus();}catch(e){}},0);"
    "function submit(){"
    "var now=Date.now();"
    "var wait=window.__ZCODE_FNOS_WAIT__||0;"
    "if(now<wait){msg.style.color='#f87171';msg.textContent='请 '+Math.ceil((wait-now)/1000)+' 秒后再试';return;}"
    "var v=(inp.value||'').trim();"
    "if(!v){msg.textContent='请输入访问令牌';return;}"
    "if(v.length<16){msg.textContent='令牌至少 16 位。若旧令牌不足 16 位，请到 应用中心 → ZCode → 应用设置 重设访问令牌';return;}"
    "msg.style.color='#94a3b8';msg.textContent='验证中…';btn.disabled=true;"
    "fetch('/api/server-info?token='+encodeURIComponent(v),{cache:'no-store',credentials:'same-origin'}).then(function(r){"
    "if(r.ok){location.reload();return;}"
    "window.__ZCODE_FNOS_FAIL__=(window.__ZCODE_FNOS_FAIL__||0)+1;"
    "window.__ZCODE_FNOS_WAIT__=Date.now()+Math.min(8000,window.__ZCODE_FNOS_FAIL__*800);"
    "showLogin('令牌不正确或服务未就绪');"
    "}).catch(function(){"
    "window.__ZCODE_FNOS_FAIL__=(window.__ZCODE_FNOS_FAIL__||0)+1;"
    "window.__ZCODE_FNOS_WAIT__=Date.now()+Math.min(8000,window.__ZCODE_FNOS_FAIL__*800);"
    "showLogin('无法连接服务，请稍后重试');"
    "});"
    "}"
    "btn.onclick=submit;"
    "inp.addEventListener('keydown',function(e){if(e.key==='Enter')submit();});"
    "}"
    "function removeGate(){if(root&&root.parentNode)root.parentNode.removeChild(root);}"
    "function check(){"
    "fetch('/api/server-info',{cache:'no-store',credentials:'same-origin'}).then(function(r){"
    "if(r.ok){removeGate();return;}"
    "showLogin('');"
    "}).catch(function(){showLogin('');});"
    "}"
    "showStatus('正在验证访问权限…');check();"
    "})();"
    "</script>"
)


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: inject-entry-token.py <web/index.html>", file=sys.stderr)
        return 2

    path = Path(sys.argv[1])
    if not path.is_file():
        print(f"✗ 找不到 {path}", file=sys.stderr)
        return 1

    html = path.read_text(encoding="utf-8")

    for old in ("zcode-fnos-entry-token", "zcode-fnos-login-gate"):
        while True:
            start = html.find("<script>/* " + old)
            if start == -1:
                break
            end = html.find("</script>", start)
            if end == -1:
                break
            html = html[:start] + html[end + len("</script>") :]

    inject = SNIPPET
    if "<head>" in html:
        html = html.replace("<head>", "<head>" + inject, 1)
    else:
        html = inject + html

    path.write_text(html, encoding="utf-8", newline="\n")
    print("[build] 已注入访问令牌登录门禁 → web/index.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
