import sys
sys.stdout.reconfigure(encoding='utf-8')
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('8.166.120.119', username='root', password='5408854088Ab@')

# Write seed SQL file on server
sql_content = r"""INSERT INTO experiences (title, company, position, level, round, content, summary, view_count, like_count, collect_count, is_anonymous, status, created_at) VALUES
('Redis + MySQL + 分布式事务', '字节跳动', '后端开发', '校招', '一面', '## Redis持久化
RDB和AOF的区别...
## MySQL索引
B+树原理...
## 分布式事务
2PC/TCC/Saga...', '字节后端一面，Redis持久化、MySQL索引B+树、分布式事务', 1234, 89, 67, true, 'published', NOW()),
('系统设计 + 高并发 + 消息队列', '字节跳动', '后端开发', '校招', '二面', '## 短链接系统设计
雪花算法+Base62编码...
## 消息队列
Kafka vs RabbitMQ...', '字节后端二面，系统设计短链接、消息队列选型', 856, 56, 45, true, 'published', NOW()),
('C++ + 操作系统 + 网络协议', '腾讯', '后端开发', '校招', '一面', '## C++智能指针
unique_ptr/shared_ptr/weak_ptr...
## 进程线程
区别和通信方式...
## TCP
三次握手四次挥手...', '腾讯后端一面，C++智能指针、进程线程、TCP握手', 2345, 156, 123, true, 'published', NOW()),
('算法 + 系统设计 + 项目经验', '腾讯', '后端开发', '校招', '二面', '## LRU Cache
HashMap+双向链表...
## 朋友圈点赞
数据模型+Redis缓存...', '腾讯后端二面，LRU Cache算法、朋友圈点赞系统', 987, 67, 56, true, 'published', NOW()),
('Vue + React + 性能优化', '字节跳动', '前端开发', '校招', '一面', '## Vue响应式
Object.defineProperty vs Proxy...
## 虚拟DOM
diff算法...
## 性能优化
懒加载/代码分割...', '字节前端一面，Vue/React原理、虚拟DOM、性能优化', 1567, 102, 78, true, 'published', NOW()),
('TypeScript + 工程化 + 首屏优化', '腾讯', '前端开发', '校招', '一面', '## TypeScript
interface vs type, 泛型...
## Webpack vs Vite
ESM按需编译...
## 首屏优化
SSR/SSG/懒加载...', '腾讯前端一面，TS泛型、Webpack vs Vite、首屏优化', 1123, 78, 65, true, 'published', NOW()),
('Java集合 + JVM + 并发编程', '阿里巴巴', '后端开发', '1-3年', '一面', '## HashMap
数组+链表+红黑树...
## JVM
内存模型+GC收集器...
## 并发
synchronized vs ReentrantLock...', '阿里社招一面，HashMap、JVM内存模型、并发编程', 1890, 134, 112, true, 'published', NOW()),
('微服务 + 中间件 + 架构设计', '阿里巴巴', '后端开发', '1-3年', '二面', '## 微服务拆分
单一职责+高内聚低耦合...
## 中间件
RocketMQ+Redis+ES...
## 高可用
熔断降级+限流...', '阿里二面，微服务拆分、中间件原理、高可用架构', 756, 56, 45, true, 'published', NOW()),
('机器学习 + 深度学习 + 推荐系统', '阿里巴巴', '算法工程师', '校招', '综合', '## ML基础
LR vs SVM, 过拟合...
## Transformer
Self-Attention机制...
## 推荐系统
召回+排序+重排...', '阿里算法面试，ML/DL基础、Transformer、推荐系统', 1456, 98, 87, true, 'published', NOW()),
('Java基础 + Spring + 数据库', '美团', '后端开发', '校招', '一面', '## Java基础
== vs equals, ArrayList vs LinkedList...
## Spring
IOC+AOP+Bean生命周期...
## 数据库
ACID+隔离级别...', '美团一面，Java基础、Spring IOC/AOP、数据库事务', 1678, 112, 89, true, 'published', NOW()),
('项目经验 + 场景题 + 算法', '美团', '后端开发', '校招', '二面', '## 项目深挖
技术难点+性能优化...
## 场景题
外卖订单超时提醒...
## 算法
二叉树层序遍历...', '美团二面，项目深挖、订单超时设计、层序遍历', 654, 45, 34, true, 'published', NOW()),
('JavaScript + Vue + CSS', '美团', '前端开发', '校招', '一面', '## JS基础
闭包+Promise...
## Vue
生命周期...
## CSS
BFC...', '美团前端一面，JS闭包、Promise、Vue生命周期、BFC', 890, 56, 45, true, 'published', NOW()),
('Java + 网络 + 数据库', '华为', '后端开发', '1-3年', '技术面', '## String
String/StringBuffer/StringBuilder...
## HTTPS
握手过程...
## SQL优化
索引+EXPLAIN...', '华为一面，String区别、HTTPS握手、SQL优化', 1234, 78, 56, true, 'published', NOW()),
('综合素质 + 项目 + HR面', '华为', '后端开发', '1-3年', '综合', '## 项目经验
技术方案+个人贡献...
## 职业规划
3年规划...
## 综合评估
表达能力+逻辑思维...', '华为二面，项目经验、职业规划、综合素质', 567, 34, 23, true, 'published', NOW()),
('推荐系统 + NLP + 编码', '字节跳动', '算法工程师', '校招', '一面', '## DeepFM
FM+DNN特征交叉...
## BERT vs GPT
编码器vs解码器...
## TopK
小顶堆/快速选择...', '字节算法一面，DeepFM、BERT/GPT、TopK算法', 890, 67, 56, true, 'published', NOW()),
('测试理论 + 自动化 + 性能', '腾讯', '测试开发', '校招', '一面', '## 测试方法
黑盒+白盒+用例设计...
## 自动化
Selenium vs Playwright...
## 性能
QPS/TPS/响应时间...', '腾讯测开一面，测试用例设计、自动化测试、性能测试', 678, 45, 34, true, 'published', NOW()),
('需求分析 + 数据分析 + 产品设计', '阿里巴巴', '产品经理', '校招', '综合', '## 需求优先级
KANO模型+四象限...
## 数据分析
DAU下降排查...
## 产品设计
微信新功能设计...', '阿里产品面试，需求分析、DAU排查、产品设计', 1567, 89, 78, true, 'published', NOW());

INSERT INTO experience_tags (experience_id, tag) VALUES
(1, 'Redis'), (1, 'MySQL'), (1, '分布式'), (1, 'Java'),
(2, '系统设计'), (2, '高并发'), (2, 'Kafka'),
(3, 'C++'), (3, '操作系统'), (3, 'TCP'),
(4, '算法'), (4, '系统设计'),
(5, 'Vue'), (5, 'React'), (5, '性能优化'),
(6, 'TypeScript'), (6, 'Webpack'), (6, 'Vite'),
(7, 'Java'), (7, 'JVM'), (7, '并发'),
(8, '微服务'), (8, '中间件'), (8, '架构设计'),
(9, '机器学习'), (9, '深度学习'), (9, '推荐系统'),
(10, 'Java'), (10, 'Spring'), (10, 'MySQL'),
(11, '系统设计'), (11, '算法'),
(12, 'JavaScript'), (12, 'Vue'), (12, 'CSS'),
(13, 'Java'), (13, '网络'), (13, '数据库'),
(14, '综合素质'), (14, '职业规划'),
(15, '推荐系统'), (15, 'NLP'), (15, '算法'),
(16, '测试'), (16, '自动化'), (16, '性能测试'),
(17, '产品'), (17, '需求分析'), (17, '数据分析');
"""

sftp = ssh.open_sftp()
with sftp.open('/tmp/seed.sql', 'w') as f:
    f.write(sql_content)
sftp.close()
print('SQL file written')

stdin, stdout, stderr = ssh.exec_command('sudo docker exec -i ai-interview-postgres psql -U ai_user -d ai_interview < /tmp/seed.sql')
out = stdout.read().decode('utf-8', errors='replace')
err = stderr.read().decode('utf-8', errors='replace')
print('OUT:', out[:300])
if err: print('ERR:', err[:300])

# Verify
stdin, stdout, stderr = ssh.exec_command('curl -s http://localhost/api/v1/experiences?size=5')
import json
data = json.loads(stdout.read().decode('utf-8', errors='replace'))
print(f"Total: {data['data']['total']}, Items: {len(data['data']['items'])}")
if data['data']['items']:
    print(f"First: {data['data']['items'][0]['title']}")

ssh.close()
