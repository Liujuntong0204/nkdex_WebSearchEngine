from flask import Flask, request, jsonify, render_template,redirect, url_for
import os
from flask import send_from_directory,session

app = Flask(__name__)
app.config['SECRET_KEY'] = 'a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6'

# 用户功能
import json
USERS_file = 'users.json'

def load_users():
    if not os.path.exists(USERS_file):
        return {"users": []}
    with open(USERS_file, 'r', encoding='utf-8') as f:
        return json.load(f)
def save_users(users_data):
    with open(USERS_file, 'w', encoding='utf-8') as f:
        json.dump(users_data, f, ensure_ascii=False, indent=4)

# 用户注册
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        # 返回注册页面
        return render_template('register.html')
    try:
        # 获取 JSON 数据
        print("Received request data:", request.get_data(as_text=True))
        data = request.get_json()
        if not data:
            print("请求体为空")
            return jsonify({"error": "请求体为空"}), 400
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            print("有空值")
            return jsonify({"error": "用户名或密码不能为空"}), 400

        # 检查用户是否已存在
        users = load_users()
        if any(user['username'] == username for user in users['users']):
            print("用户名已存在")
            return jsonify({"error": "用户名已存在"}), 400

        # 注册新用户
        new_user = {
            'username': username,
            'password': password, 
            'search_history': [],
            'clicked_links': []
        }
        users['users'].append(new_user)
        save_users(users)
        print("注册成功")
        return jsonify({"message": "注册成功"}), 200

    except Exception as e:
        print("Error in register:", e)  # 打印异常信息
        return jsonify({"error": "注册失败，请稍后再试。"}), 500
    


# 用户登录
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            # 获取 JSON 数据
            data = request.get_json()
            if not data:
                return jsonify({"error": "请求体为空"}), 400

            username = data.get('username')
            password = data.get('password')

            if not username or not password:
                return jsonify({"error": "用户名或密码不能为空"}), 400

            # 检查用户是否存在
            users = load_users()
            user = next((user for user in users['users'] if user['username'] == username and user['password'] == password), None)

            if user:
                session['user'] = user['username']  # 将登录用户存储到会话中
                return jsonify({"message": "登录成功"}), 200
            else:
                return jsonify({"error": "无效的用户名或密码"}), 400

        except Exception as e:
            print("Error in login:", e)
            return jsonify({"error": "登录失败，请稍后再试。"}), 500

    return render_template('login.html')

# 搜索记录
def update_search_history(username, query):
    users = load_users()
    user = next((user for user in users['users'] if user['username'] == username), None)
    if user:
        if query in user['search_history']:
            user['search_history'].remove(query)
        user['search_history'].append(query)
        save_users(users)
# 记录用户点击过的连接
def update_clicked_links(username, url):
    users = load_users()
    user = next((user for user in users['users'] if user['username'] == username), None)
    if user and url not in user['clicked_links']:
        user['clicked_links'].append(url)
        save_users(users)

# 显示用户信息
@app.route('/user')
def user_page():
    if 'user' not in session:
        return redirect(url_for('login'))
    users = load_users()
    user = next((user for user in users['users'] if user['username'] == session['user']), None)
    if user:
        return render_template('user_page.html', user=user)
    else:
        print("找不到用户信息")
    return "User not found", 404


