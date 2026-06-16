import sys
sys.stdout.reconfigure(encoding='utf-8')
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('8.166.120.119', username='root', password='5408854088Ab@')

# Write a Python script on the server that will insert seed data
script = '''
import psycopg2

conn = psycopg2.connect(host='localhost', port=5432, dbname='ai_interview', user='ai_user', password='Xk9mP2vL7qR4wN8')
cur = conn.cursor()

experiences = [
    ("Redis + MySQL + 分布式事务", "字节跳动", "后端开发", "校招", "一面",
     "## Redis持久化\\nRDB和AOF的区别...\\n## MySQL索引\\nB+树原理...\\n## 分布式事务\\n2PC/TCC/Saga...",
     "字节后端一面，Redis持久化、MySQL索引B+树、分布式事务", 1234, 89, 67),
    ("系统设计 + 高并发 + 消息队列", "字节跳动", "后端开发", "校招", "二面",
     "## 短链接系统设计\\n雪花算法+Base62编码...\\n## 消息队列\\nKafka vs RabbitMQ...",
     "字节后端二面，系统设计短链接、消息队列选型", 856, 56, 45),
    ("C++ + 操作系统 + 网络协议", "腾讯", "后端开发", "校招", "一面",
     "## C++智能指针\\nunique_ptr/shared_ptr/weak_ptr...\\n## 进程线程\\n区别和通信方式...\\n## TCP\\n三次握手四次挥手...",
     "腾讯后端一面，C++智能指针、进程线程、TCP握手", 2345, 156, 123),
    ("算法 + 系统设计 + 项目经验", "腾讯", "后端开发", "校招", "二面",
     "## LRU Cache\\nHashMap+双向链表...\\n## 朋友圈点赞\\n数据模型+Redis缓存...",
     "腾讯后端二面，LRU Cache算法、朋友圈点赞系统", 987, 67, 56),
    ("Vue + React + 性能优化", "字节跳动", "前端开发", "校招", "一面",
     "## Vue响应式\\nObject.defineProperty vs Proxy...\\n## 虚拟DOM\\ndiff算法...\\n## 性能优化\\n懒加载/代码分割...",
     "字节前端一面，Vue/React原理、虚拟DOM、性能优化", 1567, 102, 78),
    ("TypeScript + 工程化 + 首屏优化", "腾讯", "前端开发", "校招", "一面",
     "## TypeScript\\ninterface vs type, 泛型...\\n## Webpack vs Vite\\nESM按需编译...\\n## 首屏优化\\nSSR/SSG/懒加载...",
     "腾讯前端一面，TS泛型、Webpack vs Vite、首屏优化", 1123, 78, 65),
    ("Java集合 + JVM + 并发编程", "阿里巴巴", "后端开发", "1-3年", "一面",
     "## HashMap\\n数组+链表+红黑树...\\n## JVM\\n内存模型+GC收集器...\\n## 并发\\nsynchronized vs ReentrantLock...",
     "阿里社招一面，HashMap、JVM内存模型、并发编程", 1890, 134, 112),
    ("微服务 + 中间件 + 架构设计", "阿里巴巴", "后端开发", "1-3年", "二面",
     "## 微服务拆分\\n单一职责+高内聚低耦合...\\n## 中间件\\nRocketMQ+Redis+ES...\\n## 高可用\\n熔断降级+限流...",
     "阿里二面，微服务拆分、中间件原理、高可用架构", 756, 56, 45),
    ("机器学习 + 深度学习 + 推荐系统", "阿里巴巴", "算法工程师", "校招", "综合",
     "## ML基础\\nLR vs SVM, 过拟合...\\n## Transformer\\nSelf-Attention机制...\\n## 推荐系统\\n召回+排序+重排...",
     "阿里算法面试，ML/DL基础、Transformer、推荐系统", 1456, 98, 87),
    ("Java基础 + Spring + 数据库", "美团", "后端开发", "校招", "一面",
     "## Java基础\\n== vs equals, ArrayList vs LinkedList...\\n## Spring\\nIOC+AOP+Bean生命周期...\\n## 数据库\\nACID+隔离级别...",
     "美团一面，Java基础、Spring IOC/AOP、数据库事务", 1678, 112, 89),
    ("项目经验 + 场景题 + 算法", "美团", "后端开发", "校招", "二面",
     "## 项目深挖\\n技术难点+性能优化...\\n## 场景题\\n外卖订单超时提醒...\\n## 算法\\n二叉树层序遍历...",
     "美团二面，项目深挖、订单超时设计、层序遍历", 654, 45, 34),
    ("JavaScript + Vue + CSS", "美团", "前端开发", "校招", "一面",
     "## JS基础\\n闭包+Promise...\\n## Vue\\n生命周期...\\n## CSS\\nBFC...",
     "美团前端一面，JS闭包、Promise、Vue生命周期、BFC", 890, 56, 45),
    ("Java + 网络 + 数据库", "华为", "后端开发", "1-3年", "技术面",
     "## String\\nString/StringBuffer/StringBuilder...\\n## HTTPS\\n握手过程...\\n## SQL优化\\n索引+EXPLAIN...",
     "华为一面，String区别、HTTPS握手、SQL优化", 1234, 78, 56),
    ("综合素质 + 项目 + HR面", "华为", "后端开发", "1-3年", "综合",
     "## 项目经验\\n技术方案+个人贡献...\\n## 职业规划\\n3年规划...\\n## 综合评估\\n表达能力+逻辑思维...",
     "华为二面，项目经验、职业规划、综合素质", 567, 34, 23),
    ("推荐系统 + NLP + 编码", "字节跳动", "算法工程师", "校招", "一面",
     "## DeepFM\\nFM+DNN特征交叉...\\n## BERT vs GPT\\n编码器vs解码器...\\n## TopK\\n小顶堆/快速选择...",
     "字节算法一面，DeepFM、BERT/GPT、TopK算法", 890, 67, 56),
    ("测试理论 + 自动化 + 性能", "腾讯", "测试开发", "校招", "一面",
     "## 测试方法\\n黑盒+白盒+用例设计...\\n## 自动化\\nSelenium vs Playwright...\\n## 性能\\nQPS/TPS/响应时间...",
     "腾讯测开一面，测试用例设计、自动化测试、性能测试", 678, 45, 34),
    ("需求分析 + 数据分析 + 产品设计", "阿里巴巴", "产品经理", "校招", "综合",
     "## 需求优先级\\nKANO模型+四象限...\\n## 数据分析\\nDAU下降排查...\\n## 产品设计\\n微信新功能设计...",
     "阿里产品面试，需求分析、DAU排查、产品设计", 1567, 89, 78),
]

for exp in experiences:
    cur.execute("""
        INSERT INTO experiences (title, company, position, level, round, content, summary, view_count, like_count, collect_count, is_anonymous, status, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, true, 'published', NOW())
    """, exp)

# Insert tags
tags = [
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
    (17, '产品'), (17, '需求分析'), (17, '数据分析'),
]

for exp_id, tag in tags:
    cur.execute("INSERT INTO experience_tags (experience_id, tag) VALUES (%s, %s) ON CONFLICT DO NOTHING", (exp_id, tag))

conn.commit()
print(f"Inserted {len(experiences)} experiences and {len(tags)} tags")
cur.close()
conn.close()
'''

# Write script to server
sftp = ssh.open_sftp()
with sftp.open('/tmp/insert_seed.py', 'w') as f:
    f.write(script)
sftp.close()
print('Script uploaded')

# Execute
stdin, stdout, stderr = ssh.exec_command('python3 /tmp/insert_seed.py')
print('OUT:', stdout.read().decode('utf-8', errors='replace'))
print('ERR:', stderr.read().decode('utf-8', errors='replace'))

# Verify
stdin, stdout, stderr = ssh.exec_command('curl -s http://localhost/api/v1/experiences')
import json
data = json.loads(stdout.read().decode('utf-8', errors='replace'))
print(f"Total experiences: {data['data']['total']}")

ssh.close()
