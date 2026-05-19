from agent import process_command

with open('query.txt', 'r', encoding='utf-8') as f:
    user_command = f.read().strip()

print(f'Query: {user_command}')
result = process_command(user_command)
print(f'Result: {result}')