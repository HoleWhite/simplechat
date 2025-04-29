# lambda/index.py
import json
import os
# import boto3
import re  # 正規表現モジュールをインポート
# from botocore.exceptions import ClientError
# import requests  # HTTPリクエスト用ライブラリを追加
import urllib.request # Python標準ライブラリ
import urllib.error # Python標準ライブラリ


# Lambda コンテキストからリージョンを抽出する関数
def extract_region_from_arn(arn):
    # ARN 形式: arn:aws:lambda:region:account-id:function:function-name
    match = re.search('arn:aws:lambda:([^:]+):', arn)
    if match:
        return match.group(1)
    return "us-east-1"  # デフォルト値

# グローバル変数としてクライアントを初期化（初期値）
# bedrock_client = None

# モデルID
# MODEL_ID = os.environ.get("MODEL_ID", "us.amazon.nova-lite-v1:0")

# APIエンドポイント
#API_URL = "https://3307-35-204-236-223.ngrok-free.app/generate"
API_URL = "https://04e1-35-204-236-223.ngrok-free.app/"

def lambda_handler(event, context):
    try:
        # コンテキストから実行リージョンを取得し、クライアントを初期化
        # global bedrock_client
        # if bedrock_client is None:
        #     region = extract_region_from_arn(context.invoked_function_arn)
        #     bedrock_client = boto3.client('bedrock-runtime', region_name=region)
        #     print(f"Initialized Bedrock client in region: {region}")
        
        print("Received event:", json.dumps(event))
        
        # Cognitoで認証されたユーザー情報を取得
        user_info = None
        if 'requestContext' in event and 'authorizer' in event['requestContext']:
            user_info = event['requestContext']['authorizer']['claims']
            print(f"Authenticated user: {user_info.get('email') or user_info.get('cognito:username')}")
        
        # リクエストボディの解析
        body = json.loads(event['body'])
        message = body['message']
        conversation_history = body.get('conversationHistory', [])
        
        print("Processing message:", message)
        # print("Using model:", MODEL_ID)
        print("Using API endpoint:", API_URL)
        
        # 会話履歴を使用
        messages = conversation_history.copy()
        
        # ユーザーメッセージを追加
        messages.append({
            "role": "user",
            "content": message
        })
        
        # Nova Liteモデル用のリクエストペイロードを構築
        # 会話履歴を含める
        # bedrock_messages = []
        # for msg in messages:
        #     if msg["role"] == "user":
        #         bedrock_messages.append({
        #             "role": "user",
        #             "content": [{"text": msg["content"]}]
        #         })
        #     elif msg["role"] == "assistant":
        #         bedrock_messages.append({
        #             "role": "assistant", 
        #             "content": [{"text": msg["content"]}]
        #         })


        # 会話履歴をプロンプトに変換（外部APIは単一のプロンプト文字列を要求）
        prompt = ""
        for msg in messages:
            if msg["role"] == "user":
                prompt += f"ユーザー: {msg['content']}\n"
            elif msg["role"] == "assistant":
                prompt += f"アシスタント: {msg['content']}\n"
        print("Constructed prompt:", prompt)

        
        
        # invoke_model用のリクエストペイロード
        # request_payload = {
        #     "messages": bedrock_messages,
        #     "inferenceConfig": {
        #         "maxTokens": 512,
        #         "stopSequences": [],
        #         "temperature": 0.7,
        #         "topP": 0.9
        #     }
        # }


        # APIリクエストペイロード（外部APIのSimpleGenerationRequest形式）
        request_payload = {
            "prompt": prompt,
            "max_new_tokens": 512,
            "do_sample": True,
            "temperature": 0.7,
            "top_p": 0.9
        }

        
        # print("Calling Bedrock invoke_model API with payload:", json.dumps(request_payload))
        
        # # invoke_model APIを呼び出し
        # response = bedrock_client.invoke_model(
        #     modelId=MODEL_ID,
        #     body=json.dumps(request_payload),
        #     contentType="application/json"
        # )


        print("Calling API with payload:", json.dumps(request_payload))


        # APIにPOSTリクエストを送信 (urllib.request を使用)
        try:
            # (ステップ3で記述した try ブロックの中身)
            # 1. データ準備
            data = json.dumps(request_payload).encode('utf-8')
            # 2. ヘッダー準備
            headers = {'Content-Type': 'application/json'}
            # 3. リクエストオブジェクト作成
            req = urllib.request.Request(API_URL, data=data, headers=headers, method='POST')
            # 4. リクエスト送信・レスポンス取得
            with urllib.request.urlopen(req, timeout=10) as response:
                # 5. レスポンスボディ処理
                response_body_bytes = response.read()
                response_body_str = response_body_bytes.decode('utf-8')
                response_body = json.loads(response_body_str) # 変数に格納
                # 6. ステータスコードチェック (念のため)
                if not (200 <= response.status < 300):
                    raise Exception(f"API request failed with status: {response.status}")

        # --- ここから except 節の変更 ---
        except urllib.error.HTTPError as e:
            # HTTPステータスコードがエラー (4xx, 5xx) の場合
            error_content = "No additional error content."
            try:
                error_content = e.read().decode('utf-8') # エラー時のレスポンスボディも取得試行
            except Exception:
                pass
            raise Exception(f"API request failed with HTTP status {e.code} {e.reason}. Response: {error_content}")
        except urllib.error.URLError as e:
            # 接続エラーなど (URL間違い、DNS解決失敗、タイムアウト等) の場合
            raise Exception(f"API request failed due to network error: {e.reason}")
        except json.JSONDecodeError as e:
            # レスポンスボディのJSONパースに失敗した場合
             raise Exception(f"Failed to decode API JSON response: {str(e)}")
        except Exception as e:
            # その他の予期せぬエラー (タイムアウトはこちらで捕捉される場合もある)
            # (TimeoutErrorはPython 3.10以降ではURLErrorのサブクラス)
            raise Exception(f"An error occurred during API request: {str(e)}")
        # --- except 節の変更 ここまで ---        

        # # レスポンスを解析
        # response_body = json.loads(response['body'].read())
        # print("Bedrock response:", json.dumps(response_body, default=str))
        
        # # 応答の検証
        # if not response_body.get('output') or not response_body['output'].get('message') or not response_body['output']['message'].get('content'):
        #     raise Exception("No response content from the model")
        
        # # アシスタントの応答を取得
        # assistant_response = response_body['output']['message']['content'][0]['text']


        # レスポンスを解析
        print("API response:", json.dumps(response_body, default=str)) # ★response_body を参照

        # アシスタントの応答を取得（外部APIはgenerated_textフィールドを返す）
        if not response_body.get('generated_text'): # ★response_body を参照
            raise Exception("No generated text in API response")
        assistant_response = response_body['generated_text'].strip() # ★response_body を参照
        
        # アシスタントの応答を会話履歴に追加
        messages.append({
            "role": "assistant",
            "content": assistant_response
        })
        
        # 成功レスポンスの返却
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "OPTIONS,POST"
            },
            "body": json.dumps({
                "success": True,
                "response": assistant_response,
                "conversationHistory": messages
            })
        }
        
    except Exception as error:
        print("Error:", str(error))
        
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "OPTIONS,POST"
            },
            "body": json.dumps({
                "success": False,
                "error": str(error)
            })
        }
