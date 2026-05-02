/** 通用页面头部组件
 * 替换各页面中重复的标题行布局。
 * 支持图标、副标题、操作按钮、Badge 等多种组合。
 */

import { ReactNode } from 'react';
import { Box, Typography } from '@mui/material';
import { flexRowBetweenMb2 } from '../../styles/sxUtils';

interface PageHeaderProps {
  title: string;
  /** 右侧操作区域（按钮、Chip 等） */
  actions?: ReactNode;
  /** 标题前的图标 */
  icon?: ReactNode;
  /** 标题后的附加元素（如 Badge） */
  titleSuffix?: ReactNode;
  /** 附加说明文本（显示在标题旁边） */
  subtitle?: string;
}

export function PageHeader({ title, actions, icon, titleSuffix, subtitle }: PageHeaderProps) {
  return (
    <Box sx={flexRowBetweenMb2}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
        {icon}
        <Typography variant="h5" sx={{ fontWeight: 600 }}>
          {title}
        </Typography>
        {titleSuffix}
        {subtitle && (
          <Typography variant="body2" color="text.secondary">
            {subtitle}
          </Typography>
        )}
      </Box>
      {actions}
    </Box>
  );
}
