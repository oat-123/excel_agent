import json
import os
import re
import time
from brain.knowledge_graph import add_entity, add_relation, get_related_entities, infer_knowledge, update_entity_access, find_connection, add_person, add_rank, add_department, add_file_entity, get_entities_by_type, get_entity_suggestions
from brain.context_memory import add_interaction, learn_pattern, get_context_for_analysis, load_context

THAI_RANKS = ["พล.", "พลโท.", "พลเอก", "นพ.", "น.พ.", "ร.อ.", "ร.ท.", "ร.ต.", "จ่อ.", "ส.ท.", "ส.ต.", "ส.จ.", 
              "โทร.", "พัน.", "พัน.๑", "พัน.๒", "ร้อย.", "ร้อย.๑", "ร้อย.๒"]

class AIBrain:
    def __init__(self):
        self.knowledge_cache = {}
    
    def analyze_and_learn(self, user_command, action, result):
        self._extract_entities(user_command)
        self._build_relations(user_command, action)
        self._record_interaction(user_command, action, result)
        self._learn_from_context(user_command, action)
    
    def _extract_entities(self, text):
        entities = {
            "file": re.findall(r'([a-zA-Z0-9_-]+\.xlsx)', text),
            "number": re.findall(r'\d+', text),
            "date": re.findall(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', text),
            "keyword": re.findall(r'["\']?([\u0E00-\u0E7F]+)["\']?', text)
        }
        
        for file in entities["file"]:
            add_entity(file, "file", {"extension": "xlsx"})
            add_file_entity(file)
        
        for num in entities["number"][:5]:
            add_entity(f"num_{num}", "number", {"value": num})
        
        # Extract Thai person names and ranks
        rank_pattern = r'(นพ\.|น\.พ\.|ร\.อ\.|ร\.ท\.|ร\.ต\.|จ่อ\.|ส\.ท\.|ส\.ต\.|ส\.จ\.|โทร\.|พัน\.|ร้อย\.)\s*([\u0E00-\u0E7F]+)'
        rank_matches = re.findall(rank_pattern, text)
        for rank, name in rank_matches:
            clean_rank = rank.strip()
            clean_name = name.strip()
            add_person(clean_name, rank=clean_rank)
            add_rank(clean_rank)
        
        # Extract departments (สังกัด)
        dept_match = re.search(r'สังกัด\s*([\u0E00-\u0E7F]+)', text)
        if dept_match:
            dept_name = dept_match.group(1).strip()
            add_department(dept_name)
        
        return entities
    
    def _learn_from_context(self, user_command, action):
        """Learn patterns from user's command history"""
        context = load_context()
        recent_interactions = context.get("contexts", [])[-20:]
        
        # Find similar commands and their successful patterns
        for interaction in reversed(recent_interactions):
            if interaction.get("action") == action:
                # Strengthen relation between command pattern and action
                cmd_words = set(interaction.get("user_input", "").lower().split())
                for word in cmd_words:
                    if len(word) > 2:
                        add_relation(word, action, "associated_with", 0.5)
                break
    
    def _build_relations(self, text, action):
        text_lower = text.lower()
        
        action_keywords = {
            "create": ["สร้าง", "สร้างไฟล์", "สร้างไฟล์ใหม่"],
            "add": ["เพิ่ม", "เพิ่มข้อมูล", "ใส่"],
            "read": ["อ่าน", "ดู", "แสดง"],
            "search": ["ค้นหา", "หา", "หาเบอร์"],
            "update": ["แก้ไข", "ปรับ", "เปลี่ยน"],
            "delete": ["ลบ", "ทำลาย"],
            "copy": ["คัดลอก", "copy"],
            "merge": ["ผสาน", "รวม"],
            "convert": ["แปลง", "เปลี่ยน"],
            "summarize": ["สรุป", "สรุปข้อมูล"],
            "statistics": ["สถิติ", "statistic"]
        }
        
        for action_type, keywords in action_keywords.items():
            for kw in keywords:
                if kw in text_lower:
                    add_relation(action_type, action, "triggers", 0.9)
                    break
    
    def _record_interaction(self, user_command, action, result):
        add_interaction(user_command, action, result)
        learn_pattern(user_command, action)
    
    def is_small_talk(self, text):
        """Identify if the input is a greeting or general conversation"""
        text_lower = text.lower()
        greetings = ["สวัสดี", "hello", "hi", "หวัดดี", "สบายดีไหม", "เป็นไงบ้าง", "jarvis", "จาร์วิส", "ไง", "hey", "yo"]
        thanks = ["ขอบคุณ", "แต๊ง", "thanks", "thank you", "ขอบใจ", "เยี่ยม", "ดีมาก", "ขอบพระคุณ"]
        info = ["คุณคือใคร", "ทำอะไรได้บ้าง", "who are you", "help", "ช่วยด้วย", "แนะนำตัว", "ทำอะไรได้"]
        small_talk = ["ร้อนจัง", "หิวข้าว", "เบื่อ", "งานเยอะ", "เหนื่อย"]
        
        for g in greetings:
            if g in text_lower: return "greeting"
        for t in thanks:
            if t in text_lower: return "thanks"
        for i in info:
            if i in text_lower: return "info"
        for s in small_talk:
            if s in text_lower: return "chit_chat"
        return None

    def get_conversation_response(self, category, user_input=None):
        """Provide a natural response based on the conversation category"""
        responses = {
            "greeting": [
                "สวัสดีครับท่าน มีอะไรให้ J.A.R.V.I.S รับใช้ในวันนี้ไหมครับ?",
                "สวัสดีครับ! ระบบจัดการ Excel ของผมพร้อมทำงาน 100% แล้วครับ",
                "สวัสดีครับ วันนี้มีข้อมูลชุดไหนให้ผมวิเคราะห์หรือสร้างไฟล์เพิ่มไหมครับ?",
                "ยินดีที่ได้ยินเสียงคุณครับ ต้องการให้ผมจัดการ Spreadsheet ตัวไหนดีครับ?"
            ],
            "thanks": [
                "ด้วยความยินดีอย่างยิ่งครับท่าน",
                "ยินดีรับใช้เสมอครับ!",
                "ไม่เป็นไรครับ เป็นหน้าที่ของผมอยู่แล้ว มีอะไรเรียกได้ตลอดนะครับ",
                "ความสำเร็จของคุณคือความภูมิใจของระบบเราครับ"
            ],
            "info": [
                "ผมคือ J.A.R.V.I.S ครับ ผู้ช่วยอัจฉริยะที่ออกแบบมาเพื่อจัดการงาน Excel และ Google Sheets โดยเฉพาะ ผมสามารถ สร้างไฟล์ใหม่, เพิ่มข้อมูล, ค้นหาประวัติ, สรุปสถิติเชิงลึก และสร้างกราฟให้คุณได้ในพริบตาครับ"
            ],
            "chit_chat": [
                "เข้าใจเลยครับ แต่อย่างน้อยผมก็ยังอยู่ตรงนี้ช่วยเบาแรงงาน Excel ให้คุณได้นะ!",
                "พักสายตาสักครู่ไหมครับ เดี๋ยวผมจัดการงานที่เหลือต่อให้เอง",
                "สู้ๆ ครับท่าน ผมจะช่วยให้งานของคุณเสร็จเร็วที่สุดเท่าที่จะทำได้ครับ"
            ],
            "learning": [
                "ผมยังไม่มีข้อมูลเกี่ยวกับคำสั่งนี้ในระบบหลัก แต่ผมได้บันทึกไว้ในฐานการเรียนรู้แล้วครับ ท่านต้องการให้ผมทำอะไรเมื่อได้รับคำสั่งนี้ในอนาคตไหมครับ?",
                "น่าสนใจครับ เป็นคำสั่งที่แปลกใหม่สำหรับผม ผมขอจดจำรูปแบบนี้ไว้เพื่อพัฒนาระบบการประมวลผลให้ดียิ่งขึ้นนะครับ",
                "ดูเหมือนจะเป็นหัวข้อใหม่ที่ผมยังไม่เคยเจอ ผมกำลังวิเคราะห์บริบทและเตรียมอัปเดตฐานความรู้ครับ"
            ]
        }
        import random
        return random.choice(responses.get(category, ["รับทราบครับท่าน"]))

    def handle_unrecognized_command(self, text):
        """Process commands that don't match known tools"""
        # 1. Check if it's general conversation first
        category = self.is_small_talk(text)
        if category:
            return {"status": "success", "response": self.get_conversation_response(category)}
        
        # 2. If truly unknown, trigger learning mode response
        # Here we could call an LLM API if available for a more creative response
        # For now, we use our learning-ready response
        
        # Save for later learning
        self._record_unknown_pattern(text)
        
        return {
            "status": "success", 
            "response": self.get_conversation_response("learning", text)
        }

    def _record_unknown_pattern(self, text):
        """Store unrecognized patterns for future system updates"""
        try:
            unknown_path = os.path.join("brain", "unknown_patterns.json")
            patterns = []
            if os.path.exists(unknown_path):
                with open(unknown_path, "r", encoding="utf-8") as f:
                    patterns = json.load(f)
            
            # Simple deduplication
            if text not in [p.get("input") for p in patterns]:
                patterns.append({
                    "input": text,
                    "timestamp": time.time(),
                    "frequency": 1
                })
            else:
                for p in patterns:
                    if p["input"] == text:
                        p["frequency"] += 1
                        break
            
            with open(unknown_path, "w", encoding="utf-8") as f:
                json.dump(patterns, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Error recording unknown pattern: {e}")
    def get_smart_suggestions(self, partial_input):
        suggestions = []
        patterns = get_context_for_analysis()
        
        # Thai-specific pattern matching
        thai_patterns = {
            "สร้าง|create": ["สร้างไฟล์ Excel ใหม่", "สร้างไฟล์จาก Template"],
            "เพิ่ม|add": ["เพิ่มข้อมูลลงในไฟล์", "เพิ่มนักเรียน/บุคลากร"],
            "ค้นหา|หา": ["ค้นหาข้อมูลในฐานข้อมูล", "ค้นหาในไฟล์ Excel"],
            "สรุป|สถิติ": ["สรุปและวิเคราะห์ข้อมูล", "ดูสถิติไฟล์"],
            "แก้ไข|update": ["แก้ไขข้อมูลที่เลือก", "อัปเดตข้อมูล"],
            "ลบ|delete": ["ลบแถวข้อมูล", "ลบไฟล์"]
        }
        
        for pattern, suggs in thai_patterns.items():
            keywords = pattern.split("|")
            for kw in keywords:
                if kw in partial_input.lower():
                    suggestions.extend(suggs)
                    break
        
        # Proactive contextual suggestions based on current state
        if not partial_input:
            context = load_context()
            recent = context.get("contexts", [])[-1:]
            if recent:
                last_action = recent[0].get("action")
                if last_action == "create_excel_file":
                    suggestions.append("เพิ่มข้อมูลลงในไฟล์ที่สร้างใหม่")
                elif last_action == "search_student":
                    suggestions.append("บันทึกผลการค้นหาลงไฟล์ Excel")
                elif last_action == "summarize_data":
                    suggestions.append("สร้างกราฟจากข้อมูลสรุป")

        # Get person/department suggestions from knowledge graph
        entity_suggestions = get_entity_suggestions(partial_input)
        for entity in entity_suggestions[:3]:
            if entity["type"] == "person":
                suggestions.append(f"ค้นหา {entity['name']} ({entity['properties'].get('rank', '')})")
            elif entity["type"] == "department":
                suggestions.append(f"ดูข้อมูล {entity['name']}")
        
        return list(dict.fromkeys(suggestions))

    def get_suggestions(self, partial_input: str):
        """Alias used by app to get suggestions."""
        return self.get_smart_suggestions(partial_input)


    def infer_context(self, entity_name):
        """Infer relationships and context for an entity"""
        inferred = infer_knowledge(entity_name)
        if not inferred:
            return None
        
        context = {
            "entity": inferred["entity"],
            "related": inferred["related"],
            "inferred_connections": []
        }
        
        for related_entity, strength in inferred["related"][:3]:
            path = find_connection(entity_name, related_entity)
            if path:
                context["inferred_connections"].append({
                    "to": related_entity,
                    "path": path,
                    "strength": strength
                })
        
        return context

    def reason(self, query):
        """Advanced reasoning based on knowledge graph"""
        query_lower = query.lower()
        results = {"patterns": [], "entities": [], "suggestions": []}

        knowledge = load_knowledge()
        # knowledge["entities"] is a dict {name: data}, iterate over keys
        entities_dict = knowledge.get("entities", {})
        if not isinstance(entities_dict, dict):
            entities_dict = {}

        for entity_name in entities_dict:
            if entity_name.lower() in query_lower:
                results["entities"].append(entity_name)
                inference = self.infer_context(entity_name)
                if inference:
                    results["patterns"].append(inference)

        results["suggestions"] = self.get_smart_suggestions(query)
        return results

brain = AIBrain()

def load_knowledge():
    from brain.knowledge_graph import load_knowledge as _load
    return _load()