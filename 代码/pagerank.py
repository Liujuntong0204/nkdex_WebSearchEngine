# 连接分析，计算pr值
import json
import networkx as nx
from collections import defaultdict

# 读取所有JSON文件
def read_json_files(file_paths):
    data = []
    for file_path in file_paths:
        with open(file_path, 'r', encoding='utf-8') as file:
            data.extend(json.load(file))
    print(f"Total number of data: {len(data)}")
    return data

# 根据URL去重
def deduplicate_by_url(data):
    seen_urls = set()
    unique_data = []
    for item in data:
        if item['url'] not in seen_urls:
            seen_urls.add(item['url'])
            unique_data.append(item)
    print(f"Total number of unique_data: {len(unique_data)}")
    return unique_data

# 构建图模型
def build_graph(data):
    graph = nx.DiGraph()
    for item in data:
        graph.add_node(item['url'], pr=0)
        for referenced_url in item['referenced_urls']:
            graph.add_edge(item['url'], referenced_url)
    return graph

# 计算PageRank
def calculate_pagerank(graph):
    pageranks = nx.pagerank(graph)
    for node, pr in pageranks.items():
        graph.nodes[node]['pr'] = pr
    return graph

# 更新JSON数据
def update_data_with_pagerank(data, graph):
    for item in data:
        item['pr'] = graph.nodes[item['url']]['pr']
    return data

# 写入结果JSON文件
def write_result_to_json(data, output_file):
    with open(output_file, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

# 主程序
def main(file_paths, output_file):
    data = read_json_files(file_paths)
    unique_data = deduplicate_by_url(data)
    graph = build_graph(unique_data)
    graph = calculate_pagerank(graph)
    updated_data = update_data_with_pagerank(data, graph)
    write_result_to_json(updated_data, output_file)

file_paths = ['crawl\\nankai_ai.json', 'crawl\\nankai_bs.json','crawl\\nankai_cc.json','crawl\\nankai_ceo.json','crawl\\nankai_cs.json','crawl\\nankai_finance.json','crawl\\nankai_history.json','crawl\\nankai_law.json','crawl\\nankai_news.json','crawl\\nankai_phil.json','crawl\\nankai_sfs.json','crawl\\nankai_syber.json','crawl\\nankai_weekly.json','crawl\\nankai_wxy.json','crawl\\nankai_zfxy.json']
# file_paths = ['crawl\\nankai_cc.json']
output_file = 'result.json'
main(file_paths, output_file)

# import json
# from collections import Counter

# def read_result_json(file_path):
#     with open(file_path, 'r', encoding='utf-8') as file:
#         data = json.load(file)
#     return data

# def count_unique_pagerank_values(data):
#     # 使用集合收集所有独特的PR值
#     pr_values = {float(item['pr']) for item in data if 'pr' in item}
    
#     # 计算每个PR值出现的次数
#     pr_counter = Counter(float(item['pr']) for item in data if 'pr' in item)
    
#     return pr_values, pr_counter

# def print_pagerank_statistics(pr_values, pr_counter):
#     unique_pr_count = len(pr_values)
#     print(f"Total number of unique PageRank values: {unique_pr_count}")
    
#     # 打印每个PR值及其出现次数
#     print("PageRank values and their occurrences:")
#     for pr, count in sorted(pr_counter.items()):
#         print(f"PR value: {pr:.6f}, Occurrences: {count}")

# # 主程序
# def main(result_file):
#     data = read_result_json(result_file)
#     pr_values, pr_counter = count_unique_pagerank_values(data)
#     print_pagerank_statistics(pr_values, pr_counter)

# if __name__ == "__main__":
#     result_file = 'result.json'  
#     main(result_file)