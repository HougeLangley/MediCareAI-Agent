import { Box, Typography, Avatar, Paper } from '@mui/material';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import PersonIcon from '@mui/icons-material/Person';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { ChatMessageItem } from '../types/agent';
import DiagnosisCard from './DiagnosisCard';
import AgentWorkflow from './AgentWorkflow';

interface Props { message: ChatMessageItem; }

const warmPrimary = '#E8956A';
const warmText = '#5C4033';

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
          <Box sx={{ color: 'text.primary', wordBreak: 'break-word', lineHeight: 1.6, '& > *:first-of-type': { mt: 0 }, '& > *:last-of-type': { mb: 0 } }}>
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                p: ({ children }) => <Typography variant="body2" sx={{ mb: 1, lineHeight: 1.6 }}>{children}</Typography>,
                h1: ({ children }) => <Typography variant="h6" sx={{ fontWeight: 700, color: warmText, mt: 1.5, mb: 0.75 }}>{children}</Typography>,
                h2: ({ children }) => <Typography variant="subtitle1" sx={{ fontWeight: 700, color: warmText, mt: 1.25, mb: 0.5 }}>{children}</Typography>,
                h3: ({ children }) => <Typography variant="subtitle2" sx={{ fontWeight: 700, color: warmText, mt: 1, mb: 0.5 }}>{children}</Typography>,
                strong: ({ children }) => <Box component="strong" sx={{ fontWeight: 700, color: warmPrimary }}>{children}</Box>,
                em: ({ children }) => <Box component="em" sx={{ fontStyle: 'italic', color: '#8B7355' }}>{children}</Box>,
                ul: ({ children }) => <Box component="ul" sx={{ pl: 2.5, mb: 1, '& li': { mb: 0.5, lineHeight: 1.6 } }}>{children}</Box>,
                ol: ({ children }) => <Box component="ol" sx={{ pl: 2.5, mb: 1, '& li': { mb: 0.5, lineHeight: 1.6 } }}>{children}</Box>,
                li: ({ children }) => <Box component="li">{children}</Box>,
                code: ({ children, className }) => {
                  const isInline = !className;
                  return (
                    <Box
                      component="code"
                      sx={{
                        fontFamily: 'monospace',
                        fontSize: '0.85em',
                        bgcolor: isInline ? 'rgba(232,149,106,0.12)' : '#2D2D2D',
                        color: isInline ? warmText : '#F5E6D3',
                        px: isInline ? 0.5 : 1.5,
                        py: isInline ? 0.25 : 1,
                        borderRadius: 1,
                        display: isInline ? 'inline' : 'block',
                        overflowX: 'auto',
                        whiteSpace: 'pre-wrap',
                        wordBreak: 'break-word',
                      }}
                    >
                      {children}
                    </Box>
                  );
                },
                pre: ({ children }) => (
                  <Box component="pre" sx={{ bgcolor: '#2D2D2D', p: 1.5, borderRadius: 1.5, overflowX: 'auto', mb: 1 }}>
                    {children}
                  </Box>
                ),
                blockquote: ({ children }) => (
                  <Box component="blockquote" sx={{ borderLeft: `3px solid ${warmPrimary}`, pl: 1.5, ml: 0, color: '#8B7355', fontStyle: 'italic', mb: 1 }}>
                    {children}
                  </Box>
                ),
                a: ({ children, href }) => (
                  <Box component="a" href={href} target="_blank" rel="noopener noreferrer" sx={{ color: warmPrimary, textDecoration: 'underline', '&:hover': { color: '#D4835A' } }}>
                    {children}
                  </Box>
                ),
                hr: () => <Box component="hr" sx={{ border: 'none', borderTop: '1px solid #F5E6D3', my: 1.5 }} />,
                table: ({ children }) => (
                  <Box component="table" sx={{ borderCollapse: 'collapse', width: '100%', mb: 1, fontSize: '0.875rem' }}>
                    {children}
                  </Box>
                ),
                thead: ({ children }) => <Box component="thead" sx={{ bgcolor: 'rgba(232,149,106,0.15)' }}>{children}</Box>,
                th: ({ children }) => (
                  <Box component="th" sx={{ border: '1px solid #F5E6D3', p: 0.75, textAlign: 'left', fontWeight: 700, color: warmText }}>
                    {children}
                  </Box>
                ),
                td: ({ children }) => (
                  <Box component="td" sx={{ border: '1px solid #F5E6D3', p: 0.75, color: 'text.primary' }}>
                    {children}
                  </Box>
                ),
              }}
            >
              {message.content || (message.isStreaming ? '思考中...' : '')}
            </ReactMarkdown>
          </Box>
        </Paper>

        {isAgent && message.structured && <DiagnosisCard report={message.structured} />}

        {isAgent && message.workflowSteps && message.workflowSteps.length > 0 && (
          <AgentWorkflow steps={message.workflowSteps} />
        )}

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
