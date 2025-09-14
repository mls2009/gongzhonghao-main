from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os

# 获取当前文件所在目录的绝对路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "wechat_matrix.db")

SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password = Column(String)
    author_name = Column(String)
    account_type = Column(String)  # 账号类型
    browser_id = Column(String)
    browser_name = Column(String)
    homepage = Column(String, nullable=True)  # 账号主页
    status = Column(String, default="active")  # active, deleted
    created_at = Column(DateTime, default=datetime.now)
    can_login = Column(Boolean, default=False)  # 添加登录状态字段

    # 关联素材
    materials = relationship("Material", back_populates="account")

class Browser(Base):
    __tablename__ = "browsers"

    id = Column(Integer, primary_key=True, index=True)
    browser_id = Column(String, unique=True, index=True)
    browser_name = Column(String)
    status = Column(String, default="active")  # active, deleted
    created_at = Column(DateTime, default=datetime.now)

class Material(Base):
    __tablename__ = "materials"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    original_title = Column(String)
    content = Column(Text)  # 添加文章内容字段
    word_count = Column(Integer)
    image_count = Column(Integer)
    status = Column(String, default="unpublished")  # unpublished, published, scheduled
    publish_status = Column(String, nullable=True)  # success, failed
    publish_time = Column(DateTime, nullable=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)
    error_message = Column(String, nullable=True)
    # 添加预约发布相关字段
    schedule_time = Column(DateTime, nullable=True)  # 预约发布时间
    schedule_status = Column(String, nullable=True)  # scheduled, processing
    
    account = relationship("Account", back_populates="materials")

class Settings(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, index=True)
    materials_path = Column(String)  # 素材库路径
    total_files = Column(Integer, default=0)  # 文件总数
    last_scan = Column(DateTime, nullable=True)  # 最后扫描时间
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

class XiaohongshuMaterial(Base):
    __tablename__ = "xiaohongshu_materials"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    folder_path = Column(String)
    email_subject = Column(String, nullable=True)
    image_count = Column(Integer, default=0)
    status = Column(String, default="unpublished")  # unpublished, published
    publish_status = Column(String, nullable=True)  # success, failed
    publish_time = Column(DateTime, nullable=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)
    image_template_id = Column(Integer, ForeignKey("image_templates.id"), nullable=True)
    template_mode = Column(String, nullable=True)  # 模板模式
    error_message = Column(String, nullable=True)
    schedule_time = Column(DateTime, nullable=True)  # 预约发布时间
    schedule_status = Column(String, nullable=True)  # scheduled, processing
    created_at = Column(DateTime, default=datetime.now)

class XiaohongshuSettings(Base):
    __tablename__ = "xiaohongshu_settings"

    id = Column(Integer, primary_key=True, index=True)
    materials_path = Column(String)  # 小红书素材库路径
    total_folders = Column(Integer, default=0)
    last_scan = Column(DateTime, nullable=True)
    region_account_mapping = Column(Text, nullable=True)  # 地区账号映射 JSON
    # 自动发布相关
    auto_publish_time = Column(String, nullable=True)  # 每日触发时间，格式 HH:MM（24小时制）
    auto_publish_enabled = Column(Boolean, default=False)
    # 全局添加商品开关（由小红书素材页的开关控制，不在设置页展示）
    add_product_enabled = Column(Boolean, default=False)
    # 默认模式: 'insert' | 'overlay' | 'random'
    default_mode = Column(String, default='random')
    # 自动发布日期范围（天）
    publish_days_window = Column(Integer, default=2)
    # 三个时间段，HH:MM 格式
    window1_start = Column(String, nullable=True)
    window1_end = Column(String, nullable=True)
    window2_start = Column(String, nullable=True)
    window2_end = Column(String, nullable=True)
    window3_start = Column(String, nullable=True)
    window3_end = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

class ImageTemplate(Base):
    __tablename__ = "image_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    template_type = Column(String)  # 'insert' or 'overlay'
    text_style = Column(String)
    text_color = Column(String, default='#2c3e50')  # 文字颜色
    background_style = Column(String)
    font_size = Column(Integer, default=40)
    line_height = Column(String, default='1.2')
    mask_opacity = Column(String, default='0')
    custom_background_path = Column(String, nullable=True)
    text_lines = Column(Integer, default=3)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

class ContentTemplate(Base):
    __tablename__ = "content_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description_templates = Column(Text, nullable=True)  # JSON格式存储描述模板
    use_random_description = Column(Boolean, default=True)
    no_description = Column(Boolean, default=False)
    topic_templates = Column(Text, nullable=True)  # JSON格式存储话题模板
    topic_count = Column(Integer, default=7)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

class TemplateState(Base):
    __tablename__ = "template_state"
    
    id = Column(Integer, primary_key=True, index=True)
    current_image_template_id = Column(Integer, ForeignKey('image_templates.id'), nullable=True)
    current_content_template_id = Column(Integer, ForeignKey('content_templates.id'), nullable=True)
    image_template_mode = Column(String, default='random')  # 'insert', 'overlay', 'random'
    content_template_mode = Column(String, default='random')  # 'specific', 'random'
    image_template_enabled = Column(Boolean, default=False)
    content_template_enabled = Column(Boolean, default=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 关系
    image_template = relationship("ImageTemplate", foreign_keys=[current_image_template_id])
    content_template = relationship("ContentTemplate", foreign_keys=[current_content_template_id])

Base.metadata.create_all(bind=engine) 
