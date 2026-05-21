import streamlit as st
from openai import OpenAI

from PIL import (
    Image,
    ImageDraw,
    ImageFont
)

from moviepy.editor import (
    ImageClip,
    AudioFileClip,
    concatenate_videoclips
)

import os
import json
import base64
import shutil

from io import BytesIO


st.set_page_config(
    page_title="AI Topic Video Generator",
    layout="wide"
)

st.title("🎬 AI Topic → Video Generator")

client = OpenAI(
    api_key=st.secrets["OPENAI_API_KEY"]
)

TEMP_DIR = "temp"

WIDTH = 1280
HEIGHT = 720

os.makedirs(
    TEMP_DIR,
    exist_ok=True
)


def cleanup():

    if os.path.exists(TEMP_DIR):

        shutil.rmtree(TEMP_DIR)

    os.makedirs(
        TEMP_DIR,
        exist_ok=True
    )


def font(size):

    try:

        return ImageFont.truetype(
            "DejaVuSans.ttf",
            size
        )

    except:

        return ImageFont.load_default()


def generate_content(topic):

    prompt = f"""
Create educational content about:

{topic}

Return JSON:

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

Rules:

Generate 5 slides.

Heading:
Short

Content:
Maximum 25 words

Image prompt:
Highly visual and descriptive
"""

    response = client.chat.completions.create(
        model="gpt-4.1",
        messages=[
            {
                "role":"user",
                "content":prompt
            }
        ],
        response_format={
            "type":"json_object"
        }
    )

    return json.loads(
        response.choices[0].message.content
    )


def generate_image(prompt,index):

    response = client.images.generate(
        model="gpt-image-1",
        prompt=prompt,
        size="1536x1024",
        quality="high"
    )

    image_bytes = base64.b64decode(
        response.data[0].b64_json
    )

    image = Image.open(
        BytesIO(image_bytes)
    )

    image = image.convert("RGB")

    path = os.path.join(
        TEMP_DIR,
        f"image_{index}.png"
    )

    image.save(
        path,
        quality=100
    )

    return path


def generate_audio(text,index):

    speech = client.audio.speech.create(
        model="gpt-4o-mini-tts",
        voice="alloy",
        input=text
    )

    path = os.path.join(
        TEMP_DIR,
        f"audio_{index}.mp3"
    )

    speech.stream_to_file(
        path
    )

    return path


def wrap_text(
    draw,
    text,
    font_obj,
    width
):

    words = text.split()

    lines = []

    current = ""

    for word in words:

        test = current + " " + word

        size = draw.textbbox(
            (0,0),
            test,
            font=font_obj
        )[2]

        if size > width:

            lines.append(
                current.strip()
            )

            current = word

        else:

            current = test

    lines.append(
        current.strip()
    )

    return "\n".join(lines)


def create_slide(
    heading,
    content,
    image_path,
    index
):

    slide = Image.new(
        "RGB",
        (WIDTH,HEIGHT),
        "white"
    )

    image = Image.open(
        image_path
    )

    image.thumbnail(
        (500,500),
        Image.LANCZOS
    )

    x = 700
    y = 100

    slide.paste(
        image,
        (x,y)
    )

    draw = ImageDraw.Draw(
        slide
    )

    title_font = font(52)

    body_font = font(30)

    draw.text(
        (60,80),
        heading,
        fill="black",
        font=title_font
    )

    wrapped = wrap_text(
        draw,
        content,
        body_font,
        550
    )

    draw.multiline_text(
        (60,180),
        wrapped,
        fill="black",
        font=body_font,
        spacing=10
    )

    slide_path = os.path.join(
        TEMP_DIR,
        f"slide_{index}.png"
    )

    slide.save(
        slide_path,
        quality=100
    )

    return slide_path


def build_video(
    slides,
    audios
):

    clips = []

    for slide,audio in zip(
        slides,
        audios
    ):

        narration = AudioFileClip(
            audio
        )

        duration = narration.duration

        clip = (
            ImageClip(slide)
            .set_duration(duration)
            .set_audio(narration)
        )

        clips.append(
            clip
        )

    final = concatenate_videoclips(
        clips,
        method="compose"
    )

    output = os.path.join(
        TEMP_DIR,
        "video.mp4"
    )

    final.write_videofile(
        output,
        fps=24,
        codec="libx264",
        audio_codec="aac",
        preset="medium",
        bitrate="5000k",
        threads=4,
        logger=None
    )

    final.close()

    return output


topic = st.text_input(
    "Enter Topic"
)

if st.button(
    "Generate Video"
):

    if not topic:

        st.warning(
            "Enter a topic"
        )

        st.stop()

    cleanup()

    progress = st.progress(0)

    with st.spinner(
        "Generating content..."
    ):

        data = generate_content(
            topic
        )

    slides = []

    audios = []

    total = len(
        data["slides"]
    )

    for idx,slide in enumerate(
        data["slides"]
    ):

        progress.progress(
            idx/total
        )

        image = generate_image(
            slide["image_prompt"],
            idx
        )

        audio = generate_audio(
            slide["content"],
            idx
        )

        slide_path = create_slide(
            slide["heading"],
            slide["content"],
            image,
            idx
        )

        slides.append(
            slide_path
        )

        audios.append(
            audio
        )

    progress.progress(0.9)

    with st.spinner(
        "Creating video..."
    ):

        video = build_video(
            slides,
            audios
        )

    progress.progress(1.0)

    st.success(
        "Video Generated"
    )

    st.video(video)

    with open(
        video,
        "rb"
    ) as file:

        st.download_button(
            "⬇ Download Video",
            file,
            file_name="video.mp4",
            mime="video/mp4"
        )
