import re
import orjson
from blacksheep.contents import Content
from blacksheep.messages import Response
from blacksheep.server.authorization import auth
from guardpost.authentication import Identity
from dataclasses import dataclass
from pydantic.main import BaseModel
from tortoise.query_utils import Q
from encr import Encryptor
from models import UserPydanticIn,Users
from response import *
from components.rediscon import RedisCon
class Login_Form(BaseModel):
    userName: str
    passWord: str

@dataclass
class token_result:
    token: str
    expires_at: int
    token_type: str = "Bearer"
# POST /api/user/token
async def token(info:Login_Form,encr:Encryptor,redis:RedisCon) -> Response:
    '''
    登录获取token
    '''
    data = await redis.redis_conn.keys('user:%s:*' % info.userName)
    if data:
        data = orjson.loads(await redis.redis_conn.get(data[0]))
    else:
        return  res(404,"用户不存在")
    # data = await Users.filter(userName=info.userName).first()
    # if data == None:
    #     return  res(404,"用户不存在")
    if data['passWord'] == encr.hash_password(info.passWord):
        if data['state'] != 0:
            return res(403,"用户已被禁用")
        token,exp = encr.creact_jwt_token({'ID':data['id'],'UserName':data['userName'],'role':data['role'],'state':data['state'],'createDate':str(data['createDate'])})
        return Response(
            status=200,
            content = Content(
                b"application/json",
                orjson.dumps(token_result(token,exp))
                )
            )
    else:
        return res(401,"密码错误")


# POST /api/user/register
async def reg(info:UserPydanticIn,encry:Encryptor,redis:RedisCon) -> Response:
    '''
    注册
    '''
    if await redis.redis_conn.keys('user:%s:*' % info.userName):
        return res(409,"用户名已存在")
    if re.match(r'^(?![0-9]+$)(?![a-zA-Z]+$)[0-9A-Za-z_.-]{6,16}$', info.passWord) is None:
        return res(400,"密码格式错误")
    info.passWord = encry.hash_password(info.passWord)
    await Users.create(**info.dict(exclude_unset=True))
    return res(201,"注册成功")

# DELETE /api/user/delete/{id}
@auth('admin')
async def delect_user(id:int,user: Identity) -> Response:
    '''
    删除用户
    '''
    authuser = user.claims.get("ID")
    role = user.claims.get("role")
    # 普通管理员权限控制
    if role == 1:
        find_user = await Users.filter(id=id).first().values('role')
        if find_user is None:
            return res(404,"用户不存在")
        if authuser == id:
            return res(403,"不能删除自己")
        if find_user['role'] == 1:
            return res(403,"权限不足,不能删除管理员")
        if find_user['role'] == 2:
            return res(403,"权限不足,不能删除超级管理员")
    await Users.filter(id=id).delete()
    return res(204,"删除成功")

class change_pass_form(BaseModel):
    current_pass: str
    passWord: str
    repassword: str

@auth("authenticated")
async def change_pass(info:change_pass_form,user:Identity,encry:Encryptor) -> Response:
    '''
    修改密码
    '''
    authuser = user.claims.get("ID")
    if info.passWord != info.repassword:
        return res(400,"两次密码不一致")
    if await Users.filter(id=authuser,passWord=encry.hash_password(info.current_pass)).exists():
        await Users.filter(id=authuser).update(passWord=encry.hash_password(info.passWord))
        return res(200,"修改成功")
    else:
        return res(400,"密码错误")