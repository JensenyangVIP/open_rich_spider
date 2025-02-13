"""
自媒体选题挖掘系统 v1.2
作者：Jensenyang 微信公众号【Jensen不惑】
功能：多平台爆款内容自动挖掘+选题生成+风险控制

"""
import asyncio
import json
import re
import time
from urllib.parse import quote
import jieba.analyse
import pandas as pd
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import schedule

# ========== 核心配置区 ==========
CONFIG = {
    # "platforms": ["xiaohongshu", "zhihu"],
    # # "platforms": ["zhihu"],
    # "keywords": ["副业", "裁员", "轻创业"],
    # "max_pages": 1,  # 每个平台爬取页数
    # "output_file": "ouput_new_topics.csv",
    # "output_origin_hot_titles": "output_origin_hot_titles.csv",
    # "proxy_server": None,  # 如需代理可填写例如 'http://127.0.0.1:1080'
    # "headless": False  # 是否显示浏览器界面 True | False
}

# 加载 JSON 配置文件
with open('config.json', 'r', encoding='utf-8') as f:
    CONFIG = json.load(f)

# ========== 反爬伪装配置 ==========
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36...",
    "Accept-Language": "zh-CN,zh;q=0.9"
}

# ========== NLP分析模型 ==========
jieba.analyse.set_stop_words("stopwords.txt")
jieba.load_userdict("user_dict.txt")

# ========== 爆款模板库 ==========
TOPIC_TEMPLATES = [
    "被裁第3天，我靠{keyword}赚到{income}（前大厂程序员自述）", # 身份代入+悬念钩子
    "35岁失业后才发现：{keyword}才是打工人的救生圈", # 痛点共鸣+价值锚点
    "偷偷做{keyword}副业，工资外多赚{income}的野路子", # 人性弱点+利益刺激
    "为什么没人告诉我{keyword}能月入5W？35岁老码农转型实录", # 颠覆认知+年龄标签
    "{keyword}搞钱实操：3个步骤让我摆脱职场危机（含工具包）", # 具体方法+资源诱惑
    "程序员转行做{keyword}：从时薪50到日入8000的黑暗进化", # 反差对比+暗黑叙事
    "被HR约谈后，我在茶水间偷偷注册了{keyword}账号", # 场景细节+行动号召
    "35岁程序员血泪警告：这{num}种{keyword}副业千万别碰！", # 风险警示+权威人设
    "前大厂码农：用这{num}个公式，我把{keyword}做成自动提款机", # 技术降维+结果承诺
    "中年失业不可怕，可怕的是不知道{keyword}这么能搞钱" # 情绪共振+价值反转
]

# # 思维破局层（认知冲突）
# "思维觉醒": [
#     "认知杀猪盘",
#     "信息茧房破壁", 
#     "穷人思维癌症",
#     "学生思维死刑",
#     "打工者思维绝症"
# ],

# # 认知变现层（功利吸引）
# "降维打击": [
#     "认知套利",
#     "思维模型盗取", 
#     "元认知作弊器",
#     "反人性操作",
#     "暗黑进化论"
# ],

# # 情绪钩子层（传播裂变）
# "冲突制造": [
#     "毁三观思维",
#     "反常识认知", 
#     "被禁人性课",
#     "精英灭智阴谋",
#     "认知税收割"
# ],

# # 场景化长尾词（精准打击）
# "生存焦虑": [
#     "为什么越努力越贫穷",
#     "底层思维正在毁掉你",
#     "认知差距十倍收入差", 
#     "人性弱点负债陷阱",
#     "思维固化中年危机"
# ]

