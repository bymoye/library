import asyncio
from functools import cache
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
    data = await redis.redis_conn.keys('book:%s:*'%id)
    if len(data) != 0:
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
    check = await redis.redis_conn.keys('book:*:%s'% item.isbn)
    if check != []:
        return res(400, '该书籍已存在')
    else:
       data = await BooksTable.create(**item.dict(exclude_unset=True))
       book = dict(i for i in data)
       await redis.set('book:%s:%s'%(book['id'],book['isbn']),orjson.dumps(book))
    return data_res(201, dict(i for i in book))

# patch /api/books/{id}
@auth('admin')
async def update_books(book: BookPydanticIn,id:int) -> Response:
    '''
    更新书籍
    '''
    if not await BooksTable.filter(id=id).exists() or await BooksTable.filter(isbn=book.isbn).exclude(id=id).exists():
        return res(400, '该书籍不存在或ISBN已存在')
    book = await BooksTable.filter(id=id).update(**book.dict(exclude_unset=True))
    return data_res(200, await BooksTable.filter(id=id).first().values())

# delete /api/books/{id}
@auth('admin')
async def delete_books(id:int) -> Response:
    '''
    删除书籍
    '''
    borrow_info = await BorrowTable.filter(borrowId=id,backdate=None).count()
    if borrow_info != 0:
        return res(400, '该书籍已被借出，无法删除')
    else:
        deletenum = await BooksTable.filter(id=id).delete()
        return res(204, '数据已不存在' if deletenum == 0 else '删除成功')
    

