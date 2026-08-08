"""使用项目现有 Qwen 配置生成并发布高质量面经。

特点：
- 12 个岗位方向，每个方向 5 篇，共 60 篇；
- 每篇必须包含完整流程、项目背景、逐题问答、追问、技术细节、复盘和准备建议；
- 标题和正文明确标注“AI 生成案例”，不伪装成真实个人爆料；
- 结果写入 scripts/codepus-agent/generated_experiences.json，可断点续跑；
- 使用客户端游客账号投稿，再使用后台管理员审核发布。
"""
from __future__ import annotations

import json
import os
import re
import ssl
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = ROOT / "ai-interview-backend" / ".env"
OUTPUT_PATH = ROOT / "scripts" / "codepus-agent" / "generated_experiences.json"
BASE_URL = os.environ.get("EXPERIENCE_BASE_URL", "https://zhangzhengqiang.xyz")
MAX_RETRIES = 3

DIRECTIONS = [
    ("Java 后端", "字节跳动", "Java 后端开发工程师", ["Java", "Spring", "MySQL", "Redis", "分布式"]),
    ("Go 微服务", "美团", "Go 后端开发工程师", ["Go", "微服务", "RPC", "Kafka", "高并发"]),
    ("Python 后端与 AI 应用", "阿里云", "Python 后端工程师", ["Python", "FastAPI", "RAG", "Agent", "异步编程"]),
    ("C++ 基础架构", "腾讯", "C++ 基础架构工程师", ["C++", "操作系统", "网络", "性能优化", "多线程"]),
    ("前端 Vue 工程化", "字节跳动", "前端开发工程师", ["Vue 3", "TypeScript", "Vite", "性能优化", "工程化"]),
    ("前端 React 全栈", "阿里巴巴", "React 全栈工程师", ["React", "Next.js", "Node.js", "SSR", "前端安全"]),
    ("机器学习算法", "快手", "机器学习算法工程师", ["机器学习", "特征工程", "模型评估", "训练优化", "在线服务"]),
    ("大模型算法与 RAG", "百度", "大模型算法工程师", ["Transformer", "RAG", "Embedding", "Rerank", "评测"]),
    ("AI Agent 应用", "商汤科技", "AI 应用工程师", ["Agent", "Tool Calling", "LangGraph", "记忆", "安全"]),
    ("数据分析与增长", "携程", "数据分析师", ["SQL", "指标体系", "A/B 实验", "漏斗分析", "增长"]),
    ("测试开发与质量", "京东", "测试开发工程师", ["自动化测试", "接口测试", "质量体系", "性能测试", "CI/CD"]),
    ("SRE 云原生运维", "华为云", "SRE 工程师", ["Kubernetes", "Docker", "可观测性", "容量规划", "故障演练"]),
]


def load_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values.setdefault(key.strip(), value.strip().strip('"').strip("'"))
    return values


ENV = load_env(ENV_PATH)
AI_KEY = os.environ.get("AI_API_KEY") or ENV.get("AI_API_KEY", "")
AI_BASE_URL = os.environ.get("AI_BASE_URL") or ENV.get("AI_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
AI_MODEL = os.environ.get("AI_MODEL") or ENV.get("AI_MODEL", "qwen-plus")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL") or ENV.get("ADMIN_EMAIL", "")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")


def request_json(method: str, url: str, payload: dict | None = None, token: str | None = None, api_key: str | None = None) -> dict:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    last_error: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            req = urllib.request.Request(url, data=body, headers=headers, method=method)
            context = ssl.create_default_context()
            with urllib.request.urlopen(req, context=context, timeout=90) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            return {"code": exc.code, "message": detail[:500]}
        except Exception as exc:
            last_error = exc
            if attempt < MAX_RETRIES:
                time.sleep(attempt * 2)
    return {"code": 0, "message": str(last_error)}


def prompt_for(direction: tuple[str, str, str, list[str]], index: int) -> str:
    category, company, position, tags = direction
    level = ["实习", "校招", "1-3年社招", "3-5年社招", "高级岗位"][index]
    round_name = ["一面", "二面", "三面/架构面", "综合面", "终面复盘"][index]
    return f"""你是资深面试内容编辑。请为“{category}”岗位生成一篇高质量、可学习的 AI 生成面经案例。

硬约束：
1. 这是一篇“AI 生成案例”，不要声称来自真实候选人，不要捏造具体真实个人、薪资、内部机密或“我拿到 offer”等事实。
2. 公司场景可作为练习背景：{company}；岗位：{position}；经验层级：{level}；重点轮次：{round_name}。
3. 正文不少于 3500 个中文字符，必须具体，禁止“考察了基础知识”“做好准备即可”这类空话。
4. 必须包含以下 Markdown 标题，且每节有实质内容：
   - ## 案例说明（明确 AI 生成案例、适用人群和阅读方式）
   - ## 岗位与项目背景（业务目标、规模、技术约束、候选人职责）
   - ## 完整面试流程（至少 4 个环节、时长、淘汰点和评价维度）
   - ## 自我介绍与项目深挖（给出可复用表达结构和至少 3 个追问）
   - ## 技术面真题与参考作答（至少 8 题；每题包含题目、考察点、分层答案、追问及追问答案）
   - ## 系统设计/场景题（需求澄清、容量估算、架构、数据模型、稳定性、监控、取舍）
   - ## 手写代码或 SQL 题（题意、思路、边界、复杂度、测试用例；数据岗位至少包含 SQL）
   - ## 失败回答与改进方式（至少 5 个常见失分点）
   - ## 面试复盘（知识缺口、沟通表现、时间管理、下一轮行动）
   - ## 准备清单（按 1 天、1 周、1 个月拆分）
5. 技术内容必须结合这些关键词并解释取舍：{', '.join(tags)}。
6. 参考答案要体现“先结论、再原理、再项目例子、最后边界”的结构；不要只列概念。
7. 不要使用表格承载大段答案；可以使用列表、代码块和小标题。

只输出完整 Markdown 正文，不要输出前言、JSON 或文章标题之外的说明。"""


