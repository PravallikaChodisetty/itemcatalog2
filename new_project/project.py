# Imports
from flask import Flask, render_template, \
                  url_for, request, redirect,\
                  flash, jsonify, make_response
from flask import session as login_session
from sqlalchemy import create_engine, asc, desc
from sqlalchemy.orm import sessionmaker
from database_setup import *
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import os
import random
import string
import datetime
import json
import httplib2
import requests
# Import login_required from login_decorator.py
from login_decorator import login_required

# Flask instance
app = Flask(__name__)


# GConnect CLIENT_ID

CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Item-Catalog"


# Connect to database
engine = create_engine('sqlite:///catalog.db')
Base.metadata.bind = engine
# Create session
DBSession = sessionmaker(bind=engine)
session = DBSession()


# Login - Create anti-forgery state token
@app.route('/login')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase +
                    string.digits) for x in range(32))
    login_session['state'] = state
    return render_template('login.html', STATE=state)


# GConnect
@app.route('/gconnect', methods=['POST'])
def gconnect():
    """
    Gathers data from Google Sign In API and places
    it inside a session variable.
    """
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code, now compatible with Python3
    request.get_data()
    code = request.data.decode('utf-8')

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    # Submit request, parse response
    h = httplib2.Http()
    response = h.request(url, 'GET')[1]
    str_response = response.decode('utf-8')
    result = json.loads(str_response)

    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user is'
                                            'already connected.'),
                                 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']

    # see if user exists, if it doesn't make a new one
    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;'
    ' -webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    flash("You are now logged in as %s" % login_session['username'])
    return output

# User Helper Functions


