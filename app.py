import os
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'emperor_market_secret_key_2026'

database_url = os.environ.get('DATABASE_URL')
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url or 'sqlite:///market.db'
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    balance = db.Column(db.Integer, default=0)
    rating = db.Column(db.Float, default=5.0)

class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    seller_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    seller = db.relationship('User', backref=db.backref('items', lazy=True))

@app.route('/')
def index():
    with app.app_context():
        db.create_all()
        if not User.query.first():
            u = User(username="DarkEmperor_99", balance=1000, rating=5.0)
            db.session.add(u)
            db.session.commit()
            item = Item(seller_id=u.id, title="1000 Robux (Трансфер)", price=480, status="active")
            db.session.add(item)
            db.session.commit()

    active_items = Item.query.filter_by(status='active').all()
    return render_template('index.html', items=active_items)

if __name__ == '__main__':
    app.run(debug=False)