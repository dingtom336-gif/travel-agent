import sys
sys.path.insert(0, '/Users/xiaozhang/Desktop/new_start/claude-code/travel-agent')
try:
    from agent.main import app
    print('Import OK')
except Exception as e:
    print(f'Import FAILED: {e}')
    import traceback
    traceback.print_exc()
