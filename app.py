import os

# --- 强制清除代理配置 (解决 socks4 报错) ---
# DeepSeek 在国内无需代理，清除环境变量防止 httpx 库读取错误的代理设置
os.environ.pop("HTTP_PROXY", None)
os.environ.pop("HTTPS_PROXY", None)
os.environ.pop("ALL_PROXY", None)
os.environ.pop("http_proxy", None)
os.environ.pop("https_proxy", None)
# ----------------------------------------

import streamlit as st
import time
from openai import OpenAI

st.set_page_config(page_title="简历经历修改器", layout="wide", initial_sidebar_state="auto")

# --- 状态管理 ---
if "generated_result" not in st.session_state:
    st.session_state.generated_result = None
if "show_thought" not in st.session_state:
    st.session_state.show_thought = False

# --- 注入自定义 CSS (纯净修复版) ---
st.markdown("""
<style>
    /* 1. 修复 Toggle 开关文字换行 (保留此功能) */
    div[data-testid="stWidgetLabel"] p,
    div[data-testid="stCheckbox"] label p {
        white-space: nowrap !important;
        font-size: 14px !important;
    }

    /* 2. iOS 风格卡片 (保留此样式) */
    .ios-card {
        background-color: #ffffff;
        border: 1px solid #e5e5ea;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    
    /* 深色模式适配 */
    @media (prefers-color-scheme: dark) {
        .ios-card {
            background-color: #1c1c1e;
            border-color: #2c2c2e;
            color: #ffffff;
        }
    }
</style>
""", unsafe_allow_html=True)

# --- 读取 API Key & 初始化 Client ---
try:
    api_key = st.secrets["DEEPSEEK_API_KEY"]
except (KeyError, FileNotFoundError):
    st.error("⚠️ 只有房主（开发者）才能配置 API Key 哦！请在 Secrets 中添加。")
    st.stop()

client = OpenAI(
    api_key=api_key,
    base_url="https://api.deepseek.com"
)

# 侧边栏内容
with st.sidebar:
    st.markdown("### 💡 关于本工具")
    # 修改点：使用自定义 HTML 替代 st.info，去除蓝色背景
    st.markdown("""
    <div class="ios-card">
        本工具由DeepSeek驱动🚀
    </div>
    """, unsafe_allow_html=True)
    
    # 恢复单行文案
    show_thought = st.toggle("🕵️‍♂️ 显示思考过程 (验证 JD 匹配)")

    st.markdown("---")
    st.markdown("### ⚠️ 测试说明")
    st.warning("本产品处于测试期，开发者提供有限算力支持。**如账户中 API 余额不足，测试将即刻停止。**")

    st.markdown("---")
    st.caption("© 2026 | 防刷冷却时间：15秒")

# ============ 主界面 ============
st.title("✨ 简历经历修改器")
# 修改点：更新副标题指引
st.caption("只需输入目标岗位与真实经历，即可生成一份符合目标岗位的专业经历描述。")

# --- 交互区 (Before) - 始终显示 ---
target_position = st.text_input(
    "🎯 目标岗位",
    placeholder="例如：前端开发工程师、产品经理...",
    key="target_job"
)

real_experience = st.text_area(
    "📝 真实经历",
    height=150,
    placeholder="例如：负责给客户买咖啡，打印文件...",
    key="real_exp"
)

target_jd = st.text_area(
    "📋 目标岗位 JD (选填)",
    height=100,
    placeholder="可粘贴职位描述，有助于更精准修改",
    key="target_jd"
)

