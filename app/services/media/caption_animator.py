import os
import uuid
import logging
from typing import List, Dict, Optional
from moviepy.editor import TextClip, CompositeVideoClip

logger = logging.getLogger(__name__)

class CaptionAnimator:
    """
    Generates word-by-word "karaoke style" captions for short-form video.
    This requires precise audio timing, but in the absence of a forced-alignment STT,
    we estimate duration based on word count.
    """
    
    def __init__(self):
        # We need ImageMagick installed and accessible to Moviepy for TextClips
        self.font = 'Arial-Bold'
        self.fontsize = 80
        self.color = 'white'
        self.highlight_color = 'yellow'
        self.stroke_color = 'black'
        self.stroke_width = 3

    def generate_caption_clips(self, text: str, total_duration: float, video_w: int, video_h: int) -> List[TextClip]:
        """
        Splits text into chunks and estimates timing to create animated TextClips.
        """
        words = text.split()
        if not words:
            return []

        # Naive timing estimation: equal time per word
        time_per_word = total_duration / len(words)
        
        # Group words into short phrases (e.g., 3-4 words per screen)
        chunk_size = 3
        chunks = [" ".join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]
        chunk_durations = [time_per_word * len(chunk.split()) for chunk in chunks]

        clips = []
        current_time = 0.0

        for i, chunk in enumerate(chunks):
            duration = chunk_durations[i]
            
            # Create the main text clip
            try:
                txt_clip = TextClip(
                    chunk,
                    fontsize=self.fontsize,
                    font=self.font,
                    color=self.color,
                    stroke_color=self.stroke_color,
                    stroke_width=self.stroke_width,
                    method='caption',
                    align='center',
                    size=(video_w - 100, None)
                )
                
                # Position in center-bottom
                txt_clip = txt_clip.set_position(('center', video_h * 0.7))
                txt_clip = txt_clip.set_start(current_time)
                txt_clip = txt_clip.set_duration(duration)
                
                clips.append(txt_clip)

            except Exception as e:
                logger.warning(f"Failed to generate text clip for chunk '{chunk}': {e}")
            
            current_time += duration

        return clips

    def overlay_captions(self, video: CompositeVideoClip, text: str) -> CompositeVideoClip:
        """
        Takes a base video clip and overlays estimated animated captions.
        """
        caption_clips = self.generate_caption_clips(text, video.duration, video.w, video.h)
        
        if not caption_clips:
            return video
            
        final_composite = CompositeVideoClip([video] + caption_clips)
        # Inherit audio from base video
        if video.audio:
            final_composite = final_composite.set_audio(video.audio)
            
        return final_composite