from blacksheep.server import Application
from components.user import *
from components.book import *
from components.borrow import *
import orjson
# 图书消息队列
async def bookMqTask(app: Application):
    rediscon = app.services.build_provider().get(RedisCon)
    redis = rediscon.redis_conn
    booktable = await BooksTable.all().values()
    await redis.set('book:all',orjson.dumps(booktable))
    print(await redis.exists('bookstream'))
    if await redis.exists('bookstream') == 0:
        await redis.xgroup_create('bookstream','bookgroup',mkstream=True)
    for i in booktable:
        await redis.set('book:%s:%s' % (i['id'],i['isbn']),orjson.dumps(i))
    while True:
        getInfo = await redis.xreadgroup('bookgroup','bookconsumer',{'bookstream':'>'},block=0,count=5)
        print(getInfo)
        for i in getInfo[0][1]:
            print(i)
            await BooksTable.raw(i[1]['sql'])
            await redis.xack('bookstream','bookgroup',i[0])

# 借阅消息队列
async def borrowMqTask(app: Application):
    rediscon = app.services.build_provider().get(RedisCon)
    redis = rediscon.redis_conn
    borrowtable = await BooksTable.all().values()
    await redis.set('borrow:all',orjson.dumps(borrowtable))
    print(await redis.exists('borrowstream'))
    if await redis.exists('borrowstream') == 0:
        await redis.xgroup_create('borrowstream','borrowgroup',mkstream=True)
    for i in borrowtable:
        await redis.set('borrow:%s' % i['id'],orjson.dumps(i))

# 用户消息队列
async def userMqTask(app: Application):
    rediscon = app.services.build_provider().get(RedisCon)
    redis = rediscon.redis_conn
    userTable = await Users.all().values()
    print(await redis.exists('userstream'))
    if await redis.exists('userstream') == 0:
        await redis.xgroup_create('userstream','usergroup',mkstream=True)
    for i in userTable:
        await redis.set('user:%s:%s' % (i['userName'],i['id']),orjson.dumps(i))
