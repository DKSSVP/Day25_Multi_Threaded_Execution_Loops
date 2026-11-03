
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
start_event = threading.Event()


def enqueue_without_discarding(data_queue, data):
    """Wait for queue space while capture is active."""

    while not stop_event.is_set():
        try:
            data_queue.put(data, timeout=0.1)
            return True
        except queue.Full:
            continue

    return False


def webcam_capture(camera):
    """Capture webcam frames continuously."""

    print("[WEBCAM] Capture thread ready.")

    try:
        start_event.wait()

        if stop_event.is_set():
            return

        print("[WEBCAM] Capture started.")

        while not stop_event.is_set():

            success, frame = camera.read()

            if not success:
                print("\n[WEBCAM] Failed to capture frame.")
                stop_event.set()
                break

            if not enqueue_without_discarding(video_queue, frame):
                break

    except Exception as error:
        print("\n[WEBCAM] Error:", error)
        stop_event.set()


def microphone_capture(stream):
    """Capture microphone audio continuously."""

    print("[AUDIO] Capture thread ready.")

    try:
        start_event.wait()

        if stop_event.is_set():
            return

        print("[AUDIO] Capture started.")

        while not stop_event.is_set():

            audio_data = stream.read(
                AUDIO_CHUNK,
                exception_on_overflow=False
            )

            if not enqueue_without_discarding(audio_queue, audio_data):
                break

    except Exception as error:
        print("\n[AUDIO] Error:", error)
        stop_event.set()


def main():
    """Initialize both devices and coordinate capture threads."""

    audio = None
    stream = None
    camera = None

    webcam_thread = None
    audio_thread = None

    processed_frames = 0
    processed_audio_chunks = 0
    latest_frame = None

    print("\nDay 25 - Multi-Threaded Execution Loops")
    print("Version 1: Simultaneous Audio and Video Capture")
    print("Initializing webcam and microphone...")
    print("Please wait until both devices are ready.\n")

    try:
        # Initialize webcam first.
        camera = cv2.VideoCapture(CAMERA_INDEX)

        if not camera.isOpened():
            raise RuntimeError("Could not open webcam.")

        width = int(camera.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(camera.get(cv2.CAP_PROP_FRAME_HEIGHT))

        print("[WEBCAM] Device initialized.")
        print("[WEBCAM] Resolution:", (width, height))

        # Initialize microphone.
        audio = pyaudio.PyAudio()

        stream = audio.open(
            format=AUDIO_FORMAT,
            channels=AUDIO_CHANNELS,
            rate=AUDIO_RATE,
            input=True,
            input_device_index=MICROPHONE_INDEX,
            frames_per_buffer=AUDIO_CHUNK
        )

        print("[AUDIO] Microphone initialized.")

        # Both devices are ready. Start both threads.
        webcam_thread = threading.Thread(
            target=webcam_capture,
            args=(camera,),
            name="WebcamThread"
        )

        audio_thread = threading.Thread(
            target=microphone_capture,
            args=(stream,),
            name="MicrophoneThread"
        )

        webcam_thread.start()
        audio_thread.start()

        print("\nBoth devices are ready.")
        print("Starting simultaneous capture.")
        print("Press Q or ESC to stop.\n")

        recording_start_time = time.perf_counter()
        start_event.set()

        # Process captured data continuously.
        while not stop_event.is_set():

            # Process video frames.
            while True:

                try:
                    frame = video_queue.get_nowait()

                except queue.Empty:
                    break

                processed_frames += 1
                latest_frame = frame

            # Process audio chunks.
            while True:

                try:
                    audio_queue.get_nowait()

                except queue.Empty:
                    break

                processed_audio_chunks += 1

            # Display the latest webcam frame.
            if latest_frame is not None:

                display_frame = latest_frame.copy()

                elapsed = (
                    time.perf_counter() - recording_start_time
                )

                cv2.putText(
                    display_frame,
                    "Version 1 - Simultaneous Capture",
                    (20, 35),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.65,
                    (0, 255, 0),
                    2
                )

                cv2.putText(
                    display_frame,
                    f"Elapsed: {elapsed:.1f}s",
                    (20, 70),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.65,
                    (0, 255, 0),
                    2
                )

                cv2.imshow(
                    "Day 25 - Version 1",
                    display_frame
                )

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

    except Exception as error:

        print("\n[MAIN] Error:", error)

    finally:

        stop_event.set()
        start_event.set()

        print("\nStopping capture threads...")

        # Continue processing until both threads finish
        # and all queued data has been consumed.
        if webcam_thread is not None and audio_thread is not None:

            while (
                webcam_thread.is_alive()
                or audio_thread.is_alive()
                or not video_queue.empty()
                or not audio_queue.empty()
            ):

                while True:

                    try:
                        video_queue.get_nowait()
                        processed_frames += 1

                    except queue.Empty:
                        break

                while True:

                    try:
                        audio_queue.get_nowait()
                        processed_audio_chunks += 1

                    except queue.Empty:
                        break

                time.sleep(0.01)

            webcam_thread.join()
            audio_thread.join()

        # Release webcam.
        if camera is not None:
            camera.release()
            print("[WEBCAM] Camera released.")

        # Release microphone.
        if stream is not None:

            if stream.is_active():
                stream.stop_stream()

            stream.close()
            print("[AUDIO] Microphone released.")

        if audio is not None:
            audio.terminate()

        cv2.destroyAllWindows()

        print("\n========== VERSION 1 TEST SUMMARY ==========")
        print("Processed video frames:", processed_frames)
        print("Processed audio chunks:", processed_audio_chunks)
        print("Remaining video queue:", video_queue.qsize())
        print("Remaining audio queue:", audio_queue.qsize())
        print("Application stopped successfully.")


if __name__ == "__main__":
    main()