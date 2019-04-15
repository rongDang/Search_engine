from django.test import TestCase

# Create your tests here.
import redis
redis_cli = redis.StrictRedis()

# redis_cli.incr("test_redis")
# redis_cli.zincrby("test", 1, "小白测试")
# redis_cli.zrevrangebyscore(
#     "search_keywords_set", "+inf", "-inf", start=0, num=5
# )

# print(redis_cli.zrevrangebyscore("test", "+inf", "-inf", start=0, num=6))


