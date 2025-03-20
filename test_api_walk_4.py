import sys
import networkx as nx
from flask import Flask, request, jsonify

sys.stdout.reconfigure(encoding='utf-8')

G = nx.read_graphml('graph/graph_updated.graphml')

app = Flask(__name__)

def validate_nodes(G, start, end):
    print("🔍 กำลังตรวจสอบจุดเริ่มต้นและปลายทาง...")
    if start not in G or end not in G:
        print("⚠️ ไม่พบจุดเริ่มต้นหรือปลายทางในกราฟ")
        return False, "⚠️ ไม่พบจุดเริ่มต้นหรือปลายทางในกราฟ"
    print("✅ ตรวจสอบจุดเริ่มต้นและปลายทางสำเร็จ")
    return True, None

def find_multiple_paths(G, start, end, max_paths=5, avoid_nodes=None, walk_threshold=2, max_skipped=10):
    print(f"🔍 กำลังค้นหาเส้นทางจาก {start} ไปยัง {end}...")
    if avoid_nodes is None:
        avoid_nodes = set()

    all_paths = []
    skipped_paths = 0

    try:
        paths_generator = nx.shortest_simple_paths(G, source=start, target=end, weight='weight')
        for path in paths_generator:
            print(f"📜 พิจารณาเส้นทาง: {path}")
            
            # กรองเส้นทางที่มี node อยู่ใน avoid_nodes
            if any(node in avoid_nodes for node in path):
                print(f"❌ เส้นทางนี้ถูกกรองออกเนื่องจากมี node ใน avoid_nodes: {avoid_nodes}")
                continue

            if len(all_paths) >= max_paths:
                print(f"🔴 พบเส้นทางครบ {max_paths} เส้นทางแล้ว")
                break
            
            walk_count = sum(1 for i in range(len(path)-1) if G[path[i]][path[i+1]].get('route_id') == "WALK")
            if walk_count > walk_threshold:
                skipped_paths += 1
                if skipped_paths >= max_skipped:
                    print(f"❌ หยุดค้นหาเส้นทางเนื่องจากมีการข้ามเส้นทางที่เดินหลายเกิน {max_skipped} ครั้ง")
                    break
                print(f"🚶‍♀️ ข้ามเส้นทางนี้เนื่องจากเดินมากเกิน {walk_threshold} ครั้ง")
                continue
            
            cost = 0
            total_travel_time = 0
            num_route_changes = -1
            path_details = []
            current_group = None
            line_counter = 1

            for i in range(len(path) - 1):
                edge_data = G[path[i]][path[i + 1]]
                route_id = str(edge_data.get('route_id', 'N/A'))
                travel_time = edge_data.get('weight', 0)

                # Adjust travel time if the route is a "WALK"
                if route_id == "WALK":
                    print(f"🚶‍♀️ เวลาเดิม {travel_time} วินาที")
                    travel_time = travel_time / 2  # Dividing the travel time by 2 for walking routes
                    print(f"🚶‍♀️ เส้นทางเดิน: ลดเวลาเดินทางเหลือ {travel_time} วินาที")

                cost += travel_time
                total_travel_time += travel_time

                if current_group is None or current_group["route_id"] != route_id:
                    num_route_changes += 1
                    current_group = {
                        "route_id": route_id,
                        "lines": {}
                    }
                    path_details.append(current_group)
                    line_counter = 1

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
                "num_route_changes": num_route_changes
            })
    
    except nx.NetworkXNoPath:
        print("⚠️ ไม่มีเส้นทางที่สามารถเชื่อมต่อได้")
        return []
    
    print(f"✅ ค้นพบเส้นทางทั้งหมด: {len(all_paths)} เส้นทาง")
    return sorted(all_paths, key=lambda x: (x["num_route_changes"], x["cost"]))

