import os
import hashlib
import hmac
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SECRET_KEY'] = 'emperor_market_ultimate_2026'

database_url = os.environ.get('DATABASE_URL')
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url or 'sqlite:///market.db'
db = SQLAlchemy(app)

# Встроенный токен вашего Telegram-бота
TG_BOT_TOKEN = '8802407115:AAGJo8tf27yUk2HDPF3gOV42forwvXw9Vjw'

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tg_id = db.Column(db.String(50), unique=True, nullable=False)
    username = db.Column(db.String(100), nullable=False)
    avatar = db.Column(db.String(300), nullable=True)
    balance = db.Column(db.Integer, default=1000) # Стартовый баланс для теста 1000 ₽
    rating = db.Column(db.Float, default=5.0)

class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    seller_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    description = db.Column(db.String(500), nullable=True)
    status = db.Column(db.String(20), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    seller = db.relationship('User', backref=db.backref('items', lazy=True))

class Deal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
    buyer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    seller_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), default='in_progress')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    item = db.relationship('Item')
    buyer = db.relationship('User', foreign_keys=[buyer_id])
    seller = db.relationship('User', foreign_keys=[seller_id])

@app.before_request
def setup_db():
    db.create_all()

@app.route('/')
def index():
    category = request.args.get('category', 'all')
    search = request.args.get('search', '').lower()

    query = Item.query.filter_by(status='active')
    if category != 'all':
        query = query.filter_by(category=category)
    
    items = query.order_by(Item.created_at.desc()).all()
    if search:
        items = [i for i in items if search in i.title.lower() or search in i.seller.username.lower()]

    current_user = None
    if 'user_id' in session:
        current_user = User.query.get(session['user_id'])

    return render_template('index.html', items=items, current_cat=category, current_user=current_user)

@app.route('/auth/telegram')
def telegram_auth():
    auth_data = request.args.to_dict()
    check_hash = auth_data.get('hash')
    if not check_hash:
        return redirect(url_for('index'))
    
    data_check_arr = []
    for key, value in sorted(auth_data.items()):
        if key != 'hash':
            data_check_arr.append(f"{key}={value}")
    data_check_string = "\n".join(data_check_arr)
    
    secret_key = hashlib.sha256(TG_BOT_TOKEN.encode()).digest()
    hmac_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    
    if hmac.compare_digest(hmac_hash, check_hash):
        tg_id = str(auth_data.get('id'))
        username = auth_data.get('first_name', 'Игрок')
        avatar = auth_data.get('photo_url', '')

        user = User.query.filter_by(tg_id=tg_id).first()
        if not user:
            user = User(tg_id=tg_id, username=username, avatar=avatar)
            db.session.add(user)
            db.session.commit()
        
        session['user_id'] = user.id

    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('index'))

@app.route('/create', methods=['GET', 'POST'])
def create_item():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    current_user = User.query.get(session['user_id'])

    if request.method == 'POST':
        title = request.form.get('title')
        category = request.form.get('category')
        price = int(request.form.get('price'))
        description = request.form.get('description')

        new_item = Item(
            seller_id=current_user.id,
            title=title,
            category=category,
            price=price,
            description=description,
            status='active'
        )
        db.session.add(new_item)
        db.session.commit()
        return redirect(url_for('index'))

    return render_template('create.html', current_user=current_user)

@app.route('/buy/<int:item_id>', methods=['POST'])
def buy_item(item_id):
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    buyer = User.query.get(session['user_id'])
    item = Item.query.get_or_404(item_id)

    if item.status != 'active' or item.seller_id == buyer.id:
        return redirect(url_for('index'))

    if buyer.balance < item.price:
        return "Недостаточно средств на балансе!", 400

    buyer.balance -= item.price
    item.status = 'frozen'
    
    deal = Deal(item_id=item.id, buyer_id=buyer.id, seller_id=item.seller_id, status='in_progress')
    db.session.add(deal)
    db.session.commit()

    return redirect(url_for('view_deal', deal_id=deal.id))

@app.route('/deal/<int:deal_id>')
def view_deal(deal_id):
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    deal = Deal.query.get_or_404(deal_id)
    current_user_id = session['user_id']
    
    if current_user_id != deal.buyer_id and current_user_id != deal.seller_id:
        return "Доступ запрещен", 403

    return render_template('deal.html', deal=deal, current_user_id=current_user_id)

@app.route('/deal/<int:deal_id>/complete', methods=['POST'])
def complete_deal(deal_id):
    deal = Deal.query.get_or_404(deal_id)
    if 'user_id' not in session or session['user_id'] != deal.buyer_id:
        return "Доступ запрещен", 403

    if deal.status == 'in_progress':
        deal.status = 'completed'
        deal.item.status = 'completed'
        seller = User.query.get(deal.seller_id)
        seller.balance += deal.item.price
        db.session.commit()

    return redirect(url_for('view_deal', deal_id=deal.id))

@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    current_user = User.query.get(session['user_id'])
    my_items = Item.query.filter_by(seller_id=current_user.id).all()
    my_deals = Deal.query.filter((Deal.buyer_id == current_user.id) | (Deal.seller_id == current_user.id)).all()
    
    return render_template('profile.html', current_user=current_user, my_items=my_items, my_deals=my_deals)

if __name__ == '__main__':
    app.run(debug=False)
