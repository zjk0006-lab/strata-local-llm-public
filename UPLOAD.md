# 上传到 GitHub 的操作指引（在另一台可联网电脑上做）

本目录是**已脱敏的公开版**。带到一个能访问 GitHub 的电脑，按下面顺序做即可。

## 0. 上游数据（已用动态徽章，无需手填）
README 顶部的 star / license / release 徽章由 shields.io 动态生成，
在 GitHub 上由**访问者的浏览器**加载——本机不需要能连 GitHub，也不用手填数字。

若你想改成纯文本数字（例如徽章被广告拦截器挡掉），在能联网的机器上跑：
```bash
python scripts/fetch_upstream_stats.py
```
把输出替换掉那三行徽章即可。

## 1. 确认脱敏干净
本目录生成时已通过自动残留扫描（0 泄漏）。这里做**二次人工确认**：
```bash
# 把下面模式换成"你自己的"隐私关键词：用户名、城市、单位名、机器品牌、代理端口等
grep -rniE "你的用户名|你的城市|你的单位|你的磁盘品牌" . --include=*.md --include=*.py
```
应无输出。有输出就改掉再重新走一遍生成流程（别手改公开版，改源模板更可靠）。

## 2. 检查截图里没有隐私
`img/` 下 5 张截图来自本机运行。已确认第 5 张（agent 界面）的用户名区域被涂抹遮挡。
请再肉眼过一遍：任务管理器截图不含账号信息；Monitor 截图不含路径/密钥。

## 3. 初始化仓库并本地提交（先不 push）
```bash
cd strata-local-llm-public
git init
git add -A
git status                 # 逐条看，确认没有权重/引擎/wheel/日志/多余文件
git commit -m "Strata local LLM: Windows deployment notes, benchmarks and helper scripts"
git log --stat             # 通读一遍提交内容
```
> GitHub 历史很难彻底清除，**第一次就要干净**。`.gitignore` 已排除权重/二进制/wheel/日志。

## 4. 设置身份（用你想公开的身份，别用真实姓名/邮箱）
```bash
git config user.name  "你的GitHub用户名"
git config user.email "你的GitHub用户名@users.noreply.github.com"
```
> 用 `@users.noreply.github.com` 可避免暴露真实邮箱。
> 同时把 `LICENSE` 里的版权行 `strata-local-llm contributors` 换成同一身份。

## 5. 在 GitHub 建空仓库后推送
GitHub 网页新建一个**空仓库**（不要勾选自动加 README/License），然后：
```bash
git branch -M main
git remote add origin https://github.com/<你的用户名>/<仓库名>.git
git push -u origin main
```

## 6. push 后自查
打开仓库网页，确认：5 张图正常显示、README 排版正确、star 占位已替换、
没有意外文件（权重/二进制）。如需删除误传内容，光删文件不够——要用 git filter-repo 清历史并强推，
或直接删仓库重建。所以第 3 步的 `git status` 一定要看。
