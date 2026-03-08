import os
import uuid
from typing import Optional
import logging
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip, AudioFileClip

logger = logging.getLogger(__name__)

class VideoComposer:
    def __init__(self, output_dir: str = "downloads/outputs"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def create_short_video(self, background_video_path: str, caption_text: str, audio_path: Optional[str] = None) -> Optional[str]:
        """
        Creates a vertical video with text overlay and optional audio.
        If no audio, assumes the background video has its own audio or is silent.
        """
        if not os.path.exists(background_video_path):
            logger.error(f"Background video not found: {background_video_path}")
            return None

        output_path = os.path.join(self.output_dir, f"short_{uuid.uuid4().hex[:8]}.mp4")

        try:
            # 1. Load Background Video
            video = VideoFileClip(background_video_path)

            # Crop/Resize to 9:16 vertically if needed
            # We assume it's already portrait from Pexels, but we enforce size to be safe.
            target_w, target_h = 1080, 1920
            # Calculate resize scale to cover the 1080x1920 area
            ratio = max(target_w / video.w, target_h / video.h)
            video = video.resize(ratio)
            # Center crop
            x_center = video.w / 2
            y_center = video.h / 2
            video = video.crop(x1=x_center - target_w/2, y1=y_center - target_h/2, 
                               x2=x_center + target_w/2, y2=y_center + target_h/2)

            # Cap length at 30 seconds for Shorts
            if video.duration > 30:
                video = video.subclip(0, 30)

            # 2. Add Audio (if provided)
            # If AI Voice generator later added, this handles it.
            if audio_path and os.path.exists(audio_path):
                audio = AudioFileClip(audio_path)
                # Trim video to audio length or vice-versa
                duration = min(video.duration, audio.duration)
                video = video.subclip(0, duration)
                video = video.set_audio(audio)
            
            # 3. Create Text Overlay (Karaoke style)
            from app.services.media.caption_animator import CaptionAnimator
            try:
                animator = CaptionAnimator()
                final_video = animator.overlay_captions(video, caption_text)
            except Exception as text_e:
                logger.warning(f"CaptionAnimator failed (ImageMagick missing?): {text_e}. Proceeding without text.")
                final_video = video

            # 4. Export
            # Using libx264 for universal social media compatibility
            final_video.write_videofile(
                output_path, 
                codec="libx264", 
                audio_codec="aac",
                fps=24,
                threads=4,
                preset="ultrafast", # speed up dev
                logger=None # disable moviepy console spam
            )

            # Cleanup memory
            video.close()
            final_video.close()

            return output_path

        except Exception as e:
            logger.error(f"Video composition failed: {str(e)}")
            if os.path.exists(output_path):
                os.remove(output_path)
            return None