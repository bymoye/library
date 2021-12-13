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
    if await redis.exists('bookstream') == 0:
        await redis.xgroup_create('bookstream','bookgroup',mkstream=True)
    for i in booktable:
        await redis.set('book:%s:%s' % (i['id'],i['isbn']),orjson.dumps(i))
    while True:
        getInfo = await redis.xreadgroup('bookgroup','bookconsumer',{'bookstream':'>'},block=0,count=10)
        for i in getInfo[0][1]:
            await BooksTable.raw(i[1][b'sql'].decode('utf-8'))
            await redis.xack('bookstream','bookgroup',i[0])

# 借阅消息队列
async def borrowMqTask(app: Application):
    rediscon = app.services.build_provider().get(RedisCon)
    redis = rediscon.redis_conn
    borrowtable = await BorrowTable.all().values()
    await redis.set('borrow:all',orjson.dumps(borrowtable))
    if await redis.exists('borrowstream') == 0:
        await redis.xgroup_create('borrowstream','borrowgroup',mkstream=True)
    for i in borrowtable:
        back = 'false' if i['backdate'] == None else 'true'
        await redis.set('borrow:%s:%s:%s:%s' % (i['borrowUser_id'],i['borrowId_id'],i['id'],back),orjson.dumps(i))
    while True:
        getInfo = await redis.xreadgroup('borrowgroup','borrowconsumer',{'borrowstream':'>'},block=0,count=10)
        for i in getInfo[0][1]:
            print('#',i)
            # try:
            print(i[1][b'msg'].decode())
            if i[1][b'msg'].decode() == '借书成功':
                print('1')
                data = await BorrowTable.raw(i[1][b'sql'].decode('utf-8'))
                BorrowTable.save(data)
                print('@',data)
                await redis.set('borrow:%s:%s:%s:false' % (data['borrowUser_id'],data['borrowId_id'],data['id']),orjson.dumps(data))
                await redis.delete(f"borrow:{i[1][b'user'].decode()}:lock")
                await redis.xack('borrowstream','borrowgroup',i[0])
            # except:
            #     print('2')
            #     await redis.delete(f"borrow:{i[1][b'user'].decode()}:lock")
                
        

# 用户消息队列
async def userMqTask(app: Application):
    rediscon = app.services.build_provider().get(RedisCon)
    redis = rediscon.redis_conn
    userTable = await Users.all().values()
    if await redis.exists('userstream') == 0:
        await redis.xgroup_create('userstream','usergroup',mkstream=True)
    for i in userTable:
        await redis.set('user:%s:%s' % (i['userName'],i['id']),orjson.dumps(i))
