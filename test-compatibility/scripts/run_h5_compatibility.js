const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');

const repoRoot = path.resolve(__dirname, '..', '..');
const sourceRoot = path.resolve(process.env.LITEMALL_SOURCE_ROOT || repoRoot);
const WebSocket = require(path.join(sourceRoot, 'litemall-vue', 'node_modules', 'ws'));
const configPath = path.join(repoRoot, 'test-automation', 'test_config.local.json');
const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
const outputDir = path.join(repoRoot, 'test-compatibility', 'results', `h5-${timestamp}`);

const baseUrl = 'http://127.0.0.1:6255';
const browsers = [
  {
    name: 'Chrome',
    executable: 'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
    port: 9331,
  },
  {
    name: 'Edge',
    executable: 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
    port: 9332,
  },
];

const viewports = [
  { name: 'desktop-1440x900', width: 1440, height: 900, mobile: false, deviceScaleFactor: 1 },
  { name: 'mobile-390x844', width: 390, height: 844, mobile: true, deviceScaleFactor: 1 },
];

const routes = [
  { name: 'home', hash: '/' },
  { name: 'catalog', hash: '/items' },
  { name: 'search', hash: '/items/search' },
  { name: 'goods-detail', hash: '/items/detail/1110017' },
  { name: 'login', hash: '/login' },
  { name: 'orders', hash: '/order' },
  { name: 'user-center', hash: '/user' },
];

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function ensureFile(filePath, label) {
  if (!fs.existsSync(filePath)) {
    throw new Error(`${label}不存在: ${filePath}`);
  }
}

async function waitForJson(url, timeoutMs = 15000) {
  const start = Date.now();
  let lastError;
  while (Date.now() - start < timeoutMs) {
    try {
      const response = await fetch(url);
      if (response.ok) return response.json();
    } catch (error) {
      lastError = error;
    }
    await delay(250);
  }
  throw new Error(`等待浏览器调试端口超时: ${url}; ${lastError || ''}`);
}

class CdpClient {
  constructor(socketUrl) {
    this.socket = new WebSocket(socketUrl);
    this.nextId = 1;
    this.pending = new Map();
    this.listeners = new Map();
  }

  async open() {
    if (this.socket.readyState === WebSocket.OPEN) return;
    if (this.socket.readyState === WebSocket.CLOSING || this.socket.readyState === WebSocket.CLOSED) {
      throw new Error('CDP WebSocket 已关闭');
    }
    await new Promise((resolve, reject) => {
      this.socket.once('open', resolve);
      this.socket.once('error', reject);
      this.socket.once('close', () => reject(new Error('CDP WebSocket 在建立连接前已关闭')));
    });
    this.socket.on('message', (raw) => {
      const message = JSON.parse(raw.toString());
      if (message.id && this.pending.has(message.id)) {
        const { resolve, reject } = this.pending.get(message.id);
        this.pending.delete(message.id);
        if (message.error) reject(new Error(JSON.stringify(message.error)));
        else resolve(message.result || {});
        return;
      }
      if (message.method && this.listeners.has(message.method)) {
        for (const listener of this.listeners.get(message.method)) listener(message.params || {});
      }
    });
  }

  send(method, params = {}) {
    const id = this.nextId++;
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      this.socket.send(JSON.stringify({ id, method, params }));
    });
  }

  on(method, listener) {
    if (!this.listeners.has(method)) this.listeners.set(method, new Set());
    this.listeners.get(method).add(listener);
    return () => this.listeners.get(method).delete(listener);
  }

  waitFor(method, timeoutMs = 15000) {
    return new Promise((resolve, reject) => {
      const cleanup = this.on(method, (params) => {
        clearTimeout(timer);
        cleanup();
        resolve(params);
      });
      const timer = setTimeout(() => {
        cleanup();
        reject(new Error(`等待 CDP 事件超时: ${method}`));
      }, timeoutMs);
    });
  }

  close() {
    this.socket.close();
  }
}

async function login() {
  ensureFile(configPath, '本机测试配置');
  const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
  const endpoint = `${config.base_url.replace(/\/$/, '')}/wx/auth/login`;
  const response = await fetch(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      username: config.test_user.username,
      password: config.test_user.password,
    }),
  });
  const payload = await response.json();
  if (!response.ok || payload.errno !== 0 || !payload.data || !payload.data.token) {
    throw new Error(`测试账号登录失败: HTTP ${response.status}, errno=${payload.errno}`);
  }
  return {
    token: payload.data.token,
    nickname: payload.data.userInfo && payload.data.userInfo.nickName,
    avatar: payload.data.userInfo && payload.data.userInfo.avatarUrl,
  };
}

