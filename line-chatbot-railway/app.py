from flask import Flask, request, abort
import os

app = Flask(__name__)

@app.route("/", methods=['GET'])
def index():
    return "LINE Bot is running on Railway!"

@app.route("/callback", methods=['POST'])
def callback():
    return 'OK'

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)