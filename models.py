import os
import sys
from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine
from passlib.apps import custom_app_context as pwd_context
import random, string
from itsdangerous import(TimedJSONWebSignatureSerializer as Serializer, BadSignature, SignatureExpired)
 
Base = declarative_base()

secret_key = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in xrange(32))
 
class User(Base):
    __tablename__ = 'user'
    id = Column(Integer, primary_key = True)
    username = Column(String)
    picture = Column (String)
    description = Column(String)
    name = Column(String)
    password_hash = Column(String(64))

    def hash_password(self,password):
        self.password_hash = pwd_context.hash(password)    
    
    def verify_password(self, password):
        return pwd_context.verify(password, self.password_hash)

    
    def generate_auth_token(self, expiration = 600):
        s = Serializer(secret_key, expires_in = expiration)
        return s.dumps({'id': self.id})
    
    #Verify auth tokens

    @staticmethod
    def verify_auth_token(token):
        s  = Serializer(secret_key)
        try:
            data = s.loads(token)
        except SignatureExpired:
            #Valid but expired
            return None
        except BadSignature:
            #Invalid token
            return None
        user_id = data['id']
        return user_id    

    @property
    def serialize(self):

        return {
            'id': self.id,
            'user_about': self.description,
            'username': self.username,
            'picture': self.picture,
            'name' : self.name
        }

  

class Post(Base):
    __tablename__ = 'posts'

    id = Column(Integer, primary_key = True)
    content = Column(String(250))
    likes = Column(Integer)
    user_id = Column(Integer,ForeignKey('user.id'))
    user = relationship(User) 

    @property
    def serialize(self):

        return {
            'id': self.id,
            'zcontent': self.content,
            'zlikes': self.likes,
            'zauthor': self.user_id
        }

 

engine = create_engine('sqlite:///simpelapi.db')
Base.metadata.create_all(engine)