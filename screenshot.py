import os
import ffmpeg

def take_screenshot(file_path, timestamp, output_image):
    """Takes a screenshot from the video at a given timestamp."""
    try:
        (
            ffmpeg
            .input(file_path, ss=timestamp)
            .output(output_image, vframes=1)
            .run(overwrite_output=True)
        )
        if not os.path.exists(output_image):
            raise FileNotFoundError(f"Screenshot could not be created: {output_image}")
    except Exception as e:
        print(f"Error taking screenshot: {e}")
        if os.path.exists(output_image):
            os.remove(output_image)
    return output_image