# 个性化推荐功能 添加新路由
@app.route('/recommendations', methods=['GET'], endpoint='api_recommendations')
def recommendations():
    if 'user' not in session:
        return redirect(url_for('login'))

    users = load_users()
    user = next((u for u in users['users'] if u['username'] == session['user']), None)
    
    # 获取用户的查询历史
    has_search_history = user and user.get('search_history') and len(user['search_history']) > 0
    search_query = {}
    if has_search_history:
    # 构建推荐查询
        user_boost_terms = [term for term in user['search_history']]
        url_decrease_scores = [url for url in user['clicked_links']]

        # 使用最近的五条搜索历史作为查询的基础
        query = " ".join(user_boost_terms[-5:])  

        search_query = {
            "query": {
                "function_score": {
                    "query": {
                        "multi_match": {
                            "query": query,
                            "fields": ["title", "content"],
                            "type": "best_fields"
                        }
                    },
                    "functions": [
                        *[
                            {"filter": {"match_phrase": {"content": term}}, "weight": 2}
                            for term in user_boost_terms
                        ],
                        *[
                            {
                                "script_score": {
                                    "script": {
                                        "source": "if (doc['url'].value == params.url) { return _score * 0.5 } else { return _score }",
                                        "params": {"url": url}
                                    }
                                }
                            }
                            for url in url_decrease_scores
                        ]
                    ],
                    "score_mode": "sum",
                    "boost_mode": "multiply"
                }
            },
            "collapse": {
                "field": "url"
            },
            "sort": [
                {"_score": {"order": "desc"}},
                {"pr": {"order": "desc"}}
            ],
            "size": 100  # 推荐的数量
        }
    else: # 没有查询历史则直接返回权重最高的20个网页
        search_query = {
            "query": {
                "match_all": {}
            },
            "sort": [
                {"_score": {"order": "desc"}},
                {"pr": {"order": "desc"}}  
            ],
            "size": 20  # 返回20个最高权重的网页
        }

    # 执行搜索
    response = es.search(index='webpages', body=search_query)

    results = []
    for hit in response['hits']['hits']:
        html_filename = hit['_source'].get('html_filename','')
        url = hit['_source'].get('url','')
        folder=''
        if 'ai.nankai.edu.cn' in url:
            folder='nankai_ai'
        elif 'bs.nankai.edu.cn' in url:
            folder='nankai_bs'
        elif 'cc.nankai.edu.cn' in url:
            folder='nankai_cc'
        elif 'ceo.nankai.edu.cn' in url:
            folder='nankai_ceo'
        elif 'cs.nankai.edu.cn' in url:
            folder='nankai_cs'
        elif 'cyber.nankai.edu.cn' in url:
            folder='nankai_cyber'
        elif 'finance.nankai.edu.cn' in url:
            folder='nankai_finance'
        elif 'history.nankai.edu.cn' in url:
            folder='nankai_history'
        elif 'law.nankai.edu.cn' in url:
            folder='nankai_law'
        elif 'news.nankai.edu.cn' in url:
            folder='nankai_news'
        elif 'phil.nankai.edu.cn' in url:
            folder='nankai_phil'
        elif 'sfs.nankai.edu.cn' in url:
            folder='nankai_sfs'
        elif 'weekly.nankai.edu.cn' in url:
            folder='nankai_weekly'
        elif 'wxy.nankai.edu.cn' in url:
            folder='nankai_wxy'
        elif 'zfxy.nankai.edu.cn' in url:
            folder='nankai_zfxy'
        else:
            folder=None
        result = {
            'title': hit['_source'].get('title', 'No title'),
            'url': url,
            'content': hit['_source'].get('content', '')[:300] + '...',  # 截取前300个字符
            'html_filename': html_filename,
            'folder': folder
        }
        results.append(result)

    # 返回结果
    return jsonify({'hits': results})

# 登出
@app.route('/logout', methods=['POST']) 
def logout():
    session.pop('user', None)  # 移除用户会话
    if 'user' not in session:
        return jsonify({"message": "注销成功"}), 200
    else:
        return jsonify({"error": "注销失败，会话未清除"}), 500

# 捕捉用户点击的url
@app.route('/update_click', methods=['POST'])
def update_click():
    print("点击触发")
    if 'user' in session:
        url = request.json.get('url')
        if url:
            update_clicked_links(session['user'], url)
            return jsonify({"status": "success"}), 200
        else:
            return jsonify({"status": "failed", "message": "URL not provided"}), 400
    else:
        print("未登录")
    # return jsonify({"status": "failed", "message": "Not logged in"}), 403
    return jsonify({"status": "success"}), 200




@app.route('/')  # 直接访问进的是登录
def index():
    return render_template('login.html')

@app.route('/site_search.html') # 站内查询
def site_search():
    return render_template('site_search.html')

