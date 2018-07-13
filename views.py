from redis import Redis
redis = Redis()

from models import Base, User, Post
from flask import Flask, jsonify, request, url_for, abort, g
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session
from flask_httpauth import HTTPBasicAuth
import time
from functools import update_wrapper


auth = HTTPBasicAuth()

engine = create_engine('sqlite:///simpelapi.db')

Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = scoped_session(DBSession)
app = Flask(__name__)
path = '/api/v1/'


#Limit 

class RateLimit(object):
    expiration_window = 10

    def __init__(self, key_prefix, limit, per, send_x_headers):
        self.reset = (int(time.time()) // per) * per + per
        self.key = key_prefix + str(self.reset)
        self.limit = limit
        self.per = per
        self.send_x_headers = send_x_headers
        p = redis.pipeline()
        p.incr(self.key)
        p.expireat(self.key, self.reset + self.expiration_window)
        self.current = min(p.execute()[0], limit)

    remaining = property(lambda x: x.limit - x.current)
    over_limit = property(lambda x: x.current >= x.limit)

def get_view_rate_limit():
    return getattr(g, '_view_rate_limit', None)

def on_over_limit(limit):
    return (jsonify({'data':'You hit the rate limit','error':'429'}),429)

def ratelimit(limit, per=300, send_x_headers=True,
              over_limit=on_over_limit,
              scope_func=lambda: request.remote_addr,
              key_func=lambda: request.endpoint):
    def decorator(f):
        def rate_limited(*args, **kwargs):
            key = 'rate-limit/%s/%s/' % (key_func(), scope_func())
            rlimit = RateLimit(key, limit, per, send_x_headers)
            g._view_rate_limit = rlimit
            if over_limit is not None and rlimit.over_limit:
                return over_limit(rlimit)
            return f(*args, **kwargs)
        return update_wrapper(rate_limited, f)
    return decorator


@app.after_request
def inject_x_rate_headers(response):
    limit = get_view_rate_limit()
    if limit and limit.send_x_headers:
        h = response.headers
        h.add('X-RateLimit-Remaining', str(limit.remaining))
        h.add('X-RateLimit-Limit', str(limit.limit))
        h.add('X-RateLimit-Reset', str(limit.reset))
    return response

@auth.verify_password
def verify_password(username_or_token, password):
    #Checking for token first
    user_id = User.verify_auth_token(username_or_token)
    if user_id:
        user = session.query(User).filter_by(id = user_id).one()
    else:
        user = session.query(User).filter_by(username = username_or_token).first()
        if not user or not user.verify_password(password):
            return False
        g.user = user
        return True

@app.route(path + 'auth/token')
@ratelimit(limit=300, per=60 * 1)
@auth.login_required
def get_auth_token():
    token = g.user.generate_auth_token()
    return jsonify({'token': token.decode('ascii')})



#Create user
@app.route('/api/v1/user/register/new', methods = ['POST'])
@ratelimit(limit=300, per=60 * 1)
def new_user():
    username = request.json.get('username')
    password = request.json.get('password')
    if username is None or password is None:
        print "Missing argument"
        abort(400) 
        
    if session.query(User).filter_by(username = username).first() is not None:
        print "Existing user"
        user = session.query(User).filter_by(username=username).first()
        return jsonify({'User_Error':'This user aleready exists'}), 200
        
    user = User(username = username)
    user.hash_password(password)
    session.add(user)
    session.commit()
    return jsonify({ 'Created': user.username }), 201



#User

#Get information for all users

@app.route(path + 'users')
@ratelimit(limit=300, per=60 * 1)
def getUsers():

    print "All users"
    users = session.query(User).all()
    return jsonify(Users = [i.serialize for i in users])

#Get information for one user
@app.route(path + 'user/id/<int:id>')
@ratelimit(limit=300, per=60 * 1)
def getUser(id):
    print "User with id %s" % id
    user = session.query(User).filter_by(id = id).first()
    if user is None:
        return jsonify({'Post_Error_404': 'Not found,this user,can be deleted or never have been existed[post_id] = [%s]' % id}),404
    else:
        return jsonify(user.serialize)

#Get username for specific user
@app.route(path + 'user/id/<int:id>/username')
@ratelimit(limit=300, per=60 * 1)
def getUsername(id):
    print "Username for user with id %s" % id
    user = session.query(User).filter_by(id = id).first()
    if user is None:
        return jsonify({'Post_Error_404': 'Not found,this user,can be deleted or never have been existed[post_id] = [%s]' % id}),404
    else:
        return jsonify({'username': user.username}), 201

#Get name for specific user
@app.route(path + 'user/id/<int:id>/name')
@ratelimit(limit=300, per=60 * 1)
def getName(id):
    print "Name for user with id %s" % id
    user = session.query(User).filter_by(id = id).first()
    if user is None:
        return jsonify({'Post_Error_404': 'Not found,this user,can be deleted or never have been existed[post_id] = [%s]' % id}),404
    else:
        return jsonify({'username': user.name}), 201

#Get user description for specifi user
@app.route(path + 'user/id/<int:id>/description')
@ratelimit(limit=300, per=60 * 1)
def getDescription(id):
    print "Description for user with id %s" % id
    user = session.query(User).filter_by(id = id).first()
    if user is None:
        return jsonify({'Post_Error_404': 'Not found,this user,can be deleted or never have been existed[post_id] = [%s]' % id}),404
    else:
        return jsonify({'description': user.description}), 201

#Get user proifle picture
@app.route(path + 'user/id/<int:id>/picture')
@ratelimit(limit=300, per=60 * 1)
def getPicture(id):
    print "Picture for user with id %s" % id
    user = session.query(User).filter_by(id = id).first()
    if user is None:
        return jsonify({'Post_Error_404': 'Not found,this user,can be deleted or never have been existed[post_id] = [%s]' % id}),404
    else:
        return jsonify({'picture': user.picture}), 201

#Edit user username with id 
@app.route(path + 'user/id/<int:id>/edit/username' , methods = ['PUT'])
@ratelimit(limit=300, per=60 * 1)
@auth.login_required
def editUsername(id):
    print "Edit username for user with id %s" % id
    username = request.json.get('username')
    user = session.query(User).filter_by(id = id).first()
    if user is None:
        return jsonify({'Post_Error_404': 'Not found,this user,can be deleted or never have been existed[post_id] = [%s]' % id}),404
    else:
        user.username = username
        session.add(user)
        session.commit()
        return jsonify({'username': user.username}), 201


#Edit user name with id 
@app.route(path + 'user/id/<int:id>/edit/name', methods = ['PUT'])
@ratelimit(limit=300, per=60 * 1)
@auth.login_required
def editName(id):
    print "Edit name for user with id %s" % id
    name = request.json.get('name')
    user = session.query(User).filter_by(id = id).first()
    if user is None:
        return jsonify({'Post_Error_404': 'Not found,this user,can be deleted or never have been existed[post_id] = [%s]' % id}),404
    else:
        user.username = name
        session.add(user)
        session.commit()
        return jsonify({'name': user.name}), 201

#Edit user description with id 
@app.route(path + 'user/id/<int:id>/edit/description', methods = ['PUT'])
@ratelimit(limit=300, per=60 * 1)
@auth.login_required
def editDescription(id):
    print "Edit description for user with id %s" % id
    description = request.json.get('description')
    user = session.query(User).filter_by(id = id).first()
    if user is None:
        return jsonify({'Post_Error_404': 'Not found,this user,can be deleted or never have been existed[post_id] = [%s]' % id}),404
    else:
        user.description = description
        session.add(user)
        session.commit()
        return jsonify({'description': user.description}), 201

#Edit user picture with id 
@app.route(path + 'user/id/<int:id>/edit/picture', methods = ['PUT'])
@ratelimit(limit=300, per=60 * 1)
@auth.login_required
def editPicture(id):
    print "Edit picture for user with id %s" % id
    picture = request.json.get('picture')
    user = session.query(User).filter_by(id = id).one()
    if user is None:
        return jsonify({'Post_Error_404': 'Not found,this user,can be deleted or never have been existed[post_id] = [%s]' % id}),404
    else:
        user.picture = picture
        session.add(picture)
        session.commit()
        return jsonify({'picture': user.picture}), 201


#Remove user with id
@app.route(path + 'user/id/<int:id>/delete', methods = ['DELETE'])
@ratelimit(limit=300, per=60 * 1)
@auth.login_required
def removeUser(id):
    print "Remove user with id %s" % id
    user = session.query(User).filter_by(id = id).first()
    if user is None:
        return jsonify({'Post_Error_404': 'Not found,this user,can be deleted or never have been existed[post_id] = [%s]' % id}),404
    else:
        session.delete(user)
        session.commit()
        return jsonify({'Deleted': 'Success'}), 201

#Post

#Get specific post 
@app.route(path + 'post/id/<int:id>')
@ratelimit(limit=300, per=60 * 1)
def getPost(id):
    print "Post with id %s" % id
    post = session.query(Post).filter_by(id = id).first()
    if post is None:
        return jsonify({'Post_Error_404': 'Not found,this post,can be deleted or never have been existed[post_id] = [%s]' % id}),404
    else:
        return jsonify(post.serialize)

    
#Get post from specific user
@app.route(path + 'post/author/<int:user_id>/post/id/<int:post_id>/')
@ratelimit(limit=300, per=60 * 1)
def getUserpost(user_id,post_id):
    print "Post from %s" % user_id
    post = session.query(Post).filter_by(user_id = user_id, id = post_id).first()
    if post is None:
        return jsonify({'Post_Error_404': 'Not found,this user is not author of this post [post_id] = [%s]' % post_id}),404
    else:
        return jsonify(post.serialize),201
    
#Get number of likes for specific post
@app.route(path + 'post/id/<int:id>/likes/')
@ratelimit(limit=300, per=60 * 1)
def getLikes(id):
    print "Number of likes for post where id %s" % id
    post = session.query(Post).filter_by(id = id).first()
    if post is None:
        return jsonify({'Post_Error_404': 'Not found,this post likes,can be deleted or never have been existed[post_id] = [%s]' % id}),404
    else:
        return jsonify({'likes': post.likes}), 201
    
#Get post content
@app.route(path + 'post/id/<int:id>/content')
@ratelimit(limit=300, per=60 * 1)
def getContent(id):
    print "Get content for post where id %s" % id
    post = session.query(Post).filter_by(id = id).first()
    if post is None:
        return jsonify({'Post_Error_404': 'Not found,this post content,can be deleted or never have been existed[post_id] = [%s]' % id}),404
    else:
        return jsonify({'content': post.content}), 201

#Create new post
@app.route( '/api/v1/post/add/new', methods = ['POST'])
@ratelimit(limit=300, per=60 * 1)
@auth.login_required
def addPost():
    print "Add new post"
    user_id = request.json.get('user_id')
    content = request.json.get('content')
    post = Post(user_id = user_id, content = content)
    session.add(post)
    session.commit()
    return jsonify({'Post': 'Successfully created'}), 201

#Edit specific post content
@app.route(path + 'post/id/<int:id>/edit/author', methods = ['PUT'])
@ratelimit(limit=300, per=60 * 1)
@auth.login_required
def editPostAuthor(id):
    print "Edit content for post with id %s" % id
    user_id = request.json.get('user_id')
    post = session.query(Post).filter_by(id = id).first()
    if post is None:
        return jsonify({'Post_Error_404': 'Not found,this post author,can be deleted or never have been existed[post_id] = [%s]' % id}),404
    else:
        post.user_id = user_id
        session.add(post)
        session.commit()
        return jsonify({'author': post.user_id}), 201


#Edit specific post content
@app.route(path + 'post/id/<int:id>/edit/content', methods = ['PUT'])
@ratelimit(limit=300, per=60 * 1)
@auth.login_required
def editPostContent(id):
    print "Edit content for post with id %s" % id
    content = request.json.get('content')
    post = session.query(Post).filter_by(id = id).first()
    if post is None:
        return jsonify({'Post_Error_404': 'Not found,this post content,can be deleted or never have been existed[post_id] = [%s]' % id}),404
    else:    
        post.content = content
        session.add(post)
        session.commit()
        return jsonify({'content': post.content}), 201

#Remove post with id
@app.route(path + 'post/id/<int:id>/delete', methods = ['DELETE'])
@ratelimit(limit=300, per=60 * 1)
@auth.login_required
def removePost(id):
    print "Remove post with id %s" % id
    post = session.query(Post).filter_by(id = id).first()
    if post is None:
        return jsonify({'Post_Error_404': 'Not found,this post,can be deleted or never have been existed[post_id] = [%s]' % id}),404
    else:
        session.delete(post)
        session.commit()
        return jsonify({'Deleted': 'Success'}), 201






if __name__ == '__main__':
    app.debug = True
    app.run(host='0.0.0.0', port=8080)