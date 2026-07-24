import os
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'emperor_market_ultimate_2026'

database_url = os.environ.get('DATABASE_URL')
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url or 'sqlite:///market.db'
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    balance = db.Column(db.Integer, default=1500)
    rating = db.Column(db.Float, default=5.0)

class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    seller_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    description = db.Column(db.String(500), nullable=True)
    tags = db.Column(db.String(200), nullable=True)
    status = db.Column(db.String(20), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    seller = db.relationship('User', backref=db.backref('items', lazy=True))

@app.route('/')
def index():
    with app.app_context():
        db.create_all()
        if not User.query.first():
            u = User(username="DarkEmperor_99", balance=5000, rating=5.0)
            db.session.add(u)
            db.session.commit()
            item = Item(seller_id=u.id, title="1000 Robux (Трансфер)", category="robux", price=480, description="Gamepass, комиссия на мне", tags="Комиссия на мне, Выдача 5 мин")
            db.session.add(item)
            db.session.commit()

    category = request.args.get('category', 'all')
    search = request.args.get('search', '').lower()

    query = Item.query.filter_by(status='active')
    if category != 'all':
        query = query.filter_by(category=category)
    
    items = query.order_by(Item.created_at.desc()).all()
    
    if search:
        items = [i for i in items if search in i.title.lower() or search in i.seller.username.lower()]

    return render_template('index.html', items=items, current_cat=category)

@app.route('/create', methods=['GET', 'POST'])
def create_item():
    with app.app_context():
        db.create_all()
        user = User.query.first() # Тестовый пользователь-продавец
            
    if request.method == 'POST':
        title = request.form.get('title')
        category = request.form.get('category')
        price = int(request.form.get('price'))
        description = request.form.get('description')
        tags = request.form.get('tags', 'Быстрая выдача')

        new_item = Item(
            seller_id=user.id,
            title=title,
            category=category,
            price=price,
            description=description,
            tags=tags,
            status='active'
        )
        db.session.add(new_item)
        db.session.commit()
        return redirect(url_for('index'))

    return render_template('create.html')

@app.route('/buy/<int:item_id>', methods=['POST'])
def buy_item(item_id):
    item = Item.query.get_or_404(item_id)
    if item.status == 'active':
        item.status = 'frozen' # Заморозка сделки (Гарант)
        db.session.commit()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=False)
