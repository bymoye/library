from models import Users
class AuthUser:
    def __init__(self):
        self.user_state = {}
        
    async def authenticate(self):
        self.user_state = {
            'banUser': [i['id'] for i in await Users.filter(state = 1).all().values('id')],
            'superadmin': [i['id'] for i in await Users.filter(role = 2).all().values('id')],
            'admin': [i['id'] for i in await Users.filter(role = 1).all().values('id')],
        }
        print(self.user_state)
        
    async def is_ban(self, user_id):
        return user_id in self.user_state['banUser']
    
    async def is_superadmin(self, user_id):
        return user_id in self.user_state['superadmin']
    
    async def is_admin(self, user_id):
        return user_id in self.user_state['admin']