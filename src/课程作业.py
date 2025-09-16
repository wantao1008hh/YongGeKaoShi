# mitmweb -s src/课程作业.py

import base64
import json
import re
import urllib.parse
from bs4 import BeautifulSoup
from mitmproxy import http, ctx
from urllib.parse import parse_qs, urlencode
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

# 保存从 paper/start 解析到的题目数据
questions_data = []  # [{ "pqid": "xxx", "qid": "xxx", "answer": "A" }, ...]

# 选项映射表（可随时修改） ,E, F 是因为有些 题目给错了答案，选的E
real_data = {"A": "QQ", "B": "Qg", "C": "Qw", "D": "RA", "E": "QQ", "F": "QQ"}

# 全局字典，保存每个 chapterId|coursewareId 对应的 kj_duration
kj_duration_dict = {}


def encode_juu_style(text: str) -> str:
    # 1. URL 编码
    percent = urllib.parse.quote(text, safe="")  # 不保留任何字符
    # 2. Base64 编码
    encoded = base64.b64encode(percent.encode("utf-8")).decode("utf-8")
    # 去掉 Base64 末尾的 '=' 补位，和你的原始字符串保持一致
    return encoded.rstrip("=")


def response(flow):

    if flow.request.pretty_url.startswith("https://kc.jxjypt.cn/paper/start"):
        html = flow.response.text
        soup = BeautifulSoup(html, "lxml")
        questions_data.clear()

        # 遍历所有题目 li
        for li in soup.select("li[id^='question_li_']"):
            pqid_tag = li.find("input", {"name": lambda x: x and x.startswith("pqid[")})
            qid_tag = li.find("input", {"name": lambda x: x and x.startswith("qid[")})
            qver_tag = li.find("input", {"name": lambda x: x and x.startswith("qver[")})

            pqid_val = pqid_tag["value"] if pqid_tag else None
            qid_val = qid_tag["value"] if qid_tag else None
            qver_val = qver_tag["value"] if qver_tag else None

            # 找 solution 下的答案
            sol = li.find_next("div", class_="solution")
            answer_val = None

            if sol:
                # 优先查找 em.right
                answer_tag = sol.find("em", class_="right")
                if answer_tag and answer_tag.text.strip():
                    raw_text = answer_tag.text.strip()
                    if raw_text in real_data:
                        # 单选题，直接用映射
                        answer_val = real_data[raw_text]
                    elif raw_text in ("对", "错"):
                        # 判断题，对/错转码
                        answer_val = encode_juu_style({"对": "正确", "错": "错误"}[raw_text])
                    else:
                        # 多选题或其他，直接转码
                        answer_val = encode_juu_style(raw_text)
                else:
                    # 如果没有 em.right，则查找 div.wenzi 下的内容
                    wenzi_tag = sol.find("div", class_="wenzi")
                    if wenzi_tag and wenzi_tag.text.strip():
                        raw_text = wenzi_tag.text.strip()
                        # 转成 Unicode 转义形式
                        answer_val = encode_juu_style(raw_text)

            # 映射答案，如果在 real_data 中
            if answer_val in real_data:
                answer_val = real_data[answer_val]

            ctx.log.info(f"解析题目 pqid={pqid_val}, qid={qid_val}, qver={qver_val}, answer={answer_val}")

            if pqid_val and qid_val:
                questions_data.append({
                    "pqid": pqid_val,
                    "qid": qid_val,
                    "qver": qver_val,
                    "answer": answer_val
                })

        ctx.log.info(f"保存 {len(questions_data)} 个题目答案")

    #拦截 getPlayAuth 保存 kj_duration
    if "https://kc.jxjypt.cn/classroom/getPlayAuth" in flow.request.pretty_url:
        try:
            data = json.loads(flow.response.get_text())
            kj_duration = data.get("data", {}).get("kj_duration")
            parsed = urlparse(flow.request.pretty_url)
            qs = parse_qs(parsed.query)
            chapterId = qs.get("chapterId", [None])[0]
            coursewareId = qs.get("coursewareId", [None])[0]

            if chapterId and coursewareId and kj_duration:
                key = f"{chapterId}|{coursewareId}"
                kj_duration_dict[key] = kj_duration
                ctx.log.info(f"[getPlayAuth] 保存 {key} -> kj_duration={kj_duration}")
        except Exception as e:
            ctx.log.error(f"解析 getPlayAuth 响应失败: {e}")


def request(flow: http.HTTPFlow):
    """拦截 paper/submit 修改答案并打印详细日志"""
    if flow.request.pretty_url.startswith("https://kc.jxjypt.cn/paper/submit"):
        try:
            body = flow.request.content.decode("utf-8")
            form = parse_qs(body, keep_blank_values=True)  # ⚡ 保留空值

            n = 0
            while f"pqid[{n}]" in form and f"qid[{n}]" in form:
                pqid_val = form[f"pqid[{n}]"][0]
                qid_val = form[f"qid[{n}]"][0]
                old_answer = form.get(f"answer[{n}]", [""])[0]

                # 匹配之前解析保存的答案
                match = next((q for q in questions_data
                              if q["pqid"] == pqid_val and q["qid"] == qid_val), None)

                if match and match["answer"]:
                    form[f"answer[{n}]"] = [match["answer"]]
                    ctx.log.info(f"[paper/submit] 修改题目 pqid={pqid_val}, qid={qid_val}, "
                                 f"answer: {old_answer} -> {match['answer']}")
                else:
                    ctx.log.info(f"[paper/submit] 未找到答案，pqid={pqid_val}, qid={qid_val}, "
                                 f"保留原 answer: {old_answer}")

                n += 1

            # 用 urlencode 拼回请求体
            flow.request.text = urlencode(form, doseq=True)

        except Exception as e:
            ctx.log.error(f"修改 paper/submit 请求失败: {e}")

    """拦截 watch/rec2 修改 duration 和 timePoint"""
    if flow.request.pretty_url.startswith("https://kc.jxjypt.cn/classroom/watch/rec2"):
        try:
            parsed = urlparse(flow.request.pretty_url)
            qs = parse_qs(parsed.query)

            # 从 requestId 里解析 chapterId 和 coursewareId
            request_id = qs.get("requestId", [None])[0]
            if request_id:
                parts = request_id.split("|")
                if len(parts) >= 2:
                    chapterId, coursewareId = parts[0], parts[1]
                    key = f"{chapterId}|{coursewareId}"
                    kj_duration = kj_duration_dict.get(key)

                    if kj_duration:
                        qs["druation"] = [str(kj_duration)]
                        qs["timePoint"] = [str(kj_duration)]

                        # 重新拼接 URL
                        new_query = urlencode(qs, doseq=True)
                        new_url = urlunparse(parsed._replace(query=new_query))
                        flow.request.url = new_url

                        ctx.log.info(f"[watch/rec2] 修改请求URL:\n  原始: {flow.request.pretty_url}\n  修改: {new_url}")
        except Exception as e:
            ctx.log.error(f"修改 watch/rec2 请求失败: {e}")