async function launchBrowser(browser, profileDir) {
  ensureFile(browser.executable, browser.name);
  fs.mkdirSync(profileDir, { recursive: true });
  const child = spawn(browser.executable, [
    '--headless=new',
    `--remote-debugging-port=${browser.port}`,
    `--user-data-dir=${profileDir}`,
    '--no-first-run',
    '--no-default-browser-check',
    '--disable-background-networking',
    '--disable-component-update',
    '--disable-features=Translate',
    '--hide-scrollbars',
    'about:blank',
  ], { stdio: ['ignore', 'ignore', 'pipe'], windowsHide: true });

  let stderr = '';
  child.stderr.on('data', (chunk) => {
    stderr += chunk.toString();
  });

  try {
    const targets = await waitForJson(`http://127.0.0.1:${browser.port}/json/list`);
    const page = targets.find((target) => target.type === 'page');
    if (!page || !page.webSocketDebuggerUrl) throw new Error('未找到浏览器页面调试目标');
    return { child, socketUrl: page.webSocketDebuggerUrl, stderr: () => stderr };
  } catch (error) {
    child.kill();
    throw new Error(`${browser.name} 启动失败: ${error.message}; ${stderr.slice(-1000)}`);
  }
}

async function navigate(cdp, url) {
  await cdp.send('Page.navigate', { url });
  const start = Date.now();
  while (Date.now() - start < 20000) {
    const state = await evaluate(cdp, `({ readyState: document.readyState, url: location.href })`);
    if (state.readyState === 'complete' && state.url === url) break;
    await delay(200);
  }
  await delay(2500);
}

async function evaluate(cdp, expression) {
  const result = await cdp.send('Runtime.evaluate', {
    expression,
    returnByValue: true,
    awaitPromise: true,
  });
  if (result.exceptionDetails) throw new Error(result.exceptionDetails.text || '页面脚本执行失败');
  return result.result ? result.result.value : undefined;
}

async function executeProfile(browser, viewport, auth) {
  const profileName = `${browser.name.toLowerCase()}-${viewport.name}`;
  const profileDir = path.join(outputDir, '_profiles', profileName);
  const launch = await launchBrowser(browser, profileDir);
  const cdp = new CdpClient(launch.socketUrl);
  const runtimeErrors = [];
  const consoleErrors = [];
  const httpErrors = [];
  const loadingFailures = [];

  try {
    await cdp.open();
    await Promise.all([
      cdp.send('Page.enable'),
      cdp.send('Runtime.enable'),
      cdp.send('Network.enable'),
      cdp.send('Log.enable'),
    ]);

    cdp.on('Runtime.exceptionThrown', ({ exceptionDetails }) => {
      runtimeErrors.push(exceptionDetails.text || exceptionDetails.exception?.description || 'unknown exception');
    });
    cdp.on('Log.entryAdded', ({ entry }) => {
      if (entry.level === 'error') consoleErrors.push(`${entry.source}: ${entry.text}`);
    });
    cdp.on('Network.responseReceived', ({ response }) => {
      if (response.status >= 400) httpErrors.push(`${response.status} ${response.url}`);
    });
    cdp.on('Network.loadingFailed', ({ errorText, canceled, type }) => {
      if (!canceled && errorText !== 'net::ERR_ABORTED') loadingFailures.push(`${type}: ${errorText}`);
    });

    await cdp.send('Emulation.setDeviceMetricsOverride', {
      width: viewport.width,
      height: viewport.height,
      deviceScaleFactor: viewport.deviceScaleFactor,
      mobile: viewport.mobile,
      screenWidth: viewport.width,
      screenHeight: viewport.height,
    });

    await navigate(cdp, `${baseUrl}/#/`);
    await evaluate(cdp, `(() => {
      localStorage.setItem('Authorization', ${JSON.stringify(auth.token)});
      localStorage.setItem('nickName', ${JSON.stringify(auth.nickname || '')});
      localStorage.setItem('avatar', ${JSON.stringify(auth.avatar || '')});
      return true;
    })()`);

    const results = [];
    for (const route of routes) {
      runtimeErrors.length = 0;
      consoleErrors.length = 0;
      httpErrors.length = 0;
      loadingFailures.length = 0;

      const url = `${baseUrl}/#${route.hash}`;
      await navigate(cdp, url);
      const inspection = await evaluate(cdp, `(() => {
        const brokenImages = [...document.images]
          .filter((image) => image.complete && image.naturalWidth === 0)
          .map((image) => image.currentSrc || image.src || image.alt || '(unknown)');
        const root = document.documentElement;
        const bodyText = (document.body && document.body.innerText || '').trim();
        return {
          title: document.title,
          currentUrl: location.href,
          bodyTextLength: bodyText.length,
          bodyPreview: bodyText.slice(0, 160),
          viewportWidth: innerWidth,
          documentWidth: root.scrollWidth,
          horizontalOverflow: root.scrollWidth > innerWidth + 1,
          brokenImages,
        };
      })()`);

      const screenshot = await cdp.send('Page.captureScreenshot', {
        format: 'png',
        fromSurface: true,
        captureBeyondViewport: false,
      });
      const screenshotName = `${profileName}-${route.name}.png`;
      fs.writeFileSync(path.join(outputDir, screenshotName), Buffer.from(screenshot.data, 'base64'));

      const failures = [];
      if (inspection.bodyTextLength < 10) failures.push('页面正文为空或过短');
      if (inspection.horizontalOverflow) failures.push(`页面横向溢出: ${inspection.documentWidth}px > ${inspection.viewportWidth}px`);
      if (inspection.brokenImages.length) failures.push(`存在 ${inspection.brokenImages.length} 张破图`);
      if (runtimeErrors.length) failures.push(`存在 ${runtimeErrors.length} 个运行时异常`);
      if (httpErrors.length) failures.push(`存在 ${httpErrors.length} 个 HTTP 4xx/5xx 请求`);
      if (loadingFailures.length) failures.push(`存在 ${loadingFailures.length} 个资源加载失败`);

      results.push({
        browser: browser.name,
        browserVersion: fs.statSync(browser.executable) && require('child_process').execFileSync(
          'powershell.exe',
          ['-NoProfile', '-Command', `(Get-Item -LiteralPath '${browser.executable.replace(/'/g, "''")}').VersionInfo.ProductVersion`],
          { encoding: 'utf8', windowsHide: true },
        ).trim(),
        viewport: viewport.name,
        route: route.name,
        url,
        status: failures.length ? 'FAIL' : 'PASS',
        failures,
        inspection,
        runtimeErrors: [...runtimeErrors],
        consoleErrors: [...consoleErrors],
        httpErrors: [...httpErrors],
        loadingFailures: [...loadingFailures],
        screenshot: screenshotName,
      });
    }
    return results;
  } finally {
    cdp.close();
    launch.child.kill();
    await delay(500);
  }
}

function writeMarkdown(results) {
  const passed = results.filter((item) => item.status === 'PASS').length;
  const failed = results.length - passed;
  const lines = [
    '# Litemall H5 兼容性测试执行报告',
    '',
    `- 执行时间：${new Date().toLocaleString('zh-CN', { hour12: false })}`,
    `- 被测地址：${baseUrl}`,
    `- 执行组合：Chrome / Edge × 桌面 1440×900 / 移动 390×844`,
    `- 检查页面：首页、分类、搜索、商品详情、登录、订单、个人中心`,
    `- 结果：共 ${results.length} 项，PASS ${passed}，FAIL ${failed}`,
    '',
    '| 浏览器 | 版本 | 视口 | 页面 | 结果 | 主要问题 | 截图 |',
    '| --- | --- | --- | --- | --- | --- | --- |',
  ];

  for (const item of results) {
    lines.push(`| ${item.browser} | ${item.browserVersion} | ${item.viewport} | ${item.route} | ${item.status} | ${item.failures.join('；') || '-'} | [查看](${item.screenshot}) |`);
  }

  lines.push('', '## 判定口径', '',
    '- 页面正文成功渲染；',
    '- 页面没有全局横向溢出；',
    '- 页面不存在已完成加载但尺寸为 0 的破图；',
    '- 页面没有 JavaScript 运行时异常；',
    '- 页面请求没有 HTTP 4xx/5xx；',
    '- 页面关键资源没有非主动取消的加载失败。',
    '',
    '控制台普通错误单独记录在 JSON 明细中，避免第三方组件提示被误判为兼容性缺陷。',
  );
  fs.writeFileSync(path.join(outputDir, 'report.md'), `${lines.join('\n')}\n`, 'utf8');
}

async function main() {
  fs.mkdirSync(outputDir, { recursive: true });
  const auth = await login();
  const allResults = [];

  for (const browser of browsers) {
    for (const viewport of viewports) {
      process.stdout.write(`执行 ${browser.name} / ${viewport.name} ... `);
      const results = await executeProfile(browser, viewport, auth);
      allResults.push(...results);
      console.log(`${results.filter((item) => item.status === 'PASS').length}/${results.length} PASS`);
    }
  }

  fs.rmSync(path.join(outputDir, '_profiles'), { recursive: true, force: true });
  fs.writeFileSync(path.join(outputDir, 'results.json'), JSON.stringify(allResults, null, 2), 'utf8');
  writeMarkdown(allResults);
  const failed = allResults.filter((item) => item.status === 'FAIL');
  console.log(`RESULT_DIR=${outputDir}`);
  console.log(`TOTAL=${allResults.length} PASS=${allResults.length - failed.length} FAIL=${failed.length}`);
  if (failed.length) process.exitCode = 2;
}

main().catch((error) => {
  console.error(error.stack || error.message);
  process.exitCode = 1;
});
