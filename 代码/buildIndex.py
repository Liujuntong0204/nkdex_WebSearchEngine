from elasticsearch import Elasticsearch, helpers
import json
import os

# 配置Elasticsearch客户端
ELASTICSEARCH_HOST = "http://localhost:9200"
INDEX_NAME = "webpages"

def create_index(es, index_name):
    """创建索引并定义映射"""
    index_mapping = {
        "settings": {
            "analysis": {
                "analyzer": {
                    "ik_analyzer": {
                        "type": "custom",
                        "tokenizer": "ik_smart"  # 或者使用 "ik_max_word"
                    }
                }
            }
        },
        "mappings": {
            "properties": {
                "title": {"type": "text", "analyzer": "ik_analyzer"},
                "url": {"type": "keyword"},  # URL作为关键字处理
                "content": {"type": "text", "analyzer": "ik_analyzer"},
                "referenced_urls": {"type": "keyword"},  # 作为关键字处理
                "html_filename": {"type": "keyword"},
                "pr": {"type": "float"}  # PageRank值，用浮点数表示
            }
        }
    }

    if not es.indices.exists(index=index_name):
        response = es.indices.create(index=index_name, body=index_mapping)
        print(f"Index '{index_name}' created. Response: {response}")
    else:
        print(f"Index '{index_name}' already exists.")

def load_data(file_path):
    """加载JSON数据"""
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"The file {file_path} does not exist.")
    
    with open(file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    return data


def bulk_insert(es, index_name, data, batch_size=100, chunk_size=5):
    """使用Bulk API批量插入数据,分批次"""
    for i in range(0, len(data), batch_size):
        batch = data[i:i + batch_size]
        actions = [
            {
                "_index": index_name,
                "_source": item
            }
            for item in batch
        ]
        
        try:
            helpers.bulk(es, actions, chunk_size=chunk_size)
            print(f"Batch {i // batch_size + 1} inserted successfully.")
        except Exception as e:
            print(f"An error occurred while inserting batch {i // batch_size + 1}: {e}")

def main():
    # 创建Elasticsearch客户端
    from elasticsearch import Elasticsearch, helpers

    es = Elasticsearch(
        ELASTICSEARCH_HOST,
        request_timeout=30,
        max_retries=5,
        retry_on_timeout=True,
        headers={"Content-Type": "application/json"},
        http_compress=True  # 启用 HTTP 压缩
    )

    # 检查Elasticsearch是否可用
    if not es.ping():
        print("Elasticsearch is not running or unreachable.")
        return

    # 创建索引
    create_index(es, INDEX_NAME)

    # 加载数据
    file_path = 'result.json' 
    data = load_data(file_path)

    # 批量插入数据
    bulk_insert(es, INDEX_NAME, data)

if __name__ == "__main__":
    main()


# from elasticsearch import Elasticsearch

# # 配置Elasticsearch客户端
# ELASTICSEARCH_HOST = "http://localhost:9200"
# INDEX_NAME = "webpages"

# def delete_index(es, index_name):
#     """删除指定的索引"""
#     if es.indices.exists(index=index_name):
#         response = es.indices.delete(index=index_name)
#         print(f"Index '{index_name}' deleted. Response: {response}")
#     else:
#         print(f"Index '{index_name}' does not exist.")

# def main():
#     # 创建Elasticsearch客户端
#     es = Elasticsearch(ELASTICSEARCH_HOST)

#     # 检查Elasticsearch是否可用
#     if not es.ping():
#         print("Elasticsearch is not running or unreachable.")
#         return

#     # 删除索引
#     delete_index(es, INDEX_NAME)

# if __name__ == "__main__":
#     main()