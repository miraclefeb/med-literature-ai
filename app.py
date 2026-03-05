"""
医学文献 AI 助手
功能：文献检索 + AI 问答
"""

import streamlit as st
import requests
import json
from typing import List, Dict
import os
import time

# 页面配置
st.set_page_config(
    page_title="医学文献 AI 助手",
    page_icon="🔬",
    layout="wide"
)

# 标题
st.title("文献科研助手（PubMed版）")
st.markdown("**快速检索医学文献，AI 智能总结核心结论**")


# 自定义样式
st.markdown("""
<style>
    /* 侧边栏背景色 */
    section[data-testid="stSidebar"] {
        background-color: #F5F5F5;
    }
    
    /* 按钮颜色 - 浅橙色 */
    .stButton button {
        background-color: #fe791b;
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.6rem 2rem;
        font-size: 1rem;
        font-weight: 500;
        transition: all 0.3s;
    }
    
    .stButton button:hover {
        background-color: #e66a15;
        box-shadow: 0 4px 12px rgba(255, 183, 77, 0.4);
    }
    /* 输入框背景色 */
    .stTextArea textarea {
        background-color: #f7efe8;
    }

        /* 滑块样式 */
    /* 滑块轨道背景（整个条）- 米色 */
    .stSlider [data-baseweb="slider"] > div > div {
        background-color: #f7efe8 !important;
    }
    
    /* 滑块已选中部分 - 橙色 */
    .stSlider [data-baseweb="slider"] > div > div > div {
        background-color: #fe791b !important;
    }
    
    /* 滑块圆点 - 橙色 */
    .stSlider [data-baseweb="slider"] [role="slider"] {
        background-color: #fe791b !important;
    }
    
    /* 输入框去掉边框 */
    .stTextArea textarea {
        background-color: #f7efe8;
        border: 2px solid #FFFFFF;
        border-radius: 8px;
        padding: 12px;
    }
    
    .stTextArea textarea:focus {
        border: none;
        outline: none;
        box-shadow: 0 0 0 2px rgba(254, 121, 27, 0.2);
    }
</style>
""", unsafe_allow_html=True)



# 侧边栏配置
with st.sidebar:
    st.header("⚙️ 配置")
    api_key = st.text_input(
        "DeepSeek API Key",
        type="password",
        value=st.secrets.get("DEEPSEEK_API_KEY", ""),
        help="在 https://platform.deepseek.com 获取"
    )
    
    max_results = st.slider("检索文献数量", 5, 20, 10)
    
    st.markdown("---")
    st.markdown("### 📖 使用说明")
    st.markdown("""
    1. 输入医学问题
    2. AI 自动检索 PubMed 文献
    3. 智能总结核心结论
    4. 展示相关文献列表
    """)

# PubMed 检索函数
def search_pubmed(query: str, max_results: int = 10) -> List[Dict]:
    """检索 PubMed 文献"""
    try:
        # 第一步：搜索获取 PMID 列表
        search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        search_params = {
            "db": "pubmed",
            "term": query,
            "retmax": max_results,
            "retmode": "json",
            "sort": "relevance"
        }
        
        search_response = requests.get(search_url, params=search_params, timeout=10)
        search_data = search_response.json()
        
        pmids = search_data.get("esearchresult", {}).get("idlist", [])
        
        if not pmids:
            return []
        
        # 第二步：获取文献基本信息
        summary_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
        summary_params = {
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "json"
        }
        
        summary_response = requests.get(summary_url, params=summary_params, timeout=15)
        summary_data = summary_response.json()
        
        # 第三步：获取完整摘要（使用 efetch）
        fetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
        fetch_params = {
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "xml",
            "rettype": "abstract"
        }
        
        fetch_response = requests.get(fetch_url, params=fetch_params, timeout=20)
        
        # 解析 XML 获取摘要
        import xml.etree.ElementTree as ET
        abstracts = {}
        try:
            root = ET.fromstring(fetch_response.content)
            for article in root.findall(".//PubmedArticle"):
                pmid_elem = article.find(".//PMID")
                abstract_elem = article.find(".//AbstractText")
                if pmid_elem is not None and abstract_elem is not None:
                    pmid = pmid_elem.text
                    abstract = abstract_elem.text or ""
                    # 截取前150字
                    if len(abstract) > 150:
                        abstract = abstract[:150] + "..."
                    abstracts[pmid] = abstract
        except:
            pass  # 如果解析失败，继续使用空摘要
        
        # 解析结果
        articles = []
        for pmid in pmids:
            if pmid in summary_data.get("result", {}):
                article_data = summary_data["result"][pmid]
                
                # 获取作者列表
                authors = article_data.get("authors", [])
                author_names = ", ".join([author.get("name", "") for author in authors[:3]])
                if len(authors) > 3:
                    author_names += " et al."
                
                articles.append({
                    "pmid": pmid,
                    "title": article_data.get("title", ""),
                    "authors": author_names,
                    "journal": article_data.get("fulljournalname", ""),
                    "year": article_data.get("pubdate", "").split()[0] if article_data.get("pubdate") else "",
                    "abstract": abstracts.get(pmid, "暂无摘要"),
                    "link": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
                })
        
        return articles
    
    except Exception as e:
        st.error(f"PubMed 检索出错：{str(e)}")
        return []

