import jwt
import os
import hmac,hashlib,base64,ujson
from datetime import datetime, timedelta,timezone
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization,hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from config import Gconfig
class Encryptor:
    def __init__(self,config:Gconfig) -> None:
        kdf = PBKDF2HMAC(
            algorithm = hashes.SHA256(),
            length = 32,
            salt = config.get('salt'),
            iterations=100000,
        )
        self.key = base64.urlsafe_b64encode(kdf.derive(config.get('password')))
        self.init()
        
    def init(self) -> None:
        if os.path.exists('key'):
            with open('key','rb') as f:
                self.private_key = ed25519.Ed25519PrivateKey.from_private_bytes(f.read())
                self.public_key = self.private_key.public_key()
        else:
            private_key = ed25519.Ed25519PrivateKey.generate()
            out_key = private_key.private_bytes(
                        encoding=serialization.Encoding.Raw,
                        format=serialization.PrivateFormat.Raw,
                        encryption_algorithm=serialization.NoEncryption())
            with open('key','wb') as f:
                f.write(out_key)
            
    def hash_password(self,password:str) -> str:
        m = hmac.new(self.key,password.encode(),digestmod=hashlib.sha256)
        return m.hexdigest()
    
    def creact_jwt_token(self,payload:dict) -> str:
        exp = datetime.now(tz=timezone.utc) + timedelta(days=7)
        payload["exp"] = exp
        return [jwt.encode(payload,self.private_key,algorithm='EdDSA'),exp]
    
    def validate_jwt_token(self,token:str) -> dict:
        return jwt.decode(token,self.public_key,algorithms=['EdDSA'])