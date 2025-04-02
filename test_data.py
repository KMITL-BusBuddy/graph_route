import networkx as nx
import sys

sys.stdout.reconfigure(encoding='utf-8')

# โหลดกราฟจากไฟล์ graphml
G = nx.read_graphml('graph/graph_updated.graphml')

# ตรวจสอบข้อมูล weight ของทุก edge ในกราฟ
print("⚙️ ข้อมูล weight ของ edges:")
for u, v, data in G.edges(data=True):
    print(f"Edge: {u} -> {v}, weight: {data.get('weight', 'ไม่มีข้อมูล weight')}")