import sys
import networkx as nx
import csv
import json
from datetime import timedelta
from flask import Flask, request, jsonify

# ตั้งค่าการพิมพ์ให้อ่านภาษาไทยได้
sys.stdout.reconfigure(encoding='utf-8')

# โหลดกราฟจากไฟล์ graph.graphml
G = nx.read_graphml('graph/graph_updated.graphml')

# สร้าง Flask App
app = Flask(__name__)

# ตรวจสอบว่า node มีอยู่ในกราฟหรือไม่
def validate_nodes(G, start, end):
    if start not in G or end not in G:
        return False, "⚠️ ไม่พบจุดเริ่มต้นหรือปลายทางในกราฟ"
    return True, None

# ฟังก์ชันหาเส้นทางสั้นสุดหลายเส้นทางโดยใช้ NetworkX
def find_multiple_paths(G, start, end, max_paths=5, avoid_nodes=None, must_pass_nodes=None, walk_threshold=2, max_skipped=10):
    if avoid_nodes is None:
        avoid_nodes = set()
    if must_pass_nodes is None:
        must_pass_nodes = set()

    print(f"🔍 Searching paths from {start} to {end} (Avoid: {avoid_nodes}, Must Pass: {must_pass_nodes}) Max {max_paths} paths...")

    all_paths = []
    skipped_paths = 0  

    try:
        paths_generator = nx.shortest_simple_paths(G, source=start, target=end, weight='weight')
        
        for path in paths_generator:
            if len(all_paths) >= max_paths:
                break
            if must_pass_nodes.issubset(set(path)):
                cost = sum(G[path[i]][path[i+1]]['weight'] for i in range(len(path)-1))
                
                walk_count = sum(1 for i in range(len(path)-1) if G[path[i]][path[i+1]].get('route_id') == "WALK")

                if walk_count > walk_threshold:
                    skipped_paths += 1
                    print(f"🚫 Skipping path (WALK = {walk_count} > {walk_threshold}) (Skipped {skipped_paths} times)")

                    if skipped_paths >= max_skipped:
                        print("⛔ Stopping search due to excessive skips")
                        break
                    continue
                
                path_details = []
                current_group = None
                line_counter = 1
                total_travel_time = 0
                num_route_changes = -1  # เริ่มจาก -1 เพราะอันแรกยังไม่ต้องนับเปลี่ยนสาย

                for i in range(len(path) - 1):
                    edge_data = G[path[i]][path[i + 1]]
                    route_id = str(edge_data.get('route_id', 'N/A'))  
                    travel_time = edge_data.get('weight', 0)  
                    total_travel_time += travel_time

                    # 🔥 Check if we are still in the same route_id group
                    if current_group is None or current_group["route_id"] != route_id:
                        num_route_changes += 1  # นับการเปลี่ยนสาย
                        current_group = {
                            "route_id": route_id,
                            "lines": {}
                        }
                        path_details.append(current_group)
                        line_counter = 1

                    # Add line to the current route_id group
                    current_group["lines"][f"line{line_counter}"] = {
                        "start": path[i],
                        "end": path[i + 1],
                        "travel_time_seconds": travel_time
                    }
                    line_counter += 1

                all_paths.append({
                    "path": path,
                    "cost": cost,
                    "walk_count": walk_count,
                    "path_details": path_details,
                    "total_travel_time_seconds": total_travel_time,
                    "num_route_changes": num_route_changes  # ✅ เก็บจำนวนครั้งที่เปลี่ยนสาย
                })
                print(f"🔹 Found path: {path} | Cost: {cost} | WALK: {walk_count} | Changes: {num_route_changes} | Total Travel Time: {total_travel_time} sec")

    except nx.NetworkXNoPath:
        print("⚠️ No path found")
        return []

    # ✅ เรียงเส้นทางโดยให้เส้นทางที่เปลี่ยนสายน้อยที่สุดมาก่อน
    all_paths = sorted(all_paths, key=lambda x: (x["num_route_changes"], x["cost"]))

    print(f"✨ Total valid paths: {len(all_paths)}")
    return all_paths




# API Endpoint สำหรับสุขภาพเซิร์ฟเวอร์ (Health Check)
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "OK"}), 200

# รันเซิร์ฟเวอร์ Flask
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
