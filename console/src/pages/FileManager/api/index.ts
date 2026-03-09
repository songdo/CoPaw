/**
 * 文件管理API接口
 */
import { request } from '../../../api/request';
import { getApiUrl, getApiToken } from '../../../api/config';
import { 
  FileItem, 
  FileListResponse, 
  FileContentResponse,
  FileSearchParams 
} from '../types';

/**
 * 获取文件列表
 * @param path 目录路径（默认为根目录）
 * @param params 搜索参数
 */
export async function getFileList(
  path: string = '',
  params?: FileSearchParams
): Promise<FileListResponse> {
  const queryParams = new URLSearchParams();
  
  if (path) {
    queryParams.append('path', path);
  }
  console.log("getFileList params11:", queryParams);
  console.log("getFileList path:", path);
  if (params) {
    if (params.keyword) {
      queryParams.append('keyword', params.keyword);
    }
    if (params.fileType) {
      queryParams.append('file_type', params.fileType);
    }
    if (params.sortBy) {
      queryParams.append('sort_by', params.sortBy);
    }
    if (params.sortOrder) {
      queryParams.append('sort_order', params.sortOrder);
    }
    if (params.page) {
      queryParams.append('page', params.page.toString());
    }
    if (params.pageSize) {
      queryParams.append('page_size', params.pageSize.toString());
    }
  }
  console.log("getFileList params:", queryParams);
  
  const queryString = queryParams.toString();
  console.log("queryString", queryString);

  const url = `/files/list${queryString ? `?${queryString}` : ''}`;
  console.log("Requesting file list with URL:", url);
  
  return request<FileListResponse>(url);
}

/**
 * 获取文件内容
 * @param path 文件路径
 * @param encoding 文件编码（可选）
 */
export async function getFileContent(
  path: string, 
  encoding?: string
): Promise<FileContentResponse> {
  const encodedPath = encodeURIComponent(path);
  const queryParams = new URLSearchParams();
  if (encoding) {
    queryParams.append('encoding', encoding);
  }
  
  const queryString = queryParams.toString();
  const url = `/files/content/${encodedPath}${queryString ? `?${queryString}` : ''}`;
  
  return request<FileContentResponse>(url);
}

/**
 * 删除文件
 * @param path 文件路径
 */
export async function deleteFile(path: string): Promise<void> {
  const encodedPath = encodeURIComponent(path);
  const url = `/files/${encodedPath}`;
  
  return request<void>(url, {
    method: 'DELETE'
  });
}

/**
 * 下载文件
 * @param path 文件路径
 */
export async function downloadFile(path: string): Promise<Blob> {
  const encodedPath = encodeURIComponent(path);
  const response = await fetch(getApiUrl(`/files/download/${encodedPath}`), {
    headers: {
      'Authorization': `Bearer ${getApiToken()}`
    }
  });
  
  if (!response.ok) {
    throw new Error(`Download failed: ${response.status} ${response.statusText}`);
  }
  
  return response.blob();
}

/**
 * 创建目录
 * @param path 父目录路径
 * @param name 目录名称
 */
export async function createDirectory(path: string, name: string): Promise<void> {
  const formData = new FormData();
  formData.append('path', path);
  formData.append('name', name);
  
  const response = await fetch(getApiUrl('/files/directory'), {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${getApiToken()}`
    },
    body: formData
  });
  
  if (!response.ok) {
    throw new Error(`Create directory failed: ${response.status} ${response.statusText}`);
  }
}

/**
 * 上传文件
 * @param path 目标目录路径
 * @param file 文件对象
 */
export async function uploadFile(path: string, file: File): Promise<void> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('path', path);
  
  const response = await fetch(getApiUrl('/files/upload'), {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${getApiToken()}`
    },
    body: formData
  });
  
  if (!response.ok) {
    throw new Error(`Upload failed: ${response.status} ${response.statusText}`);
  }
}

/**
 * 重命名文件
 * @param oldPath 原路径
 * @param newName 新名称
 */
export async function renameFile(oldPath: string, newName: string): Promise<void> {
  const formData = new FormData();
  formData.append('old_path', oldPath);
  formData.append('new_name', newName);
  
  const response = await fetch(getApiUrl('/files/rename'), {
    method: 'PUT',
    headers: {
      'Authorization': `Bearer ${getApiToken()}`
    },
    body: formData
  });
  
  if (!response.ok) {
    throw new Error(`Rename failed: ${response.status} ${response.statusText}`);
  }
}

/**
 * 获取文件统计信息
 */
export async function getWorkspaceStats(): Promise<any> {
  return request('/files/stats');
}

/**
 * 获取文件类型图标
 * @param fileType 文件类型
 * @param extension 文件扩展名
 */
export function getFileIcon(fileType: FileItem['type'], extension: string): string {
  const iconMap: Record<string, string> = {
    directory: '📁',
    image: '🖼️',
    document: '📄',
    code: '📝',
    archive: '📦',
    pdf: '📕',
    doc: '📘',
    docx: '📘',
    txt: '📃',
    md: '📖',
    json: '📋',
    yaml: '📋',
    yml: '📋',
    xml: '📋',
    html: '🌐',
    css: '🎨',
    js: '⚡',
    ts: '⚡',
    py: '🐍',
    java: '☕',
    cpp: '⚙️',
    c: '⚙️',
    go: '🚀',
    rs: '🦀',
    php: '🐘',
    rb: '💎',
    sh: '🐚',
    bat: '🪟',
    ps1: '🪟',
    exe: '⚙️',
    dll: '🔧',
    so: '🔧',
    dylib: '🔧',
    png: '🖼️',
    jpg: '🖼️',
    jpeg: '🖼️',
    gif: '🖼️',
    svg: '🖼️',
    ico: '🖼️',
    bmp: '🖼️',
    mp3: '🎵',
    mp4: '🎬',
    avi: '🎬',
    mov: '🎬',
    wav: '🎵',
    zip: '📦',
    rar: '📦',
    '7z': '📦',
    tar: '📦',
    gz: '📦',
    xz: '📦',
  };
  
  // 优先使用扩展名匹配
  if (extension==null) {
    extension = 'directory';
  }
  if (iconMap[extension.toLowerCase()]) {
    return iconMap[extension.toLowerCase()];
  }
  
  // 使用文件类型匹配
  if (iconMap[fileType]) {
    return iconMap[fileType];
  }
  
  // 默认图标
  return '📄';
}

/**
 * 格式化文件大小
 * @param bytes 字节数
 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * 格式化修改时间
 * @param dateString 日期字符串
 */
export function formatModifiedTime(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  
  if (diffDays === 0) {
    // 今天
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } else if (diffDays === 1) {
    // 昨天
    return '昨天 ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } else if (diffDays < 7) {
    // 一周内
    const days = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];
    return days[date.getDay()] + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } else {
    // 更早
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }
}