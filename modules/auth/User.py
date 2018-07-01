from modules.auth.Priv import PrivBSONHandler
from collections import namedtuple
import hashlib, uuid

class User(namedtuple('User', ['id', 'name', 'password', 'salt', 'privs'])):
	@staticmethod
	def new(name, password, privs=[]):
		"""
		name: String
		password: String
		privs: List[Privs]=[]
		
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
	def hashPassword(password, salt=None):
		"""
		password: String
		salt: String=None

		Given a string and a salt this function will generate a hash of the password.
		If salt is not provided a new random salt is created.
		"""
		if salt is None:
			salt = uuid.uuid4().hex
		hashedPassword = hashlib.sha512(password + salt).hexdigest()
		return hashedPassword, salt

	def checkPassword(self, password):
		"""
		password: String

		Checks if a raw password matches that hashed password of the user.
		"""
		return self.hashPassword(password, self.salt) == self.password

class UserBSONHandler:
	@staticmethod
	def reads(bson):
		return User(
			id = bson['_id'],
			name = bson['name'],
			password = bson['password'],
			salt = bson['salt'],
			privs = [PrivBSONHandler.reads(p) for p in bson['privs']])

	@staticmethod
	def writes(user):
		return {
			'_id': user.id,
			'name': user.name,
			'password': user.password,
			'salt': user.salt,
			'privs': [PrivBSONHandler.writes(p) for p in user.privs]
		}

class UserDB(namedtuple('UserDB', ['coll'])):
	def write(self, user):
		self.coll.update_one({'_id': user.id}, {'$set': UserBSONHandler.writes(user)}, upsert=True)

	def byId(self, _id):
		doc = self.coll.find_one({'_id': _id})
		return None if doc is None else UserBSONHandler.reads(doc)