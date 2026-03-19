#!/usr/bin/env python3
"""
解析epub文件并搜索关于标普500股票列表的相关内容
"""

import os
import zipfile
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup

def extract_epub(epub_path):
    """提取epub文件内容"""
    try:
        with zipfile.ZipFile(epub_path, 'r') as epub:
            # 查找content.opf文件
            content_opf = None
            for file in epub.namelist():
                if file.endswith('content.opf'):
                    content_opf = file
                    break
            
            if not content_opf:
                print("未找到content.opf文件")
                return []
            
            # 解析content.opf文件
            with epub.open(content_opf) as f:
                content = f.read().decode('utf-8')
            
            # 查找所有html文件
            html_files = []
            root = ET.fromstring(content)
            ns = {'opf': 'http://www.idpf.org/2007/opf'}
            
            for item in root.findall('.//opf:item', ns):
                if item.get('media-type') == 'application/xhtml+xml':
                    href = item.get('href')
                    # 构建完整路径
                    base_path = os.path.dirname(content_opf)
                    full_path = os.path.join(base_path, href)
                    html_files.append(full_path)
            
            # 读取html文件内容
            html_contents = []
            for html_file in html_files:
                if html_file in epub.namelist():
                    with epub.open(html_file) as f:
                        try:
                            html_content = f.read().decode('utf-8')
                            html_contents.append(html_content)
                        except Exception as e:
                            print(f"读取{html_file}失败: {e}")
            
            return html_contents
    except Exception as e:
        print(f"提取epub失败: {e}")
        return []

def search_content(html_contents, keywords):
    """搜索内容"""
    results = []
    
    for i, html_content in enumerate(html_contents):
        soup = BeautifulSoup(html_content, 'html.parser')
        text = soup.get_text()
        
        # 搜索关键词
        for keyword in keywords:
            if keyword.lower() in text.lower():
                # 提取包含关键词的句子
                sentences = text.split('. ')
                for sentence in sentences:
                    if keyword.lower() in sentence.lower():
                        results.append({
                            'file_index': i,
                            'sentence': sentence.strip() + '.'
                        })
    
    return results

def main():
    """主函数"""
    # 查找epub文件
    epub_files = []
    for file in os.listdir('.'):
        if file.endswith('.epub') and 'stocks on the move' in file.lower():
            epub_files.append(file)
    
    if not epub_files:
        print("未找到Stocks on the Move的epub文件")
        return
    
    epub_path = epub_files[0]
    print(f"找到epub文件: {epub_path}")
    
    # 提取内容
    print("正在提取epub内容...")
    html_contents = extract_epub(epub_path)
    print(f"提取到{len(html_contents)}个html文件")
    
    # 搜索关键词
    keywords = [
        "S&P 500",
        "标普500",
        "stock list",
        "股票列表",
        "historical",
        "历史",
        "constituents",
        "成分股"
    ]
    
    print("正在搜索相关内容...")
    results = search_content(html_contents, keywords)
    
    print(f"找到{len(results)}个相关句子:")
    for i, result in enumerate(results):
        print(f"{i+1}. {result['sentence']}")
        print("-" * 80)

if __name__ == "__main__":
    main()
