"""测试面试评分机制"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import requests
import json
import time
from fpdf import FPDF

BASE = 'http://8.166.120.119/api/v1'

def create_test_pdf(path):
    """创建测试简历 PDF"""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 16)
    pdf.cell(0, 10, 'Zhang San - Backend Developer', ln=True)
    pdf.set_font('Helvetica', '', 12)
    pdf.cell(0, 8, 'Phone: 13800138000 | Email: zhangsan@test.com', ln=True)
    pdf.ln(5)
    pdf.set_font('Helvetica', 'B', 14)
    pdf.cell(0, 8, 'Education', ln=True)
    pdf.set_font('Helvetica', '', 12)
    pdf.cell(0, 8, 'Peking University - Computer Science - 2022-2026', ln=True)
    pdf.ln(5)
    pdf.set_font('Helvetica', 'B', 14)
    pdf.cell(0, 8, 'Skills', ln=True)
    pdf.set_font('Helvetica', '', 12)
    pdf.cell(0, 8, 'Python, Java, Redis, MySQL, Kafka, Docker, FastAPI', ln=True)
    pdf.ln(5)
    pdf.set_font('Helvetica', 'B', 14)
    pdf.cell(0, 8, 'Projects', ln=True)
    pdf.set_font('Helvetica', '', 12)
    pdf.cell(0, 8, '1. E-commerce Platform Backend - FastAPI + Redis + MySQL', ln=True)
    pdf.cell(0, 8, '2. Real-time Chat System - WebSocket + Kafka', ln=True)
    pdf.output(path)

def test_scoring():
    # 1. Guest login
    print("1. Guest login...")
    r = requests.post(f'{BASE}/auth/guest')
    token = r.json()['data']['access_token']
    headers = {'Authorization': f'Bearer {token}'}
    print("   OK")

    # 2. Upload resume
    print("2. Uploading resume...")
    pdf_path = 'test_resume.pdf'
    create_test_pdf(pdf_path)
    with open(pdf_path, 'rb') as f:
        r = requests.post(f'{BASE}/resumes/upload', headers=headers,
                         files={'file': ('resume.pdf', f, 'application/pdf')})
    result = r.json()
    print(f"   Upload: {result['message']}")

    # 3. Wait for parsing
    print("3. Waiting for resume parsing...")
    resume_id = None
    for i in range(20):
        time.sleep(3)
        r = requests.get(f'{BASE}/resumes', headers=headers)
        resumes = r.json()['data']
        if resumes and resumes[0]['status'] == 'completed':
            resume_id = resumes[0]['id']
            print(f"   Parsed! id={resume_id}")
            break
        status = resumes[0]['status'] if resumes else 'none'
        print(f"   Waiting... ({status})")
    else:
        print("   TIMEOUT!")
        return

    # 4. Start interview
    print("4. Starting interview...")
    r = requests.post(f'{BASE}/interviews/start', headers=headers, json={
        'resume_id': resume_id,
        'target_position': '后端开发',
        'difficulty': 'easy',
        'total_questions': 3
    })
    start = r.json()
    interview_id = start['data']['interview_id']
    first_q = start['data']['first_question']
    print(f"   Interview {interview_id}: {first_q[:50]}...")

    # 5. Test normal answer
    print("\n--- Test 1: Normal answer ---")
    answer1 = 'Redis是一个开源的内存数据结构存储系统，支持字符串、哈希、列表、集合等数据结构。它常用作数据库缓存，通过将热点数据存储在内存中来减少数据库查询压力，提升系统响应速度。Redis还支持持久化机制，包括RDB快照和AOF日志两种方式。'
    print(f"Answer ({len(answer1)} chars): {answer1[:50]}...")
    r = requests.post(f'{BASE}/interviews/{interview_id}/answer', headers=headers, json={'answer': answer1})
    d = r.json()['data']
    print(f"Score: {d['score']}")
    print(f"Feedback: {d['feedback'][:100]}")
    if d['score'] <= 1:
        print("FAIL: Normal answer got score 1!")
    elif '过短' in d.get('feedback', ''):
        print("FAIL: Normal answer got 'too short' feedback!")
    else:
        print("PASS")

    # 6. Test keyword answer
    print("\n--- Test 2: '不知道' answer ---")
    answer2 = '不知道'
    r = requests.post(f'{BASE}/interviews/{interview_id}/answer', headers=headers, json={'answer': answer2})
    d = r.json()['data']
    print(f"Score: {d['score']}")
    print(f"Feedback: {d['feedback'][:100]}")
    if d['score'] > 2:
        print(f"FAIL: '不知道' got score {d['score']}!")
    else:
        print("PASS")

    # 7. Test medium-length answer
    print("\n--- Test 3: Medium answer ---")
    answer3 = 'MySQL的B+树索引结构适合范围查询，叶子节点用链表连接'
    print(f"Answer ({len(answer3)} chars): {answer3}")
    r = requests.post(f'{BASE}/interviews/{interview_id}/answer', headers=headers, json={'answer': answer3})
    d = r.json()['data']
    print(f"Score: {d['score']}")
    print(f"Feedback: {d['feedback'][:100]}")
    if d['score'] <= 1:
        print("FAIL: Medium answer got score 1!")
    elif '过短' in d.get('feedback', ''):
        print("FAIL: Medium answer got 'too short' feedback!")
    else:
        print("PASS")

if __name__ == '__main__':
    test_scoring()
