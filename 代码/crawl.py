import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import sqlite3
import os
import json
import time
import chardet

def is_valid_url(url):
    """检查URL是否有效"""
    parsed = urlparse(url)
    return bool(parsed.netloc) and bool(parsed.scheme) and parsed.scheme in ['http', 'https']

def get_links(url):
    """获取页面上的所有链接"""
    try:
        response = requests.get(url, timeout=10)
        response.encoding = chardet.detect(response.content)['encoding']  # 新增：检测并设置编码
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            links = set()
            for link in soup.find_all('a', href=True):
                href = link['href']
                if is_valid_url(href):
                    links.add(href)
                else:
                    full_url = urljoin(url, href)
                    if is_valid_url(full_url):
                        links.add(full_url)
            return links
        else:
            print(f"Failed to retrieve {url}. Status code: {response.status_code}")
            return set()
    except requests.exceptions.Timeout:
        print(f"Request timed out for {url}")
        return set()
    except Exception as e:
        print(f"Error retrieving {url}: {e}")
        return set()

def save_html_to_file(url, html_content, output_dir='nankai_zfxy'):  ## 文件夹名
    """将网页内容保存为HTML文件"""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 将URL转换为合法的文件名
    filename = os.path.basename(urlparse(url).path)
    if not filename:
        filename = 'index.html'
    filename = os.path.join(output_dir, filename)

    # 确保文件名唯一
    counter = 1
    original_filename = filename
    while os.path.exists(filename):
        filename = f"{original_filename}_{counter}.html"
        counter += 1

    with open(filename, 'w', encoding='utf-8') as f:
        f.write(html_content)
    return filename  # 返回保存的文件名

def crawl_website(start_url):
    """爬取整个网站"""
    visited = set()
    queue = [start_url]
    data = []  # 用于保存网页数据的列表

    while queue:
        current_url = queue.pop(0)
        if current_url not in visited:
            print(f"Crawling: {current_url}")
            visited.add(current_url)
            links = get_links(current_url)
            for link in links:
                # if link not in visited and 'bs.nankai.edu.cn' in link:   ## 网址
                #     queue.append(link)
                if link not in visited and 'zfxy.nankai.edu.cn' in link and not (link.endswith('.doc') or link.endswith('.pdf') or link.endswith('.docx') or link.endswith('.rar') or link.endswith('.zip') or link.endswith('.xlsx') or link.endswith('.xls') or link.endswith('.ppt') or link.endswith('.pptx') or link.endswith('.jpg') or link.endswith('.png')):
                    queue.append(link)

            try:
                response = requests.get(current_url, timeout=10)
                response.encoding = chardet.detect(response.content)['encoding']  # 新增：检测并设置编码
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    title = soup.title.string if soup.title else 'No Title'
                    # content = soup.get_text().strip()
                    content = soup.get_text(strip=True, separator=' ')  # 优化：使用strip=True和separator来清理文本

                    # 保存HTML文件
                    html_filename = save_html_to_file(current_url, response.text)

                    # 提取网页中引用的URL
                    referenced_urls = [a['href'] for a in soup.find_all('a', href=True) if is_valid_url(a['href'])]

                    # 保存数据到列表
                    data.append({
                        'title': title,
                        'url': current_url,
                        'content': content,
                        'referenced_urls': referenced_urls,
                        'html_filename': os.path.basename(html_filename)
                    })

                    # 定期保存数据到JSON文件
                    with open('nankai_zfxy.json', 'w', encoding='utf-8') as f:   ## json文件
                        json.dump(data, f, ensure_ascii=False, indent=4)

                    # 模拟请求之间的延迟
                    time.sleep(0.5)

            except requests.exceptions.Timeout:
                print(f"Request timed out for {current_url}")
            except Exception as e:
                print(f"Error processing {current_url}: {e}")

if __name__ == "__main__":
    start_url = "https://zfxy.nankai.edu.cn/"  ## 网址
    crawl_website(start_url)