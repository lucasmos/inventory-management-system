from flask import Flask, render_template, request, make_response, redirect, session, url_for
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io
from datetime import datetime, timedelta

app = Flask(__name__, static_url_path='/static')
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=1)
app.secret_key = 'your_secret_key'  # Replace with your own secret key

# Sample username and password (replace with your own authentication mechanism)
USERNAME = "papa"
PASSWORD = "1234"

# Function to load inventory data from file
def load_inventory():
    inventory = []
    try:
        with open("inventory.txt", "r") as file:
            for line in file:
                data = line.strip().split(',')
                item = {
                    "id": len(inventory) + 1,
                    "name": data[0],
                    "quantity_in_stock": int(data[1]),
                    "quantity_sold": int(data[2]),
                    "price": float(data[4])
                }
                item['quantity_left'] = item['quantity_in_stock'] - item['quantity_sold']
                inventory.append(item)
    except FileNotFoundError:
        pass  # If file doesn't exist, ignore and proceed with an empty inventory
    return inventory

# Sample initial inventory
inventory = load_inventory()

@app.before_request
def before_request():
    session.modified = True
    app.permanent_session_lifetime = timedelta(hours=1)

@app.route('/')
def index():
    if 'username' in session:
        return render_template('index.html', inventory=inventory)
    else:
        return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == USERNAME and password == PASSWORD:
            session['username'] = username
            return redirect(url_for('index'))  # Redirect to index page after successful login
        else:
            error = "Invalid username or password. Please try again."
    return render_template('login.html', error=error)

@app.route('/logout', methods=['POST'])
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

def prevent_data_loss():
    with open("inventory.txt", "w") as file:
        for item in inventory:
            file.write(f"{item['name']},{item['quantity_in_stock']},{item['quantity_sold']},{item['quantity_left']},{item['price']}\n")

def prevent_redundancy(name):
    for item in inventory:
        if item['name'] == name:
            return True
    return False

@app.route('/add_item', methods=['POST'])
def add_item():
    name = request.form['name']
    quantity_in_stock = int(request.form['quantity_in_stock'])
    price = float(request.form['price'])
    if not prevent_redundancy(name):
        item_id = len(inventory) + 1
        item = {"id": item_id, "name": name, "quantity_in_stock": quantity_in_stock, "quantity_sold": 0, "price": price}
        item['quantity_left'] = item['quantity_in_stock'] - item['quantity_sold']
        inventory.append(item)
    prevent_data_loss()
    return render_template('index.html', inventory=inventory)

@app.route('/delete_item/<int:item_id>', methods=['POST', 'DELETE'])
def delete_item(item_id):
    if request.method == 'POST' or request.method == 'DELETE':
        for item in inventory:
            if item['id'] == item_id:
                inventory.remove(item)
                break
        prevent_data_loss()
        return render_template('index.html', inventory=inventory)
    else:
        return "Method Not Allowed", 405

@app.route('/update', methods=['POST'])
def update_quantity():
    item_id = int(request.form['item_id'])
    quantity_sold = int(request.form['quantity_sold'])
    for item in inventory:
        if item['id'] == item_id:
            item['quantity_sold'] += quantity_sold
            item['quantity_left'] = item['quantity_in_stock'] - item['quantity_sold']
            break
    prevent_data_loss()
    return render_template('index.html', inventory=inventory)

@app.route('/generate_report')
def generate_report():
    response = make_response(create_pdf_report())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=stock_report.pdf'
    return response

@app.route('/generate_sales_report')
def generate_sales_report():
    response = make_response(create_sales_pdf_report())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=sales_report.pdf'
    return response

def create_pdf_report():
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(100, 750, "Hardware Shop Inventory Report")

    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, 700, "Item Name")
    c.drawString(200, 700, "Quantity in Stock")
    c.drawString(300, 700, "Quantity Sold")
    c.drawString(400, 700, "Quantity Left")
    c.drawString(500, 700, "Price(KES)")

    c.setFont("Helvetica", 12)
    y_position = 680
    for item in inventory:
        c.drawString(50, y_position, item['name'])
        c.drawString(200, y_position, str(item['quantity_in_stock']))
        c.drawString(300, y_position, str(item['quantity_sold']))
        c.drawString(400, y_position, str(item['quantity_left']))
        c.drawString(500, y_position, "{:.2f} KES".format(item['price']))  # Format price as KES
        if item['quantity_left'] < 10:
            c.drawString(600, y_position, "Low Stock Alert!")
        y_position -= 20

    c.save()
    buffer.seek(0)
    return buffer.read()

def create_sales_pdf_report():
    buffer = io.BytesIO()

    c = canvas.Canvas(buffer, pagesize=letter)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(100, 750, "Items Sold Report")

    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, 700, "Item Name")
    c.drawString(200, 700, "Quantity Sold")
    c.drawString(300, 700, "Price Per Item")
    c.drawString(400, 700, "Total Cost")
    c.drawString(500, 700, "Date Sold")

    total_cost = 0
    y_position = 680
    for item in inventory:
        if item['quantity_sold'] > 0:
            c.drawString(50, y_position, item['name'])
            c.drawString(200, y_position, str(item['quantity_sold']))
            c.drawString(300, y_position, "{:.2f} KES".format(item['price']))  # Format price as KES
            total_item_cost = item['quantity_sold'] * item['price']
            total_cost += total_item_cost
            c.drawString(400, y_position, "{:.2f} KES".format(total_item_cost))  # Format total cost as KES
            c.drawString(500, y_position, datetime.now().strftime("%Y-%m-%d"))
            y_position -= 20

    c.setFont("Helvetica-Bold", 14)
    c.drawString(400, y_position - 20, "Total Sales:")
    c.drawString(500, y_position - 20, "{:.2f} KES".format(total_cost))  # Format total sales as KES

    c.save()
    buffer.seek(0)
    return buffer.read()

if __name__ == '__main__':
    app.run(debug=True)
