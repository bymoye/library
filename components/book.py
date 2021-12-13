import asyncio
import orjson
from blacksheep.contents import Content
from blacksheep.messages import Response
from blacksheep.server.authorization import auth
from tortoise.fields import data
from models import BookPydanticIn,BookPydanticOut,BooksTable,BorrowTable
from response import *
from components.rediscon import RedisCon
# GET /api/books
async def get_books(redis: RedisCon) -> BookPydanticOut:
    # 获取所有书籍
    # 优先从Redis缓存中获取
    context = await redis.get('book:all')
    # 如果缓存中有则直接返回缓存中的数据
    if context:
        context = orjson.loads(context)
        total_number = len(context)
    else:
        try:
            # 如果缓存中没有则添加一个互斥锁
            set = await redis.setnx('Book:Lock', 'True')
            # 如果该key已经存在则直接返回服务器繁忙的提示
            if not set: 
                return res(500, '服务器繁忙')
            # 获取book表所有内容
            booktable = await BooksTable.all().values()
            # 放置到redis中
            await redis.set('book:all',orjson.dumps(booktable))
            total_number = await BooksTable.all().count()
            # 解锁
            await redis.delete('Book:Lock')
        except:
            # 出现异常时也解锁
            await redis.delete('Book:Lock')
    return Response(
        status = 200,
        content=Content(
            b'application/json',
            orjson.dumps({'status':200,'data':context if context else booktable,'total_number':total_number})
        )
    )

# GET /api/books/page/{pagenum}
async def get_books_page(pagenum: int,redis:RedisCon) -> Response:
    '''
    分页获取书籍
    '''
    cache_data = await redis.get('book:all')
    if cache_data:
        data = orjson.loads(cache_data)
        # 切片 每页9个
        context = data[(pagenum-1)*9:pagenum*9]
        total_number = len(data)
    else:
        try:
            # 如果缓存中没有则添加一个互斥锁
            set = await redis.setnx('Book:Lock', 'True')
            # 如果该key已经存在则直接返回服务器繁忙的提示
            if not set: 
                return res(500, '服务器繁忙')
            # 获取book表所有内容
            booktable = await BooksTable.all().values()
            # 放置到redis中
            data = orjson.dumps(booktable)
            context = booktable[(pagenum-1)*9:pagenum*9]
            await redis.set('book:all',data)
            total_number = len(booktable)
            # 解锁
            await redis.delete('Book:Lock')
        except:
            # 出现异常时也解锁
            await redis.delete('Book:Lock')
    if len(context) == 0:
        return res(404, '没有更多书籍了')
    return Response(
        status = 200,
        content=Content(
            b'application/json',
            orjson.dumps({'status':200,'data':context,'total_number':total_number})
    )
    )

# GET /api/books/{id}
async def get_book(id: int,redis:RedisCon) -> Response:
    '''
    获取指定书籍
    '''
    # 从redis中搜索匹配
    cur,data = await redis.redis_conn.scan(match='book:%s:*'%id,count=1000)
    # 当游标(cur)为0时表示搜索完毕 否则继续搜索
    while cur != 0 and data == []:
        data = await redis.redis_conn.scan(cursor = cur,match='book:%s:*'%id,count=1000)
    # 当搜索完毕数据不为空时
    if data != []:
        data = orjson.loads(await redis.get(data[0]))
        return data_res(200,data)
    else:
        return res(404, '没有找到该书籍')

# POST /api/books
@auth('admin')
async def add_books(item : BookPydanticIn,redis:RedisCon) -> Response:
    '''
    添加书籍
    '''
    # 搜索书籍是否存在
    cur,data = await redis.redis_conn.scan(match='book:*:%s'% item.isbn,count=1000)
    # 游标为0表示搜索完毕 否则继续搜索
    while cur != 0 and data == []:
        cur,data = await redis.redis_conn.scan(cursor = cur,match='book:*:%s'% item.isbn,count=1000)
    # 如果搜索完毕数据不为空时
    if data != []:
        return res(400, '该书籍已存在')
    else:
       # 否则添加书籍
       data = await BooksTable.create(**item.dict(exclude_unset=True))
       # 将书籍信息放入redis中
       book = dict(i for i in data)
       await redis.set('book:%s:%s'%(book['id'],book['isbn']),orjson.dumps(book))
       # 清除book:all缓存 以等待下次请求 更新数据
       await redis.delete('book:all')
    return data_res(201, dict(i for i in book))

# patch /api/books/{id}
@auth('admin')
async def update_books(book: BookPydanticIn,id:int,redis:RedisCon) -> Response:
    '''
    更新书籍
    '''
    # 搜索书籍是否存在
    idcur,idcheck = await redis.redis_conn.scan(match='book:%s:*'%id,count=1000)
    # 搜索
    isbncur,isbncheck = await redis.redis_conn.scan(match='book:*:%s'% book.isbn,count=1000)
    while idcur != 0 and idcheck == []:
        idcur,idcheck = await redis.redis_conn.scan(cursor = idcur,match='book:%s:*'%id,count=1000)
    while isbncur != 0 and isbncheck == []:
        isbncur,isbncheck = await redis.redis_conn.scan(cursor = isbncur,match='book:*:%s'% book.isbn,count=1000)
    # 如果搜索完毕数据为空
    if idcheck == []:
        return res(400,'该书籍不存在')
    # 判断该isbn是否已经存在
    if isbncheck != [] and isbncheck[0].decode().split(':')[1].strip() != str(id):
        return res(400, '该ISBN已存在')
    # 生成一个sql
    booksql = BooksTable.filter(id=id).update(**book.dict(exclude_unset=True)).sql()
    # 提交到 bookstream 消息队列
    await redis.redis_conn.xadd('bookstream',{'msg':'bookupdate','sql':booksql})
    key = idcheck[0].decode()
    data = orjson.loads(await redis.get(key))
    # 删除当前缓存
    await redis.delete(key)
    # 重新将数据放入缓存
    await redis.set('book:%s:%s'%(id,book.isbn),orjson.dumps({**data,**book.dict(exclude_unset=True)}))
    return data_res(200, orjson.loads(await redis.get('book:%s:%s'%(id,book.isbn))))

# delete /api/books/{id}
@auth('admin')
async def delete_books(id:int,redis:RedisCon) -> Response:
    '''
    删除书籍
    '''
    # 搜索该书籍是否已经被借出
    cur,borrow = await redis.redis_conn.scan(match='borrow:*:%s:*:false'%id,count=1000)
    while cur != 0 and borrow == []:
        borrow = await redis.redis_conn.scan(cursor=cur,match='borrow:*:%s:*:false'%id,count=1000)
    # 如果该书籍已经被借出
    if borrow != []:
        return res(400,'该书籍已被借出，无法删除')
    # 否则查找相应的书籍
    cur,book = await redis.redis_conn.scan(match='book:%s:*'%id,count=1000)
    while cur != 0 and book == []:
        cur,book = await redis.redis_conn.scan(cursor=cur,match='book:%s:*'%id,count=1000)
    # 
    if book == []:
        return res(400,'该书籍不存在')
    # 提交到消息队列
    await redis.redis_conn.xadd('bookstream',{'msg':'bookdelete','sql':BooksTable.filter(id=id).delete().sql()})
    # 删除缓存
    await redis.delete('book:all')
    await redis.delete(book[0].decode())
    return res(200,'删除成功')