@app.route('/phrase_search.html') # 短语查询
def phrase_search():
    return render_template('phrase_search.html')

@app.route('/wildcard_search.html') # 通配查询
def wildcard_search():
    return render_template('wildcard_search.html')

@app.route('/file_search.html') # 文档查询
def file_search():
    return render_template('file_search.html')

# 快照链接路由
@app.route('/snapshot/<path:filename>', methods=['GET'])
def snapshot(filename):
    # 解析出文件夹名称和文件名
    parts = filename.split('/')
    if len(parts) != 2 or not all(parts):
        return "Invalid request", 400

    folder, file_name = parts


    directory = os.path.join(os.getcwd(), folder)

    try:
        return send_from_directory(directory, file_name, as_attachment=False)
    except FileNotFoundError:
        return "File not found", 404


@app.route('/sitesearch', methods=['POST'],endpoint='api_site_search') # 站内查询函数
def site_search():
    query = request.json.get('query')
    if not query:
        return jsonify({"error": "No query provided"}), 400

    user_boost_terms = [] # 用户的查询历史
    url_decrease_scores = [] # 用户的点击链接
    if 'user' in session:
        users = load_users()
        user = next((u for u in users['users'] if u['username'] == session['user']), None)
        if user:
            
            user_boost_terms = [term for term in user['search_history']]
            
            url_decrease_scores = [url for url in user['clicked_links']]
    
    # 构建查询语句
    search_query = {
        "query": {
            "function_score": {
                "query": {
                    "multi_match": {
                        "query": query,
                        "fields": ["title", "content"],
                        "type": "best_fields"
                    }
                },
                "functions": [
                    # Boost terms from user's search history
                    *[
                        {"filter": {"match_phrase": {"content": term}}, "weight": 2}
                        for term in user_boost_terms
                    ],
                    # Decrease score for URLs that have been clicked
                     *[
                        {
                            "script_score": {
                                "script": {
                                    "source": "if (doc['url'].value == params.url) { return _score * 0.5 } else { return _score }",
                                    "params": {"url": url}
                                }
                            }
                        }
                        for url in url_decrease_scores
                    ]
                ],
                "score_mode": "sum",
                "boost_mode": "multiply"
            }
        },
        "collapse": {
            "field": "url"
        },
        "sort": [
            {"_score": {"order": "desc"}},
            {"pr": {"order": "desc"}}
        ],
        "size": 50
    }

    # 执行搜索
    response = es.search(index='webpages', body=search_query)

    results = []
    for hit in response['hits']['hits']:
        html_filename = hit['_source'].get('html_filename','')
        url = hit['_source'].get('url','')
        folder=''
        if 'ai.nankai.edu.cn' in url:
            folder='nankai_ai'
        elif 'bs.nankai.edu.cn' in url:
            folder='nankai_bs'
        elif 'cc.nankai.edu.cn' in url:
            folder='nankai_cc'
        elif 'ceo.nankai.edu.cn' in url:
            folder='nankai_ceo'
        elif 'cs.nankai.edu.cn' in url:
            folder='nankai_cs'
        elif 'cyber.nankai.edu.cn' in url:
            folder='nankai_cyber'
        elif 'finance.nankai.edu.cn' in url:
            folder='nankai_finance'
        elif 'history.nankai.edu.cn' in url:
            folder='nankai_history'
        elif 'law.nankai.edu.cn' in url:
            folder='nankai_law'
        elif 'news.nankai.edu.cn' in url:
            folder='nankai_news'
        elif 'phil.nankai.edu.cn' in url:
            folder='nankai_phil'
        elif 'sfs.nankai.edu.cn' in url:
            folder='nankai_sfs'
        elif 'weekly.nankai.edu.cn' in url:
            folder='nankai_weekly'
        elif 'wxy.nankai.edu.cn' in url:
            folder='nankai_wxy'
        elif 'zfxy.nankai.edu.cn' in url:
            folder='nankai_zfxy'
        else:
            folder=None
        result = {
            'title': hit['_source'].get('title', 'No title'),
            'url': url,
            'content': hit['_source'].get('content', '')[:300] + '...',  # 截取前300个字符
            'html_filename':html_filename,
            'folder':folder
        }
        # print(result)
        results.append(result)
    if 'user' in session:
        update_search_history(session['user'],query)
    # 返回结果
    return jsonify({'hits':results})


