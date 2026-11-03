
import cv2
import pyaudio
import threading
import queue
import time
import wave
import os


# -------------------- CONFIGURATION --------------------

CAMERA_INDEX = 0

MICROPHONE_INDEX = 1
AUDIO_RATE = 44100
AUDIO_CHANNELS = 1
AUDIO_FORMAT = pyaudio.paInt16
AUDIO_CHUNK = 1024

VIDEO_QUEUE_SIZE = 500
AUDIO_QUEUE_SIZE = 1000

VIDEO_FPS_FALLBACK = 30.0
OUTPUT_DIR = "output"

VIDEO_OUTPUT = os.path.join(OUTPUT_DIR, "day25_video.mp4")
AUDIO_OUTPUT = os.path.join(OUTPUT_DIR, "day25_audio.wav")

# -------------------------------------------------------

video_queue = queue.Queue(maxsize=VIDEO_QUEUE_SIZE)
audio_queue = queue.Queue(maxsize=AUDIO_QUEUE_SIZE)

stop_event = threading.Event()
start_event = threading.Event()

video_info = {
    "fps": VIDEO_FPS_FALLBACK
}


def enqueue_without_discarding(data_queue, data):
    """Wait until queue space is available."""

    while True:
        try:
            data_queue.put(data, timeout=0.1)
            return True
        except queue.Full:
            continue


def webcam_capture(camera):
    """Capture webcam frames continuously."""

    print("[WEBCAM] Capture thread ready.")

    try:
        start_event.wait()

        print("[WEBCAM] Simultaneous capture started.")

        while not stop_event.is_set():

            success, frame = camera.read()

            if not success:
                print("\n[WEBCAM] Failed to capture frame.")
                stop_event.set()
                break

            enqueue_without_discarding(video_queue, frame)

    except Exception as error:
        print("\n[WEBCAM] Error:", error)
        stop_event.set()


def microphone_capture(stream):
    """Capture microphone audio continuously."""

    print("[AUDIO] Capture thread ready.")

    try:
        start_event.wait()

        print("[AUDIO] Simultaneous capture started.")

        while not stop_event.is_set():

            audio_data = stream.read(
                AUDIO_CHUNK,
                exception_on_overflow=False
            )

            enqueue_without_discarding(audio_queue, audio_data)

    except Exception as error:
        print("\n[AUDIO] Error:", error)
        stop_event.set()


