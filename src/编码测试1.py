import base64
import urllib.parse

def encode_juu_style(text: str) -> str:
    # 1. URL 编码
    percent = urllib.parse.quote(text, safe="")  # 不保留任何字符
    # 2. Base64 编码
    encoded = base64.b64encode(percent.encode("utf-8")).decode("utf-8")
    # 去掉 Base64 末尾的 '=' 补位，和你的原始字符串保持一致
    return encoded.rstrip("=")

if __name__ == "__main__":
    text = "ABCD"
    encoded = encode_juu_style(text)
    print("编码结果:", encoded)
