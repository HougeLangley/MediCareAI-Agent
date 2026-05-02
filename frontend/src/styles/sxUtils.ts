/** sx 样式工具函数
 * 封装前端最常见的重复 sx 模式，禁止散布硬编码样式。
 * 使用方式: import { flexRow, flexColumn, pageContainer } from '../../styles/sxUtils'
 */

// ============================================================================
// 基础 Flex 布局
// ============================================================================

/** 水平居中排列 */
export const flexRow = {
  display: 'flex' as const,
  alignItems: 'center' as const,
};

/** 水平居中 + 左右分布 */
export const flexRowBetween = {
  ...flexRow,
  justifyContent: 'space-between' as const,
};

/** 水平居中 + 横向居中 */
export const flexRowCenter = {
  ...flexRow,
  justifyContent: 'center' as const,
};

/** 垂直居中排列 */
export const flexColumn = {
  display: 'flex' as const,
  flexDirection: 'column' as const,
};

// ============================================================================
// 常用组合（含间距/边距）
// ============================================================================

/** 水平居中 + 左右分布 + 底部间距 mb:2 */
export const flexRowBetweenMb2 = {
  ...flexRowBetween,
  mb: 2,
};

/** 水平居中 + gap:1 */
export const flexRowGap1 = {
  ...flexRow,
  gap: 1,
};

/** 水平居中 + gap:1 + mb:0.5 */
export const flexRowGap1Mb05 = {
  ...flexRow,
  gap: 1,
  mb: 0.5,
};

/** 水平居中 + gap:1.5 */
export const flexRowGap15 = {
  ...flexRow,
  gap: 1.5,
};

/** 水平居中 + gap:2 */
export const flexRowGap2 = {
  ...flexRow,
  gap: 2,
};

/** 水平居中 + gap:0.5 */
export const flexRowGap05 = {
  ...flexRow,
  gap: 0.5,
};

/** 水平居中 + gap:1 + mb:1 */
export const flexRowGap1Mb1 = {
  ...flexRow,
  gap: 1,
  mb: 1,
};

/** 水平居中 + gap:0.5 + mb:0.5 */
export const flexRowGap05Mb05 = {
  ...flexRow,
  gap: 0.5,
  mb: 0.5,
};

// ============================================================================
// 页面/容器
// ============================================================================

/** 页面根容器（自适应最小高度） */
export const pageContainer = {
  minHeight: '100vh' as const,
  display: 'flex' as const,
  flexDirection: 'column' as const,
};

/** 页面居中容器（100vh 水平垂直居中） */
export const pageCenter = {
  minHeight: '100vh' as const,
  display: 'flex' as const,
  alignItems: 'center' as const,
  justifyContent: 'center' as const,
};

/** 页面头部行（pt:3, pb:2, gap:1） */
export const pageHeader = {
  pt: 3,
  pb: 2,
  display: 'flex' as const,
  alignItems: 'center' as const,
  gap: 1,
};

// ============================================================================
// 卡片/组件
// ============================================================================

/** 主要卡片样式 */
export const cardStyle = {
  borderRadius: 3,
  boxShadow: '0 1px 4px rgba(38,50,56,0.08)' as const,
};

/** 次要卡片样式 */
export const cardStyleSm = {
  borderRadius: 2,
  boxShadow: '0 1px 3px rgba(0,0,0,0.06)' as const,
};

/** 图标容器（圆角方形居中） */
export const iconBox = (size: number = 48) => ({
  width: size,
  height: size,
  borderRadius: 2,
  display: 'flex' as const,
  alignItems: 'center' as const,
  justifyContent: 'center' as const,
});

/** 搜索栏容器 */
export const searchBox = {
  ...flexRow,
  gap: 1,
  mb: 2,
};
