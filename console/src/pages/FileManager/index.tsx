/**
 * 文件管理页面
 */
import React, { useState, useEffect, useCallback } from 'react';
import { 
  Card, 
  Table, 
  Button, 
  Input, 
  Space, 
  Breadcrumb, 
  Modal, 
  message, 
  Tag, 
  Dropdown,
  Menu,
  Tooltip,
  Spin,
  Empty,
  Row,
  Col,
  Statistic
} from 'antd';
import { 
  FolderOutlined, 
  FileOutlined, 
  DownloadOutlined, 
  DeleteOutlined, 
  EyeOutlined,
  ReloadOutlined,
  SearchOutlined,
  MoreOutlined,
  HomeOutlined,
  FolderAddOutlined,
  CloudUploadOutlined,
  FileTextOutlined,
  PictureOutlined,
  CodeOutlined,
  FileZipOutlined,
  QuestionOutlined
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { 
  getFileList, 
  deleteFile, 
  downloadFile,
  getFileIcon,
  formatFileSize,
  formatModifiedTime,
  getWorkspaceStats
} from './api';
import { FileItem, FileSearchParams } from './types';
import FilePreviewModal from './components/FilePreviewModal';
import FileUploadModal from './components/FileUploadModal';
import CreateDirectoryModal from './components/CreateDirectoryModal';
import './index.module.less';

const { Search } = Input;

const FileManagerPage: React.FC = () => {
  const { t } = useTranslation();
  const [files, setFiles] = useState<FileItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [currentPath, setCurrentPath] = useState('');
  const [searchParams, setSearchParams] = useState<FileSearchParams>({
    path: "mycad",
    keyword: '',
    sortBy: 'name',
    sortOrder: 'ascend'
  });
  const [selectedFile, setSelectedFile] = useState<FileItem | null>(null);
  const [previewVisible, setPreviewVisible] = useState(false);
  const [uploadVisible, setUploadVisible] = useState(false);
  const [createDirVisible, setCreateDirVisible] = useState(false);
  const [stats, setStats] = useState({
    totalFiles: 0,
    totalSize: 0,
    lastModified: ''
  });

console.log('FileManagerPage rendered with currentPath:', currentPath, 'searchParams:', searchParams);

  // 加载文件列表
  const loadFiles = useCallback(async () => {
    try {
      setLoading(true);
      const response = await getFileList(searchParams.path, searchParams);
      console.log("response from getFileList:", response);
      console.log('Loaded files:', response);
      response.files = response.data
      setFiles(response.files);
      
      // 加载统计信息
      const statsData = await getWorkspaceStats();
      console.log('Workspace stats:', statsData.data);


      setStats(statsData.data);
    } catch (error) {
      console.error('Failed to load files:', error);
      message.error(t('fileManager.loadFailed'));
    } finally {
      setLoading(false);
    }
  }, [currentPath, searchParams, t]);

  // 初始化加载
  useEffect(() => {
    loadFiles();
  }, [loadFiles]);

  // 处理文件点击（目录进入，文件预览）
  const handleFileClick = (file: FileItem) => {
    if (file.isDirectory) {
      // 进入目录
      const newPath = currentPath ? `${currentPath}/${file.name}` : file.name;
      setCurrentPath(newPath);
    } else {
      // 预览文件
      setSelectedFile(file);
      setPreviewVisible(true);
    }
  };

  // 处理文件下载
  const handleDownload = async (file: FileItem) => {
    try {
      const blob = await downloadFile(file.path);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = file.name;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      message.success(t('fileManager.downloadSuccess'));
    } catch (error) {
      console.error('Download failed:', error);
      message.error(t('fileManager.downloadFailed'));
    }
  };

  // 处理文件删除
  const handleDelete = (file: FileItem) => {
    Modal.confirm({
      title: t('fileManager.deleteConfirmTitle'),
      content: t('fileManager.deleteConfirmContent', { name: file.name }),
      okText: t('common.delete'),
      okType: 'danger',
      cancelText: t('common.cancel'),
      onOk: async () => {
        try {
          await deleteFile(file.path);
          message.success(t('fileManager.deleteSuccess'));
          loadFiles(); // 刷新列表
        } catch (error) {
          console.error('Delete failed:', error);
          message.error(t('fileManager.deleteFailed'));
        }
      },
    });
  };

  // 处理搜索
  const handleSearch = (value: string) => {
    setSearchParams(prev => ({
      ...prev,
      keyword: value
    }));
  };

  // 处理排序
  const handleSort = (sortBy: 'name' | 'size' | 'modified') => {
    setSearchParams(prev => ({
      ...prev,
      sortBy,
      sortOrder: prev.sortOrder === 'ascend' ? 'descend' : 'ascend'
    }));
  };

  // 处理面包屑导航
  const handleBreadcrumbClick = (index: number) => {
    const pathParts = currentPath.split('/').filter(Boolean);
    const newPath = pathParts.slice(0, index).join('/');
    setCurrentPath(newPath);
  };

  // 获取文件类型标签
  const getFileTypeTag = (file: FileItem) => {
    const typeConfig: Record<FileItem['type'], { color: string; icon: React.ReactNode }> = {
      directory: { color: 'blue', icon: <FolderOutlined /> },
      image: { color: 'green', icon: <PictureOutlined /> },
      document: { color: 'purple', icon: <FileTextOutlined /> },
      code: { color: 'orange', icon: <CodeOutlined /> },
      archive: { color: 'red', icon: <FileZipOutlined /> },
      file: { color: 'default', icon: <FileOutlined /> },
      other: { color: 'gray', icon: <QuestionOutlined /> }
    };

    const config = typeConfig[file.type] || typeConfig.other;
    return (
      <Tag color={config.color} icon={config.icon}>
        {t(`fileManager.fileTypes.${file.type}`)}
      </Tag>
    );
  };

  // 表格列定义
  const columns = [
    {
      title: t('fileManager.columns.name'),
      dataIndex: 'name',
      key: 'name',
      width: '40%',
      render: (text: string, record: FileItem) => (
        <Space>
          <span style={{ fontSize: '16px' }}>
            {console.log("aaaaaaa",record)} 
            {getFileIcon(record.type, record.extension)}
          </span>
          <Button 
            type="link" 
            onClick={() => handleFileClick(record)}
            style={{ padding: 0, height: 'auto' }}
          >
            {text}
          </Button>
          {getFileTypeTag(record)}
        </Space>
      ),
      sorter: true,
      sortOrder: searchParams.sortBy === 'name' ? searchParams.sortOrder : undefined,
      onHeaderCell: () => ({
        onClick: () => handleSort('name')
      })
    },
    {
      title: t('fileManager.columns.size'),
      dataIndex: 'size',
      key: 'size',
      width: '15%',
      render: (size: number, record: FileItem) => 
        record.isDirectory ? '-' : formatFileSize(size),
      sorter: true,
      sortOrder: searchParams.sortBy === 'size' ? searchParams.sortOrder : undefined,
      onHeaderCell: () => ({
        onClick: () => handleSort('size')
      })
    },
    {
      title: t('fileManager.columns.modified'),
      dataIndex: 'modified',
      key: 'modified',
      width: '20%',
      render: (modified: string) => formatModifiedTime(modified),
      sorter: true,
      sortOrder: searchParams.sortBy === 'modified' ? searchParams.sortOrder : undefined,
      onHeaderCell: () => ({
        onClick: () => handleSort('modified')
      })
    },
    {
      title: t('fileManager.columns.actions'),
      key: 'actions',
      width: '25%',
      render: (_: any, record: FileItem) => (
        <Space size="small">
          {!record.isDirectory && (
            <>
              <Tooltip title={t('fileManager.preview')}>
                <Button 
                  type="text" 
                  icon={<EyeOutlined />} 
                  onClick={() => {
                    setSelectedFile(record);
                    setPreviewVisible(true);
                  }}
                />
              </Tooltip>
              <Tooltip title={t('fileManager.download')}>
                <Button 
                  type="text" 
                  icon={<DownloadOutlined />} 
                  onClick={() => handleDownload(record)}
                />
              </Tooltip>
            </>
          )}
          <Tooltip title={t('fileManager.delete')}>
            <Button 
              type="text" 
              danger 
              icon={<DeleteOutlined />} 
              onClick={() => handleDelete(record)}
            />
          </Tooltip>
          <Dropdown
            overlay={
              <Menu>
                <Menu.Item key="rename">
                  {t('fileManager.rename')}
                </Menu.Item>
                <Menu.Item key="copy">
                  {t('fileManager.copy')}
                </Menu.Item>
                <Menu.Item key="move">
                  {t('fileManager.move')}
                </Menu.Item>
                <Menu.Divider />
                <Menu.Item key="properties">
                  {t('fileManager.properties')}
                </Menu.Item>
              </Menu>
            }
            trigger={['click']}
          >
            <Button type="text" icon={<MoreOutlined />} />
          </Dropdown>
        </Space>
      ),
    },
  ];

  // 面包屑项目
  const breadcrumbItems = [
    {
      title: (
        <Button 
          type="link" 
          icon={<HomeOutlined />} 
          onClick={() => setCurrentPath('')}
        >
          {t('fileManager.home')}
        </Button>
      ),
    },
    ...currentPath.split('/').filter(Boolean).map((part, index) => ({
      title: (
        <Button 
          type="link" 
          onClick={() => handleBreadcrumbClick(index + 1)}
        >
          {part}
        </Button>
      ),
    })),
  ];

  return (
    <div className="file-manager-page">
      <Card>
        {/* 头部操作栏 */}
        <Row justify="space-between" align="middle" style={{ marginBottom: 16 }}>
          <Col>
            <Breadcrumb items={breadcrumbItems} />
          </Col>
          <Col>
            <Space>
              <Search
                placeholder={t('fileManager.searchPlaceholder')}
                onSearch={handleSearch}
                style={{ width: 300 }}
                prefix={<SearchOutlined />}
                allowClear
              />
              <Tooltip title={t('fileManager.refresh')}>
                <Button 
                  icon={<ReloadOutlined />} 
                  onClick={loadFiles}
                  loading={loading}
                />
              </Tooltip>
              <Tooltip title={t('fileManager.createDirectory')}>
                <Button 
                  icon={<FolderAddOutlined />} 
                  onClick={() => setCreateDirVisible(true)}
                />
              </Tooltip>
              <Tooltip title={t('fileManager.uploadFile')}>
                <Button 
                  type="primary" 
                  icon={<CloudUploadOutlined />}
                  onClick={() => setUploadVisible(true)}
                >
                  {t('fileManager.upload')}
                </Button>
              </Tooltip>
            </Space>
          </Col>
        </Row>

        {/* 统计信息 */}
        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col span={8}>
            <Card size="small">
              <Statistic
                title={t('fileManager.totalFiles')}
                value={stats.totalFiles}
                prefix={<FileOutlined />}
              />
            </Card>
          </Col>
          <Col span={8}>
            <Card size="small">
              <Statistic
                title={t('fileManager.totalSize')}
                value={formatFileSize(stats.totalSize)}
                prefix={<FolderOutlined />}
              />
            </Card>
          </Col>
          <Col span={8}>
            <Card size="small">
              <Statistic
                title={t('fileManager.lastModified')}
                value={formatModifiedTime(stats.lastModified)}
                prefix={<ReloadOutlined />}
              />
            </Card>
          </Col>
        </Row>

        {/* 文件列表 */}
        <Table
          columns={columns}
          dataSource={files}
          rowKey="path"
          loading={loading}
          pagination={{
            pageSize: 20,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total) => t('fileManager.totalFilesCount', { total })
          }}
          locale={{
            emptyText: loading ? (
              <Spin tip={t('fileManager.loading')} />
            ) : (
              <Empty
                image={Empty.PRESENTED_IMAGE_SIMPLE}
                description={t('fileManager.noFiles')}
              />
            )
          }}
          onRow={(record) => ({
            onDoubleClick: () => handleFileClick(record),
          })}
        />
      </Card>

      {/* 文件预览模态框 */}
      <FilePreviewModal
        visible={previewVisible}
        file={selectedFile}
        onClose={() => setPreviewVisible(false)}
      />

      {/* 文件上传模态框 */}
      <FileUploadModal
        visible={uploadVisible}
        currentPath={currentPath}
        onClose={() => setUploadVisible(false)}
        onSuccess={() => {
          message.success(t('fileManager.uploadSuccess'));
          loadFiles();
          setUploadVisible(false);
        }}
      />

      {/* 创建目录模态框 */}
      <CreateDirectoryModal
        visible={createDirVisible}
        currentPath={currentPath}
        onClose={() => setCreateDirVisible(false)}
        onSuccess={() => {
          message.success(t('fileManager.createDirectorySuccess'));
          loadFiles();
          setCreateDirVisible(false);
        }}
      />
    </div>
  );
};

export default FileManagerPage;