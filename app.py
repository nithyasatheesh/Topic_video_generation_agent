import streamlit as st
from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import ImageClip, concatenate_videoclips
import requests
import json
import os
from io import BytesIO

st.set_page_config(
    page_title="AI Content Video Generator",
    layout="wide"
)

client = OpenAI(
    api_key=st.secrets["OPENAI_API_KEY"]
)

TEMP_DIR = "temp"
os.makedirs(TEMP_DIR, exist_ok=True)


def generate_content(topic):

    prompt = f"""
Create educational slide content about "{topic}"

Return JSON only:

{{
"title":"",
"slides":[
    {{
        "heading":"",
        "content":"",
        "image_prompt":""
    }}
]
}}

Generate 5 slides.
Keep content under 25 words each.
Image prompt should describe a visual.
"""

    response = client.chat.completions.create(
        model="gpt-4.1",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        response_format={"type": "json_object"}
    )

    return json.loads(
        response.choices[0].message.content
    )


def generate_image(prompt, index):

    result = client.images.generate(
        model="gpt-image-1",
        prompt=prompt,
        size="1024x1024"
    )

    image_base64 = result.data[0].b64_json

    import base64

    image_data = base64.b64decode(
        image_base64
    )

    image = Image.open(
        BytesIO(image_data)
    )

    path = os.path.join(
        TEMP_DIR,
        f"img_{index}.png"
    )

    image.save(path)

    return path


def wrap_text(draw, text, width):

    words = text.split()

    lines = []

    current = ""

    for word in words:

        test = current + " " + word

        box = draw.textbbox(
            (0,0),
            test
        )

        if box[2] > width:

            lines.append(current)

            current = word

        else:

            current = test

    lines.append(current)

    return "\n".join(lines)


def create_slide(
    heading,
    content,
    image_path,
    index
):

    canvas = Image.new(
        "RGB",
        (1280,720),
        (15,15,25)
    )

    image = Image.open(
        image_path
    )

    image = image.resize(
        (500,500)
    )

    canvas.paste(
        image,
        (700,100)
    )

    draw = ImageDraw.Draw(canvas)

    try:
        title_font = ImageFont.truetype(
            "arial.ttf",
            42
        )

        body_font = ImageFont.truetype(
            "arial.ttf",
            28
        )

    except:

        title_font = ImageFont.load_default()
        body_font = ImageFont.load_default()

    draw.text(
        (50,80),
        heading,
        fill="white",
        font=title_font
    )

    text = wrap_text(
        draw,
        content,
        550
    )

    draw.multiline_text(
        (50,180),
        text,
        fill="white",
        font=body_font,
        spacing=12
    )

    slide_path = os.path.join(
        TEMP_DIR,
        f"slide_{index}.png"
    )

    canvas.save(slide_path)

    return slide_path


def build_video(slides):

    clips = []

    for slide in slides:

        clip = (
            ImageClip(slide)
            .set_duration(5)
        )

        clips.append(clip)

    video = concatenate_videoclips(
        clips,
        method="compose"
    )

    output = os.path.join(
        TEMP_DIR,
        "output.mp4"
    )

    video.write_videofile(
        output,
        fps=24,
        codec="libx264",
        audio=False,
        logger=None
    )

    return output


st.title(
    "🎬 AI Topic → Video Generator"
)

topic = st.text_input(
    "Enter topic"
)

if st.button(
    "Generate Video"
):

    if not topic:

        st.warning(
            "Enter a topic"
        )

        st.stop()

    with st.spinner(
        "Generating content..."
    ):

        data = generate_content(
            topic
        )

    slide_paths = []

    progress = st.progress(0)

    total = len(
        data["slides"]
    )

    for i, slide in enumerate(
        data["slides"]
    ):

        img = generate_image(
            slide["image_prompt"],
            i
        )

        slide_img = create_slide(
            slide["heading"],
            slide["content"],
            img,
            i
        )

        slide_paths.append(
            slide_img
        )

        progress.progress(
            (i+1)/total
        )

    with st.spinner(
        "Building video..."
    ):

        video = build_video(
            slide_paths
        )

    st.success(
        "Done"
    )

    st.video(video)

    with open(
        video,
        "rb"
    ) as f:

        st.download_button(
            "Download MP4",
            f,
            file_name="video.mp4"
        )
