// ==UserScript==
// @name         Agent Reach Cookie Helper
// @namespace    https://github.com/panniantong/agent-reach
// @version      4.0.0
// @description  Agent Reach Cookie 提取助手：用 GM_cookie 读取 HttpOnly 认证 cookie，可拖动悬浮按钮 + 操作面板 + 一键自动采集多网站
// @author       Agent Reach
// @match        https://twitter.com/*
// @match        https://x.com/*
// @match        https://xueqiu.com/*
// @match        https://www.reddit.com/*
// @match        https://www.reddit.com/
// @match        https://www.xiaohongshu.com/*
// @match        https://xiaohongshu.com/*
// @match        https://www.facebook.com/*
// @match        https://facebook.com/*
// @match        https://www.instagram.com/*
// @match        https://instagram.com/*
// @match        https://www.linkedin.com/*
// @match        https://linkedin.com/*
// @match        https://console.groq.com/*
// @icon         https://www.google.com/s2/favicons?sz=64&domain=openai.com
// @grant        GM_setClipboard
// @grant        GM_getValue
// @grant        GM_setValue
// @grant        GM_notification
// @grant        GM_cookie
// @run-at       document-idle
// ==/UserScript==

(function () {
  "use strict";

  // ════════════════════════════════════════════════════════════
  // 1. 平台配置清单
  //    关键：HttpOnly cookie（auth_token、reddit_session、sessionid、li_at 等）
  //    必须用 GM_cookie 才能读到，document.cookie 读不到。
  // ════════════════════════════════════════════════════════════
  const PLATFORMS = [
    {
      id: "twitter",
      name: "Twitter / X",
      icon: "🐦",
      domains: ["twitter.com", "x.com"],
      loginUrl: "https://x.com/home",
      cookies: ["auth_token", "ct0", "twid", "kdt", "guest_id"],
      required: ["auth_token", "ct0"],
      category: "cookie",
    },
    {
      id: "xueqiu",
      name: "雪球",
      icon: "❄️",
      domains: ["xueqiu.com"],
      loginUrl: "https://xueqiu.com/",
      cookies: ["xq_a_token", "xqat", "xq_r_token", "xq_is_trade"],
      required: ["xq_a_token"],
      category: "cookie",
    },
    {
      id: "reddit",
      name: "Reddit",
      icon: "🤖",
      domains: ["reddit.com"],
      loginUrl: "https://www.reddit.com/",
      cookies: ["reddit_session", "token", "csv_v2_token", "loid"],
      required: ["reddit_session"],
      category: "cookie",
    },
    {
      id: "xiaohongshu",
      name: "小红书",
      icon: "📕",
      domains: ["xiaohongshu.com"],
      loginUrl: "https://www.xiaohongshu.com/",
      cookies: ["web_session", "a1", "webId", "gid"],
      required: ["web_session"],
      category: "cookie",
    },
    {
      id: "facebook",
      name: "Facebook",
      icon: "👥",
      domains: ["facebook.com"],
      loginUrl: "https://www.facebook.com/",
      cookies: ["c_user", "xs", "fr", "datr"],
      required: ["c_user", "xs"],
      category: "cookie",
    },
    {
      id: "instagram",
      name: "Instagram",
      icon: "📸",
      domains: ["instagram.com"],
      loginUrl: "https://www.instagram.com/",
      cookies: ["sessionid", "csrftoken", "ds_user_id", "mid"],
      required: ["sessionid"],
      category: "cookie",
    },
    {
      id: "linkedin",
      name: "LinkedIn",
      icon: "💼",
      domains: ["linkedin.com"],
      loginUrl: "https://www.linkedin.com/feed/",
      cookies: ["li_at", "li_rm", "JSESSIONID", "bcookie"],
      required: ["li_at"],
      category: "cookie",
    },
    {
      id: "groq",
      name: "小宇宙/Groq API",
      icon: "🎙️",
      applyUrl: "https://console.groq.com/keys",
      keyPrefix: "gsk_",
      category: "apikey",
    },
    {
      id: "zeroconfig",
      name: "零配置平台（无需提取）",
      icon: "✨",
      platforms: [
        "YouTube",
        "Bilibili",
        "GitHub（gh CLI 自带）",
        "Web / Jina Reader",
        "Exa Search",
        "RSS",
        "V2EX",
      ],
      category: "info",
    },
  ];

  const SESSION_KEY = "are_collect_session";

  // ════════════════════════════════════════════════════════════
  // 2. 持久化配置
  // ════════════════════════════════════════════════════════════
  let outputFormat = GM_getValue("outputFormat", "text"); // "text" | "json"
  let panelVisible = GM_getValue("panelVisible", false);

  // ════════════════════════════════════════════════════════════
  // 3. 工具函数
  // ════════════════════════════════════════════════════════════

  function findPlatformById(id) {
    return PLATFORMS.find((p) => p.id === id);
  }

  function getCurrentHost() {
    return location.hostname.replace(/^www\./, "");
  }

  function getCurrentPlatform() {
    const host = getCurrentHost();
    return PLATFORMS.find(
      (p) => p.category === "cookie" && p.domains.includes(host)
    );
  }

  function isCurrentDomain(platform) {
    if (!platform || !platform.domains) return false;
    const host = getCurrentHost();
    return platform.domains.includes(host);
  }

  function copyToClipboard(text) {
    if (typeof GM_setClipboard !== "undefined") {
      GM_setClipboard(text, "text");
      return Promise.resolve();
    }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      return navigator.clipboard.writeText(text);
    }
    const textarea = document.createElement("textarea");
    textarea.value = text;
    textarea.style.position = "fixed";
    textarea.style.opacity = "0";
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand("copy");
    document.body.removeChild(textarea);
    return Promise.resolve();
  }

  /** 用 document.cookie 读取（只能读到非 HttpOnly cookie） */
  function getCookieFromDocument(name) {
    const escaped = name.replace(/[-[\]{}()*+?.,\\^$|#\s]/g, "\\$&");
    const match = document.cookie.match(
      new RegExp("(?:^|;\\s*)" + escaped + "=([^;]*)")
    );
    return match ? decodeURIComponent(match[1]) : null;
  }

  /**
   * 用 GM_cookie.list 读取当前域名下所有 cookie（包含 HttpOnly）。
   * 返回 Promise<{name: value}>。
   * 如果 GM_cookie 不可用，回退到 document.cookie。
   */
  function getAllCookiesViaGM() {
    return new Promise((resolve) => {
      if (typeof GM_cookie === "undefined" || !GM_cookie.list) {
        // 回退：document.cookie（读不到 HttpOnly）
        const result = {};
        document.cookie.split(";").forEach((pair) => {
          const idx = pair.indexOf("=");
          if (idx > -1) {
            const k = pair.slice(0, idx).trim();
            const v = pair.slice(idx + 1).trim();
            result[k] = v;
          }
        });
        resolve({ cookies: result, source: "document.cookie", httpOnly: false });
        return;
      }

      try {
        GM_cookie.list({ domain: getCurrentHost() }, (cookies, error) => {
          if (error || !cookies) {
            // 回退
            const result = {};
            document.cookie.split(";").forEach((pair) => {
              const idx = pair.indexOf("=");
              if (idx > -1) {
                const k = pair.slice(0, idx).trim();
                const v = pair.slice(idx + 1).trim();
                result[k] = v;
              }
            });
            resolve({
              cookies: result,
              source: "document.cookie (fallback)",
              httpOnly: false,
            });
            return;
          }
          const result = {};
          for (const c of cookies) {
            if (c.name) result[c.name] = c.value;
          }
          resolve({
            cookies: result,
            source: "GM_cookie",
            httpOnly: true,
          });
        });
      } catch (e) {
        const result = {};
        document.cookie.split(";").forEach((pair) => {
          const idx = pair.indexOf("=");
          if (idx > -1) {
            const k = pair.slice(0, idx).trim();
            const v = pair.slice(idx + 1).trim();
            result[k] = v;
          }
        });
        resolve({
          cookies: result,
          source: "document.cookie (error fallback)",
          httpOnly: false,
        });
      }
    });
  }

  /** 提取某个平台的所有目标 cookie（异步，因为要用 GM_cookie） */
  async function extractCookiesForPlatform(platform) {
    const { cookies: allCookies, source } = await getAllCookiesViaGM();
    const result = {};
    for (const name of platform.cookies) {
      if (allCookies[name]) {
        result[name] = allCookies[name];
      }
    }
    // 也尝试用 document.cookie 补充（防止 GM_cookie 漏读某些 cookie）
    for (const name of platform.cookies) {
      if (!result[name]) {
        const v = getCookieFromDocument(name);
        if (v) result[name] = v;
      }
    }
    return { cookies: result, source };
  }

  async function isPlatformReady(platform) {
    if (platform.category !== "cookie") return false;
    const { cookies } = await extractCookiesForPlatform(platform);
    return platform.required.every((name) => cookies[name]);
  }

  // ════════════════════════════════════════════════════════════
  // 4. 会话管理（跨页面状态机）
  // ════════════════════════════════════════════════════════════

  function getSession() {
    return GM_getValue(SESSION_KEY, null);
  }

  function setSession(s) {
    GM_setValue(SESSION_KEY, s);
  }

  function clearSession() {
    GM_setValue(SESSION_KEY, null);
  }

  function isCollecting() {
    const s = getSession();
    return s && s.status === "collecting";
  }

  function newSession(queue) {
    const results = {};
    for (const id of queue) {
      results[id] = { status: "pending", cookies: {} };
    }
    return {
      status: "collecting",
      queue: queue,
      currentIndex: 0,
      results: results,
      startedAt: Date.now(),
    };
  }

  // ════════════════════════════════════════════════════════════
  // 5. 采集流程（异步，因为提取 cookie 是异步的）
  // ════════════════════════════════════════════════════════════

  function startCollection(selectedIds) {
    if (selectedIds.length === 0) {
      showNotification("请至少勾选一个网站", "warn");
      return;
    }
    const validIds = selectedIds.filter(
      (id) => findPlatformById(id)?.category === "cookie"
    );
    if (validIds.length === 0) {
      showNotification("勾选的平台无效", "warn");
      return;
    }

    const session = newSession(validIds);
    setSession(session);

    const firstPlatform = findPlatformById(validIds[0]);
    showNotification(
      `开始采集 ${validIds.length} 个网站，跳转到 ${firstPlatform.name}...`,
      "info"
    );

    setTimeout(() => {
      location.href = firstPlatform.loginUrl;
    }, 600);
  }

  async function tryCollectCurrent() {
    const session = getSession();
    if (!session || session.status !== "collecting") return;

    const platformId = session.queue[session.currentIndex];
    const platform = findPlatformById(platformId);
    if (!platform) {
      goToNextPlatform();
      return;
    }

    if (!isCurrentDomain(platform)) {
      showCollectingBar(
        `${platform.name} 域名不匹配，请手动导航到该网站，或点"重试"自动跳转`,
        "warn"
      );
      return;
    }

    const { cookies, source } = await extractCookiesForPlatform(platform);
    const ready = platform.required.every((name) => cookies[name]);

    if (ready) {
      session.results[platformId] = { status: "success", cookies: cookies };
      setSession(session);
      showNotification(`✅ ${platform.name} Cookie 采集成功（via ${source}）`, "success");
      setTimeout(() => goToNextPlatform(), 1200);
    } else {
      const missing = platform.required.filter((n) => !cookies[n]);
      session.results[platformId] = {
        status: "failed",
        cookies: cookies,
        missing: missing,
        source: source,
      };
      setSession(session);
      showCollectingBar(
        `${platform.name} 未检测到登录态（缺: ${missing.join(", ")}），请登录后点"重试"`,
        "warn"
      );
    }
  }

  function goToNextPlatform() {
    const session = getSession();
    if (!session || session.status !== "collecting") return;

    session.currentIndex += 1;
    setSession(session);

    if (session.currentIndex >= session.queue.length) {
      finishCollection();
      return;
    }

    const nextPlatform = findPlatformById(session.queue[session.currentIndex]);
    if (!nextPlatform) {
      goToNextPlatform();
      return;
    }

    showNotification(
      `下一个：${nextPlatform.name} (${session.currentIndex + 1}/${session.queue.length})`,
      "info"
    );
    setTimeout(() => {
      location.href = nextPlatform.loginUrl;
    }, 600);
  }

  function retryCurrent() {
    const session = getSession();
    if (!session || session.status !== "collecting") return;

    const platformId = session.queue[session.currentIndex];
    const platform = findPlatformById(platformId);
    if (!platform) return;

    if (!isCurrentDomain(platform)) {
      location.href = platform.loginUrl;
      return;
    }
    tryCollectCurrent();
  }

  function abortCollection() {
    const session = getSession();
    if (!session) return;
    session.status = "aborted";
    setSession(session);
    showNotification("已中止采集", "info");
    removeCollectingBar();
    refreshPanel();
  }

  function finishCollection() {
    const session = getSession();
    if (!session) return;
    session.status = "done";
    setSession(session);
    removeCollectingBar();

    const successCount = Object.values(session.results).filter(
      (r) => r.status === "success"
    ).length;
    const total = session.queue.length;
    showNotification(
      `采集完成！成功 ${successCount}/${total}，打开面板查看汇总`,
      "success"
    );
    panelVisible = true;
    GM_setValue("panelVisible", true);
    const panel = document.getElementById("are-panel");
    if (panel) {
      panel.style.display = "block";
      refreshPanel();
    }
  }

  function clearResults() {
    clearSession();
    showNotification("已清空采集结果", "info");
    removeCollectingBar();
    refreshPanel();
  }

  // ════════════════════════════════════════════════════════════
  // 6. 格式化输出
  // ════════════════════════════════════════════════════════════

  function formatCookiesAsText(cookies) {
    return Object.entries(cookies)
      .map(([k, v]) => `${k}=${v}`)
      .join("; ");
  }

  function formatCookiesAsJSON(platformId, cookies) {
    return JSON.stringify({ [platformId]: cookies }, null, 2);
  }

  function formatSingleOutput(platform, cookies) {
    if (outputFormat === "json") return formatCookiesAsJSON(platform.id, cookies);
    return formatCookiesAsText(cookies);
  }

  function formatAllResults(format) {
    const session = getSession();
    if (!session) return "";

    const successEntries = Object.entries(session.results).filter(
      ([id, r]) => r.status === "success"
    );

    if (format === "json") {
      const obj = {};
      for (const [id, r] of successEntries) {
        obj[id] = r.cookies;
      }
      obj._meta = {
        total: session.queue.length,
        success: successEntries.length,
      };
      return JSON.stringify(obj, null, 2);
    }

    const lines = [];
    for (const [id, r] of successEntries) {
      const platform = findPlatformById(id);
      lines.push(`=== ${platform ? platform.name : id} ===`);
      lines.push(formatCookiesAsText(r.cookies));
      lines.push("");
    }
    lines.push(`# 成功 ${successEntries.length}/${session.queue.length}`);
    return lines.join("\n");
  }

  async function copyAllResults(format) {
    const text = formatAllResults(format);
    if (!text) {
      showNotification("没有可复制的结果", "warn");
      return;
    }
    try {
      await copyToClipboard(text);
      showNotification("已复制全部结果到剪贴板", "success");
    } catch (e) {
      showNotification("复制失败：" + e.message, "error");
    }
  }

  // ════════════════════════════════════════════════════════════
  // 7. 通知 + 状态条
  // ════════════════════════════════════════════════════════════

  function showNotification(text, type = "info") {
    const colors = {
      success: { bg: "#a6e3a1", fg: "#1e1e2e", icon: "✅" },
      warn: { bg: "#f9e2af", fg: "#1e1e2e", icon: "⚠️" },
      error: { bg: "#f38ba8", fg: "#1e1e2e", icon: "❌" },
      info: { bg: "#89b4fa", fg: "#1e1e2e", icon: "ℹ️" },
    };
    const c = colors[type] || colors.info;

    const toast = document.createElement("div");
    toast.textContent = `${c.icon} ${text}`;
    Object.assign(toast.style, {
      position: "fixed",
      top: "20px",
      left: "50%",
      transform: "translateX(-50%)",
      background: c.bg,
      color: c.fg,
      padding: "12px 24px",
      borderRadius: "12px",
      boxShadow: "0 4px 20px rgba(0, 0, 0, 0.3)",
      zIndex: "9999999",
      fontFamily: "system-ui, -apple-system, sans-serif",
      fontSize: "14px",
      fontWeight: "600",
      maxWidth: "80vw",
      textAlign: "center",
      transition: "opacity 0.3s, transform 0.3s",
    });
    document.body.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = "0";
      toast.style.transform = "translateX(-50%) translateY(-10px)";
      setTimeout(() => toast.remove(), 300);
    }, 2800);
  }

  function showCopiedToast(el) {
    const originalText = el.textContent;
    el.textContent = "✓ 已复制";
    el.classList.add("are-copied");
    setTimeout(() => {
      el.textContent = originalText;
      el.classList.remove("are-copied");
    }, 1500);
  }

  function showCollectingBar(message, type = "info") {
    removeCollectingBar();
    const session = getSession();
    if (!session || session.status !== "collecting") return;

    const platformId = session.queue[session.currentIndex];
    const platform = findPlatformById(platformId);
    const idx = session.currentIndex + 1;
    const total = session.queue.length;

    const bar = document.createElement("div");
    bar.id = "are-collecting-bar";
    Object.assign(bar.style, {
      position: "fixed",
      top: "0",
      left: "0",
      right: "0",
      zIndex: "9999998",
      background:
        type === "warn"
          ? "#f9e2af"
          : "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
      color: type === "warn" ? "#1e1e2e" : "#fff",
      padding: "10px 16px",
      fontFamily: "system-ui, -apple-system, sans-serif",
      fontSize: "13px",
      fontWeight: "600",
      boxShadow: "0 2px 12px rgba(0,0,0,0.3)",
      display: "flex",
      alignItems: "center",
      gap: "12px",
      flexWrap: "wrap",
    });

    const icon = type === "warn" ? "⚠️" : "🔄";
    const statusText =
      type === "warn"
        ? `${icon} ${platform ? platform.name : ""} 未登录 (${idx}/${total})`
        : `${icon} 正在采集: ${platform ? platform.name : ""} (${idx}/${total})`;

    const text = document.createElement("span");
    text.textContent = statusText;
    text.style.flex = "1";
    text.style.minWidth = "200px";
    bar.appendChild(text);

    const retryBtn = makeBarBtn("🔄 重试", retryCurrent, type === "warn");
    const nextBtn = makeBarBtn("⏭ 下一个", goToNextPlatform);
    const abortBtn = makeBarBtn("⏹ 中止", abortCollection);

    bar.appendChild(retryBtn);
    bar.appendChild(nextBtn);
    bar.appendChild(abortBtn);

    if (message) {
      const msg = document.createElement("div");
      msg.textContent = message;
      Object.assign(msg.style, {
        width: "100%",
        fontSize: "11px",
        fontWeight: "400",
        opacity: "0.85",
        marginTop: "2px",
      });
      bar.appendChild(msg);
    }

    document.body.appendChild(bar);
    document.body.style.paddingTop = "50px";
  }

  function makeBarBtn(text, onClick, primary = false) {
    const btn = document.createElement("button");
    btn.textContent = text;
    Object.assign(btn.style, {
      padding: "4px 12px",
      background: primary ? "#1e1e2e" : "rgba(255,255,255,0.2)",
      color: primary ? "#f9e2af" : "#fff",
      border: "1px solid rgba(255,255,255,0.4)",
      borderRadius: "6px",
      cursor: "pointer",
      fontSize: "12px",
      fontWeight: "600",
      fontFamily: "inherit",
    });
    btn.addEventListener("mouseenter", () => {
      btn.style.background = primary ? "#313244" : "rgba(255,255,255,0.35)";
    });
    btn.addEventListener("mouseleave", () => {
      btn.style.background = primary ? "#1e1e2e" : "rgba(255,255,255,0.2)";
    });
    btn.addEventListener("click", onClick);
    return btn;
  }

  function removeCollectingBar() {
    const bar = document.getElementById("are-collecting-bar");
    if (bar) bar.remove();
    document.body.style.paddingTop = "";
  }

  // ════════════════════════════════════════════════════════════
  // 8. 拖动逻辑
  // ════════════════════════════════════════════════════════════

  function makeDraggable(el, storageKey) {
    const saved = GM_getValue(storageKey, null);
    if (saved && typeof saved === "object") {
      el.style.top = saved.top + "px";
      el.style.left = saved.left + "px";
      el.style.right = "auto";
    }

    let isDragging = false;
    let startX = 0,
      startY = 0,
      startLeft = 0,
      startTop = 0;
    let moved = false;
    const DRAG_THRESHOLD = 5;

    function onMouseDown(e) {
      if (e.button !== 0) return;
      isDragging = true;
      moved = false;
      startX = e.clientX;
      startY = e.clientY;
      const rect = el.getBoundingClientRect();
      startLeft = rect.left;
      startTop = rect.top;
      e.preventDefault();
    }

    function onMouseMove(e) {
      if (!isDragging) return;
      const dx = e.clientX - startX;
      const dy = e.clientY - startY;
      if (Math.abs(dx) > DRAG_THRESHOLD || Math.abs(dy) > DRAG_THRESHOLD) {
        moved = true;
        el.style.cursor = "grabbing";
        el.style.right = "auto";
        let newLeft = startLeft + dx;
        let newTop = startTop + dy;
        const maxX = window.innerWidth - el.offsetWidth;
        const maxY = window.innerHeight - el.offsetHeight;
        newLeft = Math.max(0, Math.min(maxX, newLeft));
        newTop = Math.max(0, Math.min(maxY, newTop));
        el.style.left = newLeft + "px";
        el.style.top = newTop + "px";
      }
    }

    function onMouseUp() {
      if (!isDragging) return;
      isDragging = false;
      el.style.cursor = "grab";
      if (moved) {
        const rect = el.getBoundingClientRect();
        GM_setValue(storageKey, {
          left: Math.round(rect.left),
          top: Math.round(rect.top),
        });
      }
    }

    el.addEventListener("mousedown", onMouseDown);
    document.addEventListener("mousemove", onMouseMove);
    document.addEventListener("mouseup", onMouseUp);

    el.addEventListener("touchstart", (e) => {
      const t = e.touches[0];
      onMouseDown({
        button: 0,
        clientX: t.clientX,
        clientY: t.clientY,
        preventDefault: () => e.preventDefault(),
      });
    });
    document.addEventListener("touchmove", (e) => {
      if (!isDragging) return;
      const t = e.touches[0];
      onMouseMove({ clientX: t.clientX, clientY: t.clientY });
      e.preventDefault();
    });
    document.addEventListener("touchend", onMouseUp);

    return {
      wasMoved: () => moved,
    };
  }

  // ════════════════════════════════════════════════════════════
  // 9. 自动提取（非采集模式，单页）
  // ════════════════════════════════════════════════════════════

  async function autoExtractOnLoad() {
    const platform = getCurrentPlatform();
    if (!platform) return;

    // 等页面和 cookie 稳定
    await sleep(2000);

    const { cookies, source } = await extractCookiesForPlatform(platform);
    const ready = platform.required.every((name) => cookies[name]);

    if (ready) {
      const text = formatSingleOutput(platform, cookies);
      await copyToClipboard(text);
      showNotification(
        `检测到 ${platform.name} Cookie，已复制（via ${source}，${outputFormat.toUpperCase()}）`,
        "success"
      );
    } else if (Object.keys(cookies).length > 0) {
      const missing = platform.required.filter((n) => !cookies[n]);
      showNotification(
        `${platform.name} 部分提取，缺: ${missing.join(", ")}（来源: ${source}）`,
        "warn"
      );
    } else {
      showNotification(
        `${platform.name} 未检测到登录态（来源: ${source}）`,
        "warn"
      );
    }
  }

  function sleep(ms) {
    return new Promise((r) => setTimeout(r, ms));
  }

  // ════════════════════════════════════════════════════════════
  // 10. UI 渲染
  // ════════════════════════════════════════════════════════════

  function injectStyles() {
    const style = document.createElement("style");
    style.textContent = `
      #are-panel::-webkit-scrollbar { width: 8px; }
      #are-panel::-webkit-scrollbar-track { background: #181825; border-radius: 4px; }
      #are-panel::-webkit-scrollbar-thumb { background: #45475a; border-radius: 4px; }
      #are-panel::-webkit-scrollbar-thumb:hover { background: #585b70; }

      .are-card {
        background: #181825;
        border: 1px solid #313244;
        border-radius: 12px;
        padding: 14px;
        margin-bottom: 10px;
        transition: border-color 0.2s, background 0.2s;
      }
      .are-card:hover { border-color: #45475a; }

      .are-badge {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 6px;
        font-size: 11px;
        font-weight: 700;
        font-family: system-ui, -apple-system, sans-serif;
      }
      .are-badge-ready { background: #a6e3a1; color: #1e1e2e; }
      .are-badge-pending { background: #f9e2af; color: #1e1e2e; }
      .are-badge-loading { background: #89b4fa; color: #1e1e2e; }
      .are-badge-info { background: #6c7086; color: #cdd6f4; }

      .are-btn {
        padding: 6px 12px;
        background: #313244;
        color: #cdd6f4;
        border: 1px solid #45475a;
        border-radius: 8px;
        cursor: pointer;
        font-size: 12px;
        font-family: system-ui, -apple-system, sans-serif;
        transition: all 0.15s;
      }
      .are-btn:hover:not(:disabled) {
        background: #45475a;
        border-color: #585b70;
      }
      .are-btn:disabled { opacity: 0.4; cursor: not-allowed; }
      .are-btn-primary {
        background: #89b4fa;
        color: #1e1e2e;
        border-color: #89b4fa;
        font-weight: 600;
      }
      .are-btn-primary:hover:not(:disabled) {
        background: #74c7ec;
        border-color: #74c7ec;
      }
      .are-btn-danger {
        background: #f38ba8;
        color: #1e1e2e;
        border-color: #f38ba8;
        font-weight: 600;
      }
      .are-btn-success {
        background: #a6e3a1;
        color: #1e1e2e;
        border-color: #a6e3a1;
        font-weight: 600;
      }
      .are-copied {
        background: #a6e3a1 !important;
        color: #1e1e2e !important;
        border-color: #a6e3a1 !important;
      }

      .are-checkbox-row {
        display: flex;
        align-items: center;
        gap: 6px;
        padding: 6px 10px;
        background: #181825;
        border: 1px solid #313244;
        border-radius: 8px;
        cursor: pointer;
        font-size: 12px;
      }
      .are-checkbox-row:hover { border-color: #45475a; }
      .are-checkbox-row input { cursor: pointer; }

      .are-summary-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 8px 10px;
        background: #181825;
        border-radius: 8px;
        margin-bottom: 6px;
        font-size: 12px;
        font-family: 'SF Mono', monospace;
      }
    `;
    document.head.appendChild(style);
  }

  function createFAB() {
    if (document.getElementById("are-fab")) return;

    const fab = document.createElement("div");
    fab.id = "are-fab";
    fab.innerHTML = "🔑";
    fab.title = "Agent Reach Cookie Helper（可拖动）";
    Object.assign(fab.style, {
      position: "fixed",
      top: "12px",
      right: "12px",
      zIndex: "999999",
      width: "44px",
      height: "44px",
      borderRadius: "50%",
      background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
      color: "#fff",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      cursor: "grab",
      fontSize: "20px",
      boxShadow: "0 4px 15px rgba(102, 126, 234, 0.5)",
      userSelect: "none",
      fontFamily: "system-ui, -apple-system, sans-serif",
      transition: "transform 0.15s",
    });

    const drag = makeDraggable(fab, "fabPosition");

    fab.addEventListener("click", () => {
      if (drag.wasMoved()) return;
      const panel = document.getElementById("are-panel");
      if (panel) {
        const visible = panel.style.display !== "none";
        panel.style.display = visible ? "none" : "block";
        panelVisible = !visible;
        GM_setValue("panelVisible", panelVisible);
        if (!visible) refreshPanel();
      }
    });

    fab.addEventListener("mouseenter", () => {
      if (!drag.wasMoved()) fab.style.transform = "scale(1.1)";
    });
    fab.addEventListener("mouseleave", () => {
      fab.style.transform = "scale(1)";
    });

    document.body.appendChild(fab);
  }

  function createPanel() {
    if (document.getElementById("are-panel")) return;

    const panel = document.createElement("div");
    panel.id = "are-panel";
    Object.assign(panel.style, {
      position: "fixed",
      top: "64px",
      right: "12px",
      zIndex: "999998",
      width: "480px",
      maxHeight: "85vh",
      overflowY: "auto",
      background: "#1e1e2e",
      color: "#cdd6f4",
      borderRadius: "16px",
      padding: "20px",
      boxShadow: "0 8px 40px rgba(0, 0, 0, 0.5)",
      fontFamily: "system-ui, -apple-system, sans-serif",
      fontSize: "13px",
      lineHeight: "1.6",
      display: panelVisible ? "block" : "none",
    });

    document.body.appendChild(panel);
    refreshPanel();
  }

  function refreshPanel() {
    const panel = document.getElementById("are-panel");
    if (!panel) return;
    panel.innerHTML = "";

    // ── 头部 ────────────────────────────────────
    const header = document.createElement("div");
    Object.assign(header.style, {
      display: "flex",
      justifyContent: "space-between",
      alignItems: "center",
      marginBottom: "14px",
      paddingBottom: "12px",
      borderBottom: "1px solid #313244",
    });

    const title = document.createElement("div");
    title.innerHTML = "🔑 <strong>Agent Reach Cookie Helper</strong>";
    Object.assign(title.style, { color: "#cba6f7", fontSize: "15px" });

    const headerBtns = document.createElement("div");
    Object.assign(headerBtns.style, { display: "flex", gap: "8px" });

    const formatBtn = document.createElement("button");
    formatBtn.className = "are-btn";
    formatBtn.textContent = outputFormat === "text" ? "📝 文本格式" : "📋 JSON 格式";
    formatBtn.title = "切换输出格式";
    formatBtn.addEventListener("click", () => {
      outputFormat = outputFormat === "text" ? "json" : "text";
      GM_setValue("outputFormat", outputFormat);
      refreshPanel();
    });

    const closeBtn = document.createElement("button");
    closeBtn.className = "are-btn";
    closeBtn.textContent = "✕";
    closeBtn.title = "关闭面板";
    closeBtn.addEventListener("click", () => {
      panel.style.display = "none";
      panelVisible = false;
      GM_setValue("panelVisible", false);
    });

    headerBtns.appendChild(formatBtn);
    headerBtns.appendChild(closeBtn);
    header.appendChild(title);
    header.appendChild(headerBtns);
    panel.appendChild(header);

    // ── 汇总区 ────────────────────────────────────
    const session = getSession();
    if (session && (session.status === "done" || session.status === "aborted")) {
      panel.appendChild(renderSummarySection(session));
    }

    // ── 一键采集区 ──────────────────────────────
    panel.appendChild(renderCollectSection(session));

    // ── 说明（含 GM_cookie 状态）──────────────
    const hint = document.createElement("div");
    const gmAvailable = typeof GM_cookie !== "undefined" && GM_cookie.list;
    hint.innerHTML =
      `💡 <strong>一键采集</strong>：勾选网站 → 开始 → 自动跳转提取。<br>` +
      `🔌 HttpOnly 读取：` +
      (gmAvailable
        ? `<span style="color:#a6e3a1">GM_cookie 可用（能读到 auth_token / reddit_session 等 HttpOnly cookie）</span>`
        : `<span style="color:#f38ba8">GM_cookie 不可用！请在 Tampermonkey 设置中开启「高级」→ 允许读取 cookie，否则读不到 HttpOnly 认证 cookie</span>`);
    Object.assign(hint.style, {
      padding: "10px 12px",
      background: "#313244",
      borderRadius: "8px",
      fontSize: "12px",
      color: "#bac2de",
      marginBottom: "14px",
      lineHeight: "1.7",
    });
    panel.appendChild(hint);

    // ── 单平台卡片 ──────────────────────────────
    panel.appendChild(makeSectionTitle("🔐 需要 Cookie 的平台（手动）", "#f9e2af"));
    for (const p of PLATFORMS.filter((x) => x.category === "cookie")) {
      panel.appendChild(renderCookieCard(p));
    }

    panel.appendChild(makeSectionTitle("🔑 需要 API Key 的平台", "#f5c2e7"));
    for (const p of PLATFORMS.filter((x) => x.category === "apikey")) {
      panel.appendChild(renderApiKeyCard(p));
    }

    panel.appendChild(makeSectionTitle("✨ 零配置平台（无需提取）", "#6c7086"));
    for (const p of PLATFORMS.filter((x) => x.category === "info")) {
      panel.appendChild(renderInfoCard(p));
    }

    const footer = document.createElement("div");
    footer.textContent =
      "📋 文档：https://github.com/Panniantong/agent-reach · v4 GM_cookie · 悬浮按钮可拖动";
    Object.assign(footer.style, {
      marginTop: "14px",
      padding: "10px",
      fontSize: "11px",
      color: "#6c7086",
      textAlign: "center",
      borderTop: "1px solid #313244",
    });
    panel.appendChild(footer);
  }

  function makeSectionTitle(text, color) {
    const t = document.createElement("div");
    t.textContent = text;
    Object.assign(t.style, {
      color: color,
      fontWeight: "700",
      fontSize: "13px",
      margin: "14px 0 10px 0",
      paddingTop: "8px",
      borderTop: "1px dashed #313244",
    });
    return t;
  }

  function renderSummarySection(session) {
    const section = document.createElement("div");
    Object.assign(section.style, {
      background:
        session.status === "done"
          ? "rgba(166,227,161,0.12)"
          : "rgba(243,139,168,0.12)",
      border:
        "1px solid " + (session.status === "done" ? "#a6e3a1" : "#f38ba8"),
      borderRadius: "12px",
      padding: "14px",
      marginBottom: "14px",
    });

    const successCount = Object.values(session.results).filter(
      (r) => r.status === "success"
    ).length;
    const total = session.queue.length;

    const title = document.createElement("div");
    title.innerHTML =
      session.status === "done"
        ? `✅ <strong>采集完成</strong>　成功 ${successCount}/${total}`
        : `⏹ <strong>采集已中止</strong>　成功 ${successCount}/${total}`;
    Object.assign(title.style, {
      fontSize: "14px",
      color: session.status === "done" ? "#a6e3a1" : "#f38ba8",
      marginBottom: "10px",
    });
    section.appendChild(title);

    for (const id of session.queue) {
      const platform = findPlatformById(id);
      const result = session.results[id];
      if (!result) continue;

      const row = document.createElement("div");
      row.className = "are-summary-row";
      row.style.borderLeft =
        result.status === "success"
          ? "3px solid #a6e3a1"
          : result.status === "failed"
          ? "3px solid #f38ba8"
          : "3px solid #6c7086";

      const left = document.createElement("div");
      left.style.flex = "1";
      left.style.minWidth = "0";

      const nameLine = document.createElement("div");
      const icon =
        result.status === "success"
          ? "✅"
          : result.status === "failed"
          ? "❌"
          : "⏳";
      nameLine.innerHTML = `${icon} <strong>${platform ? platform.name : id}</strong>`;
      nameLine.style.marginBottom = "4px";
      left.appendChild(nameLine);

      if (result.status === "success") {
        const cookieText = formatCookiesAsText(result.cookies);
        const preview =
          cookieText.length > 60
            ? cookieText.slice(0, 60) + "..."
            : cookieText || "(空)";
        const cookieLine = document.createElement("div");
        cookieLine.textContent = preview;
        Object.assign(cookieLine.style, {
          fontSize: "11px",
          color: "#6c7086",
          overflow: "hidden",
          textOverflow: "ellipsis",
          whiteSpace: "nowrap",
        });
        left.appendChild(cookieLine);
      } else if (result.status === "failed") {
        const failLine = document.createElement("div");
        failLine.textContent =
          "未登录" +
          (result.missing && result.missing.length
            ? `（缺: ${result.missing.join(", ")}）`
            : "");
        Object.assign(failLine.style, { fontSize: "11px", color: "#f38ba8" });
        left.appendChild(failLine);
      }

      row.appendChild(left);

      if (result.status === "success") {
        const copyBtn = document.createElement("button");
        copyBtn.className = "are-btn";
        copyBtn.textContent = "📋";
        copyBtn.title = "复制此平台 Cookie";
        copyBtn.addEventListener("click", async () => {
          const text =
            outputFormat === "json"
              ? formatCookiesAsJSON(id, result.cookies)
              : formatCookiesAsText(result.cookies);
          await copyToClipboard(text);
          showCopiedToast(copyBtn);
        });
        row.appendChild(copyBtn);
      }

      section.appendChild(row);
    }

    if (successCount > 0) {
      const btnRow = document.createElement("div");
      Object.assign(btnRow.style, {
        display: "flex",
        gap: "8px",
        marginTop: "10px",
      });

      const copyTextBtn = document.createElement("button");
      copyTextBtn.className = "are-btn are-btn-success";
      copyTextBtn.style.flex = "1";
      copyTextBtn.textContent = "📋 复制全部（文本）";
      copyTextBtn.addEventListener("click", () => copyAllResults("text"));

      const copyJsonBtn = document.createElement("button");
      copyJsonBtn.className = "are-btn are-btn-success";
      copyJsonBtn.style.flex = "1";
      copyJsonBtn.textContent = "📋 复制全部（JSON）";
      copyJsonBtn.addEventListener("click", () => copyAllResults("json"));

      btnRow.appendChild(copyTextBtn);
      btnRow.appendChild(copyJsonBtn);
      section.appendChild(btnRow);
    }

    const clearBtn = document.createElement("button");
    clearBtn.className = "are-btn";
    clearBtn.textContent = "🗑 清空结果";
    Object.assign(clearBtn.style, { width: "100%", marginTop: "8px" });
    clearBtn.addEventListener("click", clearResults);
    section.appendChild(clearBtn);

    return section;
  }

  function renderCollectSection(session) {
    const section = document.createElement("div");
    Object.assign(section.style, {
      background: "#181825",
      border: "1px solid #313244",
      borderRadius: "12px",
      padding: "14px",
      marginBottom: "14px",
    });

    const title = document.createElement("div");
    title.innerHTML = "🎯 <strong>一键自动采集</strong>";
    Object.assign(title.style, {
      fontSize: "14px",
      color: "#cba6f7",
      marginBottom: "10px",
    });
    section.appendChild(title);

    if (session && session.status === "collecting") {
      const collectingHint = document.createElement("div");
      const platformId = session.queue[session.currentIndex];
      const platform = findPlatformById(platformId);
      const idx = session.currentIndex + 1;
      const total = session.queue.length;
      collectingHint.innerHTML =
        `🔄 <strong>采集中</strong>：${platform ? platform.name : ""} (${idx}/${total})`;
      Object.assign(collectingHint.style, {
        padding: "8px 10px",
        background: "rgba(137,180,250,0.15)",
        border: "1px solid #89b4fa",
        borderRadius: "8px",
        fontSize: "12px",
        color: "#89b4fa",
        marginBottom: "10px",
      });
      section.appendChild(collectingHint);

      const ctrlRow = document.createElement("div");
      Object.assign(ctrlRow.style, {
        display: "flex",
        gap: "8px",
        marginBottom: "10px",
      });

      const retryBtn = document.createElement("button");
      retryBtn.className = "are-btn";
      retryBtn.textContent = "🔄 重试当前";
      retryBtn.addEventListener("click", retryCurrent);

      const nextBtn = document.createElement("button");
      nextBtn.className = "are-btn";
      nextBtn.textContent = "⏭ 下一个";
      nextBtn.addEventListener("click", goToNextPlatform);

      const abortBtn = document.createElement("button");
      abortBtn.className = "are-btn are-btn-danger";
      abortBtn.textContent = "⏹ 中止采集";
      abortBtn.addEventListener("click", abortCollection);

      ctrlRow.appendChild(retryBtn);
      ctrlRow.appendChild(nextBtn);
      ctrlRow.appendChild(abortBtn);
      section.appendChild(ctrlRow);
      return section;
    }

    const checkboxGrid = document.createElement("div");
    Object.assign(checkboxGrid.style, {
      display: "grid",
      gridTemplateColumns: "1fr 1fr",
      gap: "6px",
      marginBottom: "10px",
    });

    const cookiePlatforms = PLATFORMS.filter((p) => p.category === "cookie");
    const existingResults = session?.results || {};

    for (const p of cookiePlatforms) {
      const label = document.createElement("label");
      label.className = "are-checkbox-row";

      const cb = document.createElement("input");
      cb.type = "checkbox";
      cb.value = p.id;
      cb.checked = true;
      if (existingResults[p.id]?.status === "success") {
        label.style.borderColor = "#a6e3a1";
      }

      const text = document.createElement("span");
      text.innerHTML = `${p.icon} ${p.name}`;
      if (existingResults[p.id]?.status === "success") {
        text.innerHTML += ` <span style="color:#a6e3a1">✓</span>`;
      }

      label.appendChild(cb);
      label.appendChild(text);
      checkboxGrid.appendChild(label);
    }
    section.appendChild(checkboxGrid);

    const btnRow = document.createElement("div");
    Object.assign(btnRow.style, { display: "flex", gap: "8px" });

    const startBtn = document.createElement("button");
    startBtn.className = "are-btn are-btn-primary";
    startBtn.style.flex = "1";
    startBtn.textContent = "🚀 开始采集";
    startBtn.addEventListener("click", () => {
      const checked = Array.from(
        checkboxGrid.querySelectorAll("input:checked")
      ).map((cb) => cb.value);
      startCollection(checked);
    });

    const selectAllBtn = document.createElement("button");
    selectAllBtn.className = "are-btn";
    selectAllBtn.textContent = "全选";
    selectAllBtn.addEventListener("click", () => {
      checkboxGrid.querySelectorAll("input").forEach((cb) => (cb.checked = true));
    });

    const selectNoneBtn = document.createElement("button");
    selectNoneBtn.className = "are-btn";
    selectNoneBtn.textContent = "全不选";
    selectNoneBtn.addEventListener("click", () => {
      checkboxGrid.querySelectorAll("input").forEach((cb) => (cb.checked = false));
    });

    btnRow.appendChild(selectAllBtn);
    btnRow.appendChild(selectNoneBtn);
    btnRow.appendChild(startBtn);
    section.appendChild(btnRow);

    return section;
  }

  function renderCookieCard(platform) {
    const card = document.createElement("div");
    card.className = "are-card";

    const row1 = document.createElement("div");
    Object.assign(row1.style, {
      display: "flex",
      justifyContent: "space-between",
      alignItems: "center",
      marginBottom: "8px",
    });

    const nameEl = document.createElement("div");
    nameEl.innerHTML = `<span style="font-size:18px">${platform.icon}</span> <strong style="color:#cdd6f4;font-size:14px">${platform.name}</strong>`;
    const isCurrentSite = getCurrentPlatform()?.id === platform.id;
    if (isCurrentSite) {
      const tag = document.createElement("span");
      tag.textContent = "当前页";
      Object.assign(tag.style, {
        marginLeft: "6px",
        fontSize: "10px",
        color: "#89b4fa",
        background: "rgba(137,180,250,0.15)",
        padding: "1px 6px",
        borderRadius: "4px",
      });
      nameEl.appendChild(tag);
    }

    const badge = document.createElement("span");
    badge.className = "are-badge are-badge-loading";
    badge.textContent = "⏳ 检测中...";
    row1.appendChild(nameEl);
    row1.appendChild(badge);
    card.appendChild(row1);

    const cookieList = document.createElement("div");
    Object.assign(cookieList.style, {
      fontSize: "11px",
      color: "#6c7086",
      marginBottom: "10px",
      fontFamily: "'SF Mono', monospace",
      wordBreak: "break-all",
    });
    cookieList.textContent = "正在读取 cookie...";
    card.appendChild(cookieList);

    const btnRow = document.createElement("div");
    Object.assign(btnRow.style, { display: "flex", gap: "8px" });

    const openBtn = document.createElement("button");
    openBtn.className = "are-btn";
    openBtn.textContent = "🌐 打开网站";
    openBtn.addEventListener("click", () => {
      window.open(platform.loginUrl, "_blank");
    });

    const copyBtn = document.createElement("button");
    copyBtn.className = "are-btn are-btn-primary";
    copyBtn.textContent = "📋 复制 Cookie";
    copyBtn.disabled = true;

    btnRow.appendChild(openBtn);
    btnRow.appendChild(copyBtn);
    card.appendChild(btnRow);

    // 异步填充 cookie 状态
    refreshCookieCard(platform, { cookieList, badge, copyBtn });

    return card;
  }

  /** 异步刷新单个平台卡片的 cookie 状态 */
  async function refreshCookieCard(platform, els) {
    const { cookieList, badge, copyBtn } = els;
    const { cookies, source } = await extractCookiesForPlatform(platform);
    const ready = platform.required.every((name) => cookies[name]);

    // cookie 列表
    const cookieItems = platform.cookies.map((name) => {
      const has = cookies[name];
      const mark = has ? "✓" : "✗";
      const color = has ? "#a6e3a1" : "#f38ba8";
      return `<span style="color:${color}">${mark}</span> ${name}`;
    });
    cookieList.innerHTML = cookieItems.join(" &nbsp; ") +
      `<div style="margin-top:4px;color:#6c7086;font-size:10px">来源: ${source}</div>`;

    // 徽章
    badge.className =
      "are-badge " + (ready ? "are-badge-ready" : "are-badge-pending");
    badge.textContent = ready ? "✅ 已提取" : "⏳ 未提取";

    // 复制按钮
    copyBtn.disabled = !ready;
    if (ready) {
      copyBtn.onclick = async () => {
        const text = formatSingleOutput(platform, cookies);
        try {
          await copyToClipboard(text);
          showCopiedToast(copyBtn);
        } catch (e) {
          showNotification("复制失败：" + e.message, "error");
        }
      };
    }
  }

  function renderApiKeyCard(platform) {
    const card = document.createElement("div");
    card.className = "are-card";

    const row1 = document.createElement("div");
    Object.assign(row1.style, {
      display: "flex",
      justifyContent: "space-between",
      alignItems: "center",
      marginBottom: "8px",
    });
    row1.innerHTML = `<div><span style="font-size:18px">${platform.icon}</span> <strong style="color:#cdd6f4;font-size:14px">${platform.name}</strong></div>`;
    card.appendChild(row1);

    const desc = document.createElement("div");
    desc.textContent = `需要 Groq API Key（${platform.keyPrefix} 开头），免费申请。`;
    Object.assign(desc.style, {
      fontSize: "12px",
      color: "#bac2de",
      marginBottom: "10px",
    });
    card.appendChild(desc);

    const savedKey = GM_getValue("apikey_" + platform.id, "");
    if (savedKey) {
      const keyDisplay = document.createElement("div");
      keyDisplay.textContent = `已保存: ${savedKey.slice(0, 8)}...${savedKey.slice(-4)}`;
      Object.assign(keyDisplay.style, {
        fontSize: "11px",
        color: "#a6e3a1",
        marginBottom: "8px",
        fontFamily: "monospace",
      });
      card.appendChild(keyDisplay);
    }

    const inputRow = document.createElement("div");
    Object.assign(inputRow.style, { display: "flex", gap: "8px", marginBottom: "8px" });

    const input = document.createElement("input");
    input.type = "text";
    input.placeholder = `粘贴 ${platform.keyPrefix} 开头的 Key`;
    input.value = savedKey || "";
    Object.assign(input.style, {
      flex: "1",
      padding: "6px 10px",
      background: "#181825",
      border: "1px solid #313244",
      borderRadius: "8px",
      color: "#cdd6f4",
      fontSize: "12px",
      fontFamily: "monospace",
    });

    const saveBtn = document.createElement("button");
    saveBtn.className = "are-btn";
    saveBtn.textContent = "💾 保存";
    saveBtn.addEventListener("click", () => {
      const val = input.value.trim();
      if (!val) {
        showNotification("请输入 Key", "warn");
        return;
      }
      if (!val.startsWith(platform.keyPrefix)) {
        showNotification(`Key 应以 ${platform.keyPrefix} 开头`, "warn");
        return;
      }
      GM_setValue("apikey_" + platform.id, val);
      showNotification("已保存 Groq API Key", "success");
      refreshPanel();
    });

    inputRow.appendChild(input);
    inputRow.appendChild(saveBtn);
    card.appendChild(inputRow);

    const applyBtn = document.createElement("button");
    applyBtn.className = "are-btn";
    applyBtn.textContent = "🌐 前往申请";
    applyBtn.addEventListener("click", () => {
      window.open(platform.applyUrl, "_blank");
    });
    card.appendChild(applyBtn);

    return card;
  }

  function renderInfoCard(platform) {
    const card = document.createElement("div");
    card.className = "are-card";
    Object.assign(card.style, { background: "#181825", opacity: "0.85" });

    const row1 = document.createElement("div");
    Object.assign(row1.style, { marginBottom: "8px" });
    row1.innerHTML = `<span style="font-size:18px">${platform.icon}</span> <strong style="color:#a6adc8;font-size:14px">${platform.name}</strong>`;
    card.appendChild(row1);

    const list = document.createElement("div");
    Object.assign(list.style, {
      fontSize: "12px",
      color: "#6c7086",
      lineHeight: "1.8",
    });
    list.innerHTML = platform.platforms
      .map((p) => `<span style="color:#a6e3a1">✓</span> ${p}`)
      .join("<br>");
    card.appendChild(list);

    const note = document.createElement("div");
    note.textContent = "这些平台 Agent Reach 自带支持，无需提取任何凭证。";
    Object.assign(note.style, {
      marginTop: "8px",
      fontSize: "11px",
      color: "#6c7086",
      fontStyle: "italic",
    });
    card.appendChild(note);

    return card;
  }

  // ════════════════════════════════════════════════════════════
  // 11. 初始化
  // ════════════════════════════════════════════════════════════

  function init() {
    injectStyles();
    createFAB();
    createPanel();

    const session = getSession();

    if (session && session.status === "collecting") {
      const platformId = session.queue[session.currentIndex];
      const platform = findPlatformById(platformId);

      if (platform && isCurrentDomain(platform)) {
        showCollectingBar();
        setTimeout(tryCollectCurrent, 2500);
      } else {
        showCollectingBar(
          `请手动导航到 ${platform ? platform.name : "目标网站"}，或点"重试"自动跳转`,
          "warn"
        );
      }
    } else if (getCurrentPlatform()) {
      autoExtractOnLoad();
    }

    // SPA 路由变化
    let lastPath = location.pathname;
    const observer = new MutationObserver(() => {
      if (location.pathname !== lastPath) {
        lastPath = location.pathname;
        const panel = document.getElementById("are-panel");
        if (panel && panel.style.display !== "none") {
          setTimeout(refreshPanel, 800);
        }
        if (isCollecting()) {
          setTimeout(tryCollectCurrent, 2000);
        } else if (getCurrentPlatform()) {
          setTimeout(autoExtractOnLoad, 2000);
        }
      }
    });
    observer.observe(document.body, { childList: true, subtree: true });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
