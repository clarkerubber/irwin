from default_imports import *

from modules.auth.Priv import Priv, PrivBSONHandler

from pymongo.collection import Collection
import hashlib, uuid

Username = TypeVar('Username', str)
UserID = Username
Name = TypeVar('Name', str)
Password = TypeVar('Password', str)
Salt = TypeVar('Salt', str)

@validated
class User(NamedTuple('User', [
    ('id', Username), 
    ('name', Name),
    ('password', Password),
    ('salt', Salt),
    ('privs', List[Priv])])):
	@staticmethod
    @validated
	def new(name: Name, password: Password, privs: List[Priv] = []) -> User:
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
    @validated
	def hashPassword(password: Password, salt: Opt[Salt] = None) -> Tuple[Password, Salt]:
		"""
		Given a string and a salt this function will generate a hash of the password.
		If salt is not provided a new random salt is created.
		"""
		if salt is None:
			salt = uuid.uuid4().hex
		hashedPassword = hashlib.sha512(password + salt).hexdigest()
		return hashedPassword, salt

    @validated
	def checkPassword(self, password: Password) -> bool:
		"""
		Checks if a raw password matches that hashed password of the user.
		"""
		return self.hashPassword(password, self.salt) == self.password

class UserBSONHandler:
	@staticmethod
    @validated
	def reads(bson: Dict) -> User:
		return User(
			id = bson['_id'],
			name = bson['name'],
			password = bson['password'],
			salt = bson['salt'],
			privs = [PrivBSONHandler.reads(p) for p in bson['privs']])

	@staticmethod
    @validated
	def writes(user: User) -> Dict:
		return {
			'_id': user.id,
			'name': user.name,
			'password': user.password,
			'salt': user.salt,
			'privs': [PrivBSONHandler.writes(p) for p in user.privs]
		}

@validated
class UserDB(NamedTuple('UserDB', [
        ('coll', Collection)
    ])):
    @validated
	def write(self, user: User):
		self.coll.update_one({'_id': user.id}, {'$set': UserBSONHandler.writes(user)}, upsert=True)

    @validated
	def byId(self, _id: UserID) -> Opt[User]:
		doc = self.coll.find_one({'_id': _id})
		return None if doc is None else UserBSONHandler.reads(doc)