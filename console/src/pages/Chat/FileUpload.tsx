import { useState, useRef } from "react";
import { Upload, Button, Space, Typography, List, Progress, message } from "antd";
import { UploadOutlined, PaperClipOutlined, DeleteOutlined } from "@ant-design/icons";
import { useTranslation } from "react-i18next";
import type { UploadProps } from "antd";

const { Text } = Typography;

interface FileUploadProps {
  onFilesUploaded?: (files: File[]) => void;
  maxFiles?: number;
  maxSize?: number; // in MB
  acceptedTypes?: string[];
  compactMode?: boolean;
}

interface UploadedFile {
  id: string;
  file: File;
  progress: number;
  status: 'uploading' | 'done' | 'error';
  error?: string;
}

export default function FileUpload({
  onFilesUploaded,
  maxFiles = 5,
  maxSize = 10, // 10MB
  acceptedTypes = ['.pdf', '.doc', '.docx', '.txt', '.jpg', '.jpeg', '.png', '.xlsx', '.xls'],
  compactMode = false
}: FileUploadProps) {
  const { t } = useTranslation();
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = (files: FileList | null) => {
    if (!files) return;

    const fileArray = Array.from(files);
    const validFiles: File[] = [];
    const errors: string[] = [];

    // 验证文件
    fileArray.forEach((file) => {
      // 检查文件数量
      if (uploadedFiles.length + validFiles.length >= maxFiles) {
        errors.push(`${file.name}: ${t('fileUpload.maxFilesError', { maxFiles })}`);
        return;
      }

      // 检查文件大小
      const fileSizeMB = file.size / (1024 * 1024);
      if (fileSizeMB > maxSize) {
        errors.push(`${file.name}: ${t('fileUpload.maxSizeError', { maxSize })}`);
        return;
      }

      // 检查文件类型
      const fileExtension = '.' + file.name.split('.').pop()?.toLowerCase();
      if (!acceptedTypes.includes(fileExtension)) {
        errors.push(`${file.name}: ${t('fileUpload.typeError')}`);
        return;
      }

      validFiles.push(file);
    });

    // 显示错误信息
    if (errors.length > 0) {
      message.error(
        <div>
          {errors.map((error, index) => (
            <div key={index}>{error}</div>
          ))}
        </div>
      );
    }

    // 添加有效文件
    if (validFiles.length > 0) {
      const newUploadedFiles: UploadedFile[] = validFiles.map((file) => ({
        id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
        file,
        progress: 0,
        status: 'uploading' as const
      }));

      setUploadedFiles(prev => [...prev, ...newUploadedFiles]);

      // 模拟上传过程
      newUploadedFiles.forEach((uploadedFile) => {
        simulateUpload(uploadedFile.id);
      });

      // 回调
      if (onFilesUploaded) {
        onFilesUploaded(validFiles);
      }
    }
  };

  const simulateUpload = (fileId: string) => {
    let progress = 0;
    const interval = setInterval(() => {
      progress += 10;
      setUploadedFiles(prev => 
        prev.map(file => 
          file.id === fileId 
            ? { ...file, progress: Math.min(progress, 100) }
            : file
        )
      );

      if (progress >= 100) {
        clearInterval(interval);
        setUploadedFiles(prev => 
          prev.map(file => 
            file.id === fileId 
              ? { ...file, progress: 100, status: 'done' as const }
              : file
          )
        );
      }
    }, 100);
  };

  const handleRemoveFile = (fileId: string) => {
    setUploadedFiles(prev => prev.filter(file => file.id !== fileId));
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    handleFileSelect(e.dataTransfer.files);
  };

  const uploadProps: UploadProps = {
    beforeUpload: (file) => {
      handleFileSelect([file] as any);
      return false; // 阻止默认上传行为
    },
    showUploadList: false,
    multiple: true,
    accept: acceptedTypes.join(','),
  };

  // 紧凑模式：只显示一个别针图标按钮
  if (compactMode) {
    return (
      <div>
        <Button
          type="text"
          icon={<PaperClipOutlined style={{ color: '#615CED', fontSize: 18 }} />}
          onClick={() => fileInputRef.current?.click()}
          style={{ padding: '4px 8px' }}
          title={t('common.upload')}
        />
        <input
          type="file"
          ref={fileInputRef}
          style={{ display: 'none' }}
          multiple
          accept={acceptedTypes.join(',')}
          onChange={(e) => {
            handleFileSelect(e.target.files);
            e.target.value = ''; // 重置input
          }}
        />
        
        {/* 文件上传状态提示 */}
        {uploadedFiles.length > 0 && (
          <div style={{ position: 'absolute', top: 40, left: 0, zIndex: 1000, background: 'white', padding: 8, borderRadius: 4, boxShadow: '0 2px 8px rgba(0,0,0,0.15)', minWidth: 200 }}>
            <Text strong style={{ display: 'block', marginBottom: 8, fontSize: 12 }}>
              {t('fileUpload.selectedFiles')} ({uploadedFiles.length}/{maxFiles})
            </Text>
            <List
              size="small"
              dataSource={uploadedFiles}
              renderItem={(item) => (
                <List.Item
                  style={{ padding: '4px 0' }}
                  actions={[
                    <Button
                      type="text"
                      danger
                      size="small"
                      icon={<DeleteOutlined />}
                      onClick={() => handleRemoveFile(item.id)}
                      style={{ fontSize: 10 }}
                    />
                  ]}
                >
                  <List.Item.Meta
                    avatar={<PaperClipOutlined style={{ fontSize: 12 }} />}
                    title={
                      <Text ellipsis style={{ maxWidth: 120, fontSize: 12 }}>
                        {item.file.name}
                      </Text>
                    }
                    description={
                      <div style={{ fontSize: 10 }}>
                        <div>{(item.file.size / 1024).toFixed(1)} KB</div>
                        {item.status === 'uploading' && (
                          <Progress
                            percent={item.progress}
                            size="small"
                            status="active"
                            style={{ marginTop: 2 }}
                          />
                        )}
                        {item.status === 'done' && (
                          <Text type="success" style={{ fontSize: 10 }}>
                            {t('fileUpload.uploadComplete')}
                          </Text>
                        )}
                      </div>
                    }
                  />
                </List.Item>
              )}
            />
          </div>
        )}
      </div>
    );
  }

  // 完整模式：显示完整的拖拽上传区域
  return (
    <div style={{ marginBottom: 16 }}>
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        style={{
          border: `2px dashed ${isDragging ? '#615CED' : '#d9d9d9'}`,
          borderRadius: 8,
          padding: 24,
          textAlign: 'center',
          backgroundColor: isDragging ? '#f0f5ff' : '#fafafa',
          marginBottom: 16,
          transition: 'all 0.3s',
        }}
      >
        <Upload {...uploadProps}>
          <Space direction="vertical" size="middle" style={{ width: '100%' }}>
            <PaperClipOutlined style={{ fontSize: 32, color: '#615CED' }} />
            <div>
              <Text strong style={{ display: 'block', marginBottom: 8 }}>
                {t('fileUpload.dragDrop')}
              </Text>
              <Text type="secondary" style={{ fontSize: 12 }}>
                {t('fileUpload.supportedFormats', { formats: acceptedTypes.join(', ') })}
                <br />
                {t('fileUpload.maxSize', { maxSize })}
                {t('fileUpload.maxFiles', { maxFiles })}
              </Text>
            </div>
            <Button 
              type="primary" 
              icon={<UploadOutlined />}
              onClick={() => fileInputRef.current?.click()}
            >
              {t('fileUpload.browseFiles')}
            </Button>
          </Space>
        </Upload>
        <input
          type="file"
          ref={fileInputRef}
          style={{ display: 'none' }}
          multiple
          accept={acceptedTypes.join(',')}
          onChange={(e) => {
            handleFileSelect(e.target.files);
            e.target.value = ''; // 重置input
          }}
        />
      </div>

      {uploadedFiles.length > 0 && (
        <div>
          <Text strong style={{ display: 'block', marginBottom: 8 }}>
            {t('fileUpload.selectedFiles')} ({uploadedFiles.length}/{maxFiles})
          </Text>
          <List
            size="small"
            dataSource={uploadedFiles}
            renderItem={(item) => (
              <List.Item
                actions={[
                  <Button
                    type="text"
                    danger
                    size="small"
                    icon={<DeleteOutlined />}
                    onClick={() => handleRemoveFile(item.id)}
                  />
                ]}
              >
                <List.Item.Meta
                  avatar={<PaperClipOutlined />}
                  title={
                    <Text ellipsis style={{ maxWidth: 200 }}>
                      {item.file.name}
                    </Text>
                  }
                  description={
                    <div>
                      <div>
                        {(item.file.size / 1024).toFixed(1)} KB
                      </div>
                      {item.status === 'uploading' && (
                        <Progress
                          percent={item.progress}
                          size="small"
                          status="active"
                          style={{ marginTop: 4 }}
                        />
                      )}
                      {item.status === 'done' && (
                        <Text type="success" style={{ fontSize: 12 }}>
                          {t('fileUpload.uploadComplete')}
                        </Text>
                      )}
                    </div>
                  }
                />
              </List.Item>
            )}
          />
        </div>
      )}
    </div>
  );
}