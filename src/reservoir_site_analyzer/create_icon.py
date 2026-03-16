# -*- coding: utf-8 -*-
"""
간단한 플러그인 아이콘 생성 스크립트
이 스크립트를 실행하여 icon.png를 생성하세요.
"""

import base64
import os

# 32x32 파란색 물방울 아이콘 (PNG, base64 인코딩)
# 간단한 물탱크/저수지를 나타내는 아이콘
ICON_BASE64 = """
iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAABHNCSVQICAgIfAhkiAAAAAlwSFlz
AAALEwAACxMBAJqcGAAAAVlJREFUWIXtl7FKA0EQhr+5XOFhYWFhIVhYWFgIgiAIgiAIgndvoW+g
b6BvYKOFjYWFhYWFIAiCIAiCIFgIHhYWFnJkd3Zu9nYvOQgWTjXszn8z/8zOzC5UqEJZ5JIy9YNq
oA2MAhPAGLANbAI5Twi4A5aAOWADuPIxl1kAe8AJ0AImgQcFXPmYA7aBU6AFNIGeCfwKOAb2Uw6A
gRvgGJgHOiZAE+gzBTaBbeAImDMJ+B3YMw60gV1Tt28SnJmAy8CaCWDLJGj7C+oEB5j3SToOdIAD
YMEk6AJzJuEAaPsL6pjv7QKHwLxJ0AOmTAK/QYfAvL+gjnlvB5g3CXrAtEnQ/4E24LdJbQcwbxL0
gCkTwK/RAej7K7QdM2MS9IBJYNYkCH6gTvBZHWDOJOgBE8CMSeCv0DH47QBzJkEPGAdmTILQCu0A
cyZBD/gHBfiLWOEfxjdl1W2BRQAAAABJRU5ErkJggg==
"""

def create_icon():
    """icon.png 파일 생성"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    icon_path = os.path.join(script_dir, 'icon.png')

    # Base64 디코딩 및 파일 저장
    icon_data = base64.b64decode(ICON_BASE64.strip())

    with open(icon_path, 'wb') as f:
        f.write(icon_data)

    print(f"아이콘 생성 완료: {icon_path}")


if __name__ == '__main__':
    create_icon()
