import { useState, useRef } from 'react';
import { Box, TextField, IconButton, Button, Chip, Paper } from '@mui/material';
import SendIcon from '@mui/icons-material/Send';
import AttachFileIcon from '@mui/icons-material/AttachFile';
import ImageIcon from '@mui/icons-material/Image';
import MicIcon from '@mui/icons-material/Mic';
import StopIcon from '@mui/icons-material/Stop';

interface Props {
  onSend: (text: string) => void;
  disabled?: boolean;
  quickReplies?: string[];
  onQuickReply?: (text: string) => void;
}

export default function ChatInput({ onSend, disabled = false, quickReplies, onQuickReply }: Props) {
  const [text, setText] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleSend = () => {
    const trimmed = text.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setText('');
    inputRef.current?.focus();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <Box>
      {quickReplies && quickReplies.length > 0 && (
        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mb: 1.5, px: 2 }}>
          {quickReplies.map((reply) => (
            <Chip key={reply} label={reply} size="small" clickable onClick={() => onQuickReply?.(reply)}
              sx={{ bgcolor: '#FFF8F0', border: '1px solid #F5E6D3', color: 'text.primary', '&:hover': { bgcolor: '#F5E6D3', borderColor: 'primary.main' }, fontSize: 13, height: 28 }} />
          ))}
        </Box>
      )}

      <Paper elevation={2} sx={{ display: 'flex', alignItems: 'flex-end', gap: 1, p: 1.5, borderRadius: 3, border: '1px solid #F5E6D3', bgcolor: 'background.paper' }}>
        <IconButton size="small" sx={{ color: 'text.secondary' }} disabled={disabled}><AttachFileIcon fontSize="small" /></IconButton>
        <IconButton size="small" sx={{ color: 'text.secondary' }} disabled={disabled}><ImageIcon fontSize="small" /></IconButton>

        <TextField
          inputRef={inputRef}
          fullWidth
          multiline
          maxRows={4}
          placeholder={disabled ? '请稍候...' : '描述您的症状...'}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          variant="standard"
          slotProps={{
            input: {
              disableUnderline: true,
              sx: { fontSize: 15, color: 'text.primary', '&::placeholder': { color: 'text.secondary' } },
            },
          }}
        />

        <IconButton size="small" onClick={() => setIsRecording(!isRecording)} disabled={disabled}
          sx={{ color: isRecording ? 'error.main' : 'text.secondary' }}>
          {isRecording ? <StopIcon fontSize="small" /> : <MicIcon fontSize="small" />}
        </IconButton>

        <Button variant="contained" size="small" onClick={handleSend} disabled={disabled || !text.trim()}
          sx={{ minWidth: 40, width: 40, height: 40, borderRadius: '50%', p: 0, bgcolor: 'primary.main', '&:hover': { bgcolor: 'primary.dark' }, '&.Mui-disabled': { bgcolor: '#F5E6D3', color: 'text.secondary' } }}>
          <SendIcon sx={{ fontSize: 18 }} />
        </Button>
      </Paper>
    </Box>
  );
}
