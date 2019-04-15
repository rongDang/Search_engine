from django.shortcuts import render, HttpResponse, render_to_response
from search.models import DouBanIndex, CsdnBlogIndex
from elasticsearch import Elasticsearch
from datetime import datetime
import redis
import json

# 查询es中的数据直接连接Elasticsearch即可，elasticsearch_dsl是在elasticsearch的基础上进行开发的
client = Elasticsearch(hosts=["localhost"])
# 连接本地redis, redis没有设置的密码的话，不需要填写密码，默认连接本地redis 6379端口
redis_cli = redis.StrictRedis()


def index(request):
    return render(request, "index.html")


def result(request):
    # 获取搜索关键字和对应搜索类型
    key_word = request.GET.get("key", "")
    search_type = request.GET.get("type", "")

    page = request.GET.get("page", "1")

    # 对搜索关键字加1操作, redis有序集合
    if key_word:
        redis_cli.zincrby("keywords_set", 1, key_word)

    top_list = []
    # 获取查询次数最高的6个关键字,从最大值取到最小值, 下标从0开始,取6个
    tops = redis_cli.zrevrangebyscore("keywords_set", "+inf", "-inf", start=0, num=6)
    for i in tops:
        # 从redis中获取的数据类型是byte类型,需要转换
        top_list.append(str(i, encoding="utf-8"))

    # 从redis中获取爬取的数量
    douban_count = str(redis_cli.get("movie_count"), encoding="utf-8")
    csdn_count = str(redis_cli.get("csdn_count"), encoding="utf-8")

    # 搜索开始时间
    start_time = datetime.now()

    response = {}
    hit_list = []
    if search_type == "douban":
        response = client.search(
            index="movie",
            body={
                # from:从哪里开始，size:显示几条数据
                "from": (int(page)-1) * 1, "size": 6,
                "query": {
                    "multi_match": {
                        "query": key_word,
                        # 选择查询的字段，从下面这些字段中查找搜索关键字
                        "fields": ["name", "alias", "introduce"]
                    }
                },
                "highlight": {
                    # 用span标签高亮关键字
                    "pre_tags": ["<span class='keyword'>"],
                    "post_tags": ["</span>"],
                    # 高亮的字段
                    "fields": {
                        "name": {},
                        "alias": {},
                        "introduce": {}
                    }
                }
            }
        )

        for hit in response["hits"]["hits"]:
            hit_dict = {}
            # 判断搜索的title是否在高亮范围内，在的话则使用高亮的title结果， 否则使用原始的搜索结果
            if "name" in hit["highlight"]:
                hit_dict["title"] = "".join(hit["highlight"]["name"])
            else:
                hit_dict["title"] = hit["_source"]["name"]
            if "alias" in hit["highlight"]:
                hit_dict["alias"] = "".join(hit["highlight"]["alias"])
            else:
                hit_dict["alias"] = hit["_source"]["alias"]
            if "introduce" in hit["highlight"]:
                hit_dict["introduce"] = "".join(hit["highlight"]["introduce"])
                print(hit_dict["introduce"])
            else:
                hit_dict["introduce"] = hit["_source"]["introduce"]
            hit_dict["url"] = hit["_source"]["url"]
            hit_dict["rate"] = hit["_source"]["rate"]
            hit_dict["date"] = hit["_source"]["date"]
            hit_dict["directors"] = hit["_source"]["directors"]
            hit_dict["casts"] = hit["_source"]["casts"]

            hit_list.append(hit_dict)
        print(hit_list)
    elif search_type == "CSDN":
        response = client.search(
            index="csdn",
            body={
                # from:从哪里开始，size:显示几条数据
                "from": (int(page) - 1) * 1, "size": 6,
                "query": {
                    "multi_match": {
                        "query": key_word,
                        # 选择查询的字段，从下面这些字段中查找搜索关键字
                        "fields": ["title", "content", "nick_name"]
                    }
                },
                "highlight": {
                    # 用span标签高亮关键字
                    "pre_tags": ["<span class='keyword'>"],
                    "post_tags": ["</span>"],
                    # 高亮的字段
                    "fields": {
                        "title": {},
                        "content": {},
                        "nick_name": {}
                    }
                }
            }
        )

        for hit in response["hits"]["hits"]:
            hit_dict = {}
            # 判断搜索的title是否在高亮范围内，在的话则使用高亮的title结果， 否则使用原始的搜索结果
            if "title" in hit["highlight"]:
                hit_dict["title"] = "".join(hit["highlight"]["title"])
            else:
                hit_dict["title"] = hit["_source"]["title"]
            if "content" in hit["highlight"]:
                hit_dict["content"] = "".join(hit["highlight"]["content"])
            else:
                hit_dict["content"] = hit["_source"]["content"][:200]
            if "nick_name" in hit["highlight"]:
                hit_dict["nick_name"] = "".join(hit["highlight"]["nick_name"])
            else:
                hit_dict["nick_name"] = hit["_source"]["nick_name"]
            hit_dict["date"] = hit["_source"]["date"].replace("T", " ")
            hit_dict["user_url"] = hit["_source"]["user_url"]
            hit_dict["blog_url"] = hit["_source"]["blog_url"]

            hit_list.append(hit_dict)
        print(hit_list)

    # 获取搜索结果的数量
    total_nums = response["hits"]["total"]
    # 搜索结束时间
    end_time = datetime.now()
    # 使用total_seconds()来计算总的搜索时间
    elapsed_seconds = (end_time-start_time).total_seconds()
    return render(request, "result.html", locals())


def search_suggest(request):
    # 获取搜索的关键字和类型
    key_word = request.GET.get("key", "")
    search_type = request.GET.get("type", "")
    if search_type == "douban":
        suggest_list = []
        if key_word:
            # 创建一个豆瓣的搜索实例
            search = DouBanIndex.search()
            """fuzzy:模糊匹配，fuzziness:编辑距离(允许错误的数)"""
            s = search.suggest('my_suggest', key_word, completion={
                "field": "suggest", "fuzzy": {
                    "fuzziness": 2
                },
                # 获取前10条数据
                "size": 10
            })
            # 执行搜索，返回查询结果
            suggestions = s.execute()
            for match in suggestions.suggest.my_suggest[0].options[:10]:
                # 指定source的数据
                source = match._source
                # 将获取的标题存到列表中
                suggest_list.append(source["name"])
            print(suggest_list)
        return HttpResponse(json.dumps(suggest_list), content_type="application/json")
    elif search_type == "CSDN":
        suggest_list = []
        if key_word:
            # 创建一个CSDN的搜索实例
            search = CsdnBlogIndex.search()
            """fuzzy:模糊匹配，fuzziness:编辑距离(允许错误的数)"""
            s = search.suggest('my_suggest', key_word, completion={
                "field": "suggest", "fuzzy": {
                    "fuzziness": 2
                },
                # 获取前10条数据
                "size": 10
            })
            # 执行搜索，返回查询结果
            suggestions = s.execute()
            for match in suggestions.suggest.my_suggest[0].options[:10]:
                # 指定source的数据
                source = match._source
                # 将获取的标题存到列表中
                suggest_list.append(source["title"])
            print(suggest_list)
        return HttpResponse(json.dumps(suggest_list), content_type="application/json")


def test(request):
    return render(request, 'test.html')


def page_not_found(request):
    return render_to_response('404.html')


def page_error(request):
    return render_to_response('500.html')
