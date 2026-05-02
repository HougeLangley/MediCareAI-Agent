/** sx 样式工具函数
 * 封装前端最常见的重复 sx 模式，禁止散布硬编码样式。
 * 使用方式: import { flexRow, flexColumn, pageContainer } from '@/styles/sxUtils'
 */

import { SxProps, Theme } from '@mui/material/styles';

// ============================================================================
// 基础 Flex 布局
// ============================================================================

/** 水平居中排列 */
export const flexRow: SxProps<Theme> = {
  display: 'flex',
  alignItems: 'center',
};

/** 水平居中 + 左右分布 */
export const flexRowBetween: SxProps<Theme> = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
};

/** 水平居中 + 横向居中 */
export const flexRowCenter: SxProps<Theme> = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
};

/** 垂直居中排列 */
export const flexColumn: SxProps<Theme> = {
  display: 'flex',
  flexDirection: 'column',
};

// ============================================================================
// 常用组合（含间距/边距）
// ============================================================================

/** 水平居中 + 左右分布 + 底部间距 mb:2 */
export const flexRowBetweenMb2: SxProps<Theme> = {
  ...flexRowBetween,
  mb: 2,
};

/** 水平居中 + gap:1 */
export const flexRowGap1: SxProps<Theme> = {
  ...flexRow,
  gap: 1,
};

/** 水平居中 + gap:1 + mb:0.5 */
export const flexRowGap1Mb05: SxProps<Theme> = {
  ...flexRow,
  gap: 1,
  mb: 0.5,
};

/** 水平居中 + gap:1.5 */
export const flexRowGap15: SxProps<Theme> = {
  ...flexRow,
  gap: 1.5,
};

/** 水平居中 + gap:2 */
export const flexRowGap2: SxProps<Theme> = {
  ...flexRow,
  gap: 2,
};

/** 水平居中 + gap:0.5 */
export const flexRowGap05: SxProps<Theme> = {
  ...flexRow,
  gap: 0.5,
};

/** 水平居中 + gap:1 + mb:1 */
export const flexRowGap1Mb1: SxProps<Theme> = {
  ...flexRow,
  gap: 1,
  mb: 1,
};

/** 水平居中 + gap:0.5 + mb:0.5 */
export const flexRowGap05Mb05: SxProps<Theme> = {
  ...flexRow,
  gap: 0.5,
  mb: 0.5,
};

// ============================================================================
// 页面/容器
// ============================================================================

/** 页面根容器（自适应最小高度） */
export const pageContainer: SxProps<Theme> = {
  minHeight: '100vh',
  display: 'flex',
  flexDirection: 'column',
};

/** 页面居中容器（100vh 水平垂直居中） */
export const pageCenter: SxProps<Theme> = {
  minHeight: '100vh',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
};

/** 页面头部行（pt:3, pb:2, gap:1） */
export const pageHeader: SxProps<Theme> = {
  pt: 3,
  pb: 2,
  display: 'flex',
  alignItems: 'center',
  gap: 1,
};

// ============================================================================
// 卡片/组件
// ============================================================================

/** 主要卡片样式 */
export const cardStyle: SxProps<Theme> = {
  borderRadius: 3,
  boxShadow: '0 1px 4px rgba(38,50,56,0.08)',
};

/** 次要卡片样式 */
export const cardStyleSm: SxProps<Theme> = {
  borderRadius: 2,
  boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
};

/** 图标容器（圆角方形居中） */
export const iconBox = (size: number = 48): SxProps<Theme> => ({
  width: size,
  height: size,
  borderRadius: 2,
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
});

/** 搜索栏容器 */
export const searchBox: SxProps<Theme> = {
  display: 'flex',
  alignItems: 'center',
  gap: 1,
  mb: 2,
};
