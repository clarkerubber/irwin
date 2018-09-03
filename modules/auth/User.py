from default_imports import *

from modules.auth.Priv import Priv

from pymongo.collection import Collection
import hashlib, uuid

Username = NewType('Username', str)
UserID = NewType('UserID', str)
Password = NewType('Password', str)
Salt = NewType('Salt', str)

class User(NamedTuple('User', [
        ('id', UserID), 
        ('name', Username),
        ('password', Password),
        ('salt', Salt),
        ('privs', List[Priv])
    ])):
    @staticmethod
    def new(name: Username, password: Password, privs: List[Priv] = []):
        """
        Creates a new User object.
        """
        hashedPassword, salt = User.hashPassword(password)
        return User(
            id = name.lower().replace(' ', ''),
            name = name,
            password = hashedPassword,
            salt = salt,
            privs = privs
            )

    @staticmethod
    def hashPassword(password: Password, salt: Opt[Salt] = None) -> Tuple[Password, Salt]:
        """
        Given a string and a salt this function will generate a hash of the password.
        If salt is not provided a new random salt is created.
        """
        if salt is None:
            salt = uuid.uuid4().hex
        hashedPassword = hashlib.sha512(password + salt).hexdigest()
        return hashedPassword, salt

    def checkPassword(self, password: Password) -> bool:
        """
        Checks if a raw password matches that hashed password of the user.
        """
        return self.hashPassword(password, self.salt) == self.password

class UserBSONHandler:
    @staticmethod
    def reads(bson: Dict) -> User:
        return User(
            id = bson['_id'],
            name = bson['name'],
            password = bson['password'],
            salt = bson['salt'],
            privs = [Priv(p) for p in bson['privs']])

    @staticmethod
    def writes(user: User) -> Dict:
        return {
            '_id': user.id,
            'name': user.name,
            'password': user.password,
            'salt': user.salt,
            'privs': [p.permission for p in user.privs]
        }

class UserDB(NamedTuple('UserDB', [
        ('coll', Collection)
    ])):
    def write(self, user: User):
        self.coll.update_one({'_id': user.id}, {'$set': UserBSONHandler.writes(user)}, upsert=True)

    def byId(self, _id: UserID) -> Opt[User]:
        doc = self.coll.find_one({'_id': _id})
        return None if doc is None else UserBSONHandler.reads(doc)