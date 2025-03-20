import sys
import pandas as pd
import networkx as nx
from datetime import timedelta
from geopy.distance import geodesic  # ใช้คำนวณระยะทางระหว่างพิกัด
from tqdm import tqdm  # ใช้สำหรับแสดง progress bar

# ตั้งค่าการพิมพ์ให้อ่านภาษาไทยได้
sys.stdout.reconfigure(encoding='utf-8')

# โหลดข้อมูลจากไฟล์ GTFS
print("📥 กำลังโหลดข้อมูล GTFS...")
trips = pd.read_csv('namtang.gtfs/trips.txt')
stop_times = pd.read_csv('namtang.gtfs/stop_times.txt')
stops = pd.read_csv('namtang.gtfs/stops.txt')
print("✅ โหลดข้อมูลเสร็จสิ้น!")

# แปลงเวลาจาก string เป็น datetime
stop_times['arrival_time'] = pd.to_datetime(stop_times['arrival_time'], format='%H:%M:%S')
stop_times['departure_time'] = pd.to_datetime(stop_times['departure_time'], format='%H:%M:%S')

# สร้างกราฟเปล่า (Directed Graph)
G = nx.DiGraph()

# รวมข้อมูล trips.txt กับ stop_times.txt ตาม trip_id
merged_data = pd.merge(stop_times, trips, on='trip_id')

# เพิ่ม edges สำหรับเส้นทางรถโดยสาร
print("🚌 กำลังเพิ่มเส้นทางรถโดยสารลงในกราฟ...")
for trip_id, trip_data in tqdm(merged_data.groupby('trip_id'), desc="Adding bus routes", dynamic_ncols=True, leave=False):
    for i in range(len(trip_data) - 1):
        stop_1, stop_2 = trip_data.iloc[i], trip_data.iloc[i + 1]
        stop_1_id, stop_2_id = str(stop_1['stop_id']), str(stop_2['stop_id'])
        route_id = stop_1['route_id']

        # คำนวณเวลาที่ใช้เดินทาง
        travel_time = (stop_2['arrival_time'] - stop_1['departure_time']).seconds

        # เพิ่ม edge ในกราฟ
        G.add_edge(stop_1_id, stop_2_id, weight=travel_time, route_id=route_id)

print("✅ เพิ่มเส้นทางรถโดยสารเสร็จแล้ว!")

# เพิ่ม edges สำหรับการเดินทางด้วยเท้า
WALKING_SPEED = 1.39  # ความเร็วเดินเฉลี่ย (เมตรต่อวินาที)
WALKING_DISTANCE_THRESHOLD = 400  # จำกัดระยะห่างของป้ายที่สามารถเดินถึงกัน (เมตร)

# สร้าง dictionary ของพิกัดป้าย
stop_locations = {str(row['stop_id']): (row['stop_lat'], row['stop_lon']) for _, row in stops.iterrows()}

# คำนวณระยะทางระหว่างป้ายทั้งหมดและเพิ่มเส้นทางเดิน
stop_ids = list(stop_locations.keys())

print("🚶 กำลังคำนวณเส้นทางเดิน...")
for i in tqdm(range(len(stop_ids)), desc="Adding walking paths", dynamic_ncols=True, leave=False):
    for j in range(i + 1, len(stop_ids)):
        stop_1_id, stop_2_id = stop_ids[i], stop_ids[j]
        coord_1, coord_2 = stop_locations[stop_1_id], stop_locations[stop_2_id]

        # คำนวณระยะทาง (เมตร)
        distance = geodesic(coord_1, coord_2).meters

        if distance <= WALKING_DISTANCE_THRESHOLD:
            walking_time = distance / WALKING_SPEED
            G.add_edge(stop_1_id, stop_2_id, weight=int(walking_time), route_id="WALK")
            G.add_edge(stop_2_id, stop_1_id, weight=int(walking_time), route_id="WALK")  # เดินกลับได้

print("✅ เพิ่มเส้นทางเดินเรียบร้อยแล้ว!")


# บันทึกกราฟในรูปแบบ GPickle
print("💾 กำลังบันทึกไฟล์กราฟ...")

# บันทึกกราฟเป็นไฟล์ GraphML
nx.write_graphml(G, 'graph/graph.graphml')

print("✅ กราฟถูกบันทึกในไฟล์ graph/graph.graphml")