def createUser(login_session):
    newUser = User(name=login_session['username'], email=login_session[
                   'email'], picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user


def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except Exception as e:
        return None

# DISCONNECT - Revoke a current user's token and reset their login_session


@app.route('/gdisconnect')
def gdisconnect():
        # Only disconnect a connected user.
    access_token = login_session.get('access_token')
    if access_token is None:
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    try:
        result['status'] == '200'
        # Reset the user's sesson.
        del login_session['access_token']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']

        response = redirect(url_for('showCatalog'))
        flash("You are now logged out.")
        return response
    except Exception as e:
        # For whatever reason, the given token was invalid.
        response = make_response(
            json.dumps('Failed to revoke token for given user.'+e, 400))
        response.headers['Content-Type'] = 'application/json'
        return response


# Flask Routing

# Homepage
@app.route('/')
@app.route('/catalog/')
def showCatalog():
    genres = session.query(Genre).order_by(asc(Genre.name))
    books = session.query(Books).order_by(desc(Books.date)).limit(5)
    return render_template('catalog.html',
                           genres=genres,
                           books=books)


# Genre Books
@app.route('/catalog/<path:genre_name>/books/')
def showGenre(genre_name):
    genres = session.query(Genre).order_by(asc(Genre.name))
    genre = session.query(Genre).filter_by(name=genre_name).one()
    books = session.query(Books).filter_by(
            genre=genre).order_by(asc(Books.name)).all()
    print(books)
    count = session.query(Books).filter_by(genre=genre).count()
    creator = getUserInfo(genre.user_id)
    if 'username' not in login_session or \
       creator.id != login_session['user_id']:
        return render_template('public_books.html',
                               genre=genre.name,
                               genres=genres,
                               books=books,
                               count=count)
    else:
        user = getUserInfo(login_session['user_id'])
        return render_template('books.html',
                               genre=genre.name,
                               genres=genres,
                               books=books,
                               count=count,
                               user=user)


# Add a genre
@app.route('/catalog/addgenre', methods=['GET', 'POST'])
@login_required
def addGenre():
    if request.method == 'POST':
        newGenre = Genre(
            name=request.form['name'],
            user_id=login_session['user_id'])
        print(newGenre)
        session.add(newGenre)
        session.commit()
        flash('Genre Successfully Added!')
        return redirect(url_for('showCatalog'))
    else:
        return render_template('addgenre.html')


# Edit a genre
@app.route('/catalog/<path:genre_name>/c_edit', methods=['GET', 'POST'])
@login_required
def editGenre(genre_name):
    editedGenre = session.query(Genre).filter_by(name=genre_name).one()
    genre = session.query(Genre).filter_by(name=genre_name).one()
    # See if the logged in user is the owner of item
    creator = getUserInfo(editedGenre.user_id)
    user = getUserInfo(login_session['user_id'])
    # If logged in user != item owner redirect them
    if creator.id != login_session['user_id']:
        flash("You cannot edit this Genre."
              "This Genre belongs to %s" % creator.name)
        return redirect(url_for('showCatalog'))
    # POST methods
    if request.method == 'POST':
        if request.form['name']:
            editedGenre.name = request.form['name']
        session.add(editedGenre)
        session.commit()
        flash('Genre Book Successfully Edited!')
        return redirect(url_for('showCatalog'))
    else:
        return render_template('editgenre.html',
                               genres=editedGenre,
                               genre=genre)


# Delete a genre
@app.route('/catalog/<path:genre_name>/c_delete', methods=['GET', 'POST'])
@login_required
def deleteGenre(genre_name):
    genreToDelete = session.query(
                       Genre).filter_by(name=genre_name).one()
    # See if the logged in user is the owner of item
    creator = getUserInfo(genreToDelete.user_id)
    user = getUserInfo(login_session['user_id'])
    # If logged in user != item owner redirect them
    if creator.id != login_session['user_id']:
        flash("You cannot delete this Genre."
              "This Genre belongs to %s" % creator.name)
        return redirect(url_for('showCatalog'))
    if request.method == 'POST':
        session.delete(genreToDelete)
        session.commit()
        flash('Genre Successfully Deleted! '+genreToDelete.name)
        return redirect(url_for('showCatalog'))
    else:
        return render_template('deletegenre.html',
                               genre=genreToDelete)


# Add an item
@app.route('/catalog/add', methods=['GET', 'POST'])
@login_required
def addBook():
    genres = session.query(Genre).all()
    if request.method == 'POST':
        newBook = Books(
            name=request.form['name'],
            description=request.form['description'],
            picture=request.form['picture'],
            genre=session.query(
                     Genre).filter_by(name=request.form['genre']).one(),
            date=datetime.datetime.now(),
            user_id=login_session['user_id'])
        session.add(newBook)
        session.commit()
        flash('Book Successfully Added!')
        return redirect(url_for('showCatalog'))
    else:
        return render_template('addbook.html',
                               genres=genres)


# Edit an item
@app.route('/catalog/<path:genre_name>/'
           '<path:book_name>/i_edit', methods=['GET', 'POST'])
@login_required
def editBook(genre_name, book_name):
    editedBook = session.query(Books).filter_by(name=book_name).one()
    genres = session.query(Genre).all()
    # See if the logged in user is the owner of item
    creator = getUserInfo(editedBook.user_id)
    user = getUserInfo(login_session['user_id'])
    # If logged in user != item owner redirect them
    if creator.id != login_session['user_id']:
        flash("You cannot edit this item. "
              "This book belongs to %s" % creator.name)
        return redirect(url_for('showCatalog'))
    # POST methods
    if request.method == 'POST':
        if request.form['name']:
            editedBook.name = request.form['name']
        if request.form['description']:
            editedBook.description = request.form['description']
        if request.form['picture']:
            editedBook.picture = request.form['picture']
        if request.form['genre']:
            genre = session.query(Genre).filter_by(
                       name=request.form['genre']).one()
            editedBook.genre = genre
        time = datetime.datetime.now()
        editedBook.date = time
        session.add(editedBook)
        session.commit()
        flash('Genre Book Successfully Edited!')
        return redirect(url_for('showGenre',
                                genre_name=editedBook.genre.name))
    else:
        return render_template('editbook.html',
                               book=editedBook,
                               genres=genres)


# Delete a book
@app.route('/catalog/<path:genre_name>/<path:book_name>/i_delete',
           methods=['GET', 'POST'])
@login_required
def deleteBook(genre_name, book_name):
    bookToDelete = session.query(Books).filter_by(name=book_name).one()
    genre = session.query(Genre).filter_by(name=genre_name).one()
    genres = session.query(genre).all()
    # See if the logged in user is the owner of item
    creator = getUserInfo(bookToDelete.user_id)
    user = getUserInfo(login_session['user_id'])
    # If logged in user != item owner redirect them
    if creator.id != login_session['user_id']:
        flash("You cannot delete this item. "
              "This item belongs to %s" % creator.name)
        return redirect(url_for('showCatalog'))
    if request.method == 'POST':
        session.delete(bookToDelete)
        session.commit()
        flash('Book Successfully Deleted! '+bookToDelete.name)
        return redirect(url_for('showGenre',
                                genre_name=genre.name))
    else:
        return render_template('deletebook.html', book=bookToDelete)

# JSON


@app.route('/catalog/JSON')
def allBooksJSON():
    genres = session.query(Genre).all()
    genre_dict = [c.serialize for c in genres]
    for c in range(len(genre_dict)):
        books = [i.serialize for i in session.query(
                 Books).filter_by(genre_id=genre_dict[c]["id"]).all()]
        if books:
            genre_dict[c]["Book"] = books
    return jsonify(Genre=genre_dict)


@app.route('/catalog/genres/JSON')
def genresJSON():
    genres = session.query(Genre).all()
    return jsonify(genres=[c.serialize for c in genres])


@app.route('/catalog/books/JSON')
def booksJSON():
    books = session.query(Books).all()
    return jsonify(books=[i.serialize for i in books])


@app.route('/catalog/<path:genre_name>/books/JSON')
def genreBooksJSON(genre_name):
    genre = session.query(Genre).filter_by(name=genre_name).one()
    books = session.query(Books).filter_by(genre=genre).all()
    return jsonify(books=[i.serialize for i in books])


@app.route('/catalog/<path:genre_name>/<path:book_name>/JSON')
def BookJSON(genre_name, book_name):
    genre = session.query(Genre).filter_by(name=genre_name).one()
    book = session.query(Books).filter_by(
           name=book_name, genre=genre).one()
    return jsonify(book=[book.serialize])


# Always at end of file !Important!
if __name__ == '__main__':
    app.secret_key = 'APP_SECRET_KEY'
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
