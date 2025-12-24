"""获取并显示小红书登录二维码"""
import httpx
import base64

def get_qrcode():
    """获取登录二维码并保存为 HTML 文件"""
    print("Fetching QR code from xiaohongshu-mcp...")
    
    response = httpx.get("http://localhost:18060/api/v1/login/qrcode", timeout=120)
    data = response.json()
    
    if data.get("success"):
        qr_data = data.get("data", {})
        img_base64 = qr_data.get("img", "")
        timeout = qr_data.get("timeout", "")
        is_logged_in = qr_data.get("is_logged_in", False)
        
        if is_logged_in:
            print("[OK] Already logged in!")
            return True
        
        # 保存为 HTML 文件
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Xiaohongshu Login</title>
    <style>
        body {{ 
            display: flex; 
            flex-direction: column;
            align-items: center; 
            justify-content: center; 
            min-height: 100vh;
            font-family: sans-serif;
            background: #ff2442;
            color: white;
        }}
        h1 {{ margin-bottom: 20px; }}
        img {{ 
            border: 10px solid white;
            border-radius: 20px;
            background: white;
        }}
        p {{ margin-top: 20px; font-size: 18px; }}
    </style>
</head>
<body>
    <h1>Scan to Login Xiaohongshu</h1>
    <img src="{img_base64}" alt="QR Code" />
    <p>Timeout: {timeout}</p>
    <p>Open Xiaohongshu app and scan this QR code</p>
</body>
</html>"""
        
        with open("login_qrcode.html", "w", encoding="utf-8") as f:
            f.write(html)
        
        print("[OK] QR code saved to login_qrcode.html")
        print("Please open login_qrcode.html in browser and scan with Xiaohongshu app")
        return False
    else:
        print(f"[ERROR] {data}")
        return False


if __name__ == "__main__":
    get_qrcode()
