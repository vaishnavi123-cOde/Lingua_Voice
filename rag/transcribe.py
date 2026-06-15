import os
from faster_whisper import WhisperModel

os.makedirs("transcripts", exist_ok=True)

print("Loading model...")
model = WhisperModel(
    "base",
    device="cpu",
    compute_type="int8"
)

video_files = [
    f for f in os.listdir(".")
    if f.endswith((".mp4", ".mkv", ".avi", ".webm"))
]

print(f"Found {len(video_files)} videos")

for video in video_files:

    print(f"\nProcessing: {video}")

    segments, info = model.transcribe(video)

    output_file = os.path.join(
        "transcripts",
        f"{os.path.splitext(video)[0]}.txt"
    )

    with open(output_file, "w", encoding="utf-8") as f:
        for segment in segments:
            f.write(segment.text + "\n")

    print(f"Saved: {output_file}")

print("\nDone!")