@app.route('/phrasesearch', methods=['POST'],endpoint='api_phrase_search') # 短语查询函数
def phrase_search():
    query = request.json.get('query')
    if not query:
        return jsonify({"error": "No query provided"}), 400

    user_boost_terms = [] # 用户的查询历史
    url_decrease_scores = [] # 用户的点击链接
    if 'user' in session:
        users = load_users()
        user = next((u for u in users['users'] if u['username'] == session['user']), None)
        if user:
            # Increase the weight of terms from search history
            user_boost_terms = [term for term in user['search_history']]
            # Decrease the weight of URLs that have been clicked
            url_decrease_scores = [url for url in user['clicked_links']]
    # 构建查询语句
    search_query = {
        "query": {
            "function_score": {
                "query": {
                    "multi_match": {
                        "query": query,
                        "fields": ["title", "content"],
                        "type": "phrase"
                    }
                },
                "functions": [
                    # Boost terms from user's search history
                    *[
                        {"filter": {"match_phrase": {"content": term}}, "weight": 2}
                        for term in user_boost_terms
                    ],
                    # Decrease score for URLs that have been clicked
                     *[
                        {
                            "script_score": {
                                "script": {
                                    "source": "if (doc['url'].value == params.url) { return _score * 0.5 } else { return _score }",
                                    "params": {"url": url}
                                }
                            }
                        }
                        for url in url_decrease_scores
                    ]
                ],
                "score_mode": "sum",
                "boost_mode": "multiply"
            }
        },
        "collapse": {
            "field": "url"
        },
        "sort": [
            {"_score": {"order": "desc"}},
            {"pr": {"order": "desc"}}
        ],
        "size": 50
    }

    # 执行搜索
    response = es.search(index='webpages', body=search_query)

    results = []
    for hit in response['hits']['hits']:
        html_filename = hit['_source'].get('html_filename','')
        url = hit['_source'].get('url','')
        folder=''
        if 'ai.nankai.edu.cn' in url:
            folder='nankai_ai'
        elif 'bs.nankai.edu.cn' in url:
            folder='nankai_bs'
        elif 'cc.nankai.edu.cn' in url:
            folder='nankai_cc'
        elif 'ceo.nankai.edu.cn' in url:
            folder='nankai_ceo'
        elif 'cs.nankai.edu.cn' in url:
            folder='nankai_cs'
        elif 'cyber.nankai.edu.cn' in url:
            folder='nankai_cyber'
        elif 'finance.nankai.edu.cn' in url:
            folder='nankai_finance'
        elif 'history.nankai.edu.cn' in url:
            folder='nankai_history'
        elif 'law.nankai.edu.cn' in url:
            folder='nankai_law'
        elif 'news.nankai.edu.cn' in url:
            folder='nankai_news'
        elif 'phil.nankai.edu.cn' in url:
            folder='nankai_phil'
        elif 'sfs.nankai.edu.cn' in url:
            folder='nankai_sfs'
        elif 'weekly.nankai.edu.cn' in url:
            folder='nankai_weekly'
        elif 'wxy.nankai.edu.cn' in url:
            folder='nankai_wxy'
        elif 'zfxy.nankai.edu.cn' in url:
            folder='nankai_zfxy'
        else:
            folder=None
        result = {
            'title': hit['_source'].get('title', 'No title'),
            'url': url,
            'content': hit['_source'].get('content', '')[:300] + '...',  # 截取前300个字符
            'html_filename':html_filename,
            'folder':folder
        }
        # print(result)
        results.append(result)
    if 'user' in session:
        update_search_history(session['user'],query)
    # 返回结果
    return jsonify({'hits':results})