def find_paths_with_must_pass(G, start, end, must_pass_nodes, max_paths=5, avoid_nodes=None, walk_threshold=2, max_skipped=10):
    print(f"🔍 กำลังค้นหาเส้นทางจาก {start} ไปยัง {end} ที่ต้องผ่าน {must_pass_nodes}...")
    if avoid_nodes is None:
        avoid_nodes = set()
    
    must_pass_nodes = list(must_pass_nodes) if must_pass_nodes else []
    
    if not must_pass_nodes:
        return find_multiple_paths(G, start, end, max_paths, avoid_nodes, walk_threshold, max_skipped)
    
    all_segments = []
    current_start = start
    
    for must_pass in must_pass_nodes:
        print(f"🔀 กำลังหาส่วนเส้นทางที่ต้องผ่าน {must_pass}...")
        segment_paths = find_multiple_paths(G, current_start, must_pass, max_paths, avoid_nodes, walk_threshold, max_skipped)
        if not segment_paths:
            print(f"⚠️ ไม่พบเส้นทางที่ผ่าน {must_pass}")
            return []
        all_segments.append(segment_paths)
        current_start = must_pass
    
    final_segment = find_multiple_paths(G, current_start, end, max_paths, avoid_nodes, walk_threshold, max_skipped)
    if not final_segment:
        print("⚠️ ไม่พบเส้นทางไปยังปลายทางสุดท้าย")
        return []
    all_segments.append(final_segment)
    
    combined_paths = []
    def combine_segments(segments, path_so_far=[], cost_so_far=0, walk_count_so_far=0, path_details_so_far=[], num_route_changes_so_far=0):
        if not segments:
            combined_paths.append({
                "path": path_so_far,
                "cost": cost_so_far,
                "walk_count": walk_count_so_far,
                "path_details": path_details_so_far,
                "total_travel_time_seconds": cost_so_far,
                "num_route_changes": num_route_changes_so_far
            })
            return
        
        for segment in segments[0]:
            new_path = path_so_far[:-1] + segment["path"] if path_so_far else segment["path"]
            new_cost = cost_so_far + segment["cost"]
            new_walk_count = walk_count_so_far + segment["walk_count"]
            new_path_details = path_details_so_far + segment["path_details"]
            new_num_route_changes = num_route_changes_so_far + segment["num_route_changes"]
            combine_segments(segments[1:], new_path, new_cost, new_walk_count, new_path_details, new_num_route_changes)
    
    combine_segments(all_segments)
    
    print(f"✅ ค้นพบเส้นทางที่ต้องผ่าน {len(combined_paths)} เส้นทาง")
    return sorted(combined_paths, key=lambda x: (x["num_route_changes"], x["cost"]))


@app.route('/find_paths', methods=['POST'])
def find_paths():
    data = request.get_json()

    start_station = str(data.get("start_station"))
    end_station = str(data.get("end_station"))
    avoid_nodes = set(map(str, data.get("avoid_nodes", [])))
    must_pass_nodes = set(map(str, data.get("must_pass_nodes", [])))
    max_paths_to_show = data.get("max_paths", 20)
    walk_threshold = data.get("walk_threshold", 2)
    max_skipped_paths = data.get("max_skipped_paths", 10)

    print("🔍 รับข้อมูลการค้นหาจากผู้ใช้...")
    is_valid, error_message = validate_nodes(G, start_station, end_station)
    if not is_valid:
        print(f"⚠️ ข้อผิดพลาดในการตรวจสอบจุดเริ่มต้นหรือปลายทาง: {error_message}")
        return jsonify({"error": error_message}), 400

    paths = find_paths_with_must_pass(
        G, start_station, end_station, must_pass_nodes,
        max_paths=max_paths_to_show,
        avoid_nodes=avoid_nodes,
        walk_threshold=walk_threshold,
        max_skipped=max_skipped_paths
    )

    if not paths:
        print("⚠️ ไม่พบเส้นทางที่สามารถเดินทางได้")
        return jsonify({"message": "⚠️ ไม่มีเส้นทางที่สามารถเดินทางได้"}), 404

    print(f"✅ พบเส้นทางที่สามารถเดินทางได้จำนวน {len(paths)} เส้นทาง")
    return jsonify({"paths": paths}), 200

@app.route('/health', methods=['GET'])
def health_check():
    print("🩺 ตรวจสอบสถานะระบบ...")
    return jsonify({"status": "OK"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
