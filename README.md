#### mitmweb -s src/课程作业.py 执行脚本
#### 视频时长修改
1. 拦截播放视频地址 https://kc.jxjypt.cn/classroom/getPlayAuth 获取视频播放时长
2. 拦截播放时长地址 https://kc.jxjypt.cn/classroom/watch/rec2
#### 作业答题修改
1. 拦截作业地址 https://kc.jxjypt.cn/paper/start 
    1. 单选题，{"A": "QQ", "B": "Qg", "C": "Qw", "D": "RA", "E": "QQ", "F": "QQ"}
   2. 多选题，填空题，URL 编码->Base64 编码->去掉 Base64 末尾的 '=' 补位
   3. 判断题，{"对": "正确", "错": "错误"}，按照上面的编码处理
2. 拦截作业提交地址 https://kc.jxjypt.cn/paper/submit
    根据缓存的答案，修改对应结果
