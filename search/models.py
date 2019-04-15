"""
    elasticsearch的字段类型，类似django的ORM中的字段，使用dsl的原因，是它的中文分词效果更好
"""
from elasticsearch_dsl import Text, Date, Keyword, Document, Completion, Float
from elasticsearch_dsl.connections import connections
from elasticsearch_dsl import analyzer

# 创建es的连接
connections.create_connection(hosts=["localhost"])

# 分词级别ik_smart: 会做最粗粒度的拆分，比如会将“中华人民共和国国歌”拆分为“中华人民共和国,国歌”。
my_analyzer = analyzer("ik_smart")


class CsdnBlogIndex(Document):
    suggest = Completion(analyzer="ik_max_word")
    blog_id = Keyword()
    title = Text(analyzer="ik_max_word")
    content = Text(analyzer="ik_smart")
    nick_name = Text(analyzer="ik_smart")
    user_url = Keyword()
    blog_url = Keyword()
    date = Date()

    class Index:
        name = "csdn"

        # 设置分片数量，副本数量，
        settings = {
            "number_of_shards": 2,
            "number_of_replicas": 0
        }


class DouBanIndex(Document):
    """
        :param: 电影id，电影名，别名，简介，链接，导演，演员，类型，上映时间
    """
    suggest = Completion(analyzer=my_analyzer)
    movie_id = Keyword()
    name = Text(analyzer="ik_max_word")
    alias = Text(analyzer="ik_smart")
    introduce = Text(analyzer="ik_smart")
    url = Keyword()
    directors = Keyword()
    rate = Float()
    casts = Keyword()
    type = Keyword()
    date = Keyword()

    class Index:
        name = "movie"

        # 设置分片数量，副本数量，
        settings = {
            "number_of_shards": 2,
            "number_of_replicas": 0
        }
