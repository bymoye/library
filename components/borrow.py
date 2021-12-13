import orjson
from blacksheep.contents import Content
from blacksheep.messages import Response
from blacksheep.server.authorization import auth
from guardpost.authentication import Identity
from typing import Optional
from models import Users,BooksTable,BorrowTable
from response import *
from datetime import datetime
from components.rediscon import RedisCon
# POST /api/books/borrow/{id}
@auth("authenticated")
async def borrow_books(id:int,user: Optional[Identity],redis:RedisCon) -> Response:
    '''
    借书
    '''
    # 获取当前用户的ID
    user = user.claims.get("ID")
    # 搜索当前用户是否已经借阅过该书籍
    cur,data = await redis.redis_conn.scan(match=f"borrow:{user}:{id}:*:false",count=1000)
    while cur != 0 and data == []:
        cur,data = await redis.redis_conn.scan(cursor=cur,match=f"borrow:{user}:{id}:*:false",count=1000)
    if data != []:
        return res(403,"该书籍已被您借出，且尚未归还")
    # 搜索该书是否存在
    bookcur,bookdata = await redis.redis_conn.scan(match=f"book:{id}:*",count=1000)
    while bookcur != 0 and bookdata == []:
        bookcur,bookdata = await redis.redis_conn.scan(cursor=cur,match=f"book:{id}:*",count=1000)
    # 如果书籍不存在
    if bookdata == []:
        return res(404,"该书籍不存在")
    # 读入书籍信息
    nbook = orjson.loads(await redis.get(bookdata[0].decode("utf-8")))
    if nbook.get('bookAmount') == 0:
        return res(400, "该书籍已借完")
    try:
        # 加锁
        Lock = await redis.redis_conn.setnx(f"borrow:{user}:lock",'true')
        # 判断锁是否已经加过
        if Lock == 0:
            return res(400,"您有借阅请求已提交处理,请等待处理完毕后再提交")
        # 重新获取一下书籍信息
        nbook = orjson.loads(await redis.get(bookdata[0].decode("utf-8")))
        # 书籍数量减一
        nbook['bookAmount'] -= 1
        # 先更新redis
        await redis.set(bookdata[0].decode("utf-8"),orjson.dumps(nbook))
        User = await Users.filter(id=user).first()
        borrowId = await BooksTable.filter(id=id).first()
        # 再对数据库进行更新
        borrow = await BorrowTable.create(borrowId = borrowId,borrowUser = User)
        await BooksTable.filter(id=id).update(bookAmount = nbook['bookAmount'])
        # borrow为元组，所以要将元组转为字典
        data = dict({i for i in borrow})
        # 将数据放入redis中
        await redis.set(f"borrow:{user}:{id}:{data['id']}:false",orjson.dumps(await BorrowTable.filter(id=data['id']).first().values()))
        # 删除锁
        await redis.delete(f"borrow:{user}:lock")
        await redis.delete(f"borrow:{user}:all")
        # 返回数据
        return data_res(201,data)
    except:
        await redis.delete(f"borrow:{user}:lock")
        return res(400,"提交借阅请求失败")

# GET /api/books/borrow
@auth("authenticated")
async def get_borrow(user: Identity,redis:RedisCon) -> Response:
    '''
    获取当前用户借阅的书籍
    '''
    # 获取当前登录用户的ID
    user = user.claims.get("ID")
    # 从Redis中获取数据
    cache = await redis.get(f"borrow:{user}:all")
    # 如果Redis中有数据 就从缓存中取
    if cache != None:
        contents = orjson.loads(cache.decode("utf-8"))
    else:
        # 否则从数据库中取
        contents = await BorrowTable.filter(borrowUser=user).all().values('id','borrowId_id','borrowTime','backdate','borrowId__bookName')
        # 然后存到Redis中
        await redis.set(f"borrow:{user}:all",orjson.dumps(contents))
    if contents == []:
        return res(400, "您还没有借阅任何书籍")
    return data_res(200,contents)

# GET /api/books/borrow/{id}
@auth("admin")
async def get_borrow_id(id:int,redis:RedisCon) -> Response:
    '''
    获取指定用户借阅的书籍
    '''
    # 搜索当前用户是否存在
    cur,user = await redis.redis_conn.scan(match=f"user:*:{id}",count=1000)
    # scan cur为0时才代表全部搜索完毕
    while cur != 0 and user == []:
        cur,user = await redis.redis_conn.scan(cursor=cur,match=f"user:*:{id}",count=1000)
    if user == []:
        return res(404, "用户不存在")
    # 用户存在 进入下一步 搜索该用户借阅的书籍
    cache = await redis.get(f"borrow:{id}:all")
    # 如果缓存中没有则从数据库中取
    if cache != None:
        contents = orjson.loads(cache.decode("utf-8"))
    else:
        contents = await BorrowTable.filter(borrowUser=id).all().values('id','borrowId_id','borrowTime','backdate','borrowId__bookName')
        # 写入缓存
        await redis.set(f"borrow:{id}:all",orjson.dumps(contents))
    if contents == []:
        return res(400, "该用户没有借阅任何书籍")
    return Response(
        status=200,
        content=Content(b"application/json",
                        orjson.dumps({"status":200,"userId":id,"data":contents})
        )
    )

# POST /api/books/return/{id}
@auth("authenticated")
async def return_books(id:int,user: Identity,redis:RedisCon) -> Response:
    '''
    还书
    ''' 
    user = user.claims.get('ID')
    # 上锁
    lock = await redis.redis_conn.setnx(f"return:{user}:{id}:lock",'true')
    if lock == 0:
        return res(400,"请勿多次请求")
    try:
        # 从数据库中获取借阅信息
        info = await BorrowTable.filter(id=id,borrowUser=user).first().values('id','borrowId_id','borrowTime','backdate','borrowId__bookAmount')
        if info == None:
            return res(404, "该借阅记录不存在")
        if info['backdate'] != None:
            return res(400, "该借阅记录已归还")
        # 将数据库中的数据更新 backdate已存在则代表已归还
        await BorrowTable.filter(id=id,borrowUser=user).update(backdate=datetime.now())
        # 将数据库中的数据更新 书本数量+1
        await BooksTable.filter(id=info['borrowId_id']).update(bookAmount = info['borrowId__bookAmount'] + 1)
        # 删除该用户的借阅缓存
        await redis.delete(f"borrow:{user}:all")
        # 从Redis中搜索该条借阅记录
        cur,data = await redis.redis_conn.scan(match=f"borrow:{user}:*:{id}:false",count=1000)
        while cur != 0 and data == []:
            cur,data = await redis.redis_conn.scan(cursor=cur,match=f"borrow:{user}:*:{id}:false",count=1000)
        # 并删除
        await redis.delete(data[0].decode("utf-8"))
        # 返回信息
        returninfo = await BorrowTable.get(id=id,borrowUser=user).values('id','borrowId_id','borrowTime','backdate')
        # 重新写入该条记录 并且标记为已归还
        await redis.set(f"borrow:{user}:{returninfo['borrowId_id']}:{id}:true",orjson.dumps(returninfo))
        return data_res(200,returninfo)
    finally:
        # 删除锁
        await redis.redis_conn.delete(f"borrow:{user}:{id}:lock")