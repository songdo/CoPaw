/**
 * 文件管理类型定义
 */

export interface FileItem {
  /** 文件名 */
  name: string;
  /** 文件路径（相对路径） */
  path: string;
  /** 文件大小（字节） */
  size: number;
  /** 修改时间 */
  modified: string;
  /** 是否是目录 */
  is_dir: boolean;
  /** 文件类型 */
  type: 'file' | 'directory' | 'image' | 'document' | 'code' | 'archive' | 'other';
  /** 文件扩展名 */
  extension: string;
}

export interface FileListResponse {
  /** 文件列表 */
  files: FileItem[];
  /** 当前路径 */
  currentPath: string;
  /** 总文件数 */
  total: number;
  data: FileItem[]; // 兼容后端返回格式
}

export interface FileContentResponse {
  /** 文件内容 */
  content: string;
  /** 文件路径 */
  path: string;
  /** 文件大小 */
  size: number;
  /** 是否可读 */
  readable: boolean;
}

export interface FileOperationRequest {
  /** 文件路径 */
  path: string;
}

export interface FileDeleteRequest extends FileOperationRequest {
  /** 是否强制删除 */
  force?: boolean;
}

export interface FileUploadRequest {
  /** 文件路径 */
  path: string;
  /** 文件内容 */
  file: File;
}

export interface FileSearchParams {
  path: string;
  /** 搜索关键词 */
  keyword: string;
  /** 文件类型过滤 */
  fileType?: FileItem['type'];
  /** 排序字段 */
  sortBy?: 'name' | 'size' | 'modified';
  /** 排序方向 */
  sortOrder?: 'ascend' | 'descend';
  /** 页码 */
  page?: number;
  /** 每页数量 */
  pageSize?: number;
}
