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

# ฟังก์ชันหาเส้นทางสั้นสุดหลายเส้นทางโดยใช้ NetworkX
def find_multiple_paths(G, start, end, max_paths=5, avoid_nodes=None, must_pass_nodes=None, walk_threshold=2, max_skipped=10):
    if avoid_nodes is None:
        avoid_nodes = set()
    if must_pass_nodes is None:
        must_pass_nodes = set()
    
    print(f"🔍 กำลังค้นหาเส้นทางจาก {start} ไป {end} (หลีกเลี่ยง: {avoid_nodes}, ต้องผ่าน: {must_pass_nodes}) สูงสุด {max_paths} เส้นทาง...")

    all_paths = []
    skipped_paths = 0  # ตัวนับเส้นทางที่ถูกข้าม

    try:
        # ใช้ NetworkX หาเส้นทางที่ดีที่สุด
        paths_generator = nx.shortest_simple_paths(G, source=start, target=end, weight='weight')
        
        for path in paths_generator:
            if len(all_paths) >= max_paths:
                break
            if must_pass_nodes.issubset(set(path)):
                cost = sum(G[path[i]][path[i+1]]['weight'] for i in range(len(path)-1))
                
                # ตรวจสอบจำนวนครั้งที่ WALK ปรากฏ
                walk_count = sum(1 for i in range(len(path)-1) if G[path[i]][path[i+1]].get('route_id') == "WALK")

                if walk_count > walk_threshold:
                    skipped_paths += 1
                    print(f"🚫 ข้ามเส้นทางนี้ (WALK = {walk_count} เกิน {walk_threshold}) (ข้ามแล้ว {skipped_paths} ครั้ง)")

                    # ถ้าข้ามถึงจำนวนที่กำหนด → หยุดค้นหา
                    if skipped_paths >= max_skipped:
                        print("⛔ หยุดค้นหาเนื่องจากข้ามเส้นทางมากเกินไป")
                        break
                    continue  # ข้ามเส้นทางที่มี WALK มากเกินไป
                
                all_paths.append((path, cost))
                print(f"🔹 พบเส้นทาง: {path} | ค่าใช้จ่าย: {cost} | WALK: {walk_count}")

    except nx.NetworkXNoPath:
        print("⚠️ ไม่พบเส้นทางที่สามารถเดินทางได้")

    print(f"✨ เส้นทางทั้งหมดที่พบหลังกรอง WALK: {len(all_paths)} เส้นทาง")
    return all_paths

# ฟังก์ชันบันทึกข้อมูลเส้นทางลงในไฟล์ CSV
def save_paths_to_csv(G, all_paths, filename='csv/path_details2.csv'):
    with open(filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['Path Number', 'Route ID', 'Start Stop', 'End Stop', 'Travel Time (seconds)'])

        for path_index, (path_taken, total_cost) in enumerate(all_paths, start=1):
            print(f"📝 บันทึกเส้นทางที่ {path_index} ลงไฟล์ CSV...")
            for i in range(len(path_taken) - 1):
                edge_data = G[path_taken[i]][path_taken[i + 1]]
                route_id = edge_data.get('route_id', 'N/A')
                travel_time = edge_data.get('weight', 0)
                print(f"  ▶️ {path_taken[i]}\t→\t{path_taken[i + 1]}\t\t| Route ID: {route_id}\t\t| เวลาเดินทาง: {travel_time} วินาที")
                writer.writerow([path_index, route_id, path_taken[i], path_taken[i + 1], str(timedelta(seconds=travel_time))])
            print(f"✅ เส้นทางที่ {path_index} ได้บันทึกลงในไฟล์ {filename}")

# ตั้งค่าจุดเริ่มต้นและปลายทาง
start_station = "2794"
end_station = "2797"
avoid_nodes = set()  # node ที่ต้องการหลีกเลี่ยง
must_pass_nodes = set()  # node ที่ต้องผ่าน
max_paths_to_show = 20
walk_threshold = 4  # จำกัด WALK ได้สูงสุด 2 ครั้ง
max_skipped_paths = 1000  # ถ้าข้ามถึง 10 ครั้ง ให้หยุดค้นหา

# ตรวจสอบว่าโหนดมีอยู่ในกราฟ
validate_nodes(G, start_station, end_station)

# ค้นหาเส้นทาง
paths = find_multiple_paths(
    G, start_station, end_station, 
    max_paths=max_paths_to_show, 
    avoid_nodes=avoid_nodes, 
    must_pass_nodes=must_pass_nodes,
    walk_threshold=walk_threshold,
    max_skipped=max_skipped_paths
)

# บันทึกลง CSV ถ้ามีเส้นทาง
if paths:
    save_paths_to_csv(G, paths)
else:
    print("⚠️ ไม่มีเส้นทางที่สามารถเดินทางได้")
