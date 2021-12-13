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
async def borrow_books(id:int,user: Optional[Identity]) -> Response:
    '''
    借书
    '''
    user = user.claims.get("ID")
    if await BorrowTable.filter(borrowId=id,borrowUser=user,backdate=None).exists():
        return res(400, "该书籍已被您借出，且尚未归还")
    data = await BooksTable.filter(id=id).first()
    if data is None:
        return res(400, "该书籍不存在")
    if data.bookAmount == 0:
        return res(400, "该书籍已借完")
    User = await Users.filter(id=user.claims.get("ID")).first()
    borrowId = await BooksTable.filter(id=id).first()
    borrow = await BorrowTable.create(borrowId = borrowId,borrowUser = User)
    await BooksTable.filter(id=id).update(bookAmount = data.bookAmount-1)
    return data_res(201,dict([i for i in borrow]))

# GET /api/books/borrow
@auth("authenticated")
async def get_borrow(user: Identity) -> Response:
    '''
    获取当前用户借阅的书籍
    '''
    user = user.claims.get("ID")
    contents = await BorrowTable.filter(borrowUser=user).all().values('id','borrowId_id','borrowTime','backdate','borrowId__bookName')
    if contents == []:
        return res(400, "您还没有借阅任何书籍")
    return data_res(200,contents)

# GET /api/books/borrow/{id}
@auth("admin")
async def get_borrow_id(id:int,user: Identity) -> Response:
    '''
    获取指定用户借阅的书籍
    '''
    if not await Users.filter(id=id).exists():
        return res(404, "用户不存在")
    contents = await BorrowTable.filter(borrowUser=id).all().values('id','borrowId_id','borrowTime','backdate','borrowId__bookName')
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
async def return_books(id:int,user: Identity) -> Response:
    '''
    还书
    '''
    info = await BorrowTable.filter(id=id,borrowUser=user.claims.get("ID")).first().values('id','borrowId_id','borrowTime','backdate','borrowId__bookAmount')
    if info == None:
        return res(404, "该借阅记录不存在")
    if info['backdate'] != None:
        return res(400, "该借阅记录已归还")
    await BorrowTable.filter(id=id,borrowUser=user.claims.get("ID")).update(backdate=datetime.now())
    await BooksTable.filter(id=info['borrowId_id']).update(bookAmount = info['borrowId__bookAmount'] + 1)
    returninfo = await BorrowTable.get(id=id,borrowUser=user.claims.get("ID")).values('id','borrowId_id','borrowTime','backdate')
    return data_res(200,returninfo)