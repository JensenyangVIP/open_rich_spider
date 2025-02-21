import json
import jieba

from main import TopicSpider

# class HotTopicPredictor:
#     @staticmethod
#     def predict_hot_score(topic):
#         """爆款预测模型"""
#         # 读取 JSON 文件
#         with open('hot_signals.json', 'r', encoding='utf-8') as file:
#             hot_signals = json.load(file)

#         score = 0
#         for word in jieba.lcut(topic):
#             for _, words in hot_signals.items():
#                 if word in words:
#                     score += 1
#         return score

# 示例使用
if __name__ == "__main__":
    topic = "揭秘程序员的血泪故事：如何逆袭成为大厂打工人"
    print(f"jieba.lcut: {jieba.lcut(topic)}")
    score = TopicSpider.predict_hot_score(topic)
    print(f"话题热度评分: {score}")