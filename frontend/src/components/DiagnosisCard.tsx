import { useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Chip,
  Collapse,
  IconButton,
  Divider,
  Stack,
  Button,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import LocalHospitalIcon from '@mui/icons-material/LocalHospital';
import ScienceIcon from '@mui/icons-material/Science';
import MedicationIcon from '@mui/icons-material/Medication';
import EventNoteIcon from '@mui/icons-material/EventNote';
import type { DiagnosisReport } from '../types/agent';

interface Props { report: DiagnosisReport; }

function ConfidenceStars({ level }: { level: string }) {
  const count = level === 'high' ? 5 : level === 'medium' ? 3 : 1;
  return (
    <Box sx={{ color: '#FFB300', fontSize: 14 }}>
      {'⭐'.repeat(count)}{'☆'.repeat(5 - count)}
    </Box>
  );
}

export default function DiagnosisCard({ report }: Props) {
  const [expanded, setExpanded] = useState(true);

  return (
    <Card sx={{ mt: 1.5, borderLeft: '4px solid #E8956A', background: '#FFF8F0', '&:hover': { boxShadow: '0 4px 16px rgba(92,64,51,0.1)' }, transition: 'box-shadow 0.2s' }}>
      <CardContent sx={{ pb: 1 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <LocalHospitalIcon sx={{ color: '#E8956A', fontSize: 20 }} />
            <Typography variant="subtitle1" sx={{ fontWeight: 600, color: '#5C4033' }}>诊断报告</Typography>
          </Box>
          <IconButton size="small" onClick={() => setExpanded(!expanded)}>
            {expanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
          </IconButton>
        </Box>

        <Collapse in={expanded}>
          <Box sx={{ mb: 2 }}>
            <Typography variant="body2" color="text.secondary" gutterBottom>初步诊断</Typography>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, flexWrap: 'wrap' }}>
              <Typography variant="h6" sx={{ fontWeight: 600, color: '#E8956A' }}>{report.primary_diagnosis}</Typography>
              {report.icd11_code && (
                <Chip label={report.icd11_code} size="small" variant="outlined" sx={{ borderColor: '#F5E6D3', color: '#8B7355' }} />
              )}
            </Box>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 0.5 }}>
              <Typography variant="body2" color="text.secondary">置信度:</Typography>
              <ConfidenceStars level={report.confidence} />
              <Chip label={report.confidence === 'high' ? '高' : report.confidence === 'medium' ? '中' : '低'} size="small"
                color={report.confidence === 'high' ? 'success' : report.confidence === 'medium' ? 'warning' : 'error'}
                sx={{ height: 20, fontSize: 12 }} />
            </Box>
          </Box>

          {report.differential_diagnoses && report.differential_diagnoses.length > 0 && (
            <Box sx={{ mb: 2 }}>
              <Typography variant="body2" color="text.secondary" gutterBottom>鉴别诊断</Typography>
              <Stack spacing={1}>
                {report.differential_diagnoses.map((d, i) => (
                  <Box key={i} sx={{ bgcolor: '#FFFFFF', p: 1.5, borderRadius: 2, border: '1px solid #F5E6D3' }}>
                    <Typography variant="body2" sx={{ fontWeight: 500 }}>{d.diagnosis} <span style={{ color: '#8B7355', fontSize: 12 }}>({d.icd11_code})</span></Typography>
                    <Typography variant="caption" color="text.secondary">{d.reasoning}</Typography>
                  </Box>
                ))}
              </Stack>
            </Box>
          )}

          {report.recommended_exams && report.recommended_exams.length > 0 && (
            <Box sx={{ mb: 2 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                <ScienceIcon sx={{ color: '#8B7355', fontSize: 16 }} />
                <Typography variant="body2" sx={{ fontWeight: 500, color: '#5C4033' }}>建议检查</Typography>
              </Box>
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                {report.recommended_exams.map((exam, i) => (
                  <Chip key={i} label={exam} size="small" sx={{ bgcolor: '#F5E6D3', color: '#5C4033' }} />
                ))}
              </Box>
            </Box>
          )}

          {report.treatment_suggestions && report.treatment_suggestions.length > 0 && (
            <Box sx={{ mb: 2 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                <MedicationIcon sx={{ color: '#8B7355', fontSize: 16 }} />
                <Typography variant="body2" sx={{ fontWeight: 500, color: '#5C4033' }}>治疗建议</Typography>
              </Box>
              <ul style={{ margin: 0, paddingLeft: 20 }}>
                {report.treatment_suggestions.map((s, i) => (
                  <li key={i}><Typography variant="body2" sx={{ color: '#5C4033' }}>{s}</Typography></li>
                ))}
              </ul>
            </Box>
          )}

          {report.follow_up_plan && (
            <Box sx={{ mb: 2 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                <EventNoteIcon sx={{ color: '#8B7355', fontSize: 16 }} />
                <Typography variant="body2" sx={{ fontWeight: 500, color: '#5C4033' }}>随访计划</Typography>
              </Box>
              <Typography variant="body2" sx={{ color: '#5C4033', bgcolor: '#FFFFFF', p: 1.5, borderRadius: 2 }}>{report.follow_up_plan}</Typography>
            </Box>
          )}

          {(report.red_flags && report.red_flags.length > 0) || report.referral_needed ? (
            <>
              <Divider sx={{ my: 1.5, borderColor: '#F5E6D3' }} />
              <Box>
                {report.red_flags && report.red_flags.length > 0 && (
                  <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1, mb: 1 }}>
                    <WarningAmberIcon sx={{ color: '#E57373', fontSize: 18, mt: 0.2 }} />
                    <Box>
                      <Typography variant="body2" sx={{ fontWeight: 500, color: '#E57373' }}>警告信号</Typography>
                      {report.red_flags.map((flag, i) => (
                        <Typography key={i} variant="body2" sx={{ color: '#E57373', fontSize: 13 }}>• {flag}</Typography>
                      ))}
                    </Box>
                  </Box>
                )}
                {report.referral_needed && (
                  <Button size="small" variant="contained" color="error" startIcon={<LocalHospitalIcon />} sx={{ borderRadius: 2, textTransform: 'none' }}>
                    建议转诊: {report.referral_reason || '请尽早就医'}
                  </Button>
                )}
              </Box>
            </>
          ) : null}
        </Collapse>
      </CardContent>
    </Card>
  );
}
