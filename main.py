import asyncio
import orjson
from blacksheep.contents import Content
from blacksheep.messages import Request, Response
from blacksheep.server import Application
from tortoise.contrib.blacksheep import register_tortoise
from Auth import Init
from encr import Encryptor
from config import Gconfig
from components.user import *
from components.book import *
from components.borrow import *
from components.Authuser import AuthUser
from response import res
from components.rediscon import RedisCon
from components.Mq import *
from models import *
app = Application()
register_tortoise(
    app,
    # db_url="postgres://postgres:6306220a@42.193.254.118:5432/test",
    db_url="postgres://postgres:6306220a@42.193.254.118:5432/test",
    modules={"models": ["models"]},
    generate_schemas=True,
)
# 定义500错误返回为json
async def handler_error(request: Request, exc: Exception) -> Response:
    return Response(
            status = 500,
            content = Content(
                b"application/json",
                orjson.dumps({'status':500,'error':f'{exc}'})
                )
            )

app.handle_internal_server_error = handler_error

app.services.add_instance(Gconfig())
app.services.add_instance(AuthUser())
# app.services.add_instance(AuthUser)
Gconfig_out = app.services.build_provider().get(Gconfig)
Authser = app.services.build_provider().get(AuthUser)
app.services.add_instance(Encryptor(Gconfig_out))

# 死亡时，关闭redis连接
async def stop_something(app: Application):
    redis = app.services.build_provider().get(RedisCon)
    await redis.close()
    redis
app.on_stop += stop_something

# 开始时，启动redis连接
async def configure_something(app: Application):
    app.services.add_instance(RedisCon('192.168.56.1',10011,1))
    redis = app.services.build_provider().get(RedisCon)
    await redis.connect()
    # 创建后台任务，处理图书消息队列
    asyncio.get_event_loop().create_task(bookMqTask(app))
    # 创建后台任务，处理借阅消息队列
    asyncio.get_event_loop().create_task(borrowMqTask(app))
    # 创建后台任务，处理用户消息队列
    asyncio.get_event_loop().create_task(userMqTask(app))
    Authser = app.services.build_provider().get(AuthUser)
    await Authser.authenticate()

app.on_start += configure_something

app.services.add_instance(Init(app=app))
app.use_cors(
    allow_credentials=True,
    allow_methods="*",
    allow_origins="*",
    allow_headers="*",
    max_age=300,
)


get = app.router.add_get
post = app.router.add_post
delete = app.router.add_delete
put = app.router.add_put
patch = app.router.add_patch

# 用户登录 POST 返回token
post("/api/user/token", token)
# 用户注册 POST 返回注册信息
post("/api/user/register",reg)
# 删除用户 DELETE 返回删除信息 admin权限
delete("/api/user/delete/{id}",delect_user)
# 修改密码 POST 返回修改信息
post("/api/user/update",change_pass)
# 获取所有书籍 GET 返回书籍列表
get("/api/books",get_books)
# 屏蔽 改为分页获取


# 获取书籍分页 GET 返回书籍列表 一页9个
get("/api/books/page/{pagenum}",get_books_page)
# 获取某本书 GET 返回书籍信息
get("/api/books/{id}",get_book)
# 添加书籍 POST 返回添加信息 admin权限
post("/api/books",add_books)
# 更新书籍 PATCH 返回更新信息 admin权限
patch("/api/books/{id}",update_books)
# 删除书籍 DELETE 返回删除信息 admin权限
delete("/api/books/{id}",delete_books)

# 借书 POST 返回借书信息
post("/api/books/borrow/{id}",borrow_books)
# 查看当前用户借阅信息 POST 返回借书列表
get("/api/books/borrow",get_borrow)
# 查看指定用户借阅信息 POST 返回借书列表 admin权限
get("/api/books/borrow/{id}",get_borrow_id)
# 还书 POST 返回还书信息
post("/api/books/return/{id}",return_books)