@app.route('/wildcardsearch', methods=['POST'],endpoint='api_wildcard_search') # 通配查询函数
def wildcard_search():
    query = request.json.get('query')
    if not query:
        return jsonify({"error": "No query provided"}), 400

    user_boost_terms = [] # 用户的查询历史
    url_decrease_scores = [] # 用户的点击链接
    if 'user' in session:
        users = load_users()
        user = next((u for u in users['users'] if u['username'] == session['user']), None)
        if user:
            # Increase the weight of terms from search history
            user_boost_terms = [term for term in user['search_history']]
            # Decrease the weight of URLs that have been clicked
            url_decrease_scores = [url for url in user['clicked_links']]
    # 构建查询语句
    search_query = {
    "query": {
        "function_score": {
            "query": {
                "bool": {
                    "should": [
                        {
                            "wildcard": {
                                "title": {
                                    "value": query,
                                    "boost": 1.0
                                }
                            }
                        },
                        {
                            "wildcard": {
                                "content": {
                                    "value": query,
                                    "boost": 1.0
                                }
                            }
                        }
                    ],
                    "minimum_should_match": 1
                }
            },
            "functions": [
                # Boost terms from user's search history
                *[
                    {"filter": {"match_phrase": {"content": term}}, "weight": 2}
                    for term in user_boost_terms
                ],
                # Decrease score for URLs that have been clicked using script_score
                *[
                    {
                        "script_score": {
                            "script": {
                                "source": "if (doc['url'].value == params.url) { return _score * 0.5 } else { return _score }",
                                "params": {"url": url}
                            }
                        }
                    }
                    for url in url_decrease_scores
                ]
            ],
            "score_mode": "sum",
            "boost_mode": "multiply"
        }
    },
    "collapse": {
        "field": "url"
    },
    "sort": [
        {"_score": {"order": "desc"}},  # 首先按照相关度排序
        {"pr": {"order": "desc"}}       # 其次按照PR值降序排序
    ],
    "size": 50  # 限制返回条数为50
}


    # 执行搜索
    response = es.search(index='webpages', body=search_query)

    results = []
    for hit in response['hits']['hits']:
        html_filename = hit['_source'].get('html_filename','')
        url = hit['_source'].get('url','')
        folder=''
        if 'ai.nankai.edu.cn' in url:
            folder='nankai_ai'
        elif 'bs.nankai.edu.cn' in url:
            folder='nankai_bs'
        elif 'cc.nankai.edu.cn' in url:
            folder='nankai_cc'
        elif 'ceo.nankai.edu.cn' in url:
            folder='nankai_ceo'
        elif 'cs.nankai.edu.cn' in url:
            folder='nankai_cs'
        elif 'cyber.nankai.edu.cn' in url:
            folder='nankai_cyber'
        elif 'finance.nankai.edu.cn' in url:
            folder='nankai_finance'
        elif 'history.nankai.edu.cn' in url:
            folder='nankai_history'
        elif 'law.nankai.edu.cn' in url:
            folder='nankai_law'
        elif 'news.nankai.edu.cn' in url:
            folder='nankai_news'
        elif 'phil.nankai.edu.cn' in url:
            folder='nankai_phil'
        elif 'sfs.nankai.edu.cn' in url:
            folder='nankai_sfs'
        elif 'weekly.nankai.edu.cn' in url:
            folder='nankai_weekly'
        elif 'wxy.nankai.edu.cn' in url:
            folder='nankai_wxy'
        elif 'zfxy.nankai.edu.cn' in url:
            folder='nankai_zfxy'
        else:
            folder=None
        result = {
            'title': hit['_source'].get('title', 'No title'),
            'url': url,
            'content': hit['_source'].get('content', '')[:300] + '...',  # 截取前300个字符
            'html_filename':html_filename,
            'folder':folder
        }
        # print(result)
        results.append(result)
    if 'user' in session:
        update_search_history(session['user'],query)
    # 返回结果
    return jsonify({'hits':results})


