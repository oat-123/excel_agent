import sys
sys.path.append('.')
from memory.name_mapping import get_corrected_keyword

# ทดสอบการปรับ "ภทธภูมิ ทาภักดี"
result = get_corrected_keyword('ภทธภูมิ ทาภักดี')
print(f'get_corrected_keyword("ภทธภูมิ ทาภักดี"): {result}')

# ดู mapping ที่เรียนรู้
from memory.name_mapping import _load_mappings
mappings = _load_mappings()
print(f'Current mappings: {mappings}')