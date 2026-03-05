"""
文献科研助手（PubMed版）
功能：文献检索 + AI 问答
"""

import streamlit as st
import requests
import json
from typing import List, Dict
import os
import time
import xml.etree.ElementTree as ET

# 页面配置
st.set_page_config(
    page_title="文献科研助手（PubMed版）",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义样式
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* 主背景 */
    .main {
        background-color: #EFF6FF;
    }
    
    /* 侧边栏 */
    section[data-testid="stSidebar"] {
        background-color: #FFFFFF;
        padding: 2rem 1.5rem;
    }
    
    section[data-testid="stSidebar"] h2 {
        color: #1E40AF;
        font-size: 1.1rem;
        font-weight: 600;
        margin-bottom: 1rem;
    }
    
    /* 主标题 */
    h1 {
        color: #1E3A8A;
        font-size: 2.5rem;
        font-weight: 700;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    
    .subtitle {
        color: #64748B;
        font-size: 1.1rem;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    /* 输入框 */
    .stTextArea textarea {
        background-color: #FFFFFF;
        border: 2px solid #DBEAFE;
        border-radius: 12px;
        padding: 16px;
        font-size: 1rem;
        min-height: 150px;
    }
    
    .stTextArea textarea:focus {
        border-color: #3B82F6;
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
    }
    
    /* 按钮 */
    .stButton button {
        background: linear-gradient(135deg, #3B82F6 0%, #1E40AF 100%);
        color: white;
        border-radius: 12px;
        padding: 0.8rem 2rem;
        font-size: 1.1rem;
        font-weight: 600;
        border: none;
        width: 100%;
        transition: all 0.3s;
    }
    
    .stButton button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 16px rgba(59, 130, 246, 0.3);
    }
    
    /* 文献卡片 */
    .literature-card {
        background: #FFFFFF;
        border-radius: 12px;
        padding: 24px;
        margin-bottom: 16px;
        border: 1px solid #E2E8F0;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
        transition: all 0.3s;
    }
    
    .literature-card:hover {
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
        border-color: #3B82F6;
    }
    
    .literature-title {
        color: #1E293B;
        font-size: 1.1rem;
        font-weight: 600;
        line-height: 1.5;
        margin-bottom: 12px;
    }
    
    .literature-meta {
        color: #64748B;
        font-size: 0.9rem;
        line-height: 1.6;
        margin-bottom: 14px;
    }
    
    .literature-abstract {
        color: #475569;
        font-size: 0.95rem;
        line-height: 1.7;
        margin-bottom: 14px;
        padding: 14px;
        background: #F8FAFC;
        border-radius: 8px;
        border-left: 3px solid #3B82F6;
    }
    
    .literature-link {
        color: #3B82F6;
        text-decoration: none;
        font-size: 0.9rem;
        font-weight: 500;
    }
    
    /* 核心结论 */
    .conclusion-box {
        background: #FFFFFF;
        border-radius: 12px;
        padding: 24px;
        border: 1px solid #DBEAFE;
        color: #1E293B;
        line-height: 1.7;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
    }
    
    /* 页脚 */
    .footer {
        text-align: center;
        color: #94A3B8;
        font-size: 0.85rem;
        margin-top: 3rem;
        padding-top: 2rem;
        border-top: 1px solid #E2E8F0;
    }
</style>
""", unsafe_allow_html=True)

# 侧边栏
with st.sidebar:
    st.markdown("## ⚙️ 配置")
    
    api_key = st.text_input(
        "DeepSeek API Key",
        type="password",
        value=st.secrets.get("DEEPSEEK_API_KEY", ""),
        help="在 https://platform.deepseek.com 获取"
    )
    
    max_results = st.slider(
        "检索文献数量",
        min_value=5,
        max_value=20,
        value=10,
        help="选择要检索的文献数量"
    )
    
    st.markdown("---")
    st.markdown("### 📖 使用说明")
    st.markdown("""
    **1.** 输入医学问题
    
    **2.** AI 自动检索 PubMed 文献
    
    **3.** 智能总结核心结论
    
    **4.** 展示相关文献列表
    """)

# 主内容区
st.title("📚 文献科研助手（PubMed版）")
st.markdown('<p class="subtitle">快速检索医学文献，AI 智能总结核心结论</p>', unsafe_allow_html=True)

# 输入框
query = st.text_area(
    "🔍 输入您的医学问题或关键词",
    placeholder="例如：2型糖尿病的一线用药是什么？\n\n也可以输入病例片段，AI会帮你找相关文献",
    help="用中文或英文描述您的问题",
    height=150
)

# 检索按钮
if st.button("🚀 开始检索"):
    if not query:
        st.warning("⚠️ 请输入问题")
    elif not api_key:
        st.error("❌ 请在侧边栏配置 DeepSeek API Key")
    else:
        # PubMed 检索
        with st.spinner("🔎 正在检索 PubMed 文献..."):
            try:
                # 搜索
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
                    st.warning("⚠️ 未找到相关文献，请尝试其他关键词")
                else:
                    # 获取文献信息
                    summary_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
                    summary_params = {
                        "db": "pubmed",
                        "id": ",".join(pmids),
                        "retmode": "json"
                    }
                    
                    summary_response = requests.get(summary_url, params=summary_params, timeout=15)
                    summary_data = summary_response.json()
                    
                    # 获取摘要
                    fetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
                    fetch_params = {
                        "db": "pubmed",
                        "id": ",".join(pmids),
                        "retmode": "xml",
                        "rettype": "abstract"
                    }
                    
                    fetch_response = requests.get(fetch_url, params=fetch_params, timeout=20)
                    
                    abstracts = {}
                    try:
                        root = ET.fromstring(fetch_response.content)
                        for article_elem in root.findall(".//PubmedArticle"):
                            pmid_elem = article_elem.find(".//PMID")
                            if pmid_elem is not None:
                                pmid = pmid_elem.text
                                abstract_texts = article_elem.findall(".//AbstractText")
                                if abstract_texts:
                                    abstract_parts = []
                                    for abs_elem in abstract_texts:
                                        if abs_elem.text:
                                            abstract_parts.append(abs_elem.text)
                                    abstract = " ".join(abstract_parts)
                                    if len(abstract) > 200:
                                        abstract = abstract[:200] + "..."
                                    abstracts[pmid] = abstract
                    except:
                        pass
                    
                    # 整理文献
                    articles = []
                    for pmid in pmids:
                        if pmid in summary_data.get("result", {}):
                            article_data = summary_data["result"][pmid]
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
                    
                    st.success(f"✅ 找到 {len(articles)} 篇相关文献")
                    
                    # AI 总结
                    with st.spinner("🤖 AI 正在分析文献并生成总结..."):
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

                        # 重试机制
                        max_retries = 3
                        summary = None
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
                                    timeout=60
                                )
                                
                                if response.status_code == 200:
                                    result = response.json()
                                    summary = result["choices"][0]["message"]["content"]
                                    break
                                elif attempt < max_retries - 1:
                                    time.sleep(2)
                                    continue
                            except requests.exceptions.Timeout:
                                if attempt < max_retries - 1:
                                    st.warning(f"⏱️ 请求超时，正在重试... ({attempt + 1}/{max_retries})")
                                    time.sleep(2)
                                    continue
                            except:
                                if attempt < max_retries - 1:
                                    time.sleep(2)
                                    continue
                        
                        if not summary:
                            summary = "❌ AI 总结失败，请稍后重试"
                    
                    # 显示结果
                    col1, col2 = st.columns([2, 3])
                    
                    with col1:
                        st.markdown("## 📊 核心结论")
                        st.markdown(f'<div class="conclusion-box">{summary}</div>', unsafe_allow_html=True)
                    
                    with col2:
                        st.markdown("## 📚 相关文献")
                        
                        for i, article in enumerate(articles, 1):
                            st.markdown(f"""
                            <div class='literature-card'>
                                <div class='literature-title'>{i}. {article['title']}</div>
                                <div class='literature-meta'>
                                    <strong>作者：</strong>{article['authors']}<br>
                                    <strong>期刊：</strong>{article['journal']} ({article['year']}) | <strong>PMID：</strong>{article['pmid']}
                                </div>
                                <div class='literature-abstract'>
                                    <strong>摘要：</strong>{article['abstract']}
                                </div>
                                <a href="{article['link']}" target="_blank" class='literature-link'>🔗 查看 PubMed 原文 →</a>
                            </div>
                            """, unsafe_allow_html=True)
                
            except Exception as e:
                st.error(f"❌ 检索出错：{str(e)}")

# 页脚
st.markdown("""
<div class='footer'>
    <p>文献科研助手（PubMed版） v1.0 | 数据来源：PubMed | AI 模型：DeepSeek</p>
    <p>⚠️ 本工具仅供学术研究参考，不构成医疗建议</p>
    <p>© 2026 All rights reserved</p>
</div>
""", unsafe_allow_html=True)
