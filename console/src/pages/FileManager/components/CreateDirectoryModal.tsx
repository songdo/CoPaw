/**
 * 创建目录模态框组件
 */
import React, { useState, useEffect } from 'react';
import { Modal, Form, Input, Button, message, Alert, Space, Typography } from 'antd';
import { FolderAddOutlined, FolderOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { createDirectory } from '../api';
import './CreateDirectoryModal.module.less';

const { Text } = Typography;

interface CreateDirectoryModalProps {
  visible: boolean;
  currentPath: string;
  onClose: () => void;
  onSuccess: () => void;
}

const CreateDirectoryModal: React.FC<CreateDirectoryModalProps> = ({
  visible,
  currentPath,
  onClose,
  onSuccess
}) => {
  const { t } = useTranslation();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [suggestions, setSuggestions] = useState<string[]>([]);

  // 目录名建议
  const directorySuggestions = [
    'documents',
    'images',
    'downloads',
    'backups',
    'temp',
    'projects',
    'config',
    'logs',
    'data',
    'exports'
  ];

  // 重置表单
  useEffect(() => {
    if (visible) {
      form.resetFields();
      generateSuggestions();
    }
  }, [visible, form]);

  // 生成建议
  const generateSuggestions = () => {
    const shuffled = [...directorySuggestions].sort(() => Math.random() - 0.5);
    setSuggestions(shuffled.slice(0, 3));
  };

  // 处理提交
  const handleSubmit = async (values: { directoryName: string }) => {
    try {
      setLoading(true);
      
      // createDirectory需要两个参数：父目录路径和目录名称
      await createDirectory(currentPath, values.directoryName);
      
      message.success(t('fileManager.createDirectorySuccess'));
      onSuccess();
      onClose();
    } catch (error) {
      console.error('Failed to create directory:', error);
      message.error(
        error instanceof Error 
          ? error.message 
          : t('fileManager.createDirectoryFailed')
      );
    } finally {
      setLoading(false);
    }
  };

  // 使用建议
  const useSuggestion = (suggestion: string) => {
    form.setFieldsValue({ directoryName: suggestion });
  };

  // 验证目录名
  const validateDirectoryName = (_: any, value: string) => {
    if (!value || value.trim() === '') {
      return Promise.reject(new Error(t('fileManager.directoryNameRequired')));
    }

    // 检查是否包含非法字符
    const illegalChars = /[<>:"/\\|?*\x00-\x1F]/;
    if (illegalChars.test(value)) {
      return Promise.reject(new Error(t('fileManager.invalidDirectoryName')));
    }

    // 检查是否以点开头或结尾
    if (value.startsWith('.') || value.endsWith('.')) {
      return Promise.reject(new Error(t('fileManager.invalidDirectoryName')));
    }

    // 检查长度
    if (value.length > 255) {
      return Promise.reject(new Error(t('fileManager.directoryNameTooLong')));
    }

    return Promise.resolve();
  };

  return (
    <Modal
      title={
        <Space>
          <FolderAddOutlined />
          {t('fileManager.createDirectory')}
        </Space>
      }
      open={visible}
      onCancel={onClose}
      footer={null}
      width={500}
      destroyOnClose
    >
      <Space direction="vertical" size="middle" style={{ width: '100%' }}>
        {/* 当前路径显示 */}
        <Alert
          message={t('fileManager.createIn')}
          description={
            <Text code>
              {currentPath ? `~/.copaw/${currentPath}/` : '~/.copaw/'}
            </Text>
          }
          type="info"
          showIcon
        />

        {/* 表单 */}
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
          autoComplete="off"
        >
          <Form.Item
            name="directoryName"
            label={t('fileManager.directoryName')}
            rules={[
              { required: true, validator: validateDirectoryName }
            ]}
            extra={t('fileManager.directoryNameRules')}
          >
            <Input
              placeholder={t('fileManager.enterDirectoryName')}
              prefix={<FolderOutlined />}
              maxLength={255}
              allowClear
            />
          </Form.Item>

          {/* 建议 */}
          {suggestions.length > 0 && (
            <Form.Item label={t('fileManager.suggestions')}>
              <Space wrap>
                {suggestions.map((suggestion) => (
                  <Button
                    key={suggestion}
                    type="dashed"
                    size="small"
                    onClick={() => useSuggestion(suggestion)}
                  >
                    {suggestion}
                  </Button>
                ))}
                <Button
                  type="text"
                  size="small"
                  onClick={generateSuggestions}
                >
                  {t('fileManager.moreSuggestions')}
                </Button>
              </Space>
            </Form.Item>
          )}

          {/* 创建提示 */}
          <Alert
            message={t('fileManager.createDirectoryTipsTitle')}
            description={t('fileManager.createDirectoryTips')}
            type="info"
            showIcon
            style={{ marginBottom: 16 }}
          />

          {/* 操作按钮 */}
          <Form.Item style={{ marginBottom: 0, textAlign: 'right' }}>
            <Space>
              <Button onClick={onClose}>
                {t('common.cancel')}
              </Button>
              <Button
                type="primary"
                htmlType="submit"
                loading={loading}
                icon={<FolderAddOutlined />}
              >
                {t('fileManager.create')}
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Space>
    </Modal>
  );
};

export default CreateDirectoryModal;