# AI 总结函数（带重试机制）
def summarize_with_ai(query: str, articles: List[Dict], api_key: str) -> str:
    """使用 DeepSeek AI 总结文献"""
    if not articles:
        return "未找到相关文献"
    
    # 构建 prompt
    articles_text = "\n\n".join([
        f"文献 {i+1}:\n标题: {article['title']}\n作者: {article['authors']}\n期刊: {article['journal']} ({article['year']})"
        for i, article in enumerate(articles[:8])
    ])
    
    prompt = f"""你是一个专业的医学文献分析助手。

用户问题：{query}

我检索到以下相关文献：

{articles_text}

请你：
1. 用中文总结当前医学共识和最新研究进展（2-3段话）
2. 如果有争议或不同观点，请说明
3. 给出临床实践建议（如果适用）

请用专业但易懂的语言回答，分点说明。"""

    # 重试机制：最多尝试3次
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "deepseek-chat",
                    "messages": [
                        {"role": "system", "content": "你是一个专业的医学文献分析助手，擅长总结医学研究并给出临床建议。"},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 2000
                },
                timeout=60  # 增加到60秒
            )
            
            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"]
            else:
                if attempt < max_retries - 1:
                    time.sleep(2)  # 等待2秒后重试
                    continue
                return f"❌ AI 总结失败：HTTP {response.status_code}"
                
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                st.warning(f"⏱️ 请求超时，正在重试... ({attempt + 1}/{max_retries})")
                time.sleep(2)
                continue
            return "❌ AI 请求超时，DeepSeek API 可能暂时不可用。请稍后重试。"
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                time.sleep(2)
                continue
            return f"❌ 网络请求失败：{str(e)}"
        except Exception as e:
            return f"❌ AI 总结出错：{str(e)}"
    
    return "❌ 多次重试失败，请稍后再试"

# 主界面
query = st.text_area(
    "🔍 输入您的医学问题",
    placeholder="例如：2型糖尿病的一线用药是什么？\n\n也可以输入病例片段，AI会帮你找相关文献",
    help="用中文或英文描述您的问题",
    height=120
)

if st.button("🚀 开始检索", type="primary", use_container_width=True):
    if not query:
        st.warning("⚠️ 请输入问题")
    elif not api_key:
        st.error("❌ 请在侧边栏配置 DeepSeek API Key")
    else:
        with st.spinner("🔎 正在检索 PubMed 文献..."):
            articles = search_pubmed(query, max_results)
        
        if not articles:
            st.warning("⚠️ 未找到相关文献，请尝试其他关键词")
        else:
            st.success(f"✅ 找到 {len(articles)} 篇相关文献")
            
            # AI 总结
            with st.spinner("🤖 AI 正在分析文献并生成总结..."):
                summary = summarize_with_ai(query, articles, api_key)
            
            # 左右布局显示结果
            col_left, col_right = st.columns([2, 3])
            
            # 左侧：核心结论
            with col_left:
                st.markdown("## 📊 核心结论")
                st.markdown(summary)
            
            # 右侧：文献列表
            with col_right:
                st.markdown("## 📚 相关文献")
                
                for i, article in enumerate(articles, 1):
                    with st.expander(f"📄 {i}. {article['title']}", expanded=(i <= 3)):
                        col1, col2 = st.columns([3, 1])
                    
                        with col1:
                            st.markdown(f"**作者：** {article['authors']}")
                            st.markdown(f"**期刊：** {article['journal']} ({article['year']})")
                            st.markdown(f"**摘要：** {article['abstract']}")
                    
                        with col2:
                            st.markdown(f"**PMID:** {article['pmid']}")
                            st.markdown(f"[📖 查看原文]({article['link']})")

# 页脚
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray; font-size: 0.9em;'>
    <p>医学文献 AI 助手 v1.0 | 数据来源：PubMed | AI 模型：DeepSeek</p>
    <p>⚠️ 本工具仅供学术研究参考，不构成医疗建议</p>
</div>
""", unsafe_allow_html=True)
