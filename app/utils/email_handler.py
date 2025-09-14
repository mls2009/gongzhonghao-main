import imaplib
import email
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import decode_header
import os
import logging
from typing import List, Tuple, Optional
import re
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class EmailHandler:
    """QQ邮箱处理类"""
    
    def __init__(self, email_address: str, password: str):
        self.email_address = email_address
        self.password = password
        self.imap_server = "imap.qq.com"
        self.imap_port = 993
        self.imap = None
    
    def connect(self) -> bool:
        """连接到QQ邮箱IMAP服务器"""
        try:
            logger.info(f"正在连接到 {self.imap_server}:{self.imap_port}")
            self.imap = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            
            logger.info(f"正在登录邮箱 {self.email_address}")
            self.imap.login(self.email_address, self.password)
            
            logger.info("邮箱连接成功")
            return True
        except Exception as e:
            logger.error(f"邮箱连接失败: {str(e)}")
            return False
    
    def disconnect(self):
        """断开邮箱连接"""
        if self.imap:
            try:
                self.imap.close()
                self.imap.logout()
                logger.info("邮箱连接已断开")
            except:
                pass
    
    def decode_subject(self, subject: str) -> str:
        """解码邮件主题"""
        try:
            decoded_parts = []
            for part, encoding in decode_header(subject):
                if isinstance(part, bytes):
                    if encoding:
                        decoded_parts.append(part.decode(encoding))
                    else:
                        decoded_parts.append(part.decode('utf-8', errors='ignore'))
                else:
                    decoded_parts.append(part)
            return ''.join(decoded_parts)
        except Exception as e:
            logger.error(f"解码邮件主题失败: {str(e)}")
            return subject
    
    def sanitize_folder_name(self, name: str) -> str:
        """清理文件夹名称，移除不允许的字符"""
        # 移除或替换不允许的字符
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', name)
        # 移除开头和结尾的空格和点
        sanitized = sanitized.strip(' .')
        # 限制长度
        if len(sanitized) > 100:
            sanitized = sanitized[:100]
        return sanitized or "未命名邮件"
    
    def search_emails_by_subject(self, subject_keyword: str, days_back: int = 30) -> List[str]:
        """搜索包含指定关键词的邮件"""
        try:
            # 选择收件箱
            self.imap.select('INBOX')
            
            # 计算搜索日期范围
            since_date = (datetime.now() - timedelta(days=days_back)).strftime("%d-%b-%Y")
            
            # 尝试多种搜索方式，处理中文编码问题
            search_methods = [
                # 方法1: 直接搜索所有邮件，然后在客户端过滤
                ('ALL', None),
                # 方法2: 只搜索日期范围内的邮件
                (f'SINCE "{since_date}"', None)
            ]
            
            found_emails = []
            
            for search_criteria, charset in search_methods:
                try:
                    logger.info(f"尝试搜索条件: {search_criteria}")
                    
                    if charset:
                        result, message_ids = self.imap.search(charset, search_criteria)
                    else:
                        result, message_ids = self.imap.search(None, search_criteria)
                    
                    if result == 'OK' and message_ids[0]:
                        ids = message_ids[0].split()
                        logger.info(f"搜索到 {len(ids)} 封邮件，开始检查主题")
                        
                        # 检查每封邮件的主题是否包含关键词
                        for msg_id in ids:
                            try:
                                # 获取邮件头部信息
                                result, msg_data = self.imap.fetch(msg_id, '(BODY[HEADER.FIELDS (SUBJECT)])')
                                if result == 'OK' and msg_data[0] and msg_data[0][1]:
                                    header = msg_data[0][1].decode('utf-8', errors='ignore')
                                    
                                    # 提取主题行
                                    import re
                                    subject_match = re.search(r'Subject:\s*(.*?)(?:\r?\n(?!\s)|\r?\n$|\Z)', header, re.DOTALL | re.IGNORECASE)
                                    if subject_match:
                                        subject = subject_match.group(1).strip()
                                        subject = self.decode_subject(subject)
                                        
                                        # 检查是否包含关键词
                                        if subject_keyword in subject:
                                            found_emails.append(msg_id.decode() if isinstance(msg_id, bytes) else msg_id)
                                            logger.info(f"找到匹配邮件: {subject}")
                            except Exception as msg_error:
                                logger.warning(f"检查邮件 {msg_id} 主题时出错: {str(msg_error)}")
                                continue
                        
                        # 如果找到邮件，返回结果
                        if found_emails:
                            logger.info(f"总共找到 {len(found_emails)} 封匹配的邮件")
                            return found_emails
                            
                except Exception as search_error:
                    logger.warning(f"搜索方法失败: {str(search_error)}")
                    continue
            
            logger.info("未找到匹配的邮件")
            return []
                
        except Exception as e:
            logger.error(f"搜索邮件时出错: {str(e)}")
            return []
    
    def fetch_email(self, message_id: str) -> Optional[email.message.Message]:
        """获取邮件内容"""
        try:
            result, message_data = self.imap.fetch(message_id, '(RFC822)')
            if result == 'OK':
                raw_email = message_data[0][1]
                email_message = email.message_from_bytes(raw_email)
                return email_message
            else:
                logger.error(f"获取邮件失败: {result}")
                return None
        except Exception as e:
            logger.error(f"获取邮件时出错: {str(e)}")
            return None
    
    def download_attachments(self, email_message: email.message.Message, download_path: str) -> List[str]:
        """下载邮件附件到指定文件夹"""
        downloaded_files = []
        
        try:
            # 确保下载目录存在
            os.makedirs(download_path, exist_ok=True)
            
            for part in email_message.walk():
                # 检查是否是附件
                content_disposition = part.get("Content-Disposition", "")
                
                if "attachment" in content_disposition:
                    filename = part.get_filename()
                    
                    if filename:
                        # 解码文件名
                        filename = self.decode_subject(filename)
                        filename = self.sanitize_folder_name(filename)
                        
                        filepath = os.path.join(download_path, filename)
                        
                        # 避免文件名冲突
                        counter = 1
                        base_name, extension = os.path.splitext(filename)
                        while os.path.exists(filepath):
                            new_filename = f"{base_name}_{counter}{extension}"
                            filepath = os.path.join(download_path, new_filename)
                            counter += 1
                        
                        # 下载附件
                        with open(filepath, 'wb') as f:
                            f.write(part.get_payload(decode=True))
                        
                        downloaded_files.append(filepath)
                        logger.info(f"下载附件: {filepath}")
            
            return downloaded_files
            
        except Exception as e:
            logger.error(f"下载附件时出错: {str(e)}")
            return downloaded_files
    
    def process_recruitment_emails(self, materials_base_path: str) -> Tuple[int, List[str]]:
        """处理包含"最新招聘信息"的邮件"""
        if not self.connect():
            return 0, ["邮箱连接失败"]
        
        processed_count = 0
        messages = []
        
        try:
            # 搜索包含"最新招聘信息"的邮件
            email_ids = self.search_emails_by_subject("最新招聘信息", days_back=30)
            
            if not email_ids:
                messages.append("未找到包含'最新招聘信息'的邮件")
                return 0, messages
            
            logger.info(f"开始处理 {len(email_ids)} 封邮件")
            
            for email_id in email_ids:
                try:
                    # 获取邮件内容
                    email_message = self.fetch_email(email_id)
                    if not email_message:
                        continue
                    
                    # 获取邮件主题
                    subject = email_message.get('Subject', '无标题邮件')
                    subject = self.decode_subject(subject)
                    
                    # 清理主题作为文件夹名
                    folder_name = self.sanitize_folder_name(subject)
                    folder_path = os.path.join(materials_base_path, folder_name)
                    
                    # 检查文件夹是否已存在
                    if os.path.exists(folder_path):
                        logger.info(f"文件夹已存在，跳过: {folder_name}")
                        continue
                    
                    # 创建文件夹
                    os.makedirs(folder_path, exist_ok=True)
                    logger.info(f"创建文件夹: {folder_path}")
                    
                    # 下载附件
                    downloaded_files = self.download_attachments(email_message, folder_path)
                    
                    if downloaded_files:
                        processed_count += 1
                        messages.append(f"处理邮件: {subject} (下载 {len(downloaded_files)} 个附件)")
                        logger.info(f"成功处理邮件: {subject}")
                    else:
                        # 如果没有附件，删除空文件夹
                        try:
                            os.rmdir(folder_path)
                        except:
                            pass
                        messages.append(f"邮件无附件，跳过: {subject}")
                    
                except Exception as e:
                    logger.error(f"处理邮件 {email_id} 时出错: {str(e)}")
                    messages.append(f"处理邮件时出错: {str(e)}")
                    continue
            
            return processed_count, messages
            
        except Exception as e:
            logger.error(f"处理邮件时出现总体错误: {str(e)}")
            return processed_count, [f"处理邮件时出现错误: {str(e)}"]
        
        finally:
            self.disconnect()


def fetch_qq_email_materials(materials_base_path: str) -> dict:
    """获取QQ邮箱素材的主函数"""
    
    # QQ邮箱配置
    email_address = "192288138@qq.com"
    auth_code = "rtecaswdacbebhgc"  # IMAP授权码
    
    handler = EmailHandler(email_address, auth_code)
    
    try:
        processed_count, messages = handler.process_recruitment_emails(materials_base_path)
        
        return {
            "success": processed_count > 0,
            "processed_count": processed_count,
            "messages": messages,
            "total_messages": len(messages)
        }
        
    except Exception as e:
        logger.error(f"获取邮箱素材失败: {str(e)}")
        return {
            "success": False,
            "processed_count": 0,
            "messages": [f"获取邮箱素材失败: {str(e)}"],
            "total_messages": 1
        }