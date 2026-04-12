"""
api_wrapper.py
Kimi API 请求包装器 - 自动记录 latency、tokens、errors
"""

import requests
import json
import time
from typing import Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class KimiAPIWrapper:
    """Kimi API 包装器 - 自动捕获性能数据"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.api_url = "https://api.moonshot.cn/v1/chat/completions"
        self.timeout = 60  # 请求超时时间
    
    def call_api(
        self,
        prompt: str,
        system_prompt: str = "",
        max_retries: int = 3
    ) -> Tuple[Optional[str], Dict]:
        """
        调用 Kimi API
        
        Returns:
            (response_text, metadata_dict)
            
        Example:
            response, metadata = api.call_api(prompt)
            if metadata['success']:
                print(f"Latency: {metadata['latency']}s")
                print(f"Tokens: {metadata['tokens_used']}")
            else:
                print(f"Error: {metadata['error_code']}")
        """
        
        metadata = {
            'success': False,
            'latency': 0.0,
            'tokens_used': 0,
            'tokens_input': 0,
            'tokens_output': 0,
            'error_code': None,
            'error_message': None,
            'error_log': {},
            'retry_count': 0,
            'response': None
        }
        
        if not self.api_key:
            metadata['error_code'] = 'NO_API_KEY'
            metadata['error_message'] = 'API Key not found'
            metadata['error_log'] = {'type': 'configuration_error', 'detail': 'Missing API Key'}
            logger.error("❌ API Key not found")
            return None, metadata
        
        # 重试循环
        last_error = None
        
        for attempt in range(max_retries):
            try:
                # ⏱️ 开始计时
                start_time = time.time()
                
                logger.info(f"📤 API call (attempt {attempt + 1}/{max_retries})")
                
                # 构建请求
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                }
                
                payload = {
                    "model": "moonshot-v1-8k",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.3,
                    "max_tokens": 3000
                }
                
                # 发送请求
                response = requests.post(
                    self.api_url,
                    json=payload,
                    headers=headers,
                    timeout=self.timeout
                )
                
                # ⏱️ 停止计时
                latency = time.time() - start_time
                
                # 检查 HTTP 状态码
                if response.status_code != 200:
                    error_details = {
                        'type': 'http_error',
                        'status_code': response.status_code,
                        'response_text': response.text[:500],  # 限制错误消息长度
                        'attempt': attempt + 1,
                        'latency': latency
                    }
                    
                    metadata['error_log'] = error_details
                    metadata['error_code'] = str(response.status_code)
                    metadata['error_message'] = f"HTTP {response.status_code}"
                    metadata['latency'] = latency
                    metadata['retry_count'] = attempt + 1
                    
                    logger.warning(f"⚠️ HTTP {response.status_code}: {response.text[:200]}")
                    
                    # 特定错误处理
                    if response.status_code == 429:
                        logger.error("🚨 Rate limited (429)")
                        last_error = "rate_limited"
                        time.sleep(2 ** attempt)  # 指数退避
                        continue
                    elif response.status_code >= 500:
                        logger.error(f"🚨 Server error ({response.status_code})")
                        last_error = "server_error"
                        time.sleep(2 ** attempt)
                        continue
                    else:
                        logger.error(f"❌ Client error ({response.status_code})")
                        # 客户端错误不重试
                        return None, metadata
                
                # 解析 JSON 响应
                try:
                    result = response.json()
                except json.JSONDecodeError as e:
                    error_details = {
                        'type': 'json_decode_error',
                        'error': str(e),
                        'response_text': response.text[:500],
                        'latency': latency
                    }
                    
                    metadata['error_log'] = error_details
                    metadata['error_code'] = 'INVALID_JSON'
                    metadata['error_message'] = f"JSON decode error: {str(e)}"
                    metadata['latency'] = latency
                    
                    logger.error(f"❌ JSON decode error: {e}")
                    return None, metadata
                
                # 检查响应结构
                if "choices" not in result or len(result["choices"]) == 0:
                    error_details = {
                        'type': 'invalid_response_structure',
                        'response_keys': list(result.keys()),
                        'latency': latency
                    }
                    
                    metadata['error_log'] = error_details
                    metadata['error_code'] = 'INVALID_RESPONSE'
                    metadata['error_message'] = "No choices in response"
                    metadata['latency'] = latency
                    
                    logger.error(f"❌ Invalid response structure")
                    return None, metadata
                
                # 提取响应内容
                content = result["choices"][0]["message"]["content"].strip()
                
                # ✅ 提取 Token 信息
                usage = result.get("usage", {})
                tokens_input = usage.get("prompt_tokens", 0)
                tokens_output = usage.get("completion_tokens", 0)
                tokens_used = tokens_input + tokens_output
                
                # ✅ 成功！
                metadata['success'] = True
                metadata['latency'] = latency
                metadata['tokens_used'] = tokens_used
                metadata['tokens_input'] = tokens_input
                metadata['tokens_output'] = tokens_output
                metadata['response'] = content
                
                logger.info(
                    f"✅ API call successful "
                    f"(latency: {latency:.2f}s, tokens: {tokens_used})"
                )
                
                return content, metadata
            
            except requests.Timeout as e:
                error_details = {
                    'type': 'timeout',
                    'timeout_value': self.timeout,
                    'attempt': attempt + 1,
                    'error': str(e)
                }
                
                metadata['error_log'] = error_details
                metadata['error_code'] = 'TIMEOUT'
                metadata['error_message'] = f"Request timeout after {self.timeout}s"
                metadata['latency'] = time.time() - start_time
                metadata['retry_count'] = attempt + 1
                
                logger.warning(f"⏱️ Request timeout (attempt {attempt + 1})")
                last_error = "timeout"
                
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                continue
            
            except requests.ConnectionError as e:
                error_details = {
                    'type': 'connection_error',
                    'attempt': attempt + 1,
                    'error': str(e)
                }
                
                metadata['error_log'] = error_details
                metadata['error_code'] = 'CONNECTION_ERROR'
                metadata['error_message'] = f"Connection error: {str(e)}"
                metadata['latency'] = time.time() - start_time
                metadata['retry_count'] = attempt + 1
                
                logger.warning(f"🔗 Connection error (attempt {attempt + 1})")
                last_error = "connection_error"
                
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                continue
            
            except Exception as e:
                error_details = {
                    'type': 'unknown_error',
                    'error_type': type(e).__name__,
                    'error_message': str(e),
                    'attempt': attempt + 1,
                    'latency': time.time() - start_time
                }
                
                metadata['error_log'] = error_details
                metadata['error_code'] = 'UNKNOWN_ERROR'
                metadata['error_message'] = f"{type(e).__name__}: {str(e)}"
                metadata['latency'] = time.time() - start_time
                metadata['retry_count'] = attempt + 1
                
                logger.error(f"❌ Unknown error: {e}")
                last_error = "unknown_error"
                
                return None, metadata
        
        # 所有重试都失败
        logger.error(f"❌ All {max_retries} attempts failed. Last error: {last_error}")
        return None, metadata