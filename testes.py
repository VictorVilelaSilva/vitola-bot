import os
import google.generativeai as genai

genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

imagen = genai.ImageGenerationModel("imagen-3.0-generate-001")

result = imagen.generate_images(
    prompt="Fuzzy bunnies in my kitchen",
    number_of_images=4,
    safety_filter_level="block_only_high",
    person_generation="allow_adult",
    aspect_ratio="3:4",
    negative_prompt="Outside",
)

for image in result.images:
  print(image)

# Open and display the image using your local operating system.
for image in result.images:
  image._pil_image.show()