from flask import Flask, send_file, request, render_template
import os

app = Flask(__name__)
COUNT_FILE = 'count.txt'
MY_IP = '221.138.105.134' # 당근이님의 IP (이 IP는 카운트 제외)

#@app.route('/')
# def index():
#     return send_file('index.html')

# [추가] 메인 주소 접속 시 인트로 화면 반환
@app.route('/')
def index():
    return render_template('intro.html')

@app.route('/hot/')
def hot():
    return send_file('index.html')


@app.route('/count.txt')
def get_count():
    # 내 IP가 아니면 카운트 증가
    if request.remote_addr != MY_IP:
        if not os.path.exists(COUNT_FILE):
            count = 1
        else:
            with open(COUNT_FILE, 'r') as f:
                count = int(f.read()) + 1
        with open(COUNT_FILE, 'w') as f:
            f.write(str(count))
    else:
        # 내 IP면 파일 읽기만 함
        count = open(COUNT_FILE).read() if os.path.exists(COUNT_FILE) else 0
    return str(count)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)