import sys
import pandas as pd
import networkx as nx
from datetime import timedelta
from tqdm import tqdm
import requests
import json
import re  # ใช้สำหรับแปลงค่าระยะทางจาก text เป็นตัวเลข

# ตั้งค่าการพิมพ์ให้อ่านภาษาไทยได้
sys.stdout.reconfigure(encoding='utf-8')

# โหลดข้อมูลจากไฟล์ GTFS
print("📥 กำลังโหลดข้อมูล GTFS...")
trips = pd.read_csv('namtang-gtfs(2)/trips.txt')
stop_times = pd.read_csv('namtang-gtfs(2)/stop_times.txt')
stops = pd.read_csv('namtang-gtfs(2)/stops.txt')
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
WALKING_DISTANCE_THRESHOLD = 400  # จำกัดระยะห่างของป้ายที่สามารถเดินถึงกัน (เมตร)
GOOGLE_API_KEY = "AIzaSyBv5jj2_yuiOYfLOyLFMyqSUzR0RPi7QfI"

# สร้าง dictionary ของพิกัดป้าย

stop_locations = {str(row['stop_id']): (row['stop_lat'], row['stop_lon']) for _, row in stops.iterrows()}
def parse_duration_to_seconds(duration_text):
    """ แปลงค่าระยะเวลา (เช่น '4 ชั่วโมง 20 นาที 30 วินาที' หรือ '6 นาที 15 วินาที') เป็นวินาที """
    hours = 0
    minutes = 0
    seconds = 0

    hour_match = re.search(r"(\d+)\s*ชั่วโมง", duration_text)
    minute_match = re.search(r"(\d+)\s*นาที", duration_text)
    second_match = re.search(r"(\d+)\s*วินาที", duration_text)

    if hour_match:
        hours = int(hour_match.group(1))  # ดึงค่าชั่วโมง
    if minute_match:
        minutes = int(minute_match.group(1))  # ดึงค่านาที
    if second_match:
        seconds = int(second_match.group(1))  # ดึงค่าวินาที

    total_seconds = (hours * 3600) + (minutes * 60) + seconds
    return total_seconds

# ฟังก์ชันแปลงระยะทางจากข้อความเป็นเมตร
def parse_distance_to_meters(distance_text):
    """ แปลงค่าระยะทางจาก string (เช่น '0.4 กม.') เป็นตัวเลขเมตร """
    match = re.search(r"([\d.]+)\s*(กม|เมตร|m|km)", distance_text, re.IGNORECASE)
    if match:
        value, unit = float(match.group(1)), match.group(2).lower()
        if "กม" in unit or "km" in unit:  # กิโลเมตร -> เมตร
            return int(value * 1000)
        return int(value)  # เป็นเมตรอยู่แล้ว
    return None


# ฟังก์ชันเรียก Google Routes API
def get_walking_distance_time(origin, destination):
    """ ใช้ Google Routes API คำนวณระยะทางและเวลาในการเดิน """
    url = "https://routes.googleapis.com/directions/v2:computeRoutes"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_API_KEY,
        "X-Goog-FieldMask": "routes.localizedValues"
    }
    
    body = {
        "origin": {
            "location": {
                "latLng": {
                    "latitude": origin[0],
                    "longitude": origin[1]
                }
            }
        },
        "destination": {
            "location": {
                "latLng": {
                    "latitude": destination[0],
                    "longitude": destination[1]
                }
            }
        },
        "travelMode": "WALK"
    }
    
    try:
        response = requests.post(url, headers=headers, data=json.dumps(body))
        response_data = response.json()

        # print(f"📡 API Response: {json.dumps(response_data, indent=2, ensure_ascii=False)}")  # 🟢 แสดงผลเต็ม

        if "routes" in response_data and response_data["routes"]:
            route = response_data["routes"][0]["localizedValues"]
            distance_text = route["distance"]["text"]  # ตัวอย่าง: "0.4 กม."
            duration_text = route["duration"]["text"]  # ตัวอย่าง: "6 นาที"

            # print(f"📝 Raw Data -> Distance: {distance_text}, Duration: {duration_text}")

            # แปลงระยะทางเป็นเมตร
            distance_meters = parse_distance_to_meters(distance_text)
            duration_seconds = parse_duration_to_seconds(duration_text)

            # print(f"✅ Converted -> Distance: {distance_meters} meters, Duration: {duration_seconds} seconds")

            return distance_meters, duration_seconds
    except Exception as e:
        print(f"⚠️ API Error: {e}")
    
    return None, None

print("🚶 กำลังคำนวณเส้นทางเดิน...")
for i in tqdm(range(len(stop_locations)), desc="Adding walking paths", dynamic_ncols=True, leave=False):
    for j in range(i + 1, len(stop_locations)):
        stop_1_id, stop_2_id = list(stop_locations.keys())[i], list(stop_locations.keys())[j]
        coord_1, coord_2 = stop_locations[stop_1_id], stop_locations[stop_2_id]

        # print(f"🔄 คำนวณระยะทาง: {stop_1_id} -> {stop_2_id}")

        # ใช้ API Google Routes สำหรับเดินเท้า
        distance_meters, duration_seconds = get_walking_distance_time(coord_1, coord_2)

        if distance_meters is not None and distance_meters <= WALKING_DISTANCE_THRESHOLD:
            print(f"✅ ✅ เพิ่มเส้นทางเดิน: {stop_1_id} -> {stop_2_id} ({distance_meters} เมตร, {duration_seconds} วินาที)")

            # เพิ่มเส้นทางเดินเข้าไปในกราฟ พร้อมระยะทาง
            G.add_edge(
                stop_1_id, stop_2_id,
                weight=duration_seconds,
                distance_meters=distance_meters,
                route_id="WALK"
            )
            G.add_edge(
                stop_2_id, stop_1_id,
                weight=duration_seconds,
                distance_meters=distance_meters,
                route_id="WALK"
            )  # เดินกลับได้

print("✅ เพิ่มเส้นทางเดินเรียบร้อยแล้ว!")

# บันทึกกราฟในรูปแบบ GraphML
print("💾 กำลังบันทึกไฟล์กราฟ...")
nx.write_graphml(G, 'graph/graph2.graphml')
print("✅ กราฟถูกบันทึกในไฟล์ graph/graph2.graphml")