# --- 魔法按钮 ---
if st.button("🪄 一键修改", type="primary"):
    # ============ 校验 ============
    if not real_experience.strip():
        st.warning("请填写必填项")
    elif not target_position.strip():
        st.warning("请填写必填项")
    else:
        # ============ Rate Limiting: 15秒冷却 ============
        current_time = time.time()
        if "last_request_time" in st.session_state and current_time - st.session_state.last_request_time < 15:
            remaining = 15 - int(current_time - st.session_state.last_request_time)
            st.warning(f"⏳ 喝口水休息一下！请等待 {remaining} 秒后再试。")
            st.stop()

        st.session_state.last_request_time = current_time

        # ============ Prompt 构建策略 (核心重构) ============
        
        # 1. 定义公共铁律 (确保无论哪种模式，结果部分的标准是绝对一致的)
        strict_standards = """
#铁律 (违反即任务失败)
1. **数量铁律**：必须且只能生成 **4 到 5 条** 经历。严禁只生成 2-3 条！
2. **字数铁律**：
   - **冒号前**：严格等于 **4 个汉字**。
   - **冒号后**：严格控制在 **45-48 个汉字**（含标点符号）。
   - *注意：44字不行（太短），49字不行（太长），必须落在 [45, 48] 区间。*

#内部自检流程 (Thinking Process)
在生成每一行之前，请在后台执行以下步骤：
1. **Draft (起草)**：先根据公式撰写内容。
2. **Count (计数)**：数一下冒号后的字数。
   - 如果是 52 字 -> 删除 2 个形容词。
   - 如果是 40 字 -> 增加具体工具或交付结果。
3. **Finalize (定稿)**：只有当字数刚好在 45-48 字时，才输出该行。

#标准范例 (完全参照此长度)
- **产品策划**：深入挖掘诉求，利用AI工具辅助竞品调研，主导20余场300人级会议策划，设计多中玩法并沉淀业务SOP。
- **数据分析**：搭建供应商模型，运用Excel函数处理数据辅助预算决策，在日均万级人流展览场景下平衡成本与服务质量。

#生成策略
**[动作+专业工具/方法]** + **[具体场景/细节]** + **[交付结果]**
"""

        # 2. 定义基础人设
        base_role = """#人设
你是一名资深简历优化专家，兼具"文字洁癖"与"业务逻辑严谨性"。
你的核心能力是：在**极度严格的字数限制**下，输出**逻辑通顺、业务合理**的专业内容。
#核心任务
将用户的简短经历扩写为专业描述。
"""

        # 3. 根据开关组合最终 Prompt
        if show_thought:
            # === 模式 A：思考过程 + 严格结果 ===
            # 上半部分是分析，下半部分严格执行 strict_standards
            system_content = base_role + """
#当前任务流程
1. **第一步：深度分析 (Thinking)**
   - 分析【目标岗位JD】或【目标岗位名称】的核心关键词。
   - 思考如何将【用户真实经历】与这些关键词关联。

2. **第二步：严格执行 (Execution)**
   - 结束分析后，必须**严格按照下方的铁律**撰写简历经历。
   - 结果部分的格式必须与"不使用思考过程"时完全一致。

#输出格式要求
### 🧠 深度解析
- **JD关键词**：[列出3个核心词]
- **匹配思路**：[简述如何把用户经历往JD上靠]
- **优化策略**：[说明用了什么修饰词提升专业度]

### ✨ 优化结果
(在此处严格执行下方的格式铁律，输出 4-5 条经历)
""" + strict_standards

        else:
            # === 模式 B：纯净严格模式 (复刻经典版) ===
            # 直接拼接铁律，并强制要求不输出废话
            system_content = base_role + strict_standards + """
#最后警告
- **不要**输出任何开场白、思考过程、"好的"或寒暄。
- **直接**输出优化后的 4-5 条经历。
- 每次生成前自查字数，确保冒号后在 45-48 字之间。
"""

        # User Message (用户内容拼接)
        user_content = f"""用户真实经历：
{real_experience.strip()}

目标岗位：
{target_position.strip()}

目标岗位JD：
{target_jd.strip() if target_jd.strip() else ""}"""

        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content}
        ]

        try:
            with st.spinner("🪄 正在优化经历..."):
                stream = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=messages,
                    stream=True
                )
                accumulated = []
                for chunk in stream:
                    if chunk.choices and chunk.choices[0].delta.content:
                        accumulated.append(chunk.choices[0].delta.content)
                full_result = "".join(accumulated)
                st.session_state.generated_result = full_result
            st.rerun()
        except Exception as e:
            # 捕获所有 API 错误
            st.error("🚫 测试结束：服务暂时繁忙或余额不足")
            st.caption("提示：本产品处于测试期，如多次重试无效，说明开发者账户额度耗尽。")
            st.stop()

# --- 结果区 (After) - 有结果时显示 ---
if st.session_state.generated_result:
    st.subheader("✨ 优化结果")
    # 渲染前清洗数据，去除 Markdown 加粗符号
    clean_result = st.session_state.generated_result.replace("**", "")
    # 展示清洗后的结果
    st.code(clean_result, language="markdown")
