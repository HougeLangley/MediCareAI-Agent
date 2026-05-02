import { Box, Typography, Avatar, Paper } from '@mui/material';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import PersonIcon from '@mui/icons-material/Person';
import type { ChatMessageItem } from '../types/agent';
import DiagnosisCard from './DiagnosisCard';

interface Props { message: ChatMessageItem; }

export default function ChatMessage({ message }: Props) {
  const isAgent = message.role === 'agent';
  const isSystem = message.role === 'system';

  if (isSystem) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', my: 1 }}>
        <Typography variant="caption" color="text.secondary" sx={{ fontStyle: 'italic' }}>{message.content}</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ display: 'flex', justifyContent: isAgent ? 'flex-start' : 'flex-end', gap: 1.5, mb: 2, px: 1 }}>
      {isAgent && (
        <Avatar sx={{ bgcolor: 'primary.main', width: 36, height: 36, mt: 0.5 }}>
          <SmartToyIcon sx={{ fontSize: 20 }} />
        </Avatar>
      )}

      <Box sx={{ maxWidth: '80%' }}>
        <Paper elevation={0} sx={{
          p: 1.5,
          borderRadius: isAgent ? '4px 16px 16px 16px' : '16px 4px 16px 16px',
          background: isAgent ? '#F5E6D3' : 'background.paper',
          border: isAgent ? 'none' : '1px solid #F5E6D3',
        }}>
          <Typography variant="body2" sx={{ color: 'text.primary', whiteSpace: 'pre-wrap', wordBreak: 'break-word', lineHeight: 1.6 }}>
            {message.content || (message.isStreaming ? '思考中...' : '')}
          </Typography>
        </Paper>

        {isAgent && message.structured && <DiagnosisCard report={message.structured} />}

        {isAgent && message.toolCalls && message.toolCalls.length > 0 && (
          <Box sx={{ mt: 1 }}>
            {message.toolCalls.map((tc, i) => (
              <Box key={i} sx={{ display: 'flex', alignItems: 'center', gap: 1, bgcolor: '#FFF8F0', border: '1px dashed #F5E6D3', borderRadius: 2, px: 1.5, py: 0.75, mb: 0.5 }}>
                <Typography variant="caption" color="text.secondary">🔧 {tc.tool}</Typography>
                {tc.result !== undefined && <Typography variant="caption" color="success.main">✅ 已完成</Typography>}
              </Box>
            ))}
          </Box>
        )}

        <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
          {message.timestamp.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}
        </Typography>
      </Box>

      {!isAgent && (
        <Avatar sx={{ bgcolor: 'primary.dark', width: 36, height: 36, mt: 0.5 }}>
          <PersonIcon sx={{ fontSize: 20 }} />
        </Avatar>
      )}
    </Box>
  );
}
