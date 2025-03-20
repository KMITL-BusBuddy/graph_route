import sys
import networkx as nx

# ตั้งค่าการพิมพ์ให้อ่านภาษาไทยได้
sys.stdout.reconfigure(encoding='utf-8')

# โหลดกราฟจากไฟล์ graph.graphml
G = nx.read_graphml("graph/graph.graphml")

# อัตราการเพิ่ม weight (เช่น 10 เท่าจากค่าเดิม)
WALKING_WEIGHT_MULTIPLIER = 10

# แก้ไข weight สำหรับเส้นทางที่เป็นการเดิน
for u, v, data in G.edges(data=True):
    if data.get("route_id") == "WALK":
        original_weight = data["weight"]
        new_weight = int(original_weight * WALKING_WEIGHT_MULTIPLIER)  # ปรับค่า weight
        data["weight"] = new_weight  # อัปเดตค่า weight
        
        # แสดงค่าเดิมและค่าใหม่
        print(f"🔄 ปรับเส้นทาง {u} → {v} | weight เดิม: {original_weight} → weight ใหม่: {new_weight}")

# บันทึกกลับเป็นไฟล์ใหม่
nx.write_graphml(G, "graph/graph_updated.graphml")

print("✅ ปรับค่าการเดินเรียบร้อยแล้วและบันทึกเป็น graph_updated.graphml")
