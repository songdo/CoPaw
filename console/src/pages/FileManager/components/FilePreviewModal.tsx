/**
 * 文件预览模态框组件
 */
import React, { useState, useEffect } from 'react';
import { Modal, Spin, Alert, Tabs, Typography, Space, Button, Tag } from 'antd';
import { 
  FileTextOutlined, 
  CodeOutlined, 
  PictureOutlined,
  DownloadOutlined
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { getFileContent, formatFileSize } from '../api';
import { FileItem } from '../types';
import './FilePreviewModal.module.less';

const { Text } = Typography;
const { TabPane } = Tabs;

interface FilePreviewModalProps {
  visible: boolean;
  file: FileItem | null;
  onClose: () => void;
}

const FilePreviewModal: React.FC<FilePreviewModalProps> = ({
  visible,
  file,
  onClose
}) => {
  const { t } = useTranslation();
  const [content, setContent] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState('preview');

  // 加载文件内容
  useEffect(() => {
    if (visible && file && !file.isDirectory) {
      loadFileContent();
    } else {
      setContent('');
      setError(null);
    }
  }, [visible, file]);

  const loadFileContent = async () => {
    if (!file) return;
    
    try {
      setLoading(true);
      setError(null);
      const response = await getFileContent(file.path);
      
      if (response.readable) {
        setContent(response.content);
      } else {
        setError(t('fileManager.previewNotSupported'));
      }
    } catch (err) {
      console.error('Failed to load file content:', err);
      setError(t('fileManager.previewFailed'));
    } finally {
      setLoading(false);
    }
  };

  // 获取文件类型图标
  const getFileTypeIcon = () => {
    if (!file) return <FileTextOutlined />;
    
    switch (file.type) {
      case 'code':
        return <CodeOutlined />;
      case 'image':
        return <PictureOutlined />;
      default:
        return <FileTextOutlined />;
    }
  };

  // 判断是否支持预览
  const isPreviewSupported = () => {
    if (!file) return false;
    
    const supportedTypes = ['document', 'code', 'json', 'xml', 'yaml', 'md', 'txt'];
    const imageTypes = ['png', 'jpg', 'jpeg', 'gif', 'svg', 'bmp'];
    
    const ext = file.extension.toLowerCase();
    return supportedTypes.includes(file.type) || 
           supportedTypes.includes(ext) || 
           imageTypes.includes(ext);
  };

  // 渲染文件内容
  const renderFileContent = () => {
    if (loading) {
      return (
        <div style={{ textAlign: 'center', padding: '40px' }}>
          <Spin size="large" tip={t('fileManager.loadingContent')} />
        </div>
      );
    }

    if (error) {
      return (
        <Alert
          message={t('fileManager.previewError')}
          description={error}
          type="error"
          showIcon
        />
      );
    }

    if (!file || file.isDirectory) {
      return (
        <Alert
          message={t('fileManager.directoryPreview')}
          description={t('fileManager.directoryPreviewDesc')}
          type="info"
          showIcon
        />
      );
    }

    // 根据文件类型渲染不同内容
    if (file.type === 'image') {
      return (
        <div style={{ textAlign: 'center' }}>
          <img
            src={`data:image/${file.extension};base64,${content}`}
            alt={file.name}
            style={{ maxWidth: '100%', maxHeight: '500px' }}
          />
        </div>
      );
    } else {
      // 对于代码、文档和其他文本类型文件
      return (
        <div style={{ 
          backgroundColor: '#f6f8fa', 
          padding: '16px', 
          borderRadius: '4px',
          fontFamily: 'monospace',
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-all',
          maxHeight: '500px',
          overflow: 'auto'
        }}>
          {content}
        </div>
      );
    }
  };

  // 渲染文件信息
  const renderFileInfo = () => {
    if (!file) return null;

    return (
      <div style={{ padding: '16px', backgroundColor: '#fafafa', borderRadius: '4px' }}>
        <Space direction="vertical" size="small" style={{ width: '100%' }}>
          <div>
            <Text strong>{t('fileManager.fileName')}: </Text>
            <Text>{file.name}</Text>
          </div>
          <div>
            <Text strong>{t('fileManager.filePath')}: </Text>
            <Text code>{file.path}</Text>
          </div>
          <div>
            <Text strong>{t('fileManager.fileSize')}: </Text>
            <Text>{formatFileSize(file.size)}</Text>
          </div>
          <div>
            <Text strong>{t('fileManager.modifiedTime')}: </Text>
            <Text>{new Date(file.modified).toLocaleString()}</Text>
          </div>
          <div>
            <Text strong>{t('fileManager.fileType')}: </Text>
            <Tag color="blue">{file.type}</Tag>
            {file.extension && <Tag>{file.extension}</Tag>}
          </div>
        </Space>
      </div>
    );
  };

  return (
    <Modal
      title={
        <Space>
          {getFileTypeIcon()}
          <span>{file?.name || t('fileManager.filePreview')}</span>
          {file && !file.isDirectory && (
            <Tag color={isPreviewSupported() ? 'green' : 'orange'}>
              {isPreviewSupported() 
                ? t('fileManager.previewSupported') 
                : t('fileManager.previewLimited')}
            </Tag>
          )}
        </Space>
      }
      open={visible}
      onCancel={onClose}
      width={800}
      footer={[
        <Button key="close" onClick={onClose}>
          {t('common.close')}
        </Button>,
        file && !file.isDirectory && (
          <Button 
            key="download" 
            type="primary" 
            icon={<DownloadOutlined />}
            onClick={() => {
              // 这里可以添加下载逻辑
              onClose();
            }}
          >
            {t('fileManager.download')}
          </Button>
        )
      ].filter(Boolean)}
      destroyOnClose
    >
      {file ? (
        <Tabs activeKey={activeTab} onChange={setActiveTab}>
          <TabPane 
            tab={
              <span>
                <FileTextOutlined />
                {t('fileManager.preview')}
              </span>
            } 
            key="preview"
          >
            {renderFileContent()}
          </TabPane>
          
          <TabPane 
            tab={
              <span>
                <CodeOutlined />
                {t('fileManager.properties')}
              </span>
            } 
            key="properties"
          >
            {renderFileInfo()}
          </TabPane>
          
          {file.type === 'code' && (
            <TabPane 
              tab={
                <span>
                  <CodeOutlined />
                  {t('fileManager.codeAnalysis')}
                </span>
              } 
              key="analysis"
            >
              <Alert
                message={t('fileManager.analysisComingSoon')}
                description={t('fileManager.analysisDesc')}
                type="info"
                showIcon
              />
            </TabPane>
          )}
        </Tabs>
      ) : (
        <Alert
          message={t('fileManager.noFileSelected')}
          description={t('fileManager.selectFileToPreview')}
          type="warning"
          showIcon
        />
      )}
    </Modal>
  );
};

export default FilePreviewModal;