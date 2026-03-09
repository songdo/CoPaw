/**
 * 文件上传模态框组件
 */
import React, { useState } from 'react';
import { 
  Modal, 
  Upload, 
  Button, 
  message, 
  Progress, 
  List, 
  Space, 
  Typography,
  Alert,
  Tag
} from 'antd';
import { 
  UploadOutlined, 
  InboxOutlined, 
  FileOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  LoadingOutlined
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import './FileUploadModal.module.less';

const { Dragger } = Upload;
const { Text } = Typography;

interface FileUploadModalProps {
  visible: boolean;
  currentPath: string;
  onClose: () => void;
  onSuccess: () => void;
}

interface UploadFile {
  file: File;
  status: 'pending' | 'uploading' | 'success' | 'error';
  progress: number;
  error?: string;
}

const FileUploadModal: React.FC<FileUploadModalProps> = ({
  visible,
  currentPath,
  onClose,
  onSuccess
}) => {
  const { t } = useTranslation();
  const [uploadFiles, setUploadFiles] = useState<UploadFile[]>([]);
  const [uploading, setUploading] = useState(false);

  // 处理文件选择
  const handleFileSelect = (files: File[]) => {
    const newUploadFiles: UploadFile[] = files.map(file => ({
      file,
      status: 'pending',
      progress: 0
    }));
    
    setUploadFiles(prev => [...prev, ...newUploadFiles]);
  };

  // 开始上传
  const handleUpload = async () => {
    if (uploadFiles.length === 0) {
      message.warning(t('fileManager.selectFilesFirst'));
      return;
    }

    setUploading(true);
    const results = [];

    for (const fileItem of uploadFiles) {
      if (fileItem.status === 'success') continue;

      try {
        // 更新状态为上传中
        setUploadFiles(prev => prev.map(f => 
          f.file === fileItem.file 
            ? { ...f, status: 'uploading', progress: 10 }
            : f
        ));

        // 模拟上传进度
        const interval = setInterval(() => {
          setUploadFiles(prev => prev.map(f => {
            if (f.file === fileItem.file && f.status === 'uploading') {
              const newProgress = Math.min(f.progress + 10, 90);
              return { ...f, progress: newProgress };
            }
            return f;
          }));
        }, 200);

        // 实际上传 - 这里需要实现实际上传逻辑
        // TODO: 实现实际上传API调用
        await new Promise(resolve => setTimeout(resolve, 1000));

        clearInterval(interval);

        // 更新状态为成功
        setUploadFiles(prev => prev.map(f => 
          f.file === fileItem.file 
            ? { ...f, status: 'success', progress: 100 }
            : f
        ));

        results.push({ file: fileItem.file.name, success: true });
      } catch (error) {
        // 更新状态为错误
        setUploadFiles(prev => prev.map(f => 
          f.file === fileItem.file 
            ? { 
                ...f, 
                status: 'error', 
                progress: 0,
                error: error instanceof Error ? error.message : t('fileManager.uploadFailed')
              }
            : f
        ));

        results.push({ 
          file: fileItem.file.name, 
          success: false, 
          error: error instanceof Error ? error.message : undefined 
        });
      }
    }

    setUploading(false);

    // 统计结果
    const successCount = results.filter(r => r.success).length;
    const errorCount = results.filter(r => !r.success).length;

    if (errorCount === 0) {
      message.success(t('fileManager.allFilesUploaded', { count: successCount }));
      onSuccess();
    } else if (successCount === 0) {
      message.error(t('fileManager.allFilesFailed'));
    } else {
      message.warning(
        t('fileManager.partialUploadResult', { 
          success: successCount, 
          error: errorCount 
        })
      );
    }
  };

  // 移除文件
  const handleRemoveFile = (fileToRemove: File) => {
    setUploadFiles(prev => prev.filter(f => f.file !== fileToRemove));
  };

  // 清空所有文件
  const handleClearAll = () => {
    setUploadFiles([]);
  };

  // 获取状态图标
  const getStatusIcon = (status: UploadFile['status']) => {
    switch (status) {
      case 'pending':
        return <FileOutlined style={{ color: '#999' }} />;
      case 'uploading':
        return <LoadingOutlined style={{ color: '#1890ff' }} />;
      case 'success':
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
      case 'error':
        return <CloseCircleOutlined style={{ color: '#ff4d4f' }} />;
      default:
        return <FileOutlined />;
    }
  };

  // 获取状态标签
  const getStatusTag = (status: UploadFile['status']) => {
    const statusConfig = {
      pending: { color: 'default', text: t('fileManager.statusPending') },
      uploading: { color: 'processing', text: t('fileManager.statusUploading') },
      success: { color: 'success', text: t('fileManager.statusSuccess') },
      error: { color: 'error', text: t('fileManager.statusError') }
    };

    const config = statusConfig[status];
    return <Tag color={config.color}>{config.text}</Tag>;
  };

  // 格式化文件大小
  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 B';
    
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  // 渲染文件列表项
  const renderFileItem = (uploadFile: UploadFile) => (
    <List.Item
      actions={[
        uploadFile.status === 'pending' && (
          <Button 
            type="text" 
            danger 
            size="small"
            onClick={() => handleRemoveFile(uploadFile.file)}
          >
            {t('common.remove')}
          </Button>
        )
      ].filter(Boolean)}
    >
      <List.Item.Meta
        avatar={getStatusIcon(uploadFile.status)}
        title={
          <Space>
            <Text strong>{uploadFile.file.name}</Text>
            {getStatusTag(uploadFile.status)}
          </Space>
        }
        description={
          <Space direction="vertical" size={2} style={{ width: '100%' }}>
            <Text type="secondary">
              {formatFileSize(uploadFile.file.size)} • {uploadFile.file.type || t('fileManager.unknownType')}
            </Text>
            
            {uploadFile.status === 'uploading' && (
              <Progress 
                percent={uploadFile.progress} 
                size="small" 
                status="active"
                style={{ marginTop: 8 }}
              />
            )}
            
            {uploadFile.status === 'error' && uploadFile.error && (
              <Alert
                message={uploadFile.error}
                type="error"
                showIcon
                style={{ marginTop: 8 }}
              />
            )}
          </Space>
        }
      />
    </List.Item>
  );

  return (
    <Modal
      title={
        <Space>
          <UploadOutlined />
          {t('fileManager.uploadFiles')}
        </Space>
      }
      open={visible}
      onCancel={onClose}
      width={600}
      footer={[
        <Button key="cancel" onClick={onClose}>
          {t('common.cancel')}
        </Button>,
        uploadFiles.length > 0 && (
          <Button key="clear" onClick={handleClearAll}>
            {t('fileManager.clearAll')}
          </Button>
        ),
        <Button 
          key="upload" 
          type="primary" 
          loading={uploading}
          onClick={handleUpload}
          disabled={uploadFiles.length === 0 || uploading}
        >
          {uploading ? t('fileManager.uploading') : t('fileManager.startUpload')}
        </Button>
      ].filter(Boolean)}
      destroyOnClose
      afterClose={() => {
        setUploadFiles([]);
        setUploading(false);
      }}
    >
      <Space direction="vertical" size="middle" style={{ width: '100%' }}>
        {/* 当前路径显示 */}
        <Alert
          message={t('fileManager.uploadTo')}
          description={
            <Text code>
              {currentPath ? `~/.copaw/${currentPath}` : '~/.copaw/'}
            </Text>
          }
          type="info"
          showIcon
        />

        {/* 文件拖拽区域 */}
        <Dragger
          multiple
          showUploadList={false}
          beforeUpload={(file) => {
            handleFileSelect([file]);
            return false; // 阻止默认上传
          }}
          disabled={uploading}
        >
          <p className="ant-upload-drag-icon">
            <InboxOutlined />
          </p>
          <p className="ant-upload-text">
            {t('fileManager.dragOrClick')}
          </p>
          <p className="ant-upload-hint">
            {t('fileManager.uploadHint')}
          </p>
        </Dragger>

        {/* 文件列表 */}
        {uploadFiles.length > 0 && (
          <div>
            <div style={{ 
              display: 'flex', 
              justifyContent: 'space-between', 
              alignItems: 'center',
              marginBottom: 16 
            }}>
              <Text strong>
                {t('fileManager.selectedFiles')} ({uploadFiles.length})
              </Text>
              <Space>
                <Text type="secondary">
                  {t('fileManager.totalSize')}:{' '}
                  {formatFileSize(uploadFiles.reduce((sum, f) => sum + f.file.size, 0))}
                </Text>
              </Space>
            </div>
            
            <List
              dataSource={uploadFiles}
              renderItem={renderFileItem}
              size="small"
              style={{ maxHeight: 300, overflow: 'auto' }}
              locale={{ emptyText: t('fileManager.noFilesSelected') }}
            />
          </div>
        )}

        {/* 上传提示 */}
        <Alert
          message={t('fileManager.uploadTipsTitle')}
          description={t('fileManager.uploadTips')}
          type="info"
          showIcon
        />
      </Space>
    </Modal>
  );
};

export default FileUploadModal;