def main():

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("\nDay 25 - Multi-Threaded Execution Loops")
    print("Version 2: Synchronized Separate Video and Audio Recording")
    print("Initializing webcam and microphone...")
    print("Please wait until both devices are ready.\n")

    camera = None
    audio = None
    stream = None

    webcam_thread = None
    audio_thread = None

    video_writer = None
    audio_writer = None

    processed_frames = 0
    processed_audio_chunks = 0
    latest_frame = None

    try:

        # Initialize webcam BEFORE starting capture threads.
        camera = cv2.VideoCapture(CAMERA_INDEX)

        if not camera.isOpened():
            raise RuntimeError("Could not open webcam.")

        width = int(camera.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(camera.get(cv2.CAP_PROP_FRAME_HEIGHT))

        camera_fps = camera.get(cv2.CAP_PROP_FPS)

        if 1 <= camera_fps <= 120:
            video_info["fps"] = camera_fps

        print("[WEBCAM] Device initialized.")
        print("[WEBCAM] Resolution:", (width, height))
        print("[WEBCAM] FPS:", video_info["fps"])

        # Initialize microphone BEFORE starting capture threads.
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

        # Both devices are ready. Create capture threads.
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

        # Release both capture threads at the same time.
        print("\nBoth devices are ready.")
        print("Starting synchronized recording now.")
        print("Press Q or ESC to stop recording.\n")

        recording_start_time = time.perf_counter()
        start_event.set()

        # Create output writers and process queues.
        def process_queues():

            nonlocal video_writer
            nonlocal audio_writer
            nonlocal processed_frames
            nonlocal processed_audio_chunks
            nonlocal latest_frame

            # Process video frames.
            while True:

                try:
                    frame = video_queue.get_nowait()

                except queue.Empty:
                    break

                if video_writer is None:

                    frame_height, frame_width = frame.shape[:2]

                    fourcc = cv2.VideoWriter_fourcc(*"mp4v")

                    video_writer = cv2.VideoWriter(
                        VIDEO_OUTPUT,
                        fourcc,
                        video_info["fps"],
                        (frame_width, frame_height)
                    )

                    if not video_writer.isOpened():
                        raise RuntimeError(
                            "Could not create MP4 video file."
                        )

                    print("\n[VIDEO] Recording started.")

                video_writer.write(frame)

                processed_frames += 1
                latest_frame = frame

            # Process audio chunks.
            while True:

                try:
                    audio_data = audio_queue.get_nowait()

                except queue.Empty:
                    break

                if audio_writer is None:

                    audio_writer = wave.open(
                        AUDIO_OUTPUT,
                        "wb"
                    )

                    audio_writer.setnchannels(AUDIO_CHANNELS)
                    audio_writer.setsampwidth(
                        audio.get_sample_size(AUDIO_FORMAT)
                    )
                    audio_writer.setframerate(AUDIO_RATE)

                    print("\n[AUDIO] Recording started.")

                audio_writer.writeframes(audio_data)

                processed_audio_chunks += 1

        # Main processing loop.
        while not stop_event.is_set():

            process_queues()

            if latest_frame is not None:

                display_frame = latest_frame.copy()

                elapsed = time.perf_counter() - recording_start_time

                cv2.putText(
                    display_frame,
                    "Version 2 - Synchronized Recording",
                    (20, 35),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.65,
                    (0, 255, 0),
                    2
                )

                cv2.putText(
                    display_frame,
                    f"Recording Time: {elapsed:.1f}s",
                    (20, 70),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.65,
                    (0, 255, 0),
                    2
                )

                cv2.imshow(
                    "Day 25 - Version 2",
                    display_frame
                )

            print(
                f"\rVideo Frames: {processed_frames} | "
                f"Audio Chunks: {processed_audio_chunks}",
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

        print("\nStopping capture threads and saving remaining data...")

        # Release the start signal if initialization failed
        # after the worker threads were created.
        start_event.set()

        # Continue draining queues while capture threads finish.
        if webcam_thread is not None and audio_thread is not None:

            while (
                webcam_thread.is_alive()
                or audio_thread.is_alive()
                or not video_queue.empty()
                or not audio_queue.empty()
            ):

                # Process remaining frames.
                while True:

                    try:
                        frame = video_queue.get_nowait()

                    except queue.Empty:
                        break

                    if video_writer is None:

                        frame_height, frame_width = frame.shape[:2]

                        fourcc = cv2.VideoWriter_fourcc(*"mp4v")

                        video_writer = cv2.VideoWriter(
                            VIDEO_OUTPUT,
                            fourcc,
                            video_info["fps"],
                            (frame_width, frame_height)
                        )

                        if not video_writer.isOpened():
                            raise RuntimeError(
                                "Could not create MP4 video file."
                            )

                    video_writer.write(frame)
                    processed_frames += 1

                # Process remaining audio.
                while True:

                    try:
                        audio_data = audio_queue.get_nowait()

                    except queue.Empty:
                        break

                    if audio_writer is None:

                        audio_writer = wave.open(
                            AUDIO_OUTPUT,
                            "wb"
                        )

                        audio_writer.setnchannels(AUDIO_CHANNELS)
                        audio_writer.setsampwidth(
                            audio.get_sample_size(AUDIO_FORMAT)
                        )
                        audio_writer.setframerate(AUDIO_RATE)

                    audio_writer.writeframes(audio_data)
                    processed_audio_chunks += 1

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

        # Finalize video.
        if video_writer is not None:
            video_writer.release()
            print("[VIDEO] Recording saved:", VIDEO_OUTPUT)

        # Finalize audio.
        if audio_writer is not None:
            audio_writer.close()
            print("[AUDIO] Recording saved:", AUDIO_OUTPUT)

        cv2.destroyAllWindows()

        # Calculate saved file durations.
        video_duration = 0.0
        audio_duration = 0.0

        if os.path.exists(VIDEO_OUTPUT):

            video_capture = cv2.VideoCapture(VIDEO_OUTPUT)

            total_video_frames = video_capture.get(
                cv2.CAP_PROP_FRAME_COUNT
            )

            saved_video_fps = video_capture.get(
                cv2.CAP_PROP_FPS
            )

            if saved_video_fps > 0:
                video_duration = (
                    total_video_frames / saved_video_fps
                )

            video_capture.release()

        if os.path.exists(AUDIO_OUTPUT):

            with wave.open(AUDIO_OUTPUT, "rb") as wav_file:

                audio_duration = (
                    wav_file.getnframes()
                    / wav_file.getframerate()
                )

        print("\n========== VERSION 2 TEST SUMMARY ==========")

        print("Processed video frames:", processed_frames)
        print("Processed audio chunks:", processed_audio_chunks)

        print("Video queue remaining:", video_queue.qsize())
        print("Audio queue remaining:", audio_queue.qsize())

        print("Video duration:", round(video_duration, 2), "seconds")
        print("Audio duration:", round(audio_duration, 2), "seconds")

        print(
            "Duration difference:",
            round(abs(video_duration - audio_duration), 2),
            "seconds"
        )

        print("Video file exists:", os.path.exists(VIDEO_OUTPUT))
        print("Audio file exists:", os.path.exists(AUDIO_OUTPUT))

        print("\nApplication stopped.")


if __name__ == "__main__":
    main()