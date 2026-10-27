const fs = require('fs');
const path = require('path');

const repoRoot = path.resolve(__dirname, '..', '..');
const sourceRoot = path.resolve(process.env.LITEMALL_SOURCE_ROOT || repoRoot);
const projectRoot = path.join(sourceRoot, 'litemall-wx');
const outputRoot = path.join(repoRoot, 'test-compatibility', 'results', 'miniprogram-static');

function readJson(relativePath) {
  const filePath = path.join(projectRoot, relativePath);
  return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

function walk(directory, files = []) {
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    const fullPath = path.join(directory, entry.name);
    if (entry.isDirectory()) walk(fullPath, files);
    else files.push(fullPath);
  }
  return files;
}

function relative(filePath) {
  return path.relative(projectRoot, filePath).replace(/\\/g, '/');
}

const app = readJson('app.json');
const project = readJson('project.config.json');
const findings = [];
const checks = [];

function check(name, passed, detail) {
  checks.push({ name, status: passed ? 'PASS' : 'FAIL', detail });
}

for (const page of app.pages) {
  const missing = ['js', 'json', 'wxml', 'wxss']
    .map((extension) => `${page}.${extension}`)
    .filter((file) => !fs.existsSync(path.join(projectRoot, file)));
  check(`页面四件套: ${page}`, missing.length === 0, missing.length ? `缺少 ${missing.join(', ')}` : '文件齐全');
}

for (const item of app.tabBar.list) {
  const declared = app.pages.includes(item.pagePath);
  const icons = [item.iconPath, item.selectedIconPath].filter((file) => !fs.existsSync(path.join(projectRoot, file)));
  check(`TabBar: ${item.text}`, declared && icons.length === 0,
    !declared ? `页面未在 app.json 注册: ${item.pagePath}` : icons.length ? `图标不存在: ${icons.join(', ')}` : '路由和图标有效');
}

const jsonFiles = walk(projectRoot).filter((file) => file.endsWith('.json'));
for (const file of jsonFiles) {
  try {
    JSON.parse(fs.readFileSync(file, 'utf8'));
    check(`JSON: ${relative(file)}`, true, '语法有效');
  } catch (error) {
    check(`JSON: ${relative(file)}`, false, error.message);
  }
}

const apiFile = fs.readFileSync(path.join(projectRoot, 'config', 'api.js'), 'utf8');
const localApi = apiFile.match(/var\s+WxApiRoot\s*=\s*['"]([^'"]+)['"]/);
check('本地接口配置', Boolean(localApi), localApi ? localApi[1] : '未识别 WxApiRoot');

if (localApi && /^http:\/\/(127\.0\.0\.1|localhost)/.test(localApi[1])) {
  findings.push({
    level: 'INFO',
    item: '真机访问限制',
    detail: `${localApi[1]} 只适用于开发者工具；真机中的 127.0.0.1 指向手机本身，真机测试需改为电脑局域网 IP 或测试环境 HTTPS 域名。`,
  });
}

if (project.libVersion === '2.4.0') {
  findings.push({
    level: 'RISK',
    item: '基础库版本',
    detail: 'project.config.json 固定为 2.4.0，版本较旧。运行态应至少覆盖项目版本 2.4.0 与开发者工具当前稳定基础库。',
  });
}

if (app.debug === true) {
  findings.push({
    level: 'INFO',
    item: '调试模式',
    detail: 'app.json 的 debug=true 适用于测试环境；发布构建前应关闭，避免保留额外调试信息。',
  });
}

const jsFiles = walk(projectRoot).filter((file) => file.endsWith('.js'));
const apiUsage = new Map();
for (const file of jsFiles) {
  const content = fs.readFileSync(file, 'utf8');
  for (const match of content.matchAll(/\bwx\.([A-Za-z_$][\w$]*)/g)) {
    const api = `wx.${match[1]}`;
    if (!apiUsage.has(api)) apiUsage.set(api, new Set());
    apiUsage.get(api).add(relative(file));
  }
}

for (const api of ['wx.getSystemInfo', 'wx.chooseImage']) {
  if (apiUsage.has(api)) {
    findings.push({
      level: 'RISK',
      item: `兼容性敏感 API: ${api}`,
      detail: `使用位置：${[...apiUsage.get(api)].join(', ')}。应在新基础库和目标机型上回归，并关注开发者工具的废弃提示。`,
    });
  }
}

fs.mkdirSync(outputRoot, { recursive: true });
const passed = checks.filter((item) => item.status === 'PASS').length;
const failed = checks.length - passed;
const report = [
  '# Litemall 微信小程序静态兼容性预检报告',
  '',
  `- 开发者工具版本：2.02.2608070`,
  `- 项目基础库版本：${project.libVersion}`,
  `- 页面数量：${app.pages.length}`,
  `- JSON 文件数量：${jsonFiles.length}`,
  `- 检查项：${checks.length}，PASS ${passed}，FAIL ${failed}`,
  '',
  '## 风险与运行态关注点',
  '',
  '| 等级 | 项目 | 说明 |',
  '| --- | --- | --- |',
  ...findings.map((item) => `| ${item.level} | ${item.item} | ${item.detail} |`),
  '',
  '## 静态检查明细',
  '',
  '| 检查项 | 结果 | 说明 |',
  '| --- | --- | --- |',
  ...checks.map((item) => `| ${item.name} | ${item.status} | ${item.detail} |`),
  '',
  '## 边界说明',
  '',
  '静态预检只能证明工程文件、路由和配置结构完整，不能替代开发者工具模拟器与真机运行测试。',
  '完成运行态兼容性测试前，不应把本报告描述为“小程序兼容性全部通过”。',
  '',
].join('\n');

fs.writeFileSync(path.join(outputRoot, 'report.md'), report, 'utf8');
fs.writeFileSync(path.join(outputRoot, 'results.json'), JSON.stringify({ checks, findings, apiUsage: Object.fromEntries([...apiUsage].map(([key, value]) => [key, [...value]])) }, null, 2), 'utf8');

console.log(`RESULT_DIR=${outputRoot}`);
console.log(`PAGES=${app.pages.length} CHECKS=${checks.length} PASS=${passed} FAIL=${failed} FINDINGS=${findings.length}`);
if (failed) process.exitCode = 2;