# ========== 核心爬虫类 ==========
class TopicSpider:
    def __init__(self):
        self.results = []
        self.browser = None
        self.context = None

    async def login_context(self):
        # 首次运行需手动登录
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context(
                # user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)...",
                user_agent=HEADERS["User-Agent"],
                viewport={"width": 1024, "height": 768},
                storage_state="xiaohongshu_auth.json"
            )
            page = await context.new_page()

            if "xiaohongshu" in CONFIG["platforms"]:
                print("请完成登录操作：xiaohongshu...")
                await page.goto("https://www.xiaohongshu.com")
                
                # 检测是否需要登录
                # if "登录" in await page.title():
                try:
                    # 等待 div class=login-container 元素出现，超时时间设为 5 秒
                    await page.wait_for_selector('div.login-container', timeout=5000)
                    print("div class=login-container 元素存在")
                    # 检查 div class=login-container 元素是否可见
                    is_visible = await page.is_visible('div.login-container')
                    if is_visible:
                        print("请手动完成登录操作（60秒等待）...")
                        # await page.wait_for_event("framenavigated", timeout=60000)
                        try:
                            # 等待登录成功后显示的特定元素
                            await page.wait_for_selector('div.login-container', state='detached', timeout=60000)
                            print("登录成功")
                            # 保存认证状态
                            await context.storage_state(path="xiaohongshu_auth.json")
                        except TimeoutError:
                            print("登录失败或超时")
                    else:
                        print("没有检测到登录弹框...")
                except:
                    print("div class=login-container 元素不存在")
                
            if "zhihu" in CONFIG["platforms"]:
                print("请完成登录操作：zhihu...")
                await page.goto("https://www.zhihu.com/hot")
                
                # 检测是否需要登录
                # if "登录" in await page.title():
                try:
                    # 等待 div class=login-container 元素出现，超时时间设为 5 秒
                    await page.wait_for_selector('div.signQr-container', timeout=5000)
                    print("div class=signQr-container 元素存在")
                    # 检查 div class=login-container 元素是否可见
                    is_visible = await page.is_visible('div.signQr-container')
                    if is_visible:
                        print("请手动完成登录操作（60秒等待）...")
                        # await page.wait_for_event("framenavigated", timeout=60000)
                        try:
                            # 等待登录成功后显示的特定元素
                            await page.wait_for_selector('div.signQr-container', state='detached', timeout=60000)
                            print("登录成功")
                            # 保存认证状态
                            await context.storage_state(path="xiaohongshu_auth.json")
                        except TimeoutError:
                            print("登录失败或超时")
                    else:
                        print("没有检测到登录弹框...")
                except:
                    print("div class=signQr-container 元素不存在")
            # 后续代码
            print("继续执行其他操作...")
            await browser.close()
            
    async def init_browser(self):
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=CONFIG["headless"],
            proxy={"server": CONFIG["proxy_server"]} if CONFIG["proxy_server"] else None
        )
        # if "xiaohongshu" in CONFIG["platforms"]:
        self.context = await self.browser.new_context(
            user_agent=HEADERS["User-Agent"],
            viewport={"width": 1024, "height": 768},
            storage_state="xiaohongshu_auth.json"
        )

    async def stealth_crawl(self, url):
        """智能反反爬策略"""
        page = await self.context.new_page()
        await page.goto(url)
        
        # 模拟人类操作模式
        await page.wait_for_timeout(2000)
        for _ in range(3):
            await page.mouse.wheel(0, 15000)
            await page.wait_for_timeout(3000)
            # await page.click("body")  # 随机点击
            
        content = await page.content()
        await page.close()
        return content

    async def parse_xiaohongshu(self, keyword):
        """小红书解析引擎"""
        encoded_keyword = quote(keyword)
        for page in range(1, CONFIG["max_pages"]+1):
            url = f"https://www.xiaohongshu.com/search_result?keyword={encoded_keyword}&page={page}"
            html = await self.stealth_crawl(url)
            soup = BeautifulSoup(html, 'lxml')
            
            # 新版小红书页面解析
            for item in soup.select('section.note-item'):
                try:
                    title = item.select_one('a.title').text.strip()
                    likes = item.select_one('span.count').text
                    self.results.append({
                        "platform": "xiaohongshu",
                        "keyword": keyword,
                        "title": title,
                        "likes": self.format_number(likes)
                    })
                except Exception as e:
                    print(f"解析异常: {str(e)}")
                    continue
        

    async def parse_zhihu(self):
        """知乎热榜解析引擎"""
        url = "https://www.zhihu.com/hot"
        html = await self.stealth_crawl(url)
        soup = BeautifulSoup(html, 'lxml')
        
        for item in soup.select('section.HotItem'):
            title = item.select_one('h2.HotItem-title').text
            heat = item.select_one('div.HotItem-metrics').text
            heat = self.process_text(heat)
            self.results.append({
                "platform": "zhihu",
                "keyword": "热榜",
                "title": title,
                "likes": self.format_number(heat)
            })
    
    # 定义一个函数来处理文本
    @staticmethod
    def process_text(text):
        # 检查文本中是否包含 '万' 字
        if '万' in text:
            # 如果包含 '万' 字，使用正则表达式匹配 '万' 前面的数字部分
            match = re.search(r'(\d+.*?)万.*', text)
            if match:
                return match.group(1) + '万'
        else:
            # 如果不包含 '万' 字，使用正则表达式匹配最前面的数字部分
            match = re.search(r'(\d+).*', text)
            if match:
                return match.group(1)
        return None

    @staticmethod
    def format_number(num_str):
        """格式化数字"""
        if '万' in num_str:
            return float(num_str.replace('万', '')) * 10000
        return float(num_str)

    def analyze_keywords(self):
        """NLP关键词分析"""
        df = pd.DataFrame(self.results)
        text = ' '.join(df['title'].tolist())
        
        # 基于TF-IDF和TextRank的混合算法
        keywords_tfidf = jieba.analyse.extract_tags(
            text, topK=50, withWeight=True, allowPOS=('n', 'v', 'eng'))
        
        keywords_textrank = jieba.analyse.textrank(
            text, topK=50, withWeight=True, allowPOS=('n', 'v', 'eng'))
        
        # 混合加权算法
        combined = {}
        for word, weight in keywords_tfidf:
            combined[word] = weight * 0.6
        for word, weight in keywords_textrank:
            if word in combined:
                combined[word] += weight * 0.4
            else:
                combined[word] = weight * 0.4
                
        return sorted(combined.items(), key=lambda x: x[1], reverse=True)[:20]

    def generate_topics(self, keywords):
        """选题生成器"""
        topics = []
        for word, _ in keywords[:10]:
            for template in TOPIC_TEMPLATES:
                topic = template.format(
                    keyword=word,
                    num=5 if "真相" in template else 3,
                    age=35,
                    income=30000
                )
                topics.append({
                    "topic": topic,
                    "hot_score": self.predict_hot_score(topic)
                })
        return topics

    @staticmethod
    def predict_hot_score(topic):
        """爆款预测模型"""
        hot_signals = {
            "情绪词": ["惊爆", "揭秘", "血泪", "救命", "逆袭"],
            "结构词": ["X步", "X天", "X个", "模型", "公式"],
            "人群词": ["打工人", "宝妈", "00后", "程序员", "体制内"]
        }
        score = 0
        for word in jieba.lcut(topic):
            for _, words in hot_signals.items():
                if word in words:
                    score += 1
        return score

    async def run(self):
        """主运行函数"""
        await self.login_context()
        await self.init_browser()
        
        if "xiaohongshu" in CONFIG["platforms"]:
            for kw in CONFIG["keywords"]:
                await self.parse_xiaohongshu(kw)
                
        if "zhihu" in CONFIG["platforms"]:
            await self.parse_zhihu()
        
        await self.browser.close()

        # 保存原始的热门标题
        ##
        df = pd.DataFrame(self.results)
        df.to_csv(CONFIG["output_origin_hot_titles"], index=False, encoding='utf-8-sig')

        # 数据分析与保存
        keywords = self.analyze_keywords()
        topics = self.generate_topics(keywords)
        
        df = pd.DataFrame(topics)
        df.to_csv(CONFIG["output_file"], index=False)
        print(f"生成选题成功！保存至 {CONFIG['output_file']}")

# ========== 定时任务模块 ==========
def job():
    """每日自动更新任务"""
    print(f"开始执行定时爬取任务：{time.strftime('%Y-%m-%d %H:%M:%S')}")
    spider = TopicSpider()
    asyncio.run(spider.run())

if __name__ == "__main__":
    # 首次立即执行
    job()
    
    # 设置每日定时执行
    schedule.every().day.at("09:00").do(job)
    
    while True:
        schedule.run_pending()
        time.sleep(60)
        