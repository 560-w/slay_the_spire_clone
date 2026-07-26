"""emoji_renderer.py: 彩色 emoji 渲染器。"""

from __future__ import annotations
import logging, os
from typing import Dict, Optional
import pygame

logger = logging.getLogger(__name__)

try:
    from PIL import Image, ImageDraw, ImageFont
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False

EMOJI_FONT_PATH = "C:/Windows/Fonts/seguiemj.ttf"


class EmojiRenderer:
    _cache = {}

    @classmethod
    def _get_font(cls, size):
        if not PILLOW_AVAILABLE: return None
        if not os.path.isfile(EMOJI_FONT_PATH): return None
        try: return ImageFont.truetype(EMOJI_FONT_PATH, size)
        except: return None

    @classmethod
    def render_emoji(cls, emoji, size=20):
        if not PILLOW_AVAILABLE: return None
        key = f"{emoji}_{size}"
        if key in cls._cache: return cls._cache[key]
        font = cls._get_font(size)
        if font is None: return None
        try:
            bbox = font.getbbox(emoji)
            w = bbox[2]-bbox[0]+4; h = bbox[3]-bbox[1]+4
            if w<=0 or h<=0: w=h=size+4
            img = Image.new("RGBA",(w,h),(0,0,0,0))
            draw = ImageDraw.Draw(img)
            draw.text((2-bbox[0],2-bbox[1]),emoji,font=font,embedded_color=True)
            data = img.tobytes()
            surface = pygame.image.fromstring(data,img.size,"RGBA")
            surface = surface.convert_alpha()
            cls._cache[key] = surface
            return surface
        except Exception as e:
            logger.warning("emoji render fail: %s",e)
            return None

    @classmethod
    def render_text(cls, text, font, color, size=20):
        """渲染含emoji文本: emoji用Pillow, 中文用pygame, 合成一个Surface。"""
        if not PILLOW_AVAILABLE: return font.render(text,True,color)
        pil_font = cls._get_font(size)
        if pil_font is None: return font.render(text,True,color)
        try:
            bbox = pil_font.getbbox(text)
            w = bbox[2]-bbox[0]+4; h = bbox[3]-bbox[1]+4
            if w<=0 or h<=0: return font.render(text,True,color)
            img = Image.new("RGBA",(w,h),(0,0,0,0))
            draw = ImageDraw.Draw(img)
            draw.text((2-bbox[0],2-bbox[1]),text,font=pil_font,fill=color,embedded_color=True)
            data = img.tobytes()
            surface = pygame.image.fromstring(data,img.size,"RGBA")
            return surface.convert_alpha()
        except: return font.render(text,True,color)
