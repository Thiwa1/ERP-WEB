from flask import Flask, render_template, session
app = Flask(__name__)
app.secret_key = 'test'

@app.route('/customer_receipt')
def customer_receipt():
    session['username'] = 'Admin'
    session['role'] = 'Admin'
    return render_template('customer_receipt.html', current_theme='dark', company_currency='LKR')

if __name__ == '__main__':
    app.run(port=5000)
