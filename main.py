import cv2
import numpy as np
import requests
from ultralytics import YOLO
from sort03 import Sort
import os
import mysql.connector
from datetime import datetime
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

# ==================== FASTAPI ====================
app = FastAPI()

# ==================== STREAM URL ====================
url = "http://100.119.95.125:8000/video"
stream = requests.get(url, stream=True)
bytes_data = b""

# ==================== MySQL Connection ====================
db = mysql.connector.connect(
    host="mysql-3538d07b-learntrydummyacc-4de5.c.aivencloud.com",
    user="avnadmin",
    password="AVNS_brlyJsLSltykSCZU3Ic",
    database="testDB",
    port=24006,
)
cursor = db.cursor()

# ==================== Folder to Save Images ====================
save_folder = (
    r"F:/nn-clg/programming/imageRecognition/programs/personDetectMySql/saved_persons"
)
os.makedirs(save_folder, exist_ok=True)

# ==================== YOLO & SORT ====================
model = YOLO("F:/nn-clg/programming/imageRecognition/modelWeights/yolov8n.pt")
className = model.names
tracker = Sort(max_age=20, min_hits=3, iou_threshold=0.3)

totalPerson = set()
savedPersonIDs = set()


# ==================== STREAM GENERATOR ====================
def generate_frames():

    global bytes_data

    while True:

        # Read chunk from remote MJPEG stream
        chunk = stream.raw.read(1024)
        if not chunk:
            print("Stream disconnected!")
            break

        bytes_data += chunk

        start = bytes_data.find(b"\xff\xd8")  # JPEG start
        end = bytes_data.find(b"\xff\xd9")  # JPEG end

        if start == -1 or end == -1:
            continue

        jpg = bytes_data[start : end + 2]
        bytes_data = bytes_data[end + 2 :]

        frame = cv2.imdecode(np.frombuffer(jpg, np.uint8), cv2.IMREAD_COLOR)
        if frame is None:
            continue

        # =================== YOLO Detection ====================
        results = model(frame, stream=True)
        detections = np.empty((0, 5))

        for r in results:
            for box in r.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                conf = float(box.conf[0])
                cls = int(box.cls[0])

                if className[cls] == "person" and conf>0.4:
                    detections = np.vstack([detections, [x1, y1, x2, y2, conf]])

        # ==================== SORT Tracking ====================
        tracked = tracker.update(detections)

        for result in tracked:
            x1, y1, x2, y2, id = map(int, result)

            # Draw visualization
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(
                frame,
                f"ID {id}",
                (x1, max(30, y1)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2,
            )

            target_prefix = f"person_{id}"

            exists = any(
                filename.startswith(target_prefix)
                for filename in os.listdir(save_folder)
            )

            # Save unique image of a new person ID
            if (id not in savedPersonIDs) and not(exists):
                totalPerson.add(id)
                crop = frame[max(0, y1 - 10) : y2 + 10, max(0, x1 - 10) : x2 + 10]

                if crop.size > 0:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    image_path = os.path.join(
                        save_folder, f"person_{id}_{timestamp}.jpg"
                    )
                    cv2.imwrite(image_path, crop)

                    try:
                        cursor.execute(
                            "INSERT INTO detected_person (person_id, image_path) VALUES (%s, %s)",
                            (id, image_path),
                        )
                        db.commit()
                        savedPersonIDs.add(id)
                        # print(f"[DB] Saved Person {id}")
                    except mysql.connector.IntegrityError:
                        pass

        # Text overlay (optional)
        cv2.putText(
            frame,
            f"Total Persons: {len(totalPerson)}",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 255),
            2,
        )

        # ==================== ENCODE & STREAM ====================
        ret, encoded = cv2.imencode(".jpg", frame)
        if not ret:
            continue

        frame_bytes = encoded.tobytes()

        yield (
            b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
        )


# ==================== API ENDPOINT ====================
@app.get("/person_stream")
def person_stream():
    return StreamingResponse(
        generate_frames(), media_type="multipart/x-mixed-replace; boundary=frame"
    )
