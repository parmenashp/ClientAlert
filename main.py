from src import CentroidTracker, TrackableObject
from imutils.video import FPS
import numpy as np
import argparse, imutils
import dlib, cv2


def run():
    ap = argparse.ArgumentParser()
    ap.add_argument("-p", "--prototxt", required=False, help="Caminho para o arquivo de prototipo Caffe")
    ap.add_argument("-m", "--model", required=True, help="Caminho para o modelo pré-treinado")
    ap.add_argument("-i", "--input", type=str, help="Caminho para o video de entrada")
    ap.add_argument("-o", "--output", type=str, help="Caminho para o video de saida")
    ap.add_argument("-c", "--confidence", type=float, default=0.4, help="Valor de confiança para filtrar detecções fracas")
    ap.add_argument("-s", "--skip-frames", type=int, default=30, help="Numero de frames para pular entre detecções")
    args = vars(ap.parse_args())

    # Lista de classes que podem ser detectadas pelo modelo MobileNet SSD
    CLASSES = [
        "background",
        "aeroplane",
        "bicycle",
        "bird",
        "boat",
        "bottle",
        "bus",
        "car",
        "cat",
        "chair",
        "cow",
        "diningtable",
        "dog",
        "horse",
        "motorbike",
        "person",
        "pottedplant",
        "sheep",
        "sofa",
        "train",
        "tvmonitor",
    ]

    net = cv2.dnn.readNetFromCaffe(args["prototxt"], args["model"])

    print("[INFO] Iniciando vídeo..")
    vs = cv2.VideoCapture(args["input"])

    writer = None
    W = None
    H = None
    ct = CentroidTracker(maxDisappeared=40, maxDistance=50)
    trackers = []
    trackableObjects = {}
    totalFrames = 0
    totalDown = 0
    totalUp = 0
    x = []
    empty = []
    empty1 = []

    fps = FPS().start()

    while True:
        frame = vs.read()
        frame = frame[1] if args.get("input", False) else frame

        if args["input"] is not None and frame is None:
            break

        frame = imutils.resize(frame, width=500)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        if W is None or H is None:
            (H, W) = frame.shape[:2]

        if args["output"] is not None and writer is None:
            fourcc = cv2.VideoWriter_fourcc(*"MJPG")
            writer = cv2.VideoWriter(args["output"], fourcc, 30, (W, H), True)

        rects = []

        if totalFrames % args["skip_frames"] == 0:
            trackers = []

            blob = cv2.dnn.blobFromImage(frame, 0.007843, (W, H), 127.5)
            net.setInput(blob)
            detections = net.forward()

            for i in np.arange(0, detections.shape[2]):
                confidence = detections[0, 0, i, 2]

                if confidence > args["confidence"]:
                    idx = int(detections[0, 0, i, 1])

                    if CLASSES[idx] != "person":
                        continue

                    box = detections[0, 0, i, 3:7] * np.array([W, H, W, H])
                    (startX, startY, endX, endY) = box.astype("int")

                    tracker = dlib.correlation_tracker()
                    rect = dlib.rectangle(startX, startY, endX, endY)
                    tracker.start_track(rgb, rect)

                    trackers.append(tracker)

        else:
            for tracker in trackers:
                tracker.update(rgb)
                pos = tracker.get_position()

                startX = int(pos.left())
                startY = int(pos.top())
                endX = int(pos.right())
                endY = int(pos.bottom())

                rects.append((startX, startY, endX, endY))

        cv2.line(frame, (0, H // 2), (W, H // 2), (0, 0, 0), 3)
        cv2.putText(
            frame,
            "Linha de deteccao - Entrada",
            (10, H - ((i * 20) + 200)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 0, 0),
            1,
        )

        objects = ct.update(rects)

        for objectID, centroid in objects.items():
            to = trackableObjects.get(objectID, None)

            if to is None:
                to = TrackableObject(objectID, centroid)

            else:
                y = [c[1] for c in to.centroids]
                direction = centroid[1] - np.mean(y)
                to.centroids.append(centroid)

                if not to.counted:
                    if direction < 0 and centroid[1] < H // 2:
                        totalUp += 1
                        empty.append(totalUp)
                        to.counted = True

                    elif direction > 0 and centroid[1] > H // 2:
                        totalDown += 1
                        empty1.append(totalDown)
                        x = []
                        x.append(len(empty1) - len(empty))

                        to.counted = True

            trackableObjects[objectID] = to

            text = "Pessoa {}".format(objectID)
            cv2.putText(
                frame,
                text,
                (centroid[0] - 10, centroid[1] - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 255, 255),
                2,
            )
            cv2.circle(frame, (centroid[0], centroid[1]), 4, (255, 255, 255), -1)

        info = [
            ("Saida", totalUp),
            ("Entrada", totalDown),
        ]

        for i, (k, v) in enumerate(info):
            text = "{}: {}".format(k, v)
            cv2.putText(frame, text, (10, H - ((i * 20) + 20)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

        info2 = [("Total pessoas dentro", abs(totalDown - totalUp))]

        for i, (k, v) in enumerate(info2):
            text = "{}: {}".format(k, v)
            cv2.putText(frame, text, (250, H - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        cv2.imshow("Janela de monitoramento de pessoas", frame)
        key = cv2.waitKey(1) & 0xFF

        # Fechar o programa quando apertar a tecla Q
        if key == ord("q"):
            break

        totalFrames += 1
        fps.update()

    fps.stop()
    print("[INFO] Tempo total: {:.2f}".format(fps.elapsed()))
    print("[INFO] FPS aproximado: {:.2f}".format(fps.fps()))

    cv2.destroyAllWindows()


if __name__ == "__main__":
    run()
