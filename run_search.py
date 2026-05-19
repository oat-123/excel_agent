import sys
import codecs

# บังคับ stdin/stdout ใช้ UTF-8
sys.stdin = codecs.getreader('utf-8')(sys.stdin.buffer)
sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)

from agent import process_command

# อ่านจาก command line
user_command = sys.argv[1] if len(sys.argv) > 1 else ''

if user_command:
    result = process_command(user_command)
    print(result)