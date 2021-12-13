import aioredis

class RedisCon:
    def __init__(self, host, port, db):
        self.host = host
        self.port = port
        self.db = db
        self.redis_conn = None
        self.lock = {}

    async def connect(self):
        self.redis_conn = await aioredis.from_url(f'redis://{self.host}:{self.port}/{self.db}')

    async def close(self):
        await self.redis_conn.close()

    async def get(self, key):
        return await self.redis_conn.get(key)

    async def set(self, key, value):
        return await self.redis_conn.set(key, value)

    async def delete(self, key):
        return await self.redis_conn.delete(key)
    
    async def setnx(self,key,value):
        return await self.redis_conn.setnx(key,value)
    
    async def keys(self,pattern):
        return await self.redis_conn.keys(pattern)