def generate_one(direction: tuple[str, str, str, list[str]], index: int) -> dict:
    category, company, position, tags = direction
    payload = {
        "model": AI_MODEL,
        "messages": [
            {"role": "system", "content": "你负责生成结构严谨、技术准确、可执行的中文面试学习内容。"},
            {"role": "user", "content": prompt_for(direction, index)},
        ],
        "temperature": 0.7,
        "max_tokens": 7000,
    }
    result = request_json("POST", f"{AI_BASE_URL.rstrip('/')}/chat/completions", payload, api_key=AI_KEY)
    if result.get("error"):
        raise RuntimeError(str(result["error"]))
    try:
        content = result["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"AI 返回格式异常: {result}") from exc
    required = ["## 案例说明", "## 岗位与项目背景", "## 完整面试流程", "## 技术面真题与参考作答", "## 系统设计/场景题", "## 面试复盘", "## 准备清单"]
    missing = [heading for heading in required if heading not in content]
    if len(content) < 3500 or missing:
        raise ValueError(f"内容未通过质量门禁: chars={len(content)}, missing={missing}")
    title = f"{company}{position}深度面经（AI生成案例·第{index + 1}篇）"
    return {
        "title": title,
        "company": company,
        "position": position,
        "level": ["实习", "校招", "1-3年", "3-5年", "5年+"][index],
        "round": ["一面", "二面", "三面", "综合面", "终面"][index],
        "summary": f"{category}岗位的 AI 生成深度面经，覆盖完整流程、项目深挖、技术追问、系统设计、代码题和复盘。正文约 {len(content)} 字，适合系统准备。",
        "tags": ["AI生成案例", "深度面经", category, *tags[:3]],
        "content": f"# {title}\n\n{content}",
        "is_anonymous": True,
    }


def save(items: list[dict]) -> None:
    OUTPUT_PATH.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


def load_items() -> list[dict]:
    if OUTPUT_PATH.exists():
        return json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
    return []


def get_client_token() -> str:
    result = request_json("POST", f"{BASE_URL}/api/v1/auth/guest", {})
    if result.get("code") != 200:
        raise RuntimeError(f"游客登录失败: {result}")
    return result["data"]["access_token"]


def get_admin_token() -> str:
    if not ADMIN_EMAIL or not ADMIN_PASSWORD:
        raise RuntimeError("缺少 ADMIN_EMAIL 或 ADMIN_PASSWORD 环境变量，无法执行审核发布")
    result = request_json("POST", f"{BASE_URL}/api/v1/backoffice/auth/login", {"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    if result.get("code") != 200:
        raise RuntimeError(f"管理员登录失败: {result}")
    return result["data"]["access_token"]


def publish_items(items: list[dict]) -> None:
    client_token = get_client_token()
    admin_token = get_admin_token()
    published = 0
    for item in items:
        marker = item["title"]
        result = request_json("POST", f"{BASE_URL}/api/v1/experiences/submit", item, client_token)
        if result.get("code") != 200:
            if "已存在" not in str(result):
                raise RuntimeError(f"投稿失败 {marker}: {result}")
            continue
        experience_id = result.get("data", {}).get("id")
        if not experience_id:
            raise RuntimeError(f"投稿未返回 id: {result}")
        review = request_json("PUT", f"{BASE_URL}/api/v1/backoffice/experiences/{experience_id}/review?action=approve", token=admin_token)
        if review.get("code") != 200:
            raise RuntimeError(f"审核失败 id={experience_id}: {review}")
        published += 1
        print(f"[发布 {published}/{len(items)}] id={experience_id} {marker}")
        time.sleep(0.3)


def main() -> None:
    if not AI_KEY:
        raise SystemExit("缺少 AI_API_KEY：请在 ai-interview-backend/.env 或环境变量中配置")
    os.environ.setdefault("AI_API_KEY", AI_KEY)
    items = load_items()
    existing_titles = {item["title"] for item in items}
    for direction in DIRECTIONS:
        for index in range(5):
            expected_prefix = f"{direction[1]}{direction[2]}深度面经（AI生成案例·第{index + 1}篇）"
            if expected_prefix in existing_titles:
                print(f"[跳过已生成] {expected_prefix}")
                continue
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    item = generate_one(direction, index)
                    items.append(item)
                    save(items)
                    print(f"[生成 {len(items)}/60] {item['title']} chars={len(item['content'])}")
                    break
                except Exception as exc:
                    print(f"[生成失败 {attempt}/{MAX_RETRIES}] {direction[0]} #{index + 1}: {exc}")
                    if attempt == MAX_RETRIES:
                        save(items)
                        raise
                    time.sleep(attempt * 3)
    save(items)
    if len(items) != 60:
        raise RuntimeError(f"生成数量异常: {len(items)}，未执行发布")
    publish_items(items)


if __name__ == "__main__":
    main()
