from pydantic.class_validators import validator
from tortoise import fields, models
from tortoise.contrib.pydantic import pydantic_model_creator
from pydantic import validate_email
from tortoise.exceptions import ValidationError
import re
def validateEmail(value: str):
    try:
        validate_email(value)
    except:
        raise ValidationError("无效电子邮件")
def validateUserName(value: str):
    if re.match(r'^[a-zA-Z]{1}[a-zA-Z0-9_]{4,12}$', value) is None:
        raise ValidationError("用户名不合法")

def validatetelephone(value: str):
    if re.match(r'^1[3-9]\d{9}$', value) is None:
        raise ValidationError("无效手机号")

class Users(models.Model):
    id = fields.IntField(pk=True)   # 用户ID (唯一,primary key,自增)
    userName = fields.CharField(max_length=20, unique=True, validators=[validateUserName])  # 用户名 (唯一,unique)
    passWord = fields.CharField(max_length=200) # 密码 交由程序校验 规则 ^(?![0-9]+$)(?![a-zA-Z]+$)[0-9A-Za-z_.-]{6,16}$
    email = fields.CharField(max_length=50, validators=[validateEmail]) # 邮箱
    telephone = fields.CharField(max_length=11,validators=[validatetelephone])  # 手机号
    role = fields.SmallIntField(default=0)  # 角色 0:普通用户 1:管理员 2:超级管理员
    state = fields.SmallIntField(default=0) # 状态 0:正常 1:禁用
    createDate = fields.DatetimeField(auto_now_add=True) # 创建时间
    
    borrowtable : fields.ReverseRelation["BorrowTable"] # 外键关系容器
    
class BooksTable(models.Model):
    id = fields.IntField(pk=True)       # 书籍ID (唯一,primary key,自增)
    isbn = fields.CharField(max_length=20, unique=True) # 书籍ISBN (唯一,unique)
    author = fields.CharField(max_length=20)    # 书籍作者
    bookName = fields.CharField(max_length=50)  # 书籍名称
    bookAmount = fields.IntField(default=0)     # 书籍数量
    Tag = fields.TextField(default="未分类")    # 书籍标签
    Content = fields.TextField(default="")      # 书籍简介
    Cover = fields.CharField(max_length=200,default="") # 书籍封面
    
    borrowtable : fields.ReverseRelation["BorrowTable"] # 外键关系容器
    
    
class BorrowTable(models.Model):
    id = fields.IntField(pk=True)    # 借阅ID (唯一,primary key,自增)
    borrowUser : fields.ForeignKeyRelation[BooksTable] = fields.ForeignKeyField(
        "models.Users", related_name="borrowtable", to_field="id"
    )   # 借阅用户 外键取自Users表
    borrowId : fields.ForeignKeyRelation[BooksTable] = fields.ForeignKeyField(
        "models.BooksTable", related_name="borrowtable", to_field="id"
    )   # 借阅书籍  外键取自BooksTable表
    borrowTime = fields.DatetimeField(auto_now_add=True)    # 借阅时间
    backdate = fields.DatetimeField(null=True)  # 还书时间
        
UserPydanticOut = pydantic_model_creator(Users, name="UserOut")
UserPydanticIn = pydantic_model_creator(Users, name="UserIn", exclude=('id','createDate','role','state'),exclude_readonly=True)
LoginPydanticIn = pydantic_model_creator(Users, name="LoginIn", exclude=('id','createDate','role','state','passWord'),exclude_readonly=True)
LoginPydanticOut = pydantic_model_creator(Users, name="LoginOut", exclude=('id','createDate','role','state','passWord'),exclude_readonly=True)
BookPydanticOut = pydantic_model_creator(BooksTable, name="BookOut")
BookPydanticIn = pydantic_model_creator(BooksTable, name="BookIn", exclude=('id'),exclude_readonly=True)
BorrowPydanticOut = pydantic_model_creator(BorrowTable,exclude_readonly=False)
BorrowPydanticIn = pydantic_model_creator(BorrowTable, name="BorrowIn", exclude=('id','borrowTime','backdate'))
