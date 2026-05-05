import { useState } from 'react';
import { Box, Typography, Collapse, IconButton, Chip } from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import PsychologyIcon from '@mui/icons-material/Psychology';
import SwapHorizIcon from '@mui/icons-material/SwapHoriz';
import BuildIcon from '@mui/icons-material/Build';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';
import RadioButtonUncheckedIcon from '@mui/icons-material/RadioButtonUnchecked';
import type { WorkflowStep } from '../types/agent';

interface Props {
  steps: WorkflowStep[];
}

const warmPrimary = '#E8956A';
const warmLight = '#FFF8F0';
const warmBorder = '#F5E6D3';

function stepIcon(type: WorkflowStep['type'], status: WorkflowStep['status']) {
  if (status === 'error') return <ErrorIcon sx={{ fontSize: 16, color: 'error.main' }} />;
  if (status === 'done') return <CheckCircleIcon sx={{ fontSize: 16, color: 'success.main' }} />;

  switch (type) {
    case 'intent': return <PsychologyIcon sx={{ fontSize: 16, color: warmPrimary }} />;
    case 'agent_switch': return <SwapHorizIcon sx={{ fontSize: 16, color: warmPrimary }} />;
    case 'tool_call': return <BuildIcon sx={{ fontSize: 16, color: warmPrimary }} />;
    case 'tool_result': return <CheckCircleIcon sx={{ fontSize: 16, color: 'success.main' }} />;
    case 'thinking': return <PsychologyIcon sx={{ fontSize: 16, color: '#8B7355' }} />;
    case 'complete': return <CheckCircleIcon sx={{ fontSize: 16, color: 'success.main' }} />;
    default: return <RadioButtonUncheckedIcon sx={{ fontSize: 16, color: '#8B7355' }} />;
  }
}

function stepLabel(type: WorkflowStep['type']): string {
  switch (type) {
    case 'intent': return '意图识别';
    case 'agent_switch': return 'Agent 切换';
    case 'tool_call': return '工具调用';
    case 'tool_result': return '工具结果';
    case 'thinking': return '思考分析';
    case 'complete': return '完成';
    default: return type;
  }
}

export default function AgentWorkflow({ steps }: Props) {
  const [expanded, setExpanded] = useState(true);

  if (!steps || steps.length === 0) return null;

  const allDone = steps.every(s => s.status === 'done' || s.status === 'error');

  return (
    <Box sx={{ mt: 1, mb: 0.5 }}>
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          gap: 1,
          cursor: 'pointer',
          py: 0.5,
          px: 1,
          borderRadius: 1,
          '&:hover': { bgcolor: warmLight },
        }}
        onClick={() => setExpanded(!expanded)}
      >
        <Chip
          size="small"
          label={allDone ? '✅ 多 Agent 协作完成' : '🔄 多 Agent 协作中...'}
          sx={{
            bgcolor: allDone ? 'rgba(76,175,80,0.1)' : 'rgba(232,149,106,0.12)',
            color: allDone ? '#2E7D32' : warmPrimary,
            fontSize: '0.7rem',
            height: 22,
            fontWeight: 600,
          }}
        />
        <Typography variant="caption" color="text.secondary" sx={{ flex: 1, fontSize: '0.7rem' }}>
          {steps.length} 个步骤
        </Typography>
        <IconButton size="small" sx={{ p: 0.25 }}>
          {expanded ? <ExpandLessIcon sx={{ fontSize: 16 }} /> : <ExpandMoreIcon sx={{ fontSize: 16 }} />}
        </IconButton>
      </Box>

      <Collapse in={expanded}>
        <Box sx={{ pl: 2, pt: 0.5, pb: 0.5 }}>
          {steps.map((step, index) => (
            <Box key={step.id} sx={{ display: 'flex', position: 'relative' }}>
              {/* 时间线 */}
              {index < steps.length - 1 && (
                <Box
                  sx={{
                    position: 'absolute',
                    left: 7,
                    top: 20,
                    bottom: -4,
                    width: 2,
                    bgcolor: step.status === 'done' ? 'rgba(76,175,80,0.3)' : warmBorder,
                    borderRadius: 1,
                  }}
                />
              )}

              {/* 图标 */}
              <Box
                sx={{
                  width: 16,
                  height: 16,
                  borderRadius: '50%',
                  bgcolor: step.status === 'done' ? 'rgba(76,175,80,0.1)' : warmLight,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  mt: 0.5,
                  mr: 1,
                  flexShrink: 0,
                  border: `1px solid ${step.status === 'done' ? 'rgba(76,175,80,0.3)' : warmBorder}`,
                }}
              >
                {stepIcon(step.type, step.status)}
              </Box>

              {/* 内容 */}
              <Box sx={{ flex: 1, pb: 1 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
                  <Typography variant="caption" sx={{ fontWeight: 600, color: warmPrimary, fontSize: '0.7rem' }}>
                    {stepLabel(step.type)}
                  </Typography>
                  {step.status === 'running' && (
                    <Box
                      sx={{
                        width: 8,
                        height: 8,
                        borderRadius: '50%',
                        bgcolor: warmPrimary,
                        animation: 'pulse 1.5s infinite',
                        '@keyframes pulse': {
                          '0%': { opacity: 1, transform: 'scale(1)' },
                          '50%': { opacity: 0.4, transform: 'scale(0.8)' },
                          '100%': { opacity: 1, transform: 'scale(1)' },
                        },
                      }}
                    />
                  )}
                </Box>
                <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem', lineHeight: 1.4, display: 'block' }}>
                  {step.title}
                </Typography>
                {step.detail && (
                  <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.65rem', lineHeight: 1.4, display: 'block', mt: 0.25, opacity: 0.8 }}>
                    {step.detail}
                  </Typography>
                )}
                {step.toolName && (
                  <Chip
                    size="small"
                    label={`🔧 ${step.toolName}`}
                    sx={{ mt: 0.25, height: 18, fontSize: '0.6rem', bgcolor: warmLight, color: '#8B7355', border: `1px dashed ${warmBorder}` }}
                  />
                )}
              </Box>
            </Box>
          ))}
        </Box>
      </Collapse>
    </Box>
  );
}
