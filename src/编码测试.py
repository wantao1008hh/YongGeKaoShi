import base64
import urllib.parse

def decode_juu_style(s: str) -> str:
    # 先尝试把整串作为 base64 解码（补齐 '=' 到长度为 4 的倍数）
    try:
        s_padded = s + ("=" * ((4 - len(s) % 4) % 4))
        percent_bytes = base64.b64decode(s_padded)
        percent = percent_bytes.decode("utf-8")
    except Exception:
        # 退而求其次：按每 4 字符一块解码（某些实现会这样分块）
        parts = []
        for i in range(0, len(s), 4):
            chunk = s[i:i+4]
            chunk_p = chunk + ("=" * ((4 - len(chunk) % 4) % 4))
            parts.append(base64.b64decode(chunk_p))
        percent = b"".join(parts).decode("utf-8")

    # 如果解出来是 %E6... 这种形式，就 URL 解码一次
    if "%" in percent:
        return urllib.parse.unquote(percent)
    return percent

if __name__ == "__main__":
    enc = "JUU2JUIyJTg5JUU2JUI1JUI4JUU2JTgwJUE3JTdDJUU0JUJBJUE0JUU0JUJBJTkyJUU2JTgwJUE3JTdDJUU2JTgzJUIzJUU1JTgzJThGJUU2JTgwJUE3"
    print(decode_juu_style(enc))   # -> 沉浸性|交互性|想像性
