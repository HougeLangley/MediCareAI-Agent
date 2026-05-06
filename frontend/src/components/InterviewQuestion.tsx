import { useState } from 'react';
import { Box, Typography, Chip, TextField, Button } from '@mui/material';
import type { InterviewQuestion } from '../types/agent';

interface Props {
  question: InterviewQuestion;
  onAnswer: (questionId: string, answer: string) => void;
  disabled?: boolean;
}

export default function InterviewQuestion({ question, onAnswer, disabled = false }: Props) {
  const [textAnswer, setTextAnswer] = useState('');
  const [answered, setAnswered] = useState(false);

  const handleChoice = (option: string) => {
    if (disabled || answered) return;
    setAnswered(true);
    onAnswer(question.question_id, option);
  };

  const handleTextSubmit = () => {
    const trimmed = textAnswer.trim();
    if (!trimmed || disabled || answered) return;
    setAnswered(true);
    onAnswer(question.question_id, trimmed);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleTextSubmit();
    }
  };

  return (
    <Box sx={{ mt: 1.5, mb: 1 }}>
      <Typography variant="subtitle2" sx={{ fontWeight: 600, color: '#5C4033', mb: 1 }}>
        {question.question}
      </Typography>

      {question.hint && (
        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1 }}>
          {question.hint}
        </Typography>
      )}

      {question.type === 'choice' && question.options && (
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
          {question.options.map((option) => (
            <Chip
              key={option}
              label={option}
              clickable
              disabled={disabled || answered}
              onClick={() => handleChoice(option)}
              sx={{
                bgcolor: answered ? '#F5E6D3' : '#FFF8F0',
                border: '1px solid #F5E6D3',
                color: '#5C4033',
                fontWeight: 500,
                '&:hover': {
                  bgcolor: '#F5E6D3',
                  borderColor: '#E8956A',
                },
                '&.Mui-disabled': {
                  opacity: answered ? 0.7 : 0.4,
                  bgcolor: '#FFF8F0',
                },
              }}
            />
          ))}
          {question.allow_skip && (
            <Chip
              label="跳过"
              clickable
              disabled={disabled || answered}
              onClick={() => handleChoice('skipped')}
              sx={{
                bgcolor: 'transparent',
                border: '1px dashed #C4A484',
                color: '#8B7355',
                '&:hover': {
                  bgcolor: '#FFF8F0',
                  borderColor: '#E8956A',
                },
              }}
            />
          )}
        </Box>
      )}

      {question.type === 'text' && (
        <Box sx={{ display: 'flex', gap: 1, alignItems: 'flex-end' }}>
          <TextField
            fullWidth
            size="small"
            placeholder="请输入您的回答..."
            value={textAnswer}
            onChange={(e) => setTextAnswer(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={disabled || answered}
            variant="outlined"
            sx={{
              '& .MuiOutlinedInput-root': {
                bgcolor: '#FFF8F0',
                borderRadius: 2,
                fontSize: 14,
              },
            }}
          />
          <Button
            variant="contained"
            size="small"
            onClick={handleTextSubmit}
            disabled={disabled || answered || !textAnswer.trim()}
            sx={{
              minWidth: 64,
              borderRadius: 2,
              bgcolor: '#E8956A',
              '&:hover': { bgcolor: '#D4835A' },
              '&.Mui-disabled': { bgcolor: '#F5E6D3', color: '#8B7355' },
            }}
          >
            回答
          </Button>
        </Box>
      )}

      {answered && (
        <Typography variant="caption" color="success.main" sx={{ mt: 0.5, display: 'block' }}>
          ✅ 已提交
        </Typography>
      )}
    </Box>
  );
}
