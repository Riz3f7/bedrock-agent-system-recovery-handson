from flask import Flask
import logging

app = Flask(__name__)

# ログの設定
logging.basicConfig(filename='/var/log/my-flask-app.log', level=logging.ERROR,
                    format='%(asctime)s %(levelname)s: %(message)s')

@app.route('/')
def home():
    return 'Hello from Flask application!'

@app.route('/error')
def trigger_error():
    try:
        raise Exception("This is a test error triggered on purpose.")
    except Exception as e:
        app.logger.error(f"An error occurred: {e}")  # エラーログを出力
        return "Internal Server Error", 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=80)
