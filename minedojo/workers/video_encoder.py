"""H.264 video encoder that pipes raw frames to ffmpeg."""

import subprocess
from pathlib import Path
from typing import Any, Dict, List

import numpy as np


class VideoEncoder:
    """Encodes collected POV frames to H.264 video via ffmpeg subprocess.

    Parameters:
        output_dir: Directory where ``.mp4`` files will be written.
        fps: Frames per second for the output video.
        width: Frame width in pixels.
        height: Frame height in pixels.
        crf: Constant Rate Factor for libx264 (lower = higher quality).
    """

    def __init__(
        self,
        output_dir: str,
        fps: int = 20,
        width: int = 160,
        height: int = 256,
        crf: int = 23,
    ):
        self.output_dir = Path(output_dir)
        self.fps = fps
        self.width = width
        self.height = height
        self.crf = crf
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def encode(
        self,
        frames: List[np.ndarray],
        metadata: Dict[str, Any],
    ) -> str:
        """Encode frames to an ``.mp4`` video file.

        Args:
            frames: List of numpy arrays in either HWC (height, width, 3) or
                CHW (3, height, width) format.  Values should be uint8.
            metadata: Must contain ``"task_id"`` key used to name the output file.

        Returns:
            Absolute path to the generated ``.mp4`` file, or empty string
            if *frames* is empty.
        """
        if not frames:
            return ""

        task_id = metadata.get("task_id", "unknown")
        output_path = self.output_dir / f"{task_id}.mp4"

        cmd = [
            "ffmpeg",
            "-y",                    # Overwrite output file
            "-f", "rawvideo",
            "-vcodec", "rawvideo",
            "-s", f"{self.width}x{self.height}",
            "-pix_fmt", "rgb24",
            "-r", str(self.fps),
            "-i", "-",               # Read from stdin pipe
            "-c:v", "libx264",
            "-crf", str(self.crf),
            "-preset", "fast",
            "-pix_fmt", "yuv420p",
            str(output_path),
        ]

        proc = subprocess.Popen(
            cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL
        )
        for frame in frames:
            # Convert CHW → HWC if needed
            if frame.ndim == 3 and frame.shape[0] == 3:
                frame = frame.transpose(1, 2, 0)
            # Ensure contiguous uint8
            if frame.dtype != np.uint8:
                frame = frame.astype(np.uint8)
            proc.stdin.write(frame.tobytes())
        proc.stdin.close()
        proc.wait()

        return str(output_path)
