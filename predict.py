# Prediction interface for Cog ⚙️
# https://cog.run/python
#prediciton via local model & weights
import os
import time
import torch
from PIL import Image
from cog import BasePredictor, Input, Path
from pyramid_dit import PyramidDiTForVideoGeneration
from diffusers.utils import export_to_video

 
CONFIG_PATH = "pyramid-flow-sd3/diffusion_transformer_768p/config.json"  
MODEL_DTYPE = "bf16"
current_directory = os.getcwd()
model_path = os.path.join(current_directory, "pyramid-flow-sd3")
model_name = "pyramid_flux"    # or pyramid_mmdit
model_repo = "rain1011/pyramid-flow-sd3" if model_name == "pyramid_mmdit" else "rain1011/pyramid-flow-miniflux"
class Predictor(BasePredictor):
    def setup(self) -> None:
        self.is_canonical = False
        
        # Verify the weights exist
        self.model = PyramidDiTForVideoGeneration(
            model_path,
            model_name=model_name,
            model_dtype=MODEL_DTYPE,
            model_variant="diffusion_transformer_768p",
        )

        self.model.vae.to("cuda")
        self.model.dit.to("cuda")
        self.model.text_encoder.to("cuda")
        self.model.vae.enable_tiling()

    def predict(
        self,
        prompt: str = Input(description="Text prompt for video generation"),
        image: Path = Input(
            description="Optional input image for image-to-video generation",
            default=None,
        ),
        duration: int = Input(
            description="Duration of the video in seconds (1-3 for canonical mode, 1-10 for non-canonical mode)",
            default=3,
            ge=1,
            le=10,
        ),
        guidance_scale: float = Input(
            description="Guidance Scale for text-to-video generation",
            default=9.0,
            ge=1.0,
            le=15.0
        ),
        video_guidance_scale: float = Input(
            description="Video Guidance Scale",
            default=5.0,
            ge=1.0,
            le=15.0
        ),
        frames_per_second: int = Input(
            description="Frames per second (8 or 24, only applicable in canonical mode)",
            default=8,
            choices=[8, 24],
        ),
    ) -> Path:
        # Handle canonical vs non-canonical cases
        if self.is_canonical:
            duration = min(duration, 3)
            frames_per_second = frames_per_second  # Already limited to 8 or 24 by choices
        else:
            frames_per_second = 24  # Non-canonical always uses 24 fps
            duration = min(duration, 10)  # Ensure max 10 seconds for non-canonical

        torch_dtype = torch.bfloat16 if MODEL_DTYPE == "bf16" else torch.float32
        multiplier = 1.2 if self.is_canonical else 3.0
        temp = int(duration * multiplier) + 1

        if image:
            image = Image.open(image).convert("RGB")
            cropped_image = self.center_crop(image, 1280, 768)
            resized_image = cropped_image.resize((1280, 768))
            with torch.no_grad(), torch.cuda.amp.autocast(
                enabled=True, dtype=torch_dtype
            ):
                frames = self.model.generate_i2v(
                    prompt=prompt,
                    input_image=resized_image,
                    num_inference_steps=[10, 10, 10],
                    temp=temp,
                    guidance_scale=7.0,  # Fixed for image-to-video
                    video_guidance_scale=video_guidance_scale,
                    output_type="pil",
                    save_memory=True,
                )
        else:
            with torch.no_grad(), torch.cuda.amp.autocast(
                enabled=True, dtype=torch_dtype
            ):
                frames = self.model.generate(
                    prompt=prompt,
                    num_inference_steps=[20, 20, 20],
                    video_num_inference_steps=[10, 10, 10],
                    height=1280,
                    width=768,
                    temp=temp,
                    guidance_scale=guidance_scale,
                    video_guidance_scale=video_guidance_scale,
                    output_type="pil",
                    save_memory=True,
                )

        output_path = f"/tmp/output_video.mp4"
        export_to_video(frames, output_path, fps=frames_per_second)
        return Path(output_path)

    def center_crop(self, image, target_width, target_height):
        width, height = image.size
        aspect_ratio_target = target_width / target_height
        aspect_ratio_image = width / height

        if aspect_ratio_image > aspect_ratio_target:
            new_width = int(height * aspect_ratio_target)
            left = (width - new_width) // 2
            right = left + new_width
            top, bottom = 0, height
        else:
            new_height = int(width / aspect_ratio_target)
            top = (height - new_height) // 2
            bottom = top + new_height
            left, right = 0, width

        return image.crop((left, top, right, bottom))
