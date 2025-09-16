from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os
import gspread
from google.oauth2.service_account import Credentials

app = Flask(__name__)

# 環境変数から設定を取得
LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
LINE_CHANNEL_SECRET = os.getenv('LINE_CHANNEL_SECRET')

# LINE API設定
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# Google Sheets設定
SPREADSHEET_ID = '10KIQgCLBoPpP8Jn7NKQTl5blJJl-DTKwcNZvMF1Pf4k'
SHEET_NAME = '商品マスタ'

def get_google_sheets_client():
    """Google Sheetsクライアントを取得"""
    try:
        # 環境変数からJSONキーを取得
        creds_info = os.getenv('GOOGLE_CREDENTIALS_JSON')
        if creds_info:
            import json
            creds_dict = json.loads(creds_info)
            credentials = Credentials.from_service_account_info(creds_dict)
        else:
            # ローカル開発用
            credentials = Credentials.from_service_account_file('credentials.json')
        
        scope = ['https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive']
        credentials = credentials.with_scopes(scope)
        
        client = gspread.authorize(credentials)
        return client
    except Exception as e:
        print(f"Google Sheets接続エラー: {e}")
        return None

def search_products(keyword):
    """商品検索"""
    try:
        client = get_google_sheets_client()
        if not client:
            return []
        
        sheet = client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)
        all_records = sheet.get_all_records()
        
        results = []
        keyword_lower = keyword.lower()
        
        for record in all_records:
            if len(results) >= 10:  # 最大10件
                break
                
            # A列(メーカー), B列(商品名), C列(機種品番)で部分一致検索
            maker = str(record.get('メーカー', '')).lower()
            product_name = str(record.get('商品名', '')).lower()
            model_number = str(record.get('機種品番', '')).lower()
            
            if (keyword_lower in maker or 
                keyword_lower in product_name or 
                keyword_lower in model_number):
                results.append(record)
        
        return results
    except Exception as e:
        print(f"検索エラー: {e}")
        return []

def format_search_results(results):
    """検索結果をフォーマット"""
    if not results:
        return "該当商品が見つかりませんでした"
    
    message = ""
    for i, result in enumerate(results, 1):
        message += f"【検索結果】{i}件目\n"
        message += f"メーカー: {result.get('メーカー', '')}\n"
        message += f"商品名: {result.get('商品名', '')}\n"
        message += f"機種品番: {result.get('機種品番', '')}\n"
        message += f"掛け率: {result.get('掛け率(NET)', '')}\n"
        message += f"概要: {result.get('概要', '')}\n"
        
        if i < len(results):
            message += "-------------------\n"
    
    return message

@app.route("/", methods=['GET'])
def index():
    return "LINE Bot is running on Railway!"

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_message = event.message.text
    
    # まず「検索中」メッセージを送信
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text="検索中です。しばらくお待ちください")
    )
    
    # 商品検索を実行
    search_results = search_products(user_message)
    response_message = format_search_results(search_results)
    
    # 検索結果をプッシュメッセージで送信
    line_bot_api.push_message(
        event.source.user_id,
        TextSendMessage(text=response_message)
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)