
import cv2
import pyaudio
import threading
import queue
import time


# -------------------- CONFIGURATION --------------------

CAMERA_INDEX = 0

MICROPHONE_INDEX = 1
AUDIO_RATE = 44100
AUDIO_CHANNELS = 1
AUDIO_FORMAT = pyaudio.paInt16
AUDIO_CHUNK = 1024

VIDEO_QUEUE_SIZE = 500
AUDIO_QUEUE_SIZE = 1000

# -------------------------------------------------------

video_queue = queue.Queue(maxsize=VIDEO_QUEUE_SIZE)
audio_queue = queue.Queue(maxsize=AUDIO_QUEUE_SIZE)

stop_event = threading.Event()


def enqueue_without_discarding(data_queue, data, stream_name):
    """Wait for queue space instead of discarding captured data."""

    while not stop_event.is_set():
        try:
            data_queue.put(data, timeout=0.1)
            return True
        except queue.Full:
            continue

    return False


def webcam_capture():
    """Capture webcam frames continuously."""

    camera = cv2.VideoCapture(CAMERA_INDEX)

    if not camera.isOpened():
        print("\n[WEBCAM] ERROR: Could not open webcam.")
        stop_event.set()
        return

    print("\n[WEBCAM] Capture thread started.")

    try:
        while not stop_event.is_set():
            success, frame = camera.read()

            if not success:
                print("\n[WEBCAM] Failed to capture frame.")
                continue

            if not enqueue_without_discarding(
                video_queue, frame, "WEBCAM"
            ):
                break

    except Exception as error:
        print("\n[WEBCAM] Error:", error)
        stop_event.set()

    finally:
        camera.release()
        print("\n[WEBCAM] Camera released.")


def microphone_capture():
    """Capture microphone audio continuously."""

    audio = pyaudio.PyAudio()
    stream = None

    try:
        stream = audio.open(
            format=AUDIO_FORMAT,
            channels=AUDIO_CHANNELS,
            rate=AUDIO_RATE,
            input=True,
            input_device_index=MICROPHONE_INDEX,
            frames_per_buffer=AUDIO_CHUNK
        )

        print("\n[AUDIO] Capture thread started.")

        while not stop_event.is_set():
            audio_data = stream.read(
                AUDIO_CHUNK,
                exception_on_overflow=False
            )

            if not enqueue_without_discarding(
                audio_queue, audio_data, "AUDIO"
            ):
                break

    except Exception as error:
        print("\n[AUDIO] Error:", error)
        stop_event.set()

    finally:
        if stream is not None:
            if stream.is_active():
                stream.stop_stream()

            stream.close()

        audio.terminate()
        print("\n[AUDIO] Microphone released.")


def main():
    """Start and coordinate both capture threads."""

    print("\nDay 25 - Multi-Threaded Execution Loops")
    print("Starting simultaneous webcam and microphone capture.")
    print("Press Q or ESC to stop.\n")

    webcam_thread = threading.Thread(
        target=webcam_capture,
        name="WebcamThread"
    )

    audio_thread = threading.Thread(
        target=microphone_capture,
        name="MicrophoneThread"
    )

    webcam_thread.start()
    audio_thread.start()

    processed_frames = 0
    processed_audio_chunks = 0
    latest_frame = None

    try:
        while not stop_event.is_set():

            # Process every available video frame.
            while True:
                try:
                    frame = video_queue.get_nowait()
                    processed_frames += 1
                    latest_frame = frame
                except queue.Empty:
                    break

            # Process every available audio chunk.
            while True:
                try:
                    audio_queue.get_nowait()
                    processed_audio_chunks += 1
                except queue.Empty:
                    break

            # Display the latest captured frame.
            if latest_frame is not None:
                display_frame = latest_frame.copy()

                cv2.putText(
                    display_frame,
                    "Webcam Capture Active",
                    (20, 35),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 0),
                    2
                )

                cv2.imshow("Day 25 - Webcam", display_frame)

            print(
                f"\rFrames: {processed_frames} | "
                f"Audio chunks: {processed_audio_chunks}",
                end="",
                flush=True
            )

            key = cv2.waitKey(1) & 0xFF

            if key == ord("q") or key == 27:
                print("\n\nStop requested.")
                break

            time.sleep(0.001)

    except KeyboardInterrupt:
        print("\nKeyboard interrupt received.")

    finally:
        stop_event.set()

        print("\nWaiting for capture threads to finish...")

        webcam_thread.join()
        audio_thread.join()

        cv2.destroyAllWindows()

        print("\nCapture Summary")
        print("-----------------------------")
        print("Processed video frames:", processed_frames)
        print("Processed audio chunks:", processed_audio_chunks)
        print("Remaining video queue:", video_queue.qsize())
        print("Remaining audio queue:", audio_queue.qsize())
        print("Application stopped successfully.")


if __name__ == "__main__":
    main()