@app.route('/filesearch', methods=['POST'],endpoint='api_file_search') # 文档查询函数
def file_search():
    query = request.json.get('query')
    if not query:
        return jsonify({"error": "No query provided"}), 400

    user_boost_terms = [] # 用户的查询历史
    url_decrease_scores = [] # 用户的点击链接
    if 'user' in session:
        users = load_users()
        user = next((u for u in users['users'] if u['username'] == session['user']), None)
        if user:
            # Increase the weight of terms from search history
            user_boost_terms = [term for term in user['search_history']]
            # Decrease the weight of URLs that have been clicked
            url_decrease_scores = [url for url in user['clicked_links']]
    # 构建查询语句
    search_query = {
        "query": {
            "function_score": {
                "query": {
                    "multi_match": {
                        "query": query,
                        "fields": ["title", "content"],
                        "type": "best_fields"
                    }
                },
                "functions": [
                    # Boost terms from user's search history
                    *[
                        {"filter": {"match_phrase": {"content": term}}, "weight": 2}
                        for term in user_boost_terms
                    ],
                    # Decrease score for URLs that have been clicked
                     *[
                        {
                            "script_score": {
                                "script": {
                                    "source": "if (doc['url'].value == params.url) { return _score * 0.5 } else { return _score }",
                                    "params": {"url": url}
                                }
                            }
                        }
                        for url in url_decrease_scores
                    ]
                ],
                "score_mode": "sum",
                "boost_mode": "multiply"
            }
        },
        "collapse": {
            "field": "url"
        },
        "sort": [
            {"_score": {"order": "desc"}},
            {"pr": {"order": "desc"}}
        ],
        "size": 1000
    }

    # 执行搜索
    response = es.search(index='webpages', body=search_query)

    results = []
    for hit in response['hits']['hits']:
        html_filename = hit['_source'].get('html_filename','')
        url = hit['_source'].get('url','')
        folder=''
        if 'ai.nankai.edu.cn' in url:
            folder='nankai_ai'
        elif 'bs.nankai.edu.cn' in url:
            folder='nankai_bs'
        elif 'cc.nankai.edu.cn' in url:
            folder='nankai_cc'
        elif 'ceo.nankai.edu.cn' in url:
            folder='nankai_ceo'
        elif 'cs.nankai.edu.cn' in url:
            folder='nankai_cs'
        elif 'cyber.nankai.edu.cn' in url:
            folder='nankai_cyber'
        elif 'finance.nankai.edu.cn' in url:
            folder='nankai_finance'
        elif 'history.nankai.edu.cn' in url:
            folder='nankai_history'
        elif 'law.nankai.edu.cn' in url:
            folder='nankai_law'
        elif 'news.nankai.edu.cn' in url:
            folder='nankai_news'
        elif 'phil.nankai.edu.cn' in url:
            folder='nankai_phil'
        elif 'sfs.nankai.edu.cn' in url:
            folder='nankai_sfs'
        elif 'weekly.nankai.edu.cn' in url:
            folder='nankai_weekly'
        elif 'wxy.nankai.edu.cn' in url:
            folder='nankai_wxy'
        elif 'zfxy.nankai.edu.cn' in url:
            folder='nankai_zfxy'
        else:
            folder=None
        referenced_files = [ref for ref in hit['_source'].get('referenced_urls', [])
                            if any(ref.endswith(ext) for ext in ['.dox', '.docx', '.pdf', '.rar', '.zip', '.xlsx', '.xls', '.ppt', '.pptx', '.jpg', '.png'])]
        if referenced_files:
            result = {
                'title': hit['_source'].get('title', 'No title'),
                'url': url,
                'content': hit['_source'].get('content', '')[:300] + '...',  # 截取前300个字符
                'html_filename':html_filename,
                'folder':folder,
                'files':referenced_files
            }
            # print(result)
            results.append(result)
    if 'user' in session:
        update_search_history(session['user'],query)
    # 返回结果
    return jsonify({'hits':results})


if __name__ == '__main__':
    from elasticsearch import Elasticsearch
    es = Elasticsearch(['http://localhost:9200']) 
    app.run(debug=True)