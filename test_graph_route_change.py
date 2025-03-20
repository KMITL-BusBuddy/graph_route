import sys
import networkx as nx
import csv
from datetime import timedelta

# ตั้งค่าการพิมพ์ให้อ่านภาษาไทยได้
sys.stdout.reconfigure(encoding='utf-8')

# โหลดกราฟจากไฟล์ graph.graphml
G = nx.read_graphml('graph/graph_updated.graphml')

# ตรวจสอบว่า node มีอยู่ในกราฟหรือไม่
def validate_nodes(G, start, end):
    if start not in G or end not in G:
        print("⚠️ ไม่พบจุดเริ่มต้นหรือปลายทางในกราฟ")
        sys.exit(1)

# ฟังก์ชันนับจำนวนครั้งที่เปลี่ยนสาย
def count_route_changes(G, path):
    route_changes = 0
    last_route = None

    for i in range(len(path) - 1):
        current_route = G[path[i]][path[i + 1]].get('route_id', 'N/A')
        if last_route is not None and current_route != last_route:
            route_changes += 1
        last_route = current_route

    return route_changes

# ฟังก์ชันหาเส้นทางสั้นสุดหลายเส้นทางโดยใช้ NetworkX
def find_multiple_paths(G, start, end, max_paths=5, avoid_nodes=None, must_pass_nodes=None, walk_threshold=2):
    if avoid_nodes is None:
        avoid_nodes = set()
    if must_pass_nodes is None:
        must_pass_nodes = set()
    
    print(f"🔍 กำลังค้นหาเส้นทางจาก {start} ไป {end} (หลีกเลี่ยง: {avoid_nodes}, ต้องผ่าน: {must_pass_nodes}) สูงสุด {max_paths} เส้นทาง...")

    all_paths = []
    
    try:
        paths_generator = nx.shortest_simple_paths(G, source=start, target=end, weight='weight')
        
        for path in paths_generator:
            if len(all_paths) >= max_paths:
                break
            if must_pass_nodes.issubset(set(path)):
                cost = sum(G[path[i]][path[i+1]]['weight'] for i in range(len(path)-1))
                
                walk_count = sum(1 for i in range(len(path)-1) if G[path[i]][path[i+1]].get('route_id') == "WALK")

                if walk_count > walk_threshold:
                    print(f"🚫 ข้ามเส้นทางนี้ (WALK = {walk_count} เกิน {walk_threshold})")
                    continue  
                
                route_changes = count_route_changes(G, path)
                all_paths.append((path, cost, route_changes, walk_count))
                print(f"🔹 พบเส้นทาง: {path} | ค่าใช้จ่าย: {cost} | เปลี่ยนสาย: {route_changes} ครั้ง | WALK: {walk_count}")

    except nx.NetworkXNoPath:
        print("⚠️ ไม่พบเส้นทางที่สามารถเดินทางได้")

    # เรียงลำดับ: เปลี่ยนสาย (`route_changes`) น้อยสุด → ค่าใช้จ่าย (`cost`) ต่ำสุด
    all_paths.sort(key=lambda x: (x[2], x[1]))  

    print(f"✨ เส้นทางทั้งหมดที่พบหลังกรอง WALK: {len(all_paths)} เส้นทาง")
    return all_paths

# ฟังก์ชันบันทึกข้อมูลเส้นทางลงในไฟล์ CSV
def save_paths_to_csv(G, all_paths, filename='csv/path_details2.csv'):
    with open(filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['Path Number', 'Route ID', 'Start Stop', 'End Stop', 'Travel Time (seconds)', 'Route Changes'])

        for path_index, (path_taken, total_cost, route_changes, walk_count) in enumerate(all_paths, start=1):
            print(f"📝 บันทึกเส้นทางที่ {path_index} ลงไฟล์ CSV...")
            for i in range(len(path_taken) - 1):
                edge_data = G[path_taken[i]][path_taken[i + 1]]
                route_id = edge_data.get('route_id', 'N/A')
                travel_time = edge_data.get('weight', 0)
                print(f"  ▶️ {path_taken[i]}\t→\t{path_taken[i + 1]}\t| Route ID: {route_id}\t| เวลาเดินทาง: {travel_time} วินาที")
                writer.writerow([path_index, route_id, path_taken[i], path_taken[i + 1], str(timedelta(seconds=travel_time)), route_changes])
            print(f"✅ เส้นทางที่ {path_index} ได้บันทึกลงในไฟล์ {filename}")

# ตั้งค่าจุดเริ่มต้นและปลายทาง
start_station = "322"
end_station = "12"
avoid_nodes = set()  
must_pass_nodes = set()  
max_paths_to_show = 20
walk_threshold = 2  

# ตรวจสอบว่าโหนดมีอยู่ในกราฟ
validate_nodes(G, start_station, end_station)

# ค้นหาเส้นทาง
paths = find_multiple_paths(
    G, start_station, end_station, 
    max_paths=max_paths_to_show, 
    avoid_nodes=avoid_nodes, 
    must_pass_nodes=must_pass_nodes,
    walk_threshold=walk_threshold
)

# บันทึกลง CSV ถ้ามีเส้นทาง
if paths:
    save_paths_to_csv(G, paths)
else:
    print("⚠️ ไม่มีเส้นทางที่สามารถเดินทางได้")
