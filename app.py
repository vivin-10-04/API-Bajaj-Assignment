import datetime
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from enum import Enum

app = Flask(__name__)
# Use SQLite for lightweight storage
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///trading.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- ENUMS & CONSTANTS ---
class OrderType(Enum):
    BUY = "BUY"
    SELL = "SELL"

class OrderStyle(Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"

class OrderStatus(Enum):
    NEW = "NEW"
    PLACED = "PLACED"
    EXECUTED = "EXECUTED"
    CANCELLED = "CANCELLED"

# --- DATABASE MODELS ---

class Instrument(db.Model):
    symbol = db.Column(db.String(10), primary_key=True)
    exchange = db.Column(db.String(10))
    instrument_type = db.Column(db.String(20))
    last_traded_price = db.Column(db.Float)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(10), nullable=False)
    order_type = db.Column(db.String(10), nullable=False) # BUY/SELL
    order_style = db.Column(db.String(10), nullable=False) # MARKET/LIMIT
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=True) # Required for LIMIT
    status = db.Column(db.String(20), default=OrderStatus.NEW.value)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)

class Trade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'))
    symbol = db.Column(db.String(10))
    quantity = db.Column(db.Integer)
    price = db.Column(db.Float)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)

class Portfolio(db.Model):
    symbol = db.Column(db.String(10), primary_key=True)
    quantity = db.Column(db.Integer, default=0)
    average_price = db.Column(db.Float, default=0.0)

# --- HELPER: INITIALIZE DATA ---
def init_db():
    with app.app_context():
        db.create_all()
        # Seed dummy instruments if empty
        if not Instrument.query.first():
            db.session.add(Instrument(symbol="AAPL", exchange="NASDAQ", instrument_type="EQUITY", last_traded_price=150.0))
            db.session.add(Instrument(symbol="GOOGL", exchange="NASDAQ", instrument_type="EQUITY", last_traded_price=2800.0))
            db.session.add(Instrument(symbol="TSLA", exchange="NASDAQ", instrument_type="EQUITY", last_traded_price=700.0))
            db.session.commit()

# --- ROUTES ---

@app.route('/api/v1/instruments', methods=['GET'])
def get_instruments():
    instruments = Instrument.query.all()
    return jsonify([{
        "symbol": i.symbol,
        "exchange": i.exchange,
        "instrumentType": i.instrument_type,
        "lastTradedPrice": i.last_traded_price
    } for i in instruments])

@app.route('/api/v1/orders', methods=['POST'])
def place_order():
    data = request.json
    
    # 1. Validation
    try:
        qty = int(data.get('quantity'))
        if qty <= 0: raise ValueError
        o_style = OrderStyle(data.get('orderStyle'))
        o_type = OrderType(data.get('orderType'))
        price = data.get('price')
        symbol = data.get('symbol')
        
        # Check if instrument exists
        inst = Instrument.query.get(symbol)
        if not inst:
            return jsonify({"error": "Instrument not found"}), 404

        if o_style == OrderStyle.LIMIT and (price is None or price <= 0):
             return jsonify({"error": "Price is mandatory for LIMIT orders"}), 400
             
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid input data"}), 400

    # 2. Create Order
    new_order = Order(
        symbol=symbol,
        order_type=o_type.value,
        order_style=o_style.value,
        quantity=qty,
        price=price if price else inst.last_traded_price, # Use LTP for market simulation
        status=OrderStatus.NEW.value
    )
    db.session.add(new_order)
    db.session.commit()

    # 3. Simulation Logic (Bonus)
    # Market orders execute immediately. Limit orders stay PLACED.
    if o_style == OrderStyle.MARKET:
        execute_trade(new_order)
    else:
        new_order.status = OrderStatus.PLACED.value
        db.session.commit()

    return jsonify({"orderId": new_order.id, "status": new_order.status}), 201

def execute_trade(order):
    """Simulates trade execution and updates portfolio."""
    # 1. Create Trade Record
    trade = Trade(
        order_id=order.id,
        symbol=order.symbol,
        quantity=order.quantity,
        price=order.price
    )
    order.status = OrderStatus.EXECUTED.value
    
    # 2. Update Portfolio
    port = Portfolio.query.get(order.symbol)
    if not port:
        port = Portfolio(symbol=order.symbol, quantity=0, average_price=0.0)
        db.session.add(port)
    
    if order.order_type == OrderType.BUY.value:
        # Weighted Average Price Calculation
        total_cost = (port.quantity * port.average_price) + (order.quantity * order.price)
        port.quantity += order.quantity
        port.average_price = total_cost / port.quantity
    elif order.order_type == OrderType.SELL.value:
        # Selling reduces quantity but doesn't change average buy price
        port.quantity -= order.quantity
        # Optional: Handle short selling logic here (omitted for simplicity)
    
    db.session.add(trade)
    db.session.commit()

@app.route('/api/v1/orders/<int:order_id>', methods=['GET'])
def get_order(order_id):
    order = Order.query.get(order_id)
    if not order:
        return jsonify({"error": "Order not found"}), 404
    return jsonify({
        "orderId": order.id,
        "symbol": order.symbol,
        "type": order.order_type,
        "style": order.order_style,
        "quantity": order.quantity,
        "price": order.price,
        "status": order.status
    })

@app.route('/api/v1/trades', methods=['GET'])
def get_trades():
    trades = Trade.query.all()
    return jsonify([{
        "tradeId": t.id,
        "orderId": t.order_id,
        "symbol": t.symbol,
        "quantity": t.quantity,
        "price": t.price,
        "timestamp": t.timestamp.isoformat()
    } for t in trades])

@app.route('/api/v1/portfolio', methods=['GET'])
def get_portfolio():
    holdings = Portfolio.query.filter(Portfolio.quantity != 0).all()
    # Fetch current prices to calculate current value
    results = []
    for h in holdings:
        # In a real app, fetch real-time price. Here we use stored Instrument price.
        inst = Instrument.query.get(h.symbol)
        current_price = inst.last_traded_price if inst else 0
        
        results.append({
            "symbol": h.symbol,
            "quantity": h.quantity,
            "averagePrice": round(h.average_price, 2),
            "currentValue": round(h.quantity * current_price, 2)
        })
    return jsonify(results)

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)