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
    id = fields.IntField(pk=True)
    userName = fields.CharField(max_length=20, unique=True, validators=[validateUserName])
    passWord = fields.CharField(max_length=200)
    email = fields.CharField(max_length=50, validators=[validateEmail])
    telephone = fields.CharField(max_length=11,validators=[validatetelephone])
    role = fields.SmallIntField(default=0)
    state = fields.SmallIntField(default=0)
    createDate = fields.DatetimeField(auto_now_add=True)
    
    borrowtable : fields.ReverseRelation["BorrowTable"]
    
class BooksTable(models.Model):
    id = fields.IntField(pk=True)
    isbn = fields.CharField(max_length=20, unique=True)
    author = fields.CharField(max_length=20)
    bookName = fields.CharField(max_length=50)
    bookAmount = fields.IntField(default=0)
    Tag = fields.TextField(default="未分类")
    Content = fields.TextField(default="")
    Cover = fields.CharField(max_length=200,default="")
    
    borrowtable : fields.ReverseRelation["BorrowTable"]
    
    
class BorrowTable(models.Model):
    id = fields.IntField(pk=True)
    borrowUser : fields.ForeignKeyRelation[BooksTable] = fields.ForeignKeyField(
        "models.Users", related_name="borrowtable", to_field="id"
    )
    borrowId : fields.ForeignKeyRelation[BooksTable] = fields.ForeignKeyField(
        "models.BooksTable", related_name="borrowtable", to_field="id"
    )
    borrowTime = fields.DatetimeField(auto_now_add=True)
    backdate = fields.DatetimeField(null=True)
        
UserPydanticOut = pydantic_model_creator(Users, name="UserOut")
UserPydanticIn = pydantic_model_creator(Users, name="UserIn", exclude=('id','createDate','role','state'),exclude_readonly=True)
LoginPydanticIn = pydantic_model_creator(Users, name="LoginIn", exclude=('id','createDate','role','state','passWord'),exclude_readonly=True)
LoginPydanticOut = pydantic_model_creator(Users, name="LoginOut", exclude=('id','createDate','role','state','passWord'),exclude_readonly=True)
BookPydanticOut = pydantic_model_creator(BooksTable, name="BookOut")
BookPydanticIn = pydantic_model_creator(BooksTable, name="BookIn", exclude=('id'),exclude_readonly=True)
BorrowPydanticOut = pydantic_model_creator(BorrowTable,exclude_readonly=False)
BorrowPydanticIn = pydantic_model_creator(BorrowTable, name="BorrowIn", exclude=('id','borrowTime','backdate'))
