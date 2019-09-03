
from app import db
from datetime import datetime


class Author(db.Model):
    __tablename__ = 'authors'
    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.Integer, nullable=False)

    books = db.relationship('Book', back_populates='author')

    def __str__(self):
        return self.name


class Book(db.Model):
    __tablename__ = 'books'
    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(db.String, nullable=False)
    year = db.Column(db.Integer, nullable=True)

    author_id = db.Column(db.Integer, db.ForeignKey('authors.id'), nullable=False)

    author = db.relationship(Author, back_populates='books')
    users = db.relationship('User', back_populates='book')
    sayfalar = db.relationship('Sayfa', back_populates='book')

    def __str__(self):
        return self.title


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    
    first_name = db.Column(db.String)
    last_name = db.Column(db.String)
    username = db.Column(db.String) 
    language_code = db.Column(db.String, default='en')

    book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=True)
    
    book = db.relationship(Book, back_populates='users')
    sayfalar = db.relationship('Sayfa', back_populates='user')

    @classmethod
    def from_telegram_user(cls, user):
        return cls(**{a: getattr(user, a) for a in 'id first_name last_name username language_code'.split()})

    @property
    def full_name(self) -> str:
        return ' '.join(filter(bool, (self.first_name, self.last_name)))

    def __str__(self):
        return self.full_name


class Sayfa(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    count = db.Column(db.Integer, nullable=False)
    time = db.Column(db.DateTime, nullable=False, default=datetime.now, server_default=db.func.now())

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=False)

    user = db.relationship(User, back_populates='sayfalar')
    book = db.relationship(Book, back_populates='sayfalar')

    def __str__(self):
        return str(